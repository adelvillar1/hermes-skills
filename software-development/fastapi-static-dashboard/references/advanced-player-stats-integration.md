# Advanced Player Stats Integration for FastAPI Dashboards

Integrating advanced player statistics (WAR, OPS, ERA, WHIP, fielding metrics) into sports prediction pipelines and dashboards.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  MLB Stats  │────▶│  WAR Proxy   │────▶│  Team-Level │
│   API       │     │  Computation │     │ Aggregation │
│ (hitting/   │     │  (per player)│     │  (per team) │
│  pitching/  │     └──────────────┘     └──────┬──────┘
│  fielding)  │                                 │
└─────────────┘                                 ▼
                                         ┌─────────────┐
                                         │  Probability │
                                         │  Adjustment  │
                                         │  (WAR diff)  │
                                         └─────────────┘
```

## MLB Stats API Endpoints

The MLB Stats API (`statsapi.mlb.com`) provides season-level stats per player:

```
GET /api/v1/stats?stats=season&group=hitting&playerPool=all&season=2026&limit=1000
GET /api/v1/stats?stats=season&group=pitching&playerPool=all&season=2026&limit=1000
GET /api/v1/stats?stats=season&group=fielding&playerPool=all&season=2026&limit=1000
```

### Response Structure

Each endpoint returns `stats[0].splits[]` where each split contains:
- `player.id`, `player.fullName` — player identity
- `team.id` — team affiliation
- `stat` — the actual statistics dict

### Hitting Stats Available

```json
{
  "gamesPlayed": 42,
  "avg": ".312",
  "obp": ".405",
  "slg": ".589",
  "ops": ".994",
  "homeRuns": 15,
  "rbi": 48,
  "runs": 52,
  "hits": 78,
  "doubles": 18,
  "triples": 2,
  "strikeOuts": 45,
  "baseOnBalls": 32,
  "stolenBases": 8,
  "caughtStealing": 2,
  "plateAppearances": 185,
  "atBats": 150,
  "totalBases": 88
}
```

### Pitching Stats Available

```json
{
  "gamesPlayed": 12,
  "gamesStarted": 12,
  "wins": 7,
  "losses": 3,
  "era": "2.85",
  "whip": "1.08",
  "inningsPitched": "72.2",
  "strikeOuts": 89,
  "baseOnBalls": 18,
  "hits": 58,
  "homeRuns": 8,
  "saves": 0,
  "holds": 0
}
```

### Fielding Stats Available

```json
{
  "gamesPlayed": 42,
  "gamesStarted": 40,
  "innings": "342.0",
  "putOuts": 245,
  "assists": 112,
  "errors": 3,
  "doublePlays": 28,
  "triplePlays": 0,
  "fielding": ".992"
}
```

## WAR Proxy Computation

Since the MLB Stats API doesn't provide fWAR, bWAR, or oWAR directly, compute a simplified WAR-like proxy:

### Hitting WAR Proxy

```python
def _compute_hitting_war(stat: dict) -> float:
    ops = float(stat.get("ops", ".000") or ".000")
    if ops == 0.0:  # Handle "-.--" placeholder
        return 0.0
    games = stat.get("gamesPlayed", 0)
    runs = stat.get("runs", 0)
    rbi = stat.get("rbi", 0)
    # Normalize to ~0-10 WAR scale
    return round((ops - 0.6) * 15 + (runs + rbi) * 0.02 + games * 0.005, 2)
```

**Formula rationale:**
- OPS is the strongest single predictor of offensive value
- `(OPS - 0.6)` centers around replacement level (~0.600 OPS)
- `* 15` scales to roughly 0-10 WAR range for full seasons
- Runs + RBI capture run production beyond just OPS
- Games played factor accounts for playing time

### Pitching WAR Proxy

```python
def _compute_pitching_war(stat: dict) -> float:
    era_raw = stat.get("era", "0.00") or "0.00"
    era = float(era_raw) if era_raw != "-.--" else 5.0
    ip_raw = stat.get("inningsPitched", "0.0") or "0.0"
    ip = float(ip_raw) if ip_raw != "-.--" else 0.0
    so = stat.get("strikeOuts", 0)
    # Lower ERA = higher WAR
    era_component = max(0, (5.0 - era) * 0.5)
    return round(era_component + ip * 0.03 + so * 0.002, 2)
