# Response Cache Middleware — Reference Implementation

This is the deep-dive for the response cache pattern documented in
`api-performance-optimization`. It's the version that was measured end-to-end
on a production FastAPI service in June 2026. Reproduce with the
`scripts/perf_baseline.py` harness.

## Architecture

```
Browser
  │
  │ GET /api/ratings?sport=mlb
  │ If-None-Match: W/"9cef20e68b8f59c6a7c5"
  ▼
CORS Middleware        ← must be FIRST (short-circuits OPTIONS preflights)
  │
ResponseCacheMiddleware
  │
  ├── _should_bypass(path, method) → passthrough if write/auth/admin/etc
  │
  ├── if If-None-Match present:
  │     ├── LRU hit + etag match → 304 + ETag (sub-ms server, ~RTT client)
  │     └── Redis hit + etag match → 304 + ETag
  │
  ├── LRU hit (body) → 200 + body + X-Cache: HIT-LRU
  │
  ├── Redis hit (body) → 200 + body + X-Cache: HIT-REDIS (+ promote to LRU)
  │
  ├── MISS → call_next(request) → store in LRU + Redis (if body ≥ 200B)
  │         → 200 + body + ETag + Cache-Control + X-Cache: MISS
  │
FastAPI route
  │
Postgres / Redis (existing) / Python pipelines
```

## Key Implementation Decisions

### 1. Two-tier storage (LRU + Redis)

The LRU is the read-through accelerator — sub-microsecond lookups, no network.
Redis is the cross-process write-through so multi-worker deploys share cache.

Order of lookup in `dispatch`:
1. LRU (`_lru.get(cache_key)`)
2. Redis (`cache_mod.cache_get(redis_key)`)
3. Call the route, populate both

This gives the lowest latency on warm hits while still sharing across workers.

### 2. Cache key with sorted query string

```python
def _normalize_query(qs: str) -> str:
    pairs = []
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            pairs.append((k, v))
        else:
            pairs.append((part, ""))
    pairs.sort()
    return "&".join(f"{k}={v}" for k, v in pairs)
```

Without this, `/api/ratings?sport=mlb&page=1` and `/api/ratings?page=1&sport=mlb` produce different cache keys, splitting the cache and reducing hit rate.

### 3. ETag: weak, SHA1, truncated

```python
def _etag_of(body: bytes) -> str:
    return 'W/"' + hashlib.sha1(body).hexdigest()[:20] + '"'
```

Weak ETag (`W/"..."`) is correct for JSON responses where the body is
semantically equivalent across cache windows but not byte-identical.
20 hex chars = 80 bits; collision probability is negligible at the body
sizes we serve (8KB-1.1MB).

### 4. Bypass rules (explicit, not implicit)

```python
_NEVER_CACHE_PATH_PREFIXES = (
    "/api/auth/",          # login, register, logout, me — user-scoped writes
    "/api/admin/",         # state-changing
    "/api/pipeline/",      # pipeline run/progress
    "/api/calibration/",   # job lifecycle
    "/api/teams/",         # per-team history varies by team
    "/api/scenarios",      # heavy, volatile (depends on injury state)
    "/api/market-odds",    # live data
    "/api/health",         # always live
)
```

The check runs BEFORE the cache key generation. Otherwise you'd generate
keys for `/api/auth/login` that never get re-hit but still pollute the LRU.

### 5. Per-route TTL table

```python
_ROUTE_TTLS = {
    "/api/ratings": 60,           # pipeline runs at 2AM; doesn't change mid-day
    "/api/teams": 60,
    "/api/divergence": 5,         # shifts with new MC data
    "/api/schedule/mlb": 5,
    "/api/playoffs/mlb": 30,
}
```

Sport-scoped schedules are listed individually because the URL path is
`/api/schedule/{sport}`. If you generalize to all sports, the routing
key becomes the path prefix; the 5s TTL applies.

For routes not in the table, `_ttl_for(path)` returns `DEFAULT_TTL_SECONDS = 5`.
That's a safe default — short enough that stale data isn't user-visible for
long, long enough that rapid nav clicks hit the cache.

### 6. Bodies < 200 bytes skip Redis

```python
if len(body) >= 200:
    cache_mod.cache_set(redis_key, entry, ttl=max_age)
```

A 50-byte JSON + SET round-trip + serialization cost more than just
serving the response. The LRU still caches tiny bodies (memory is cheap);
only the cross-process layer is skipped.

