---
name: fastapi-static-dashboard
description: "Build a FastAPI backend that serves a vanilla-JS dashboard from static files. Covers module import issues (pip install -e .), StaticFiles mounting order, explicit HTML routes, and CORS setup. For Python projects adding a web UI without a build step."
version: 1.2.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [fastapi, python, dashboard, static-files, web-ui]
    related_skills: [claude-design, popular-web-designs, init-project-structure]
---

# FastAPI Static Dashboard

Build a FastAPI backend that serves a vanilla-JS dashboard from static files. This skill captures the complete pattern: project setup, module imports, static file serving, API routing, and common pitfalls.

## When to Use

- Adding a web dashboard to an existing Python project
- Building admin/user-facing UI without React/Vue build step
- Serving static HTML/CSS/JS alongside REST API endpoints
- Need CORS, API docs, and static files in one app
- Connecting a data pipeline (ETL, scrapers, ML inference) to a web dashboard
- **Rebuilding a broken dashboard** — when 3+ sessions failed to fix accumulated frontend bugs (see `references/dashboard-rebuild-from-scratch.md`)

## When to Skip

- Full SPA with React/Vue/Angular (use a separate frontend build)
- The project already has a working web framework (Django, Flask with Jinja2, etc.)
- The dashboard is <300 lines with clear structure and an isolated bug — fix, don't rebuild

## Resource Files

| File | When to read |
|------|--------------|
| `templates/run.sh` | Wrapper script for uvicorn with PYTHONPATH — copy to project root |
| `templates/Dockerfile` | Production Docker image with PYTHONPATH fix |
| `templates/docker-compose.yml` | Docker Compose with nginx reverse proxy |
| `templates/minimal-dashboard.html` | Starting point for a new clean dashboard — copy to `ui/dashboard.html` |
| `references/dashboard-rebuild-from-scratch.md` | When to scrap a broken dashboard and rebuild clean vs. continue debugging |
| `references/team-centric-dashboard-pattern.md` | League-grouped views + team drill-down with detail tabs (Overview/History/Scenarios/Divergence), clickable stat cards, next game preview, divergence magnitude bars, grouped scenarios |
| `references/auth-header-patterns.md` | When dashboard JS calls FastAPI endpoints protected by `Depends(verify_admin_key)` — header name, key value, error parsing |
| `references/data-pipeline-integration.md` | Connecting SQLite/Postgres data pipeline to FastAPI endpoints |
| `references/scenario-integration.md` | Applying scenario adjustments (injuries, momentum, fatigue) to ELO predictions |
| `references/risk-appetite-adjustment.md` | Risk profile selector (conservative/balanced/aggressive) with bet recommendations |
| `references/docker-caching-pitfalls.md` | Docker cache serving stale code — diagnosis, fix, and prevention |
| `references/api-field-mapping-pitfalls.md` | ESPN API field paths differ per sport — inspect before assuming |
| `references/ui-state-sync.md` | Persisted selector state in vanilla JS — interpolate from state, don't hardcode |
| `references/advanced-player-stats-integration.md` | WAR proxy computation, team-level aggregation, and probability adjustment from player stats (hitting/pitching/fielding) |
| `references/scenarios-endpoint-wiring.md` | Wire injury scenarios into `/api/scenarios` endpoint and Scenarios dashboard tab |
| `references/pitcher-matchup-modeling.md` | When adding pitcher-vs-pitcher matchup adjustments to probability calculations — MLB rotation quality, ERA/WHIP/WAR comparison, bullpen factor |
| `references/svg-chart-rendering.md` | Inline SVG sparkline charts from data arrays — geometry math, event delegation for tooltips (not inline scripts), `</script>` in template-literal pitfall |
| `references/dashboard-narrative-ux.md` | Trend indicators (▲▼◆) in tables, narrative explanation cards for views, sorting by computed relevance (confidence + divergence) |
| `references/prediction-accuracy-evaluation.md` | Backtest prediction accuracy with Brier score, log loss, calibration — backend endpoint + frontend chart |
| `references/async-background-jobs.md` | Async background job pattern for long-running FastAPI endpoints — POST returns job_id, background thread, progress polling, frontend progress bar |
| `references/hash-spa-routing.md` | Hash-based SPA routing (`#/view`, `#/team/sport/id/tab`) with popstate, cross-view linking, and navigation assessment methodology for vanilla JS dashboards |

## Project Setup

### 1. Install dependencies

```bash
pip install fastapi uvicorn sse-starlette pydantic
```

If `pip install` is blocked by the terminal tool (detected as "long-lived process"), use `execute_code` with `subprocess.run(..., capture_output=True)` instead.

### 2. Fix module imports

The #1 failure mode: `ModuleNotFoundError: No module named 'src'` when running uvicorn.

**Root cause:** The project isn't installed as a Python package, so `src` isn't on `sys.path`.

**Fix:** Install in development mode:

```bash
cd /path/to/project
pip install -e .
```

This requires a valid `pyproject.toml` with:

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

**Verify:**
```bash
python3 -c "from src.api.main import app; print('OK')"
```

### 3. App structure

```
src/api/
  __init__.py
  main.py          # FastAPI app factory
  models.py        # Pydantic schemas
  dependencies.py  # Auth, DB sessions
  routes/
    __init__.py
    ratings.py
    teams.py
    ...
ui/
  index.html       # Landing page
  dashboard.html   # Dashboard
```

### 4. main.py pattern

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.api.routes import ratings, teams, scenarios

app = FastAPI(title="My App")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes FIRST
app.include_router(ratings.router, prefix="/api")
app.include_router(teams.router, prefix="/api")

# Explicit routes BEFORE static files
@app.get("/dashboard")
async def dashboard():
    return FileResponse("ui/dashboard.html")

