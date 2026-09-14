# Precompute Architecture Pattern

Detailed reference for the three-tier precompute pattern: expensive computation runs via CLI/cron, results persist in Postgres + Redis, API reads from cache only.

## When to use

- Monte Carlo simulations, probabilistic modeling
- ML inference / LLM enrichment pipelines
- Large aggregation queries that change slowly (daily or less)
- Any feature where the user says "precompute as much as possible"

## Architecture

```
┌─────────────────┐
│  Trigger: CLI    │
│  `compute X`     │
└────────┬────────┘
         │
┌────────▼────────┐
│  Compute Engine  │
│  (N iterations)  │
└────────┬────────┘
         │
    ┌────▼────┐
    │ Postgres │ (durable, queryable)
    └────┬────┘
         │ (write-through)
    ┌────▼────┐
    │  Redis   │ (hot, <1ms reads)
    └────┬────┘
         │
    ┌────▼────┐
    │ API read │ (no computation)
    └─────────┘
```

## DB table design

Each precomputed result type gets its own table. Columns include:

- Entity identifiers (sport, team_id, game_id, etc.)
- `computed_at` timestamp (ISO format)
- `iterations` or equivalent count
- Distribution stats (mean, std, percentiles p5/p25/p50/p75/p95)
- Derived probabilities (playoff odds, upset pct, etc.)

PK: composite of entity identifiers. Upsert on each run.

## Redis key schema

| Key pattern | TTL | Content |
|-------------|-----|---------|
| `prefix:entities:{scope}` | 24h | JSON array of all entities for scope |
| `prefix:entity:{scope}:{id}` | 24h | JSON object — single entity |
| `prefix:calibration:{scope}` | 72h | JSON object — infrequently changing results |
| `prefix:status:{scope}` | 24h | JSON object — `{computed_at, iterations, counts}` |

TTL rationale: compute runs daily → 24h is always fresh. Calibration changes rarely → 72h. If compute stops running, Redis keys expire and API degrades gracefully.

## Cache service implementation

```python
# src/services/cache.py
import json
import os
from typing import Any

_redis = None

def get_redis():
    """Connection factory. Returns None if REDIS_URL not set (local dev)."""
    global _redis
    if _redis is None and os.environ.get('REDIS_URL'):
        try:
            import redis
            _redis = redis.from_url(os.environ['REDIS_URL'], decode_responses=True)
            _redis.ping()  # verify connection
        except Exception:
            _redis = None  # graceful no-op
    return _redis

def cache_get(key: str) -> Any | None:
    """Get from Redis. Returns None on miss or Redis unavailable."""
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None

def cache_set(key: str, data: Any, ttl_seconds: int) -> None:
    """Set in Redis with TTL. No-op if Redis unavailable."""
    r = get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl_seconds, json.dumps(data))
    except Exception:
        pass

def cache_delete_prefix(prefix: str) -> None:
    """Delete all keys matching prefix*. Used for full replace."""
    r = get_redis()
    if not r:
        return
    try:
        for key in r.scan_iter(f"{prefix}*"):
            r.delete(key)
    except Exception:
        pass
```

Key principles:
- Every operation wrapped in try/catch — failure returns None, never throws
- No REDIS_URL → all functions no-op → API reads Postgres directly
- `cache_delete_prefix` for full replace before writing new results

## API read path

```python
async def get_mc_data(sport: str):
    """Three-tier read: Redis → Postgres → None (fallback to deterministic)"""
    # Tier 1: Redis hot cache
    cached = cache_get(f"mc:teams:{sport}")
    if cached:
        return cached
    
    # Tier 2: Postgres warm storage
    rows = load_mc_team_season(sport)  # from corpus service
    if rows:
        cache_set(f"mc:teams:{sport}", rows, ttl_seconds=86400)  # backfill Redis
        return rows
    
    # Tier 3: No precomputed data → return None
    # Caller falls back to deterministic computation
    return None
```

## CLI compute trigger

```python
# In cli.py
@cli.command()
@click.argument('sport')
@click.option('--iterations', default=1000)
def mc_simulate(sport, iterations):
    """Run Monte Carlo simulation and persist results."""
    engine = MonteCarloEngine(sport, iterations=iterations)
    results = engine.run()
    
    # Write Postgres (durable)
    upsert_mc_team_season(sport, results['teams'])
    upsert_mc_game_dist(sport, results['games'])
    
    # Write Redis (hot cache, write-through)
    cache_delete_prefix(f"mc:")  # full replace
    cache_set(f"mc:teams:{sport}", results['teams'], 86400)
    cache_set(f"mc:games:{sport}", results['games'], 86400)
    cache_set(f"mc:status:{sport}", {
        'computed_at': results['computed_at'],
        'iterations': iterations,
        'team_count': len(results['teams']),
        'game_count': len(results['games']),
    }, 86400)
    
    print(f"✓ {sport}: {iterations} iterations, {len(results['teams'])} teams, {len(results['games'])} games")
```

## Graceful degradation checklist

- [ ] API returns current deterministic results when no precomputed data exists
- [ ] Frontend works identically when MC fields are null/missing
- [ ] Redis unavailable → API reads Postgres directly, no errors
- [ ] Postgres table empty → API returns deterministic fallback
- [ ] Response includes `last_computed_at` so frontend can show staleness

## Staleness handling

- **Redis TTL** is the primary staleness guard (24h default)
- **API response** includes `last_computed_at` timestamp
- **Dashboard** shows "Last updated X hours ago" when timestamp present
- **Cache invalidation** is full replace per compute run — no incremental complexity
- If compute stops, Redis empties in 24h, Postgres data stays but gets stale → API shows old timestamp → user knows

## Worked example

The ELO Scenario Lab Monte Carlo plan uses this pattern:

| Component | Detail |
|-----------|--------|
| Compute | `MonteCarloEngine` — 1000 iterations per sport |
| Trigger | `python -m src.cli mc-simulate mlb --iterations 1000` |
| Postgres tables | `mc_team_season` (30 rows/sport), `mc_game_dist` (upcoming games), `mc_calibration` (backtest results) |
| Redis keys | `mc:teams:mlb`, `mc:games:mlb`, `mc:calibration:mlb`, `mc:status:mlb` |
| API read | Scenarios endpoint → `cache_get("mc:games:mlb")` → augment existing injury scenarios with MC confidence intervals |
| Fallback | No MC data → serve current deterministic injury scenarios unchanged |
