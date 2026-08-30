# Data Pipeline Integration for FastAPI Dashboards

Connecting a Python data pipeline (ETL, scrapers, ML inference) to a FastAPI web dashboard.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Extractors │────▶│ Transformers │────▶│   Loaders   │
│  (ESPN API) │     │ (normalize)  │     │ (corpus DB) │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Vanilla   │◀────│   FastAPI    │◀────│  SQLite/    │
│     JS      │     │   Backend    │     │  Postgres   │
│  Dashboard  │     │  (REST API)  │     │  Corpus DB  │
└─────────────┘     └──────────────┘     └─────────────┘
```

## The Double-Serialization Bug

**Symptom:** `could not convert string to float: '{"count": 97, ...}'`

**Root cause:** The `CorpusLoader` calls `json.dumps(payload)` and passes the resulting JSON string to `SportsEvidenceIngestor.ingest_elo_ratings()`, which expects a dict of team_id → rating objects. The ingestor then tries to call `float()` on the JSON string.

**Fix:** Pass Python dicts directly to ingestor methods. The ingestor handles `json.dumps()` internally.

```python
# WRONG — double-serialization
payload = {"count": len(games), "games": games}
return self._load("game_results", json.dumps(payload))  # ❌

# RIGHT — pass dict
payload = {"count": len(games), "games": games}
return self._load("game_results", payload)  # ✓
```

## Corpus Loader Pattern

```python
class CorpusLoader:
    def __init__(self, corpus_db: str, sport: str):
        self._ingestor = SportsEvidenceIngestor(corpus_db, sport)
    
    def load_games(self, games: list[dict]) -> str:
        payload = {
            "count": len(games),
            "date_range": self._date_range(games, "date"),
            "games": games,  # ⚠️ ALL games, not [:N]
            "sport": self._sport,
            "evidence_type": "game_results",
        }
        return self._ingestor._insert_item_direct(
            category="game_results",
            source_type="data_pipeline",
            payload=payload,
        )