# Static files LAST (catches everything else)
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
```

**Critical:** Order matters. StaticFiles with `html=True` catches `/dashboard` and serves `index.html` instead of routing to the API. Put explicit routes BEFORE the mount.

## Run

```bash
cd /path/to/project
pip install -e .  # MUST do this first so 'src' is importable
python3 -m uvicorn src.api.main:app --reload --port 8000
```

**If `pip install -e .` fails or uvicorn still can't find `src`:**

The issue is that uvicorn spawns a subprocess that doesn't inherit the working directory's Python path context. Use a wrapper script (see `templates/run.sh`):

```bash
#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${DIR}:${PYTHONPATH}"
cd "${DIR}"
python3 -m uvicorn src.api.main:app --reload --port 8000
```

Then: `chmod +x run.sh && ./run.sh`

**If `./run.sh` still fails** (the subprocess still can't find `src` even with PYTHONPATH set), **skip the wrapper and use Docker instead.** The local uvicorn subprocess spawning model is fragile across different shell environments. Docker provides a deterministic `PYTHONPATH` and working directory:

```bash
# Build and run with Docker
docker build -t myapp .
docker run -d -p 8000:8000 myapp
```

See the Docker section below for the production Dockerfile pattern.

**URLs:**
- API docs: `http://localhost:8000/docs`
- API: `http://localhost:8000/api/...`
- Dashboard: `http://localhost:8000/dashboard`
- Static files: `http://localhost:8000/...`

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **Auth header missing on protected endpoint** | Dashboard button does nothing, or generic "Trigger failed" toast; Network tab shows 401 | Add `headers: { 'X-API-Key': 'dev-key-change-in-production' }` to fetch; parse `res.json()` for meaningful error messages (see `references/auth-header-patterns.md`) |
| **Dashboard accumulated 3+ failed fix sessions** | Each fix introduces new bugs, state flow is incomprehensible, file >1000 lines | **Rebuild from scratch** — backup old file, keep backend intact, write clean single-file dashboard (see `references/dashboard-rebuild-from-scratch.md`) |
| **Docker cache serving stale HTML after rebuild** | Browser shows old dashboard tabs, old JS functions, old HTML structure despite file being rewritten | `docker-compose down app && docker-compose build app && docker-compose up app -d` — **always rebuild the image when static files change** |
| Docker cache serving stale API code | API returns old data counts, new fields missing | `docker-compose down && docker-compose up -d --build` — always use `--build` when code changes (see `references/docker-caching-pitfalls.md`) |
| Module not found | `No module named 'src'` | `pip install -e .` or `PYTHONPATH=/project/root` |
| Uvicorn subprocess can't find src | Same error after `pip install -e .` | Use `run.sh` wrapper with `PYTHONPATH` |
| Uvicorn still fails after run.sh | `curl: (7) Couldn't connect` — server never starts | **Use Docker** — local uvicorn is fragile, Docker is deterministic |
| StaticFiles catches API | 404 on `/api/health` | Put `app.mount("/", ...)` LAST |
| Dashboard 404 | `/dashboard` returns 404 | Add explicit `@app.get("/dashboard")` route |
| CORS blocked | Frontend can't fetch API | Add `CORSMiddleware` with `allow_origins=["*"]` |
| pip install blocked | Terminal rejects command | Use `execute_code` + `subprocess.run` |
| Port already in use | `Address already in use` | `lsof -ti:8000 \| xargs kill -9` or use `--port 8001` |
| **Docker compose up -d rejected by terminal tool** | Tool says "Run it with background=true" repeatedly while you retry the same foreground command | Pass `background=true` parameter to the `terminal` tool — the tool explicitly instructs you; ignoring it and retrying is the definition of insanity | 
| **Running sync engine from async FastAPI handler** | `await` on a sync function hangs; or `RuntimeWarning: coroutine was never awaited` | Use `db.run_sync(sync_fn)` (if you have a DB session) or `asyncio.to_thread(sync_fn)` to run blocking code without blocking the event loop. Never call sync I/O (DB reads/writes, heavy computation) directly from an `async def` endpoint. |
| **`</script>` inside JS template literal in `<script>` tag** | Browser script silently fails — entire JS file doesn't parse; content div shows placeholder text; `setView` is `undefined` | HTML parser sees `</script>` inside a template literal and closes the outer `<script>` tag. Use event delegation (attached via `addEventListener` to a parent element) instead of inline `<script>` tags inside HTML strings. See `references/svg-chart-rendering.md` |
| **Extra closing tag/brace from patching template-literal HTML** | JS syntax errors after patching — "Unexpected token '}'", page renders nothing | When patching HTML files that contain template literals (backtick strings with `${...}` interpolation), verify there are no extra `</div>` or `}` from the patch. Re-read the patched area after every patch. Test by loading the page in a browser, not by static analysis. |
| **Literal validation rejects frontend uppercase values** | 422 on `?sport=MLB` or `/api/schedule/MLB` — frontend select options send uppercase, Literal only accepts lowercase | Use `BeforeValidator` with `Annotated` for case-insensitive validation. Create a shared `src/api/sport_param.py` with `_normalize_sport` that lowercases + validates. See `references/case-insensitive-validation.md`. |
| Data pipeline returns mock data | API shows sample data instead of real computed data | Wire endpoints to query the corpus DB / data store directly (see Data Pipeline Integration) |
| Corpus loader double-serializes JSON | `could not convert string to float: '{"count": ...}'` | Pass Python dicts to ingestor methods, not `json.dumps()` strings (see API Field Mapping Pitfalls) |
| **Accidental debug slice in pipeline code** | `count` says 672 but corpus only has 5 games — dashboard shows tiny dataset despite full-season extraction | Check loader code for `[:N]`, `.head(`, `.limit(`, `.take(` left from debugging — the count metadata is correct but the actual data is sliced |
| **IIFE function not exported to public object** | Button click does nothing (silently fails); `dashboard.someFunction()` is `undefined`; user says "same experience as before" after you added new JS | When adding a function inside a vanilla-JS IIFE/module closure, you MUST also add it to the `window.dashboard = { ... }` public API object at the bottom of the file. `onclick="dashboard.fn()"` resolves against `window.dashboard` — if `fn` is private inside the closure, the call silently returns `undefined` and nothing happens. **Always check the public export after adding onclick handlers.** |
| **Synchronous POST blocks UI — no feedback during long operations** | User clicks button, page freezes, no progress visible, user reports "no way to know if it's running" | Use the async background job pattern: POST returns `job_id` immediately, runs work in `loop.run_in_executor(None, fn)`, frontend polls `GET /progress/{job_id}` every 500ms. See "Async Background Jobs with Progress Polling" section below. |
| ESPN API returns empty standings | `standings_url` returns `{"fullViewLink": ...}` with no data | Use v2 API (`apis/v2/sports/...`) for NBA/NFL; verify response structure per sport (see API Field Mapping Pitfalls) |
| Injury field KeyError | `KeyError` on `injury.get("details", [{}])[0]` | ESPN nests injuries differently per sport — inspect actual response, don't assume `[0]` exists (see API Field Mapping Pitfalls) |
| MLB team name empty | `team_id` empty string in extracted injuries | MLB uses `displayName` at team root, not `team.name` (see API Field Mapping Pitfalls) |
| **MLB Stats API placeholder values** | `ValueError: could not convert string to float: '-.--'` | MLB Stats API returns `"-.--"` for rate stats when player has no qualifying data. Guard with `if raw != "-.--"` before `float()` (see Advanced Player Stats Integration) |
| **WAR proxy out of range** | Negative or >20 WAR values | Check OPS/ERA normalization; ensure gamesPlayed factor doesn't dominate for partial seasons (see Advanced Player Stats Integration) |
| Schedule endpoint needs team names | Ratings payload only has team_id, no name | JOIN with standings evidence item to get team_name mapping |
| Engine seeding from corpus | `AttributeError: 'BaseEloEngine' has no attribute '_ratings'` | Access via `engine.base._ratings` (the concrete `Glicko2Engine` instance) |
| Confidence label computation | Frontend shows raw RD values | Compute server-side: `sqrt(phi_home² + phi_away²)` → threshold mapping |
| Scenario integration | Schedule endpoint returns only base ELO probabilities with no context adjustments | Use `EloScenarioAdapter` to apply injury/momentum/fatigue adjustments and calibrate confidence |
| Scenario generation missing | Frontend shows no scenario badge or expandable cards | Add `scenarios` field to Pydantic model, implement `_generate_injury_scenarios()`, wire into response |
| Scenarios tab shows mock data | `/api/scenarios` returns static sample data instead of real injury branches | Rewrite endpoint to query corpus, compute probabilities, generate scenarios per game, return `ScenarioResult` with full scenario array |
| **Scenarios endpoint returns empty — no alerts** | Dashboard shows zero scenario alerts even when games are scheduled | The scenarios filter `if len(scenarios) <= 1: continue` skips all games without injuries. Most games have zero injuries → zero results → zero alerts. Fix: also include games with notable probability mismatches (`home_prob > 0.65 or < 0.35`). The `generate_injury_scenarios()` always returns at least 1 scenario ("Injury Status Quo"), so `<= 1` means no actual injuries. |
| Scenario card won't expand | Clicking scenario card does nothing | Ensure `toggleScenarioCard()` is defined in global scope and `id` attribute matches |
| Scenario detail empty | Expanded card shows "No scenario branches available" | Verify `_generate_injury_scenarios()` returns non-empty list when injuries exist; check corpus has injury data |
| **Hardcoded constants bypass override system** | Applied calibration params but predictions/scenarios unchanged | Every endpoint using tunable parameters must call `get_param("PARAM_NAME", DEFAULT)` not hardcode values. Example: `scenarios.py` had `* 0.15` instead of `* get_param("INJURY_SEVERITY_MULTIPLIER", default)`. Grep for numeric literals in probability/scenario computation. |
| **Separate fetch for data already in parent response** | Frontend makes async fetch for histogram/metadata that silently fails or mismatches IDs; feature "doesn't show up" despite backend working | Embed the data in the parent API response (add field to Pydantic model, attach in route handler) instead of requiring a separate round-trip. Separate fetches fail for 3 reasons: (1) ID mismatch between parent and child queries, (2) `.catch(() => [])` swallows errors, (3) race conditions between parallel fetches. If the data is available when the parent endpoint runs, attach it. |
| **Cross-entity ID collisions when building lookup dicts** | Team/player IDs like `CHI`, `DAL` shared across sports; lookup dict shows wrong names (Bulls → Fire) | When building any dict keyed by entity ID that spans multiple categories/sports, scope by category first: `names_by_sport[sport][id]` not flat `names[id]`. Last-writer-wins overwrites are invisible until a user notices wrong data. Frontend: use composite keys (`NBA:CHI`) with bare-ID fallback. |
| Injury data loading | `KeyError` or empty injury context in scenario adjustments | Load from `evidence_items WHERE category = 'injury_report'`; map `injury_status` to severity scores |
| Scenario score normalization | Confidence labels all show "speculative" after adjustment | Normalize scenario score to [0,1] before passing to `adapter.calibrate_confidence()` |
| **Dashboard has no URL routing** | Page refresh resets to default view; browser back/forward broken; can't share links to specific teams/views | Add hash-based SPA router using `window.location.hash` + `popstate`. Use `_restoringHash` flag to prevent hash-update loops during restoration. On modal close, restore hash to current view/team. See `references/hash-spa-routing.md` for the complete pattern including cross-view linking, hash restoration, and navigation assessment methodology |
| Risk selector doesn't reflect selection | Clicking aggressive shows balanced highlight | Render function hardcodes default; interpolate from `riskProfile` state variable (see UI State Sync) |
| Selector resets on re-render | After changing league, risk profile resets | Persist to `localStorage`, read on init, interpolate in template (see UI State Sync) |
| **TestClient cookie overwrite between auth fixtures** | Tests pass individually but fail in suite; admin fixture sends user token → 403 on admin endpoints | Multiple fixtures (`auth_client`, `user_client`) sharing one `TestClient` — `client.cookies.set()` overwrites the single `access_token` cookie. **Fix:** use direct DB queries (`get_user_by_email()`) for user IDs instead of making API calls through a different fixture. See `references/auth-header-patterns.md` → "TestClient Cookie Pitfall". |
| **Moneyline columns show `—` for all games** | Accuracy table renders `—` in Home ML and Away ML columns | Backend `market_odds_map` changed from `dict[tuple, float]` (just devigged probability) to `dict[tuple, dict]` (with `devigged_prob`, `home_ml`, `away_ml` keys). Route code that does `market_odds_map.get(key, 0.0)` now gets a dict, not a float. Must access `market_odds_map.get(key, {}).get("home_ml")` and `market_odds_map.get(key, {}).get("away_ml")`. See `references/prediction-accuracy-evaluation.md`. |
| **Table sort or filter resets or stops working** | Clicking a column header sorts once then stops; typing in filter works for one character then loses focus | When `renderTable()` replaces `innerHTML`, direct `addEventListener` on header cells and filter inputs is destroyed. Use **delegated events** on the container: `container.addEventListener('click', ...)` with `e.target.closest('th[data-sort-col]')`. Filter inputs use `input` event delegation on the container. See `references/prediction-accuracy-evaluation.md` → "Moneyline Columns and Sortable/Filterable Table". |
| **422 from sync endpoint after adding new payload field** | Mobile app login fails with 422 error; sync endpoint returns 422; adding a new field to `build_sync_payload()` breaks the API | The Pydantic `response_model` (e.g., `MobileSyncPayload`) must include EVERY field that the payload dict returns. FastAPI validates the response against the model and rejects unknown fields with 422. When you add `signal_history` to the payload dict, you MUST also add `signal_history: list[SignalHistoryRow] = []` to the Pydantic model. **Always update both the payload builder AND the response_model in tandem.** The 422 is FastAPI's response validation, not a request validation — the server computes the payload fine but refuses to serialize it. |