```

**Formula rationale:**
- ERA component: 5.00 is roughly replacement level; each run below = +0.5 WAR
- Innings pitched: volume matters — each IP ≈ +0.03 WAR
- Strikeouts: each K ≈ +0.002 WAR (skill indicator)

### Fielding WAR Proxy

```python
def _compute_fielding_war(stat: dict) -> float:
    fp_raw = stat.get("fielding", ".000") or ".000"
    fp = float(fp_raw) if fp_raw != "-.--" else 0.0
    putouts = stat.get("putOuts", 0)
    assists = stat.get("assists", 0)
    return round((fp - 0.95) * 5 + (putouts + assists) * 0.001, 2)
```

**Formula rationale:**
- Fielding percentage above 0.950 is baseline; each 0.010 above = +0.5 WAR
- Putouts + assists capture defensive volume
- Fielding WAR is inherently smaller than hitting/pitching

## Range Factor

Classic defensive metric: `(PO + A) * 9 / innings`

```python
def _compute_range_factor(stat: dict) -> float:
    putouts = stat.get("putOuts", 0)
    assists = stat.get("assists", 0)
    innings = float(stat.get("innings", "0.0") or "0.0")
    if innings > 0:
        return round((putouts + assists) * 9 / innings, 2)
    return 0.0
```

## Handling Missing/Placeholder Values

The MLB Stats API returns `"-.--"` for stats when a player has no qualifying data (e.g., a pitcher with 0 IP, or a hitter with 0 PA). **Always guard against this:**

```python
# WRONG — will crash on "-.--"
ops = float(stat.get("ops", ".000") or ".000")  # ValueError!

# RIGHT — check for placeholder
ops_raw = stat.get("ops", ".000") or ".000"
ops = float(ops_raw) if ops_raw != "-.--" else 0.0
```

**Same pattern for all rate stats:** ERA, WHIP, AVG, OBP, SLG, OPS, fielding percentage.

## Team-Level Aggregation

Aggregate player stats to team level for prediction adjustments:

```python
def aggregate_team_stats(player_stats: list[dict]) -> dict[str, dict]:
    """Aggregate player WAR by team."""
    team_stats = {}
    for stat in player_stats:
        team_id = stat.get("team_id", "")
        if not team_id:
            continue
        if team_id not in team_stats:
            team_stats[team_id] = {
                "hitting_war": 0.0,
                "pitching_war": 0.0,
                "fielding_war": 0.0,
                "total_war": 0.0,
                "top_hitters": [],
                "top_pitchers": [],
            }
        
        war = stat.get("war_proxy", 0)
        stype = stat.get("stat_type", "")
        
        if stype == "hitting":
            team_stats[team_id]["hitting_war"] += war
            team_stats[team_id]["top_hitters"].append({
                "name": stat.get("player_name", ""),
                "war": war,
                "ops": stat.get("ops", 0),
            })
        elif stype == "pitching":
            team_stats[team_id]["pitching_war"] += war
            team_stats[team_id]["top_pitchers"].append({
                "name": stat.get("player_name", ""),
                "war": war,
                "era": stat.get("era", 0),
            })
        elif stype == "fielding":
            team_stats[team_id]["fielding_war"] += war
        
        team_stats[team_id]["total_war"] += war
    
    # Sort and trim top players
    for tid in team_stats:
        team_stats[tid]["top_hitters"].sort(key=lambda x: x["war"], reverse=True)
        team_stats[tid]["top_hitters"] = team_stats[tid]["top_hitters"][:5]
        team_stats[tid]["top_pitchers"].sort(key=lambda x: x["war"], reverse=True)
        team_stats[tid]["top_pitchers"] = team_stats[tid]["top_pitchers"][:5]
    
    return team_stats