```

### ⚠️ Critical: The Accidental Debug Slice Bug

**The most insidious bug in pipeline code:** leaving a `[:N]` slice, `.head(5)`, `.limit(5)`, or `.take(5)` that was added for debugging/inspection and never removed.

**Symptom:** Pipeline reports "672 games loaded" (based on `len(games)`), but the corpus only has 5 games. The `count` field is correct, but the actual `games` array is truncated.

**Root cause:**
```python
# Added during debugging: "let me just inspect the first 5"
payload = {"count": len(games), "games": games[:5]}  # ← FORGOTTEN
```

The developer counts correctly (`len(games)` = 672) but slices the data (`games[:5]` = 5 games). Every pipeline run with the same games overwrites with the same 5 games, so the corpus never grows.

**How to catch this:**
- After loading, query the corpus directly to verify storage count matches extraction count:
  ```python
  cursor = conn.execute("SELECT COUNT(*) as c FROM evidence_items WHERE category='game_results'")
  # Loader says 672, DB says 5 → bug!
  ```
- When the dashboard shows "5 games analyzed" after a full-season extraction, suspect this bug
- Search for `[:N]`, `.head(`, `.limit(`, `.take(` in loader code

## FastAPI Endpoint Reading from Corpus

```python
import sqlite3
import json

CORPUS_PATH = ".forecast/corpus.db"

def _load_corpus_teams(sport_filter: Optional[str] = None) -> List[dict]:
    if not os.path.exists(CORPUS_PATH):
        return []
    
    conn = sqlite3.connect(CORPUS_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get latest power_ratings
    cursor = conn.execute(
        """
        SELECT payload_json FROM evidence_items 
        WHERE category = 'power_ratings' 
        ORDER BY ingested_at DESC LIMIT 1
        """
    )
    row = cursor.fetchone()
    
    teams = []
    if row:
        payload = json.loads(row["payload_json"])
        ratings = payload.get("ratings", {})
        
        # Get team names from standings
        cursor = conn.execute(
            """
            SELECT payload_json FROM evidence_items 
            WHERE category = 'standings' 
            ORDER BY ingested_at DESC LIMIT 1
            """
        )
        standings_row = cursor.fetchone()
        team_names = {}
        if standings_row:
            standings_payload = json.loads(standings_row["payload_json"])
            for s in standings_payload.get("standings", []):
                team_names[s.get("team_id", "")] = s.get("team_name", "")
        
        for team_id, rating_data in ratings.items():
            teams.append({
                "id": team_id,
                "name": team_names.get(team_id, team_id),
                "sport": payload.get("sport", "mlb").upper(),
                "rating": round(rating_data.get("mu", 1500.0), 1),
                "rd": round(rating_data.get("phi", 350.0), 1),
                "last_updated": payload.get("date", ""),
            })
    
    conn.close()
    return teams
```

## Docker Volume for Persistence

```yaml
services:
  app:
    build: .
    ports:
      - "8080:8000"
    volumes:
      - ./.forecast:/app/.forecast  # Persist corpus DB
      - ./.cache:/app/.cache        # Persist API caches
```

## Evidence Corpus Schema

```sql
CREATE TABLE evidence_items (
    item_id         TEXT PRIMARY KEY,
    sport           TEXT NOT NULL,
    category        TEXT NOT NULL,  -- 'power_ratings', 'standings', 'game_results', etc.
    source_type     TEXT NOT NULL,
    payload_json    TEXT NOT NULL,  -- JSON payload
    ingested_at     TEXT NOT NULL
);

CREATE TABLE evidence_packets (
    packet_id       TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    revision        TEXT NOT NULL,
    sport           TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE packet_items (
    packet_id       TEXT NOT NULL,
    item_id         TEXT NOT NULL,
    PRIMARY KEY (packet_id, item_id)
);
```

## Categories

| Category | Content | Source |
|----------|---------|--------|
| `power_ratings` | Glicko-2 ratings (mu, phi, sigma) per team | ELO engine |
| `standings` | Wins, losses, win_pct, division_rank | Sports API |
| `game_results` | Scores, venues, dates | Sports API |
| `injury_report` | Player injuries, statuses | Sports API |
| `schedule` | Upcoming games | Sports API |
| `roster_moves` | Transactions, trades, signings | Sports API |

## Historical Snapshot Accumulation via Daily Pipeline Cron

Running the pipeline daily creates timestamped snapshots of injury reports, pitching data, ELO ratings, and game results. Over time these snapshots accumulate into a historical record, enabling date-matched back-testing for the accuracy endpoint.

### The Accumulation Pattern

Each daily pipeline run inserts new evidence items with `ingested_at` timestamps. Multiple entries per category accumulate over time:

```
evidence_items timeline (injury_report):
  2026-05-14  -- 331 injuries (full season)
  2026-05-15  -- 15 new injuries (daily sync)
  2026-05-16  -- 12 new injuries (daily sync)
  ...
```

The accuracy endpoint can then match each historical game to the injury/ratings snapshot that was current when the game was played, rather than using today's data to predict past games.

### Setting Up the Daily Cron Job

Use the Hermes Agent `cronjob` tool for automatic daily pipeline runs:

```python
# Pipeline script (run by cron)
cd /path/to/project
python3 -c "
from src.data_pipeline import SportsDataPipeline, DataSourceConfig
import logging
logging.basicConfig(level=logging.INFO)
config = DataSourceConfig.for_sport('mlb')
pipeline = SportsDataPipeline(config, corpus_db='.forecast/corpus.db')
result = pipeline.run_daily_sync('mlb-season')
print(f'Sync: {result.success}, Games: {result.games_normalized}, ELO: {result.elo_teams}')
"

# Optional: Full-season ELO recompute (reduces phi, widens prediction spread)
python3 -c "
from src.data_pipeline.extractors.mlb_extractor import MLBExtractor
from src.elo_engine import Glicko2Engine, SportSpecificElo
from src.data_pipeline.loaders.corpus_loader import CorpusLoader
from src.data_pipeline.config.config import SportConfig
extractor = MLBExtractor(SportConfig.mlb())
games = extractor.extract_games('2026-03-26', '2026-05-16')
normalizer = GameResultNormalizer()
normalized = normalizer.normalize_games(games, 'mlb')
engine = SportSpecificElo(sport='mlb', base_engine=Glicko2Engine())
ratings = engine.compute_ratings(normalized)
loader = CorpusLoader(corpus_db='.forecast/corpus.db', sport='mlb')
loader.load_elo_ratings(ratings)
phis = [r.phi for r in ratings.values()]
print(f'{len(ratings)} teams, avg phi={sum(phis)/len(phis):.1f}')
"

# Copy updated DB to Docker container
docker cp .forecast/corpus.db <container-name>:/app/.forecast/corpus.db
```

Configure the cron in Hermes:

```yaml
# Hermes cron job:
name: "Daily MLB Data Pipeline"
schedule: "0 6 * * *"   # 6 AM daily
workdir: /path/to/project
prompt: |
  Run the daily MLB data pipeline to keep injury reports, pitching data,
  ELO ratings, and game results up to date. Steps:
  1. cd /path/to/project
  2. Run pipeline sync via python3 -c "from src.data_pipeline import ..."
  3. Run full-season ELO recompute
  4. Copy corpus.db to Docker container
  5. Report success/errors
```

**Important:** After each pipeline run, copy the updated `corpus.db` to the Docker container. Without this, the container serves stale data while the host has the latest:

```bash
docker cp .forecast/corpus.db <container>:/app/.forecast/corpus.db
```

### Game Results Merge Strategy

Each pipeline run stores a new `game_results` evidence item. The accuracy endpoint must merge across ALL entries, deduping by `game_id`:

```python
def _load_completed_games(sport: str) -> list[dict]:
    # Load ALL game_results entries, oldest first
    cursor = conn.execute(
        \"\"\"SELECT payload_json, ingested_at FROM evidence_items
        WHERE sport = ? AND category = 'game_results'
        ORDER BY ingested_at ASC\"\"\", (sport.lower(),))
    
    seen: set[str] = set()
    merged: list[dict] = []
    for row in cursor.fetchall():
        for g in json.loads(row[0]).get("games", []):
            gid = g.get("game_id", "")
            if gid and gid not in seen:
                seen.add(gid)
                merged.append(g)
    return [g for g in merged if g.get("status") == "completed"]
```

**Design rules:**
- `ORDER BY ingested_at ASC` (oldest first) -- the first run usually stores the full season, subsequent runs add only new games
- `seen` set dedupes across overlapping date ranges
- Excludes games without a game_id (exhibition games, preseason)

### Snapshot Categories That Accumulate

| Category | Purpose | Accumulation rate |
|----------|---------|-------------------|
| `injury_report` | Player injuries per team | 1 entry per pipeline run |
| `power_ratings` | ELO ratings snapshot | 1 entry per pipeline run |
| `game_results` | Completed game scores | 1 entry per run (merged at query time) |
| `player_stats` | Hitting/pitching/fielding stats | 1 entry per run (full-season replacement) |

### Docker Volume for Corpus Persistence

Without volume mounts, the corpus DB resets on container restart:

```yaml
services:
  app:
    build: .
    volumes:
      - ./.forecast:/app/.forecast  # Persist corpus DB across restarts
```

But even with volumes, **updated corpus.db from the pipeline run on the host must be explicitly copied into the container** (or the container must run the pipeline itself).

## Computing Win Probabilities for Upcoming Games

The ELO engine already computes win probabilities via `win_probability(team_a, team_b, venue)`. To expose upcoming game predictions through the dashboard:

### 1. Store schedule in corpus

Ensure the pipeline stores schedule data:

```python
# In the pipeline or loader
schedule = extractor.extract_schedule()
payload = {
    "sport": sport,
    "count": len(schedule),
    "games": schedule,
}
ingestor._insert_item_direct(category="schedule", source_type="api", payload=payload)
```

### 2. Create a schedule endpoint with probabilities

```python
# src/api/routes/schedule.py
from fastapi import APIRouter
from src.elo_engine import Glicko2Engine, SportSpecificElo
import sqlite3, json, os

router = APIRouter(prefix="/schedule", tags=["schedule"])

def _load_schedule(sport: str) -> list[dict]:
    conn = sqlite3.connect(".forecast/corpus.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT payload_json FROM evidence_items WHERE category = 'schedule' AND sport = ? ORDER BY ingested_at DESC LIMIT 1",
        (sport,)
    ).fetchone()
    conn.close()
    return json.loads(row["payload_json"]).get("games", []) if row else []

def _load_ratings(sport: str) -> dict[str, dict]:
    conn = sqlite3.connect(".forecast/corpus.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT payload_json FROM evidence_items WHERE category = 'power_ratings' AND sport = ? ORDER BY ingested_at DESC LIMIT 1",
        (sport,)
    ).fetchone()
    conn.close()
    return json.loads(row["payload_json"]).get("ratings", {}) if row else {}

@router.get("/{sport}")
async def get_schedule_with_probabilities(sport: str):
    games = _load_schedule(sport)
    ratings = _load_ratings(sport)
    
    engine = SportSpecificElo(sport, Glicko2Engine())
    # Seed engine with current ratings
    for team_id, r in ratings.items():
        engine.base._ratings[team_id] = Glicko2Rating(mu=r["mu"], phi=r["phi"], sigma=r.get("sigma", 0.06))
    
    enriched = []
    for g in games:
        home_id = g["home_team_id"]
        away_id = g["away_team_id"]
        home_prob = engine.win_probability(home_id, away_id, venue="home")
        away_prob = 1.0 - home_prob
        
        enriched.append({
            "game_id": g["game_id"],
            "date": g["date"],
            "home_team": {"id": home_id, "rating": ratings.get(home_id, {}).get("mu", 1500)},
            "away_team": {"id": away_id, "rating": ratings.get(away_id, {}).get("mu", 1500)},
            "win_probability": {"home": round(home_prob, 3), "away": round(away_prob, 3)},
        })
    
    return {"games": enriched}
```

### 3. Register the router

```python
# src/api/main.py
from src.api.routes import schedule
app.include_router(schedule.router, prefix="/api")
```

### 4. Dashboard UI — Upcoming Games View

Add a tab/view that fetches `/api/schedule/{sport}` and renders matchup cards:

```html
<!-- Simplified card structure -->
<div class="game-card">
  <div class="teams">
    <span class="team home">LAD (1542)</span>
    <span class="vs">vs</span>
    <span class="team away">NYY (1511)</span>
  </div>
  <div class="probability-bar">
    <div class="home-bar" style="width: 54%">54%</div>
    <div class="away-bar" style="width: 46%">46%</div>
  </div>
  <div class="meta">May 15 • Dodger Stadium</div>
</div>
```

**Key design decisions:**
- Compute probabilities at request time (ratings change after every pipeline run)
- Use `SportSpecificElo` for sport-specific home-field advantage (MLB 54%, NBA 60%, NFL 57%)
- Seed the engine from corpus ratings rather than re-running the full ELO computation
- Return raw probabilities; let the frontend handle formatting (percentages, color coding)
- Fallback to empty list when no schedule data exists (offseason, pipeline not run)

### 5. Testing

```python
from fastapi.testclient import TestClient

def test_schedule_returns_games(client: TestClient):
    r = client.get("/api/schedule/mlb")
    assert r.status_code == 200
    data = r.json()
    assert "games" in data
    if data["games"]:
        g = data["games"][0]
        assert "win_probability" in g
        assert "home" in g["win_probability"]
        assert 0.0 <= g["win_probability"]["home"] <= 1.0
```

## Pydantic Models for Schedule + Probabilities

Define response schemas so the endpoint is self-documenting and the frontend has a contract:

```python
# src/api/models.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class MatchupTeam(BaseModel):
    id: str
    name: str
    rating: float
    rd: float
    win_probability: float

class NextGameProbability(BaseModel):
    game_id: str
    date: str
    home_team: MatchupTeam
    away_team: MatchupTeam
    home_win_prob: float
    away_win_prob: float
    tie_prob: float
    confidence: str  # "high" | "moderate" | "low" | "speculative"
    factors: Dict[str, Any]  # {"home_field_advantage": 0.54, "sport": "mlb"}

class ScheduleResponse(BaseModel):
    sport: str
    games: List[NextGameProbability]
    generated_at: str
```

**Confidence label formula:** Map combined rating deviation to a human label:

```python
import math

def _confidence_label(phi_home: float, phi_away: float) -> str:
    combined = math.sqrt(phi_home ** 2 + phi_away ** 2)
    if combined < 80:   return "high"
    elif combined < 140: return "moderate"
    elif combined < 200: return "low"
    return "speculative"
```

Lower combined RD = more confident prediction (ratings are well-established). Higher RD = ratings are provisional (new teams, few games played).

## Seeding the Engine from Corpus Ratings

When computing probabilities, seed the Glicko-2 engine with ratings loaded from the corpus rather than starting from defaults:

```python
from src.elo_engine import Glicko2Rating

engine = SportSpecificElo(sport, Glicko2Engine())
for team_id, r in ratings.items():
    engine.base._ratings[team_id] = Glicko2Rating(
        mu=r["mu"], phi=r["phi"], sigma=r.get("sigma", 0.06)
    )
```

**Why seed instead of recompute?** The pipeline already computed ratings from all historical games. Recomputing from scratch would require loading all games into memory and running the full rating-period update — expensive and unnecessary. Seeding gives instant probabilities from the latest known state.

**Pitfall:** `SportSpecificElo` wraps `BaseEloEngine`, which declares `compute_ratings` and `win_probability` as abstract methods. The internal `_ratings` dict lives on the concrete `Glicko2Engine` instance (accessible via `engine.base._ratings`). Direct assignment works because Python dataclasses are mutable unless marked `frozen=True` — and `Glicko2Rating` in `elo_engine.py` is a regular `@dataclass` (not frozen), so assignment is allowed.

## Dashboard UI Pattern for Game Cards

Render upcoming games as cards with a visual probability bar:

```javascript
// renderUpcoming(container) — vanilla JS
async function renderUpcoming(container) {
  container.innerHTML = '<div class="view-title">Upcoming Games</div>';
  
  const res = await fetch(`/api/schedule/${selectedLeague}`);
  const data = await res.json();
  
  container.innerHTML += `
    <div class="card-grid">
      ${data.games.map(g => {
        const homeColor = g.home_win_prob > 0.55 ? 'var(--success)' 
                        : g.home_win_prob < 0.45 ? 'var(--danger)' 
                        : 'var(--warning)';
        const dateStr = new Date(g.date).toLocaleDateString('en-US', { 
          weekday: 'short', month: 'short', day: 'numeric' 
        });
        
        return `
          <div class="card">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
              <span style="font-size:12px; color:var(--text-muted);">${dateStr}</span>
              <span class="confidence-badge confidence-${g.confidence}">${g.confidence}</span>
            </div>
            
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div style="flex:1;">
                <div style="font-size:15px; font-weight:590;">${g.home_team.name}</div>
                <div style="font-size:12px; color:var(--text-muted);">Rating: ${g.home_team.rating}</div>
              </div>
              <div style="text-align:center; padding:0 16px;">
                <div style="font-size:20px; font-weight:600; color:${homeColor};">
                  ${(g.home_win_prob * 100).toFixed(0)}%
                </div>
              </div>
              <div style="flex:1; text-align:right;">
                <div style="font-size:15px; font-weight:590;">${g.away_team.name}</div>
                <div style="font-size:12px; color:var(--text-muted);">Rating: ${g.away_team.rating}</div>
              </div>
            </div>
            
            <!-- Probability bar -->
            <div style="width:100%; height:6px; background:var(--bg-surface); border-radius:3px; overflow:hidden; margin-top:10px;">
              <div style="width:${g.home_win_prob * 100}%; height:100%; background:${homeColor}; float:left;"></div>
              <div style="width:${g.away_win_prob * 100}%; height:100%; background:var(--text-muted); float:right;"></div>
            </div>
            
            <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;">
              <span style="font-size:11px; padding:2px 8px; background:rgba(94,106,210,0.1); border-radius:4px; color:var(--accent-light);">
                HFA: ${(g.factors.home_field_advantage * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}
```

**Color coding convention:**
- Green (`var(--success)`) for win probability > 55%
- Yellow (`var(--warning)`) for 45–55% (toss-up)
- Red (`var(--danger)`) for < 45% (underdog)

This gives users an at-a-glance sense of which games are competitive vs. lopsided.