## Data Pipeline Integration

When the dashboard needs to display real computed data (ELO ratings, standings, etc.) from a data pipeline:

### Pattern: SQLite Corpus as Data Store

The data pipeline writes extracted + computed data into an SQLite corpus. The FastAPI endpoints read from this corpus:

```python
# src/api/routes/ratings.py
import sqlite3
import json
import os

CORPUS_PATH = ".forecast/corpus.db"

def _load_corpus_teams(sport_filter: Optional[str] = None) -> List[dict]:
    """Load real team ratings from the evidence corpus."""
    if not os.path.exists(CORPUS_PATH):
        return []
    
    conn = sqlite3.connect(CORPUS_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get latest power_ratings evidence item
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

### Critical: Corpus Loader Must Store Dicts, Not JSON Strings

The `CorpusLoader` passes payloads to `SportsEvidenceIngestor`. The ingestor's methods (`ingest_elo_ratings`, `ingest_standings`, etc.) expect Python dicts/lists and call `json.dumps()` internally. **Do NOT pre-serialize with `json.dumps()` in the loader.**

**Wrong (double-serialization):**
```python
# BAD — passes a JSON string where a dict is expected
payload = {"count": len(games), "games": games}
return self._load("game_results", json.dumps(payload))  # ❌
```

**Right (pass dict):**
```python
# GOOD — ingestor handles serialization
payload = {"count": len(games), "games": games}
return self._load("game_results", payload)  # ✓
```

**Symptom of double-serialization:** The ingestor's `ingest_elo_ratings` tries to iterate over the JSON string's characters, or `float()` fails on the JSON string: `could not convert string to float: '{"count": 97, ...}'`.

### Docker Volume for Persistent Corpus

When running in Docker, mount the `.forecast/` directory so the corpus persists across container restarts:

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "8080:8000"
    volumes:
      - ./.forecast:/app/.forecast  # Persist corpus DB
      - ./.cache:/app/.cache        # Persist API caches
    environment:
      - PYTHONPATH=/app
```