### 7. Cache-Control: private, max-age=N (not public)

Even though responses are sport-scoped (same for every user), `private`
keeps intermediaries (Railway proxy, future CDN) from caching
user-bearing data by accident. The browser still honors the max-age
for the user's own session — page-to-page nav within 5s is instant.

## Test Patterns That Caught Real Bugs

### Bug: `startswith` vs glob in the mock

The first test of `clear_cache()` was failing. The mock was:
```python
def _delete_pattern(prefix):
    keys = [k for k in fake_store if k.startswith(prefix)]
    for k in keys: del fake_store[k]
    return len(keys)
```

But the call was `cache_mod.cache_delete_pattern("resp:*")` — and
`startswith("resp:*")` checks for the literal `*` character, not a glob.

The real Redis function does `SCAN MATCH {prefix}*` (with the `*`
appended) and uses glob semantics. The mock must do the same:

```python
import fnmatch
def _delete_pattern(prefix):
    glob = f"{prefix}*"
    keys = [k for k in fake_store if fnmatch.fnmatchcase(k, glob)]
    for k in keys: del fake_store[k]
    return len(keys)
```

The bug would have shipped to production, where `clear-cache` from
the admin panel would have silently no-oped.

### Bug: tests that depended on every response hitting Redis

The first version of the response-cache tests used small (~70 byte)
response bodies and asserted that they were in both LRU and Redis.
After adding the "skip Redis for tiny bodies" optimization, those
tests failed. The fix was to use a larger body in the test that
specifically needed Redis:

```python
@app.get("/api/big")
def big():
    return {"data": "x" * 1000}  # 1KB+ body, clears the 200-byte threshold
```

Tests for LRU behavior (which is always populated) can use small bodies.
Tests for Redis promotion need bodies above the threshold.

## Measured Results (June 2026, Production)

Baseline (no cache): `/tmp/perf_prod.json`
After cache + GZip: `/tmp/perf_after.json`

| Endpoint | Baseline p95 | After p95 | Speedup |
|---|---|---|---|
| `/api/schedule/mlb` | 4,181ms | 397ms | **10.5x** |
| `/api/ratings` | 539ms | 209ms | 2.6x |
| `/api/divergence` | 564ms | 190ms | 3.0x |
| `/api/teams` | 561ms | 215ms | 2.6x |
| `/api/playoffs/mlb` | 585ms | 185ms | 3.2x |
| `/api/scenarios` (bypassed) | 655ms | 768ms | unchanged |

The 2-3x wins on the small endpoints are bounded by RTT to Railway
from the harness (US-East → Railway US-Central). The 10.5x on schedule
is the genuine server-side win — that endpoint had a 3.5s cold path
that the cache eliminated.

GZip additionally cuts wire size:
- `/api/schedule/mlb`: 1,127,668 B → 254,557 B (**4.4x**)
- `/api/scenarios`: 291 KB → 12.8 KB (**~22x**)

## Pitfalls (the things that bit us)

1. **Harness RTT dominates warm p95**: A 200ms "warm p95" measured from
   a US-East harness to a US-Central Railway app is dominated by network
   RTT, not server work. Verify with `X-Cache: HIT-LRU` on warm calls;
   if the server is returning from cache in <1ms, the harness is just
   measuring RTT. Real users on the same network will see <50ms.

2. **Cold cache first call is the truth**: The very first call to a
   cold endpoint runs the full pipeline (4,000ms+ for schedule/mlb).
   The cache makes that work happen once per TTL window, not once per
   request. That's the win.

3. **Cache middleware must be installed AFTER CORS**: CORS short-
   circuits OPTIONS preflights. If the response cache is first, the
   X-Cache / ETag headers may not make it through the CORS pass.

4. **Be ruthlessly honest about bypass rules**: A cache that serves a
   5-minute-stale `/api/auth/me` is a security incident. Default to
   bypass for user-scoped data, writes, and admin endpoints.

5. **Tests must mock the real `cache_delete_pattern` glob semantics**,
   not `startswith`. Use `fnmatch.fnmatchcase(k, f"{prefix}*")`.

6. **The conditional GET path runs BEFORE the cache hit check** so that
   a client with a fresh ETag gets 304 + empty body even if the LRU
   has been wiped (e.g. across worker processes).