```

## Probability Adjustment from WAR Differential

Apply team WAR differential as a win probability adjustment:

```python
def _compute_stats_adjustment(home_stats: dict, away_stats: dict) -> float:
    """Compute win probability adjustment based on team WAR differential.
    
    Returns a probability shift (-0.1 to +0.1) favoring the stronger team.
    """
    if not home_stats and not away_stats:
        return 0.0
    
    # WAR differentials (positive = home team advantage)
    hitting_diff = home_stats.get("hitting_war", 0) - away_stats.get("hitting_war", 0)
    pitching_diff = home_stats.get("pitching_war", 0) - away_stats.get("pitching_war", 0)
    fielding_diff = home_stats.get("fielding_war", 0) - away_stats.get("fielding_war", 0)
    
    # Weight pitching more heavily in baseball
    total_diff = hitting_diff * 0.35 + pitching_diff * 0.45 + fielding_diff * 0.20
    
    # Normalize: ~50 WAR differential = ~10% probability shift
    adjustment = total_diff / 500
    return max(-0.1, min(0.1, adjustment))
```

**Weighting rationale for baseball:**
- Pitching: 45% — starting rotation + bullpen dominate game outcomes
- Hitting: 35% — lineup depth matters but less than pitching
- Fielding: 20% — defensive runs saved are real but smaller impact

**Cap at ±10%:** Even a 100 WAR differential (which would be ~20% shift) is unrealistic for a single game. The cap prevents overfitting to season-long aggregates.

## Corpus Storage Pattern

Store player stats in the evidence corpus for the API to query:

```python
# In evidence_ingest.py
def ingest_player_stats(self, player_stats: list[dict]) -> str:
    item_id = _generate_id("stats")
    payload = {
        "report_date": _now_utc(),
        "player_stats": player_stats,
    }
    self._insert_item(item_id, "player_stats", "stats_api", payload)
    return item_id
```

## API Endpoint Integration

Load aggregated team stats from corpus and apply to predictions:

```python
# In schedule.py endpoint

def _load_player_stats_from_corpus(sport: str) -> dict[str, dict]:
    """Load aggregated player stats per team from corpus."""
    conn = sqlite3.connect(".forecast/corpus.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT payload_json FROM evidence_items
        WHERE sport = ? AND category = 'player_stats'
        ORDER BY ingested_at DESC LIMIT 1
        """,
        (sport.lower(),),
    ).fetchone()
    conn.close()
    
    if not row:
        return {}
    
    payload = json.loads(row["payload_json"])
    # Aggregate per team...
    return aggregate_team_stats(payload.get("player_stats", []))

# In the prediction loop
team_stats = _load_player_stats_from_corpus(sport)
home_stats = team_stats.get(home_id, {})
away_stats = team_stats.get(away_id, {})
stats_adjustment = _compute_stats_adjustment(home_stats, away_stats)
adjusted_home_prob += stats_adjustment
adjusted_home_prob = max(0.05, min(0.95, adjusted_home_prob))

# Include in response factors
factors = {
    "stats_adjustment": round(stats_adjustment, 3),
    "home_war": round(home_stats.get("total_war", 0), 1),
    "away_war": round(away_stats.get("total_war", 0), 1),
    # ... other factors
}
```

## Frontend: WAR Badge

Show team WAR comparison on game cards:

```html
<span style="font-size: 11px; padding: 2px 8px; 
             background: rgba(59,130,246,0.1); 
             border-radius: 4px; color: #60a5fa;"
      title="Team WAR (hitting + pitching + fielding)">
  WAR: ${g.factors.home_war} vs ${g.factors.away_war}
</span>
```

## Verification Checklist

- [ ] `extract_player_stats()` fetches all three stat groups (hitting/pitching/fielding)
- [ ] `"-.--"` placeholder values handled gracefully (no ValueError)
- [ ] WAR proxy computation produces reasonable values (0-10 range for full seasons)
- [ ] Team aggregation sums correctly per stat type
- [ ] Top 5 hitters/pitchers sorted and trimmed per team
- [ ] `_compute_stats_adjustment()` caps at ±10%
- [ ] Pitching weighted at 45% for baseball
- [ ] Response includes `factors.stats_adjustment`, `factors.home_war`, `factors.away_war`
- [ ] Frontend shows WAR badge when data available
- [ ] Corpus has `player_stats` category evidence item
- [ ] All tests pass after integration