### Fallback Pattern

Always provide mock data as fallback when the corpus is empty or missing:

```python
@router.get("", response_model=List[Team])
async def get_ratings(sport: Optional[str] = None):
    teams = _load_corpus_teams(sport)
    if not teams:
        teams = _load_mock_teams()  # Fallback
    return teams
```

This lets the dashboard work immediately (showing mock data) and switch to real data once the pipeline runs.

### Multi-Sport Pipeline Support

When supporting multiple sports (MLB, NBA, NFL, etc.), each sport runs its own pipeline sync and writes to the same corpus with a `sport` column:

```python
# Run pipeline for each sport
for sport_key in ["mlb", "nba", "nfl"]:
    config = DataSourceConfig.for_sport(sport_key)
    pipeline = SportsDataPipeline(config, corpus_db=".forecast/corpus.db")
    result = pipeline.run_daily_sync(f"{sport_key}-season", days_back=7)
    print(f"{sport_key}: {len(result.elo_ratings)} teams, {result.games_normalized} games")
```

**Offseason handling:** Some sports have no games during offseason. The pipeline returns `success=False` and `games=0`. The API endpoint falls back to mock data or last-season standings. Check for empty game results and don't fail the entire sync:

```python
# In the endpoint — try corpus first, then mock
teams = _load_corpus_teams(sport="nfl")
if not teams:
    teams = _load_mock_teams(sport="nfl")  # Offseason fallback
```

**ESPN API endpoint differences:** Different sports use different ESPN API endpoint versions. MLB uses `statsapi.mlb.com` for some data; NBA/NFL use `site.api.espn.com/apis/v2/sports/...` for standings. The v2 API returns `children` → `standings` → `entries` with `stats` as a list of `{name, value}` dicts. The site v2 API returns a different structure (`fullViewLink` only for some sports). Always verify the actual API response structure before writing the extractor.

**Injury field mapping differences:** ESPN returns injuries at different nesting levels per sport. MLB: `injury.athlete.displayName` with `displayName` at team root; NBA/NFL: `injury.athlete.displayName` with `team.name` at team root. The extractor must handle the actual response structure, not assume consistency across sports. Always verify with the verification script in `references/api-field-mapping-pitfalls.md`.

**MLB injury team name field:** MLB injuries API uses `displayName` at the team object root (`team_data.get("displayName")`), not `team.name`. Using `team_data.get("team", {}).get("name", "")` returns empty string and produces empty `team_id` mappings.

Use `fastapi.testclient.TestClient` for API tests:

```python
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
```

**TestClient works even when uvicorn doesn't.** If `python3 -m uvicorn` fails with `ModuleNotFoundError` but `TestClient` tests pass, the code is correct — the issue is uvicorn's subprocess spawning, not your imports. This is a signal to switch to Docker.

## Async Background Jobs with Progress Polling

When an API endpoint runs a computation that takes >2 seconds (simulation, batch processing, model training), **never block the HTTP request**. Use the async job pattern:

### Backend pattern

```python
import asyncio
import threading
from typing import Optional

# In-memory job state (use Redis for multi-worker setups)
_jobs: dict[str, dict] = {}

@router.post("/run-simulation")
async def start_simulation(req: SimulationRequest):
    job_id = f"sim-{req.sport}-{uuid4().hex[:8]}"
    _jobs[job_id] = {"status": "running", "progress": 0, "total": 0}

    def _run():
        try:
            result = run_heavy_computation(
                ...,
                progress_callback=lambda p: _jobs[job_id].update(p)
            )
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["result"] = result
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"job_id": job_id}

@router.get("/run-simulation/{job_id}/progress")
async def get_progress(job_id: str):
    return _jobs.get(job_id, {"status": "not_found"})

@router.delete("/run-simulation/{job_id}")
async def cancel_job(job_id: str):
    if job_id in _jobs:
        _jobs[job_id]["status"] = "cancelled"
    return {"ok": True}
```

### Frontend pattern

```javascript
async function triggerSimulation() {
    const res = await fetch('/api/run-simulation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sport: 'mlb', iterations: 1000 })
    });
    const { job_id } = await res.json();

    // Poll every 500ms
    const poll = setInterval(async () => {
        const p = await fetch(`/api/run-simulation/${job_id}/progress`);
        const data = await p.json();

        updateProgressBar(data.progress, data.total);  // CSS transition for smooth bar

        if (data.status === 'completed') {
            clearInterval(poll);
            showSuccess(data.result);
        } else if (data.status === 'failed') {
            clearInterval(poll);
            showError(data.error);
        }
    }, 500);
}
```

### Key rules

1. **Return immediately** — POST handler must respond within ~100ms. Never `await` the heavy work.
2. **Progress callback** — pass a lambda into the computation engine that updates the job dict. Call it every N iterations (not every iteration — avoid overhead).
3. **Thread, not asyncio** — for CPU-bound sync code (numpy, heavy loops), use `threading.Thread(daemon=True)`. For I/O-bound work, use `asyncio.create_task()`.
4. **Frontend CSS transitions** — set `transition: width 0.3s ease` on the progress bar so it animates smoothly between poll intervals instead of jumping.
5. **Job cleanup** — for in-memory `_jobs` dicts, add a TTL sweep (delete jobs older than 1 hour). For production, use Redis with expiry.

## In-Process Scheduled Jobs (APScheduler)

When the app needs recurring background tasks (daily data refresh, cache prewarm, batch jobs), use APScheduler's `AsyncIOScheduler` inside the FastAPI process — no external cron or worker process needed.

### Setup

```bash
uv add apscheduler
```

### Scheduler module (`src/services/scheduler.py`)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: AsyncIOScheduler | None = None

async def _daily_job():
    # ... your daily logic ...

def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler(timezone="US/Central")
    _scheduler.add_job(
        _daily_job,
        trigger=CronTrigger(hour=2, minute=0),  # 2AM local
        id="daily_job",
        max_instances=1,            # never concurrent
        misfire_grace_time=3600,    # catch up if server was down
    )
    _scheduler.start()
    return _scheduler

def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
```

### Wire into FastAPI lifecycle

```python
# src/api/main.py
@app.on_event("startup")
async def _startup():
    from src.services.scheduler import start_scheduler
    start_scheduler()

@app.on_event("shutdown")
async def _shutdown():
    from src.services.scheduler import stop_scheduler
    stop_scheduler()
```

### Admin endpoints

```python
@router.get("/scheduler/status")
async def scheduler_status():
    """No auth — shows next run time and last result."""
    return get_scheduler_status()

@router.post("/scheduler/trigger")
async def scheduler_trigger(verify_admin: bool = Depends(verify_admin_key)):
    """Manual trigger for immediate execution."""
    asyncio.create_task(_daily_job())
    return {"message": "Triggered", "status": "/api/admin/scheduler/status"}
```

### Key rules

1. **`AsyncIOScheduler`** for async jobs, not `BackgroundScheduler` — integrates with FastAPI's event loop.
2. **`max_instances=1`** — prevents overlapping runs if a job takes longer than the interval.
3. **`misfire_grace_time`** — if the server was down at scheduled time, catches up within the grace window.
4. **Startup is non-blocking** — `start_scheduler()` registers jobs but doesn't run them immediately.
5. **Manual trigger uses `asyncio.create_task()`** — runs in background, POST returns immediately.
6. **Graceful shutdown** — `shutdown(wait=False)` in the shutdown event cleans up the scheduler thread.

### Pitfall: sync vs async job functions

If the job function calls sync I/O (DB reads, subprocess calls), wrap it:

```python
async def _daily_job():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_pipeline_and_mc)
```

For purely sync code in a thread, use `BackgroundScheduler` instead. But `AsyncIOScheduler` with `run_in_executor` is more flexible since it supports both sync and async work.

## Docker (Production / Reliable Local)

When local uvicorn is fragile (subprocess can't find modules, port conflicts, shell environment issues), use Docker. This is the pattern used in production deployments (Railway, Fly, etc.):

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY src/ ./src/
COPY ui/ ./ui/

# Set PYTHONPATH so 'src' is importable inside the container
ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
```

```bash
# Build and run
docker build -t myapp .
docker run -d -p 8000:8000 myapp

# Or with docker-compose
docker-compose up
```

**Why Docker works when local uvicorn doesn't:**
- The container's `WORKDIR /app` + `ENV PYTHONPATH=/app` guarantees `src` is findable
- No subprocess spawning issues — uvicorn runs directly in the container
- Deterministic environment — same Python, same deps, same paths every time

## Scenario Integration (Context-Aware Predictions)

Beyond raw ELO probabilities, the dashboard can apply scenario adjustments (injuries, momentum, fatigue) and compute divergence-aware confidence labels. This uses the `EloScenarioAdapter` from the project's `elo_adapter.py`.

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Corpus DB  │────▶│  Schedule    │────▶│  Scenario   │
│  (ratings,  │     │  Endpoint    │     │  Adapter    │
│   injuries) │     │              │     │  (adjust)   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │  Response   │
                                         │  (base +    │
                                         │   adjusted) │
                                         └─────────────┘
```

### Implementation Pattern

```python
# src/api/routes/schedule.py
from src.elo_adapter import EloScenarioAdapter
from src.elo_engine import Glicko2Engine, SportSpecificElo, Glicko2Rating

def _load_injuries_from_corpus(sport: str) -> dict[str, list[dict]]:
    """Load injury reports per team from the evidence corpus."""
    corpus_path = ".forecast/corpus.db"
    if not os.path.exists(corpus_path):
        return {}

    injuries_by_team: dict[str, list[dict]] = {}
    try:
        conn = sqlite3.connect(corpus_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT payload_json FROM evidence_items
            WHERE sport = ? AND category = 'injury_report'
            ORDER BY ingested_at DESC LIMIT 1
            """,
            (sport.lower(),),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            payload = json.loads(row["payload_json"])
            for injury in payload.get("injuries", []):
                team_id = injury.get("team_id", "")
                if team_id:
                    if team_id not in injuries_by_team:
                        injuries_by_team[team_id] = []
                    injuries_by_team[team_id].append(injury)
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to load injuries: %s", exc)

    return injuries_by_team


def _compute_injury_severity(injuries: list[dict]) -> float:
    """Compute aggregate injury severity for a team (0-1 scale)."""
    if not injuries:
        return 0.0

    severity_map = {
        "out": 1.0,
        "day-to-day": 0.5,
        "questionable": 0.3,
        "probable": 0.1,
    }

    total = 0.0
    for injury in injuries:
        status = injury.get("injury_status", "").lower()
        total += severity_map.get(status, 0.2)

    return min(1.0, total / max(1, len(injuries)))


def _compute_probabilities(games, ratings, sport):
    """Compute win probabilities with scenario adjustments."""
    # Seed engine from corpus
    base_engine = Glicko2Engine()
    for team_id, data in ratings.items():
        base_engine._ratings[team_id] = Glicko2Rating(
            mu=data["mu"], phi=data["phi"], sigma=data["sigma"]
        )
    engine = SportSpecificElo(sport, base_engine)

    # Load injuries and initialize adapter
    injuries_by_team = _load_injuries_from_corpus(sport)
    adapter = EloScenarioAdapter(sport, engine)

    results = []
    for game in games:
        home_id = game.get("home_team_id", "")
        away_id = game.get("away_team_id", "")

        home_rating = ratings.get(home_id, {"mu": 1500.0, "phi": 350.0, "name": home_id})
        away_rating = ratings.get(away_id, {"mu": 1500.0, "phi": 350.0, "name": away_id})

        # Base probability from ELO
        home_prob = engine.win_probability(home_id, away_id, venue="home")

        # Apply scenario adjustments
        home_injuries = injuries_by_team.get(home_id, [])
        away_injuries = injuries_by_team.get(away_id, [])
        home_injury_sev = _compute_injury_severity(home_injuries)
        away_injury_sev = _compute_injury_severity(away_injuries)

        # Home team injuries reduce home_prob; away team injuries increase it
        injury_adjustment = (away_injury_sev - home_injury_sev) * 0.15
        adjusted_home_prob = max(0.05, min(0.95, home_prob + injury_adjustment))
        away_prob = 1.0 - adjusted_home_prob

        # Compute confidence using adapter's calibration
        scenario_score = max(0.0, min(1.0, 1.0 - abs(home_prob - adjusted_home_prob) * 5))
        avg_phi = (home_rating.get("phi", 350) + away_rating.get("phi", 350)) / 2
        confidence = adapter.calibrate_confidence(scenario_score, avg_phi)

        # Build enriched response
        factors = {
            "home_field_advantage": engine.home_field_advantage(),
            "sport": sport,
            "base_probability": round(home_prob, 3),
            "injury_adjustment": round(injury_adjustment, 3),
            "home_injuries": len(home_injuries),
            "away_injuries": len(away_injuries),
        }

        results.append({
            "game_id": game.get("game_id", ""),
            "date": game.get("date", ""),
            "home_team": {
                "id": home_id,
                "name": home_rating.get("name", home_id),
                "rating": round(home_rating["mu"], 1),
                "rd": round(home_rating["phi"], 1),
                "win_probability": round(adjusted_home_prob, 3),
            },
            "away_team": { /* ... */ },
            "home_win_prob": round(adjusted_home_prob, 3),
            "away_win_prob": round(away_prob, 3),
            "tie_prob": 0.0,
            "confidence": confidence,
            "factors": factors,
        })

    return results
```

### Key Design Decisions

1. **Adapter reuse:** `EloScenarioAdapter` wraps the same `SportSpecificElo` engine used for base probabilities, ensuring consistent HFA and rating math.

2. **Injury severity mapping:** ESPN injury statuses map to a 0-1 severity scale. The exact mapping should match the sport's impact model (e.g., MLB pitcher injuries have higher impact than NBA bench player injuries).

3. **Adjustment cap:** Probabilities are clamped to [0.05, 0.95] after adjustment to prevent 0% or 100% predictions (which are never realistic in sports).

4. **Scenario score normalization:** The adapter's `calibrate_confidence()` expects a score in [0, 1]. Compute as `1.0 - abs(delta) * scale_factor` where `scale_factor` normalizes the maximum expected divergence.

5. **Confidence thresholds:** The adapter uses phi thresholds (50/100/150) crossed with scenario score (>0.7, >0.5). High-confidence predictions require both low uncertainty AND low scenario divergence.

### Response Enrichment

The enriched response includes both base and adjusted probabilities so the frontend can visualize the scenario impact:

```json
{
  "home_win_prob": 0.515,
  "confidence": "speculative",
  "factors": {
    "base_probability": 0.515,
    "injury_adjustment": 0.0,
    "home_injuries": 0,
    "away_injuries": 0,
    "home_field_advantage": 0.54,
    "sport": "mlb"
  }
}
```

This allows the dashboard to show:
- The raw ELO prediction
- How much injuries/momentum/fatigue shifted it
- Whether the prediction is trustworthy (confidence badge)

### `/api/scenarios` — Scenario Simulation (Injury-Based)

Returns injury-based scenario branches for upcoming games. Previously returned static mock data; now queries the corpus and generates real scenarios from live injury data.

**Query params:** `sport` (mlb/nba/nfl), `team` (partial name match)

**Response:** `List[ScenarioResult]` with fields:
- `id`, `team_id`, `team_name`, `sport`, `scenario_type`
- `divergence_score` — how much injuries moved the probability
- `confidence` — calibrated confidence label
- `game_id`, `opponent` — matchup context
- `base_probability`, `adjusted_probability` — before/after injury adjustment
- `scenarios` — full scenario branch array (same structure as schedule endpoint)

**Implementation pattern:**
```python
# src/api/routes/scenarios.py
from src.api.routes.schedule import (
    _load_schedule_from_corpus,
    _load_ratings_from_corpus,
    _load_injuries_from_corpus,
    _compute_injury_severity,
    _generate_injury_scenarios,
)

@router.get("", response_model=List[ScenarioResult])
async def get_scenarios(sport: Optional[str] = None, team: Optional[str] = None):
    sport_lower = (sport or "mlb").lower()
    games = _load_schedule_from_corpus(sport_lower)
    ratings = _load_ratings_from_corpus(sport_lower)
    injuries_by_team = _load_injuries_from_corpus(sport_lower)
    
    # ... seed engine, compute probabilities, generate scenarios ...
    
    results = []
    for game in games:
        # ... compute base_prob, adjusted_prob, injury_adjustment ...
        scenarios = _generate_injury_scenarios(...)
        
        # Only include games with meaningful scenarios
        if not scenarios or len(scenarios) <= 1:
            continue
            
        results.append(ScenarioResult(
            id=f"scen-{home_id}-{game_id}",
            team_id=home_id,
            team_name=home_name,
            sport=sport_upper,
            scenario_type="Injury Impact",
            divergence_score=round(abs(injury_adjustment), 3),
            confidence=confidence,
            game_id=game_id,
            opponent=away_name,
            scenarios=scenarios,
            base_probability=round(home_prob, 3),
            adjusted_probability=round(adjusted_home_prob, 3),
        ))
        # ... same for away team perspective ...
    
    return results
```

**Key design decisions:**
1. **Reuses schedule endpoint infrastructure** — same corpus loaders, same injury severity computation, same scenario generator. No duplication.
2. **Filters out healthy games** — only returns games where at least one team has injuries (scenarios array length > 1).
3. **Dual perspective** — returns both home and away team results per game, each with their own probability context.
4. **Rich response** — includes base/adjusted probabilities and opponent name for quick comparison.

### Frontend: Scenarios Tab

The dashboard's "Scenarios" tab fetches `/api/scenarios` and renders expandable cards:

```javascript
async function renderScenarios(container) {
  const res = await fetch(`${API_BASE}/scenarios?sport=${selectedLeague}`);
  const scenarios = await res.json();
  
  container.innerHTML = `
    <div class="card-grid">
      ${scenarios.map(s => `
        <div class="card" onclick="toggleScenarioCard('${s.id}')">
          <div style="display: flex; justify-content: space-between;">
            <div>
              <div class="card-title">${s.team_name}</div>
              <div class="card-meta">${s.scenario_type} · vs ${s.opponent} · ${s.sport}</div>
            </div>
            <span class="confidence-badge confidence-${s.confidence}">${s.confidence}</span>
          </div>
          <div style="margin-top: 12px; display: flex; gap: 16px;">
            <div>
              <div style="font-size: 11px; color: var(--text-faint);">Divergence</div>
              <div class="card-score">${(s.divergence_score * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div style="font-size: 11px; color: var(--text-faint);">Base Prob</div>
              <div>${(s.base_probability * 100).toFixed(0)}%</div>
            </div>
            <div>
              <div style="font-size: 11px; color: var(--text-faint);">Adjusted</div>
              <div style="color: var(--accent-light);">${(s.adjusted_probability * 100).toFixed(0)}%</div>
            </div>
          </div>
          
          <div id="scenario-detail-${s.id}" style="display: none; margin-top: 16px;">
            ${s.scenarios.map(scen => `
              <div style="margin-bottom: 12px; padding: 12px; background: var(--bg-surface); border-radius: 8px;">
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-weight: 600;">${scen.name}</span>
                  <span style="padding: 3px 8px; border-radius: 4px; 
                    ${scen.impact === 'positive' ? 'background: rgba(16,185,129,0.15); color: var(--success);' : 
                      scen.impact === 'negative' ? 'background: rgba(239,68,68,0.15); color: var(--danger);' : 
                      'background: rgba(255,255,255,0.05); color: var(--text-muted);'}">${scen.impact}</span>
                </div>
                <div style="font-size: 12px; margin: 8px 0;">${scen.description}</div>
                <div style="display: flex; gap: 12px; flex-wrap: wrap; font-size: 11px; color: var(--text-faint);">
                  <span>Shift: ${scen.probability_shift > 0 ? '+' : ''}${(scen.probability_shift * 100).toFixed(0)}%</span>
                  <span>Likelihood: ${scen.likelihood}</span>
                  ${scen.key_players ? `<span>Players: ${scen.key_players.join(', ')}</span>` : ''}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function toggleScenarioCard(scenarioId) {
  const el = document.getElementById(`scenario-detail-${scenarioId}`);
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}
```

### CSS Grid Layout Pitfall — Overlay Div Breaks Grid

When using CSS Grid for sidebar + main layout, any element placed between the sidebar and main content becomes a grid item. If that element has `display: block` (even implicitly), it occupies a grid track and pushes the main content out of position.

**Symptom:** Sidebar shows correctly at 240px, but main content area is also 240px wide and positioned at `left: 0` instead of `left: 240px`. Content appears to "overflow" into the sidebar area or is severely compressed.

**Root cause:** The `.overlay` div (used for mobile sidebar backdrop) sits between `<nav class="sidebar">` and `<div class="main">` in the DOM. When `display: block`, it becomes the second grid item, consuming the `1fr` track. The `.main` div becomes the third grid item and gets pushed to a new row.

**HTML structure that breaks:**
```html
<div class="app">           <!-- grid: 240px 1fr -->
  <nav class="sidebar">...</nav>     <!-- grid item 1: 240px -->
  <div class="overlay"></div>       <!-- grid item 2: 1fr ← BREAKS -->
  <div class="main">...</div>       <!-- grid item 3: new row -->
</div>
```

**Fix options (pick one):**

1. **Hide overlay by default** (recommended — overlay only shows on mobile):
```html
<div class="overlay" id="overlay" style="display:none"></div>
```

2. **Position overlay outside the grid**:
```css
.overlay {
  position: fixed; inset: 0;
  display: none;  /* only show when .open */
}
```

3. **Use `grid-column` to force placement**:
```css
.main { grid-column: 2; }
```

**Verification:** Check `getComputedStyle('.main').width` — should be ~1040px (not 240px). Check `document.querySelector('.main').getBoundingClientRect().left` — should be 240 (not 0).

**Prevention:** Place the overlay INSIDE the sidebar (as a child) or use `position: fixed` with `display: none` by default. Never let a block-level sibling sit between grid items.

### Docker Cache Serving Stale Static Files

When static files (HTML, CSS, JS) change but the Docker container serves old content, the Docker build cache is reusing layers from before the file change.

**Symptom:** Browser shows old dashboard tabs, old JS functions, old HTML structure despite `ui/dashboard.html` being rewritten on disk.

**Diagnosis:**
```bash
# Check if the file in the container matches host
docker exec elo-scenario-lab-app-1 cat /app/ui/dashboard.html | head -5
# Compare to host
cat ui/dashboard.html | head -5
```

**Fix:** Force a full rebuild:
```bash
docker compose down app
docker compose build app --no-cache  # or just build app (COPY layer invalidates)
docker compose up app -d
```

**Note:** `docker compose restart app` does NOT rebuild the image. It restarts the existing container with the old image. Always use `down` + `build` + `up` when static files change.

**Verification:** Add a cache-buster query param: `curl http://localhost:8080/dashboard?v=$(date +%s)`

### Docker Volume Mounts for Persistent Data

When running in Docker, mount directories that need persistence across container restarts:

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "8080:8000"
    volumes:
      - ./.forecast:/app/.forecast  # SQLite corpus DB
      - ./.cache:/app/.cache        # API response caches
    environment:
      - PYTHONPATH=/app
```

Without volume mounts, the corpus DB and caches are lost on container restart.

## Verification Checklist

- [ ] **Docker image rebuild verified after static file changes** — `docker-compose down app && docker-compose build app && docker-compose up app -d` completed; `curl dashboard?v=2` shows new HTML structure (new tabs, new JS functions)
- [ ] **Docker rebuild verified** — `docker-compose down && docker-compose up -d --build` completed and API returns new data counts
- [ ] **Team-centric layout verified** — Ratings/Scenarios/Divergence views group data by league (MLB → NBA → NFL); each league has colored badge + team count; clicking any team opens detail page with Overview/History/Scenarios/Divergence tabs
- [ ] **Team history endpoint works** — `GET /api/teams/{sport}/{team_id}/history` returns 200 with team data, not 404
- [ ] `pip install -e .` succeeds
- [ ] `python3 -c "from src.api.main import app; print('OK')"` works
- [ ] `./run.sh` starts uvicorn without `ModuleNotFoundError`
- [ ] **OR** `docker build -t myapp .` succeeds and `docker run -p 8000:8000 myapp` serves requests
- [ ] `GET /api/health` returns 200
- [ ] `GET /dashboard` returns HTML (not 404)
- [ ] `GET /` serves landing page
- [ ] Frontend can fetch from `/api/*` (no CORS errors)
- [ ] All TestClient tests pass
- [ ] Data pipeline has run and corpus DB exists (`.forecast/corpus.db`)
- [ ] `GET /api/ratings` returns real computed data (not just mock data)
- [ ] `GET /api/schedule/{sport}` returns upcoming games with win probabilities (not empty)
- [ ] **Injury-based scenarios generated** — `GET /api/schedule/mlb` response includes `scenarios` array per game
- [ ] **Scenario accordion works** — clicking "⚕ N scenarios" badge expands/collapses scenario cards
- [ ] **Scenario cards show** name, impact badge, description, probability shift, likelihood, key players
- [ ] **Scenarios tab shows real data** — `GET /api/scenarios?sport=mlb` returns injury-based scenarios (not static mock data)
- [ ] **Scenario cards expandable** — clicking a scenario card reveals all scenario branches with impact badges, probability shifts, likelihood, and player names
- [ ] **Scenario card metrics** — each card shows divergence %, base probability, and adjusted probability
- [ ] **Scenarios endpoint filters** — `sport` and `team` query params work correctly
- [ ] Docker volume mounts `.forecast/` for corpus persistence
- [ ] **WAR badge visible** — game cards show "WAR: X vs Y" when player stats available
- [ ] **Stats adjustment applied** — `GET /api/schedule/mlb` includes `factors.stats_adjustment` (non-zero when teams have different WAR)
- [ ] Docker volume mounts `.forecast/` for corpus persistence
- [ ] **Injury-based scenarios generated** — `GET /api/schedule/mlb` response includes `scenarios` array per game
- [ ] **Scenario accordion works** — clicking "⚕ N scenarios" badge expands/collapses scenario cards
- [ ] **Scenario cards show** name, impact badge, description, probability shift, likelihood, key players
