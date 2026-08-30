# Prediction Accuracy Evaluation — Brier Score, Log Loss, Calibration

Evaluate model prediction accuracy against actual game results. This pattern builds the infrastructure for accuracy tracking even when data is sparse — the key insight being that the value is in the infrastructure (which accumulates data over time), not in having a large sample immediately.

## When to Use

- You want to answer "how accurate are our predictions historically?"
- You have completed games in your corpus/data store with known outcomes
- You need metrics consumers understand: "our model is correct N% of the time" or "our Brier score is X"
- You need calibration: "when we predict 80%, does the favorite actually win 80% of the time?"

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Corpus DB  │────▶│  Accuracy    │────▶│  Dashboard    │
│  (completed │     │  Endpoint    │     │  (calibration │
│   games,    │     │  (Brier,     │     │   chart, per- │
│   ratings)  │     │   log loss)  │     │   game table) │
└─────────────┘     └──────────────┘     └───────────────┘
```

## Backend: Accuracy Endpoint Pattern

### 1. Pydantic Model

```python
# src/api/models.py
class CalibrationBucket(BaseModel):
    bucket_label: str           # e.g. "40-50%"
    count: int                  # number of games
    predicted_win_rate: float   # midpoint of bucket
    actual_win_rate: float      # actual home-win % in this bucket

class GamePrediction(BaseModel):
    game_id: str
    date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    predicted_home_win: float   # predicted probability (0-1)
    correct: bool               # whether the higher-prob team won

class AccuracyReport(BaseModel):
    sport: str
    total_games: int
    correct_predictions: int
    accuracy_pct: float
    brier_score: float          # mean squared error (0=perfect, 0.25=coin flip)
    log_loss: float             # cross-entropy loss
    calibration: list[CalibrationBucket]
    predictions: list[GamePrediction]
```

### 2. Endpoint Implementation

```python
# src/api/routes/accuracy.py
import sqlite3
import json
import math
import os
from fastapi import APIRouter, HTTPException
from src.api.models import AccuracyReport, CalibrationBucket, GamePrediction
from src.elo_engine import Glicko2Engine, Glicko2Rating
from src.sport_specific import SportSpecificElo

router = APIRouter()
CORPUS_PATH = ".forecast/corpus.db"

def _load_completed_games(sport: str) -> list[dict]:
    """Load completed games from the evidence corpus."""
    if not os.path.exists(CORPUS_PATH):
        return []

    conn = sqlite3.connect(CORPUS_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        """
        SELECT payload_json FROM evidence_items
        WHERE sport = ? AND category = 'game_results'
        ORDER BY ingested_at DESC LIMIT 1
        """,
        (sport.lower(),),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return []

    payload = json.loads(row["payload_json"])
    return [g for g in payload.get("games", []) if g.get("status") == "completed"]

def _load_ratings_from_corpus(sport: str) -> dict[str, dict]:
    """Load latest ratings snapshot for seeding ELO engine."""
    if not os.path.exists(CORPUS_PATH):
        return {}

    conn = sqlite3.connect(CORPUS_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        """
        SELECT payload_json FROM evidence_items
        WHERE sport = ? AND category = 'power_ratings'
        ORDER BY ingested_at DESC LIMIT 1
        """,
        (sport.lower(),),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {}

    payload = json.loads(row["payload_json"])
    return payload.get("ratings", {})

def get_accuracy(sport: str) -> AccuracyReport:
    """Compute accuracy metrics for a sport's completed games."""
    games = _load_completed_games(sport)
    ratings = _load_ratings_from_corpus(sport)

    if not games:
        raise HTTPException(status_code=404, detail=f"No completed games found for {sport}")

    # Seed ELO engine from corpus ratings
    base = Glicko2Engine()
    for team_id, data in ratings.items():
        base._ratings[team_id] = Glicko2Rating(
            mu=data["mu"], phi=data["phi"], sigma=data["sigma"]
        )
    engine = SportSpecificElo(sport, base)

    # Compute predictions for each completed game
    predictions = []
    for g in games:
        home_id = g.get("home_team_id", "")
        away_id = g.get("away_team_id", "")
        home_score = int(g.get("home_score", 0))
        away_score = int(g.get("away_score", 0))

        predicted = engine.win_probability(home_id, away_id, venue="home")
        actual_home_win = home_score > away_score

        predictions.append(GamePrediction(
            game_id=g.get("game_id", ""),
            date=g.get("date", ""),
            home_team=g.get("home_team_name", home_id),
            away_team=g.get("away_team_name", away_id),
            home_score=home_score,
            away_score=away_score,
            predicted_home_win=round(predicted, 3),
            correct= (predicted >= 0.5) == actual_home_win,
        ))

    # --- Brier Score: MSE of predicted probability vs actual outcome ---
    brier = sum(
        (p.predicted_home_win - (1.0 if _is_home_win(p) else 0.0)) ** 2
        for p in predictions
    ) / len(predictions)

    # --- Log Loss: cross-entropy ---
    log_loss_val = sum(
        - (1.0 if _is_home_win(p) else 0.0) * math.log(max(p.predicted_home_win, 1e-15))
        - (0.0 if _is_home_win(p) else 1.0) * math.log(max(1.0 - p.predicted_home_win, 1e-15))
        for p in predictions
    ) / len(predictions)

    # --- Calibration buckets ---
    buckets = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0]
    calibration = []
    for i in range(len(buckets) - 1):
        lo, hi = buckets[i], buckets[i + 1]
        bucket_games = [p for p in predictions if lo < p.predicted_home_win <= hi]
        if not bucket_games:
            continue
        actual = sum(1 for p in bucket_games if _is_home_win(p))
        label = f"{int(lo*100)}-{int(hi*100)}%"
        calibration.append(CalibrationBucket(
            bucket_label=label,
            count=len(bucket_games),
            predicted_win_rate=round((lo + hi) / 2, 3),
            actual_win_rate=round(actual / len(bucket_games), 3),
        ))

    correct = sum(1 for p in predictions if p.correct)

    return AccuracyReport(
        sport=sport.upper(),
        total_games=len(predictions),
        correct_predictions=correct,
        accuracy_pct=round(correct / len(predictions) * 100, 1),
        brier_score=round(brier, 4),
        log_loss=round(log_loss_val, 4),
        calibration=calibration,
        predictions=predictions,
    )

def _is_home_win(p: GamePrediction) -> bool:
    return p.home_score > p.away_score
```

### 3. Register the Route

```python
# src/api/main.py
from src.api.routes import accuracy as accuracy_router
app.include_router(accuracy_router.router, prefix="/api")
```

```python
# src/api/routes/accuracy.py
@router.get("/accuracy/{sport}", response_model=AccuracyReport)
async def get_accuracy_endpoint(sport: str):
    return get_accuracy(sport)
```

## Frontend: Accuracy Dashboard View

### Rendering Pipeline

```javascript
async function renderAccuracy() {
  const sport = selectedLeague || 'MLB';
  const res = await fetch(`${API_BASE}/accuracy/${sport.toLowerCase()}`);
  if (!res.ok) {
    content.innerHTML = emptyView('sporcle', `No accuracy data available for ${sport}`);
    return;
  }
  const report = await res.json();

  content.innerHTML = `
    <h2 class="page-title" style="margin-bottom: 24px;">📐 Model Accuracy: ${report.sport}</h2>

    <!-- Summary metrics -->
    <div class="stat-grid" style="grid-template-columns: repeat(4, 1fr);">
      <div class="stat-card">
        <div class="stat-label">Games Analyzed</div>
        <div class="stat-value">${report.total_games}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Correct Picks</div>
        <div class="stat-value">${report.accuracy_pct}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Brier Score</div>
        <div class="stat-value">${report.brier_score}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Log Loss</div>
        <div class="stat-value">${report.log_loss}</div>
      </div>
    </div>

    <!-- Calibration bar chart -->
    <h3 style="margin-top: 24px;">Calibration: Predicted vs Actual Win Rate</h3>
    <div style="position:relative;margin-bottom:24px;">
      ${renderCalibrationChart(report.calibration)}
    </div>

    <!-- Per-game table -->
    <h3>Game-by-Game Breakdown</h3>
    <div class="table-scroll">
      <table>
        <thead><tr>
          <th></th>
          <th>Date</th>
          <th>Home</th>
          <th>Away</th>
          <th>Prediction</th>
          <th>Result</th>
        </tr></thead>
        <tbody>
          ${report.predictions.map(p => `
            <tr>
              <td style="text-align:center;font-size:18px;">${p.correct ? '✅' : '❌'}</td>
              <td>${formatDate(p.date)}</td>
              <td>${p.home_team}</td>
              <td>${p.away_team}</td>
              <td>${(p.predicted_home_win * 100).toFixed(1)}%</td>
              <td>${p.home_team} ${p.home_score}-${p.away_score}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}
```

### Calibration Bar Chart Rendering

```javascript
function renderCalibrationChart(buckets) {
  const maxCount = Math.max(...buckets.map(b => b.count), 1);
  const barMaxHeight = 180;

  return `
    <div style="display:flex;align-items:flex-end;gap:12px;height:${barMaxHeight + 40}px;padding:0 10px;">
      ${buckets.map(b => {
        const height = (b.count / maxCount) * barMaxHeight;
        const actualPct = (b.actual_win_rate * 100).toFixed(0);
        const idealPct = (b.predicted_win_rate * 100).toFixed(0);
        const isOverconfident = b.actual_win_rate < b.predicted_win_rate;

        return `
          <div style="flex:1;display:flex;flex-direction:column;align-items:center;height:100%;justify-content:flex-end;">
            <!-- Bar group -->
            <div style="display:flex;gap:4px;align-items:flex-end;height:${barMaxHeight}px;">
              <!-- Actual bar -->
              <div style="width:24px;height:${height}px;background:var(--accent);border-radius:4px 4px 0 0;
                          opacity:0.8;transition:height 0.3s;position:relative;"
                   title="Actual: ${actualPct}% (n=${b.count})">
              </div>
              <!-- Ideal line indicator -->
              <div style="width:2px;height:${(b.predicted_win_rate * barMaxHeight / 1.0)}px;
                          background:rgba(255,255,255,0.4);position:absolute;bottom:0;">
              </div>
            </div>
            <div style="font-size:11px;color:var(--text-faint);margin-top:4px;">${b.bucket_label}</div>
            <div style="font-size:10px;color:var(--text-muted);">n=${b.count}</div>
          </div>
        `;
      }).join('')}
    </div>
    <div style="display:flex;gap:16px;font-size:12px;color:var(--text-muted);margin-top:8px;">
      <span style="display:inline-flex;align-items:center;gap:4px;">
        <span style="width:12px;height:12px;background:var(--accent);border-radius:2px;display:inline-block;"></span> Actual
      </span>
      <span style="display:inline-flex;align-items:center;gap:4px;">
        <span style="width:12px;height:2px;background:rgba(255,255,255,0.4);display:inline-block;"></span> Ideal (perfect calibration)
      </span>
    </div>
  `;
}
```

## Key Metrics Explained

| Metric | Range | Interpretation |
|--------|-------|---------------|
| **Brier score** | 0 = perfect, 0.25 = coin flip | Mean squared error between predicted probability and binary outcome. Lower is better. A Brier of 0.25 means the model is no better than guessing 50/50 for every game. |
| **Log loss** | 0 = perfect, unbounded above | Cross-entropy loss. Penalizes confident wrong predictions heavily. A prediction of 95% that's wrong → huge penalty. |
| **Accuracy %** | 0-100% | Simple "did the higher-prob team win" metric. Misleading when predictions cluster near 50%. |
| **Calibration** | Ideal = diagonal (predicted ≈ actual) | For games predicted at X%, do they actually win X% of the time? Overconfident predictions curve below the diagonal; underconfident predictions curve above. |

## Critical Caveat: Back-Testing Bias

When using **current ratings** to predict **past games**, the accuracy is inflated:

```python
# Current code (inflated):
predictions = []
for g in games:
    # Uses today's ratings to predict yesterday's game
    predicted = engine.win_probability(home_id, away_id, venue="home")

# Ideal approach (requires historical rating snapshots):
predictions = []
for g in games:
    # Load the rating snapshot that existed BEFORE the game
    ratings = _load_ratings_as_of(g["date"])
    engine = _seed_from_ratings(ratings)
    predicted = engine.win_probability(home_id, away_id, venue="home")
```

**Mitigation strategy:** Document this bias in the explanation card on the dashboard:
> "Note: predictions use current ratings to back-test past games, which slightly inflates accuracy."

**Long-term fix (two-step):**
1. Run the data pipeline daily so injury, ratings, and pitching snapshots build up over time
2. Once multiple snapshots exist, modify _load_completed_games to merge ALL game_results entries, then match each game to the snapshot closest to its date

### Game Results Merge Strategy (Accumulate, Don't Overwrite)

Each daily pipeline run stores a new game_results evidence item with a subset of games. The accuracy endpoint must merge across ALL entries, not just load the latest:

```python
def _load_completed_games(sport: str) -> list[dict]:
    # Load ALL game_results entries, oldest first, dedupe by game_id
    cursor = conn.execute(
        \"\"\"
        SELECT payload_json, ingested_at FROM evidence_items
        WHERE sport = ? AND category = 'game_results'
        ORDER BY ingested_at ASC
        \"\"\", (sport.lower(),))
    seen = set()
    merged = []
    for row in cursor.fetchall():
        for g in json.loads(row[\"payload_json\"]).get(\"games\", []):
            gid = g.get(\"game_id\", \"\")
            if gid and gid not in seen:
                seen.add(gid)
                merged.append(g)
    return [g for g in merged if g.get(\"status\") == \"completed\"]
```

**Key design decisions:**
- ORDER BY ingested_at ASC (oldest first) -- the first run stores the full season, subsequent runs add new games. If two entries have the same game_id, the first wins.
- seen set prevents duplicates when pipeline runs produce overlapping date ranges.
- Excludes games without a game_id -- some feeds return exhibition games without IDs.

### The Phi Problem: Why Predictions Cluster Near 50%

The root cause is the ratings deviation (phi) in Glicko-2:

| Phi value | Prediction spread | Edges >5% | Accuracy |
|-----------|------------------|-----------|----------|
| 172 (recent games only) | 46.6% - 53.7% | 0 | 53.3% |
| 70.8 (full season, 668 games) | 38.8% - 60.7% | 98 | 53.6% |

**Diagnosis:** High phi produces probabilities near 50% for any pair of similar-rated teams. Two teams rated 1520 vs 1480 with phi=172 gives ~50.5% prediction. Glicko-2 is conservative with uncertain ratings but this makes all games look like coin flips.

**Fix:** Compute ELO across ALL historical games rather than just recent ones. Each game narrows phi for both teams. After 50+ games, phi drops from ~172 to ~70, widening spread from 7% to 22%. This is the single biggest accuracy lever.

### Three Levers for Improving Accuracy

| Lever | Impact | Effort | How |
|-------|--------|--------|-----|
| 1. Lower phi | Spread 7% -> 22% | Low | Compute ELO on all historical games |
| 2. Date-matched context | Eliminates back-testing noise | Medium | Store daily snapshots, match games to pre-game data |
| 3. Full adjustment pipeline | Spread 22% -> 25%+ | Medium | Reuse injury/stats/pitcher adjustments from schedule endpoint |

#### Lever 3: Reusing the Adjustment Pipeline

Raw ELO doesn't account for context. The accuracy endpoint should use the same adjustment pipeline as the schedule endpoint:

```python
from src.api.routes.schedule import (
    _load_injuries_from_corpus, _compute_injury_severity,
    _load_player_stats_from_corpus, _compute_stats_adjustment,
    _load_pitcher_stats_from_corpus, _compute_pitcher_matchup_adjustment,
)

injuries_by_team = _load_injuries_from_corpus(sport)
player_stats = _load_player_stats_from_corpus(sport)
pitcher_data = _load_pitcher_stats_from_corpus(sport)

injury_adj = (_compute_injury_severity(injuries_by_team.get(away_id, []))
              - _compute_injury_severity(injuries_by_team.get(home_id, []))) * 0.15
stats_adj, _, _, _ = _compute_stats_adjustment(home_id, away_id, player_stats)
pitcher_adj, _, _ = _compute_pitcher_matchup_adjustment(home_id, away_id, pitcher_data)
adjusted_home_prob = max(0.05, min(0.95, home_prob + injury_adj + stats_adj + pitcher_adj))
```

**Impact:** Without adjustments: Brier 0.2486, 0 games with >5% edge. With adjustments: Brier 0.2469, 98 games with >5% edge. Spread widened from 46.6-53.7% to 38.8-60.7%.

**Caveat:** Current injury/pitcher data predicting past games introduces noise. As daily pipeline runs accumulate historical snapshots, switch to date-matched adjustments.

## When Data Is Sparse

Don't skip building the infrastructure just because you only have 5 completed games. The accuracy view:

1. **Works with any sample size** — Brier and log loss are well-defined for N=1
2. **Gains power as data accumulates** — Each pipeline run adds more completed games
3. **Calibration is meaningful even at N=5** — shows which confidence buckets are working
4. **Per-game table is valuable debugging** — see exactly which predictions were wrong

**Situation: 5 games, all predictions near 50%** → Brier ≈ 0.25 (coin flip baseline). This is expected when all predictions cluster near 50% due to closely-rated teams. The calibration chart will show 1-2 buckets with tiny bars. The correct response is "we need more data" — not "the infrastructure is wrong."

## Moneyline Columns and Sortable/Filterable Table

### Backend: market_odds_map structure

The accuracy endpoint matches predictions against market odds to compute calibration. The `market_odds_map` must store both the devigged probability AND the raw moneyline strings so the frontend can display them.

**Structure:**

```python
# market_odds_map: dict[tuple[str, str], dict]
# Key: (home_team_id, away_team_id) or normalized name pair
# Value: {"devigged_prob": float, "home_ml": str, "away_ml": str}

market_odds_map[(home_id, away_id)] = {
    "devigged_prob": devigged_prob,
    "home_ml": "+150",      # American odds format
    "away_ml": "-120",
}
```

When building predictions, attach `home_ml` and `away_ml` from the map:

```python
market_data = market_odds_map.get((home_id, away_id), {})
predictions.append(GamePrediction(
    # ... other fields ...
    market_home_win=market_data.get("devigged_prob"),
    home_ml=market_data.get("home_ml"),
    away_ml=market_data.get("away_ml"),
))
```

### Frontend: Sortable/Filterable Predictions Table

For the per-game breakdown table, use client-side sorting and filtering (no API changes beyond adding ML fields):

**Sort pattern:** Click column headers to sort. Track sort column + direction in state, re-render on click.

```javascript
let accSortCol = 'date';
let accSortDir = 'desc';  // default: reverse chronological

function renderAccTable(predictions) {
    // Sort
    const sorted = [...predictions].sort((a, b) => {
        let va = a[accSortCol], vb = b[accSortCol];
        if (accSortCol === 'date') { va = new Date(va); vb = new Date(vb); }
        if (accSortCol === 'home_win') { va = parseFloat(va); vb = parseFloat(vb); }
        if (typeof va === 'string') { va = va.toLowerCase(); vb = vb.toLowerCase(); }
        return accSortDir === 'asc' ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });

    // Filter
    const homeFilter = document.getElementById('acc-home-filter')?.value?.toLowerCase() || '';
    const awayFilter = document.getElementById('acc-away-filter')?.value?.toLowerCase() || '';
    const filtered = sorted.filter(p =>
        p.home_team.toLowerCase().includes(homeFilter) &&
        p.away_team.toLowerCase().includes(awayFilter)
    );

    // Render
    const container = document.getElementById('acc-table-container');
    container.innerHTML = `
        <div style="display:flex;gap:8px;margin-bottom:8px;">
            <input id="acc-home-filter" placeholder="Filter Home..." value="${homeFilter}" style="...">
            <input id="acc-away-filter" placeholder="Filter Away..." value="${awayFilter}" style="...">
            <span style="...">${filtered.length} games</span>
        </div>
        <table>
            <thead><tr>
                ${sortableHeader('Date', 'date')}
                ${sortableHeader('Home', 'home_team')}
                ${sortableHeader('Away', 'away_team')}
                ${sortableHeader('Model', 'home_win')}
                ${sortableHeader('Market', 'market_home_win')}
                ${sortableHeader('Home ML', 'home_ml')}
                ${sortableHeader('Away ML', 'away_ml')}
                <th>Result</th>
            </tr></thead>
            <tbody>
                ${filtered.map(p => `<tr>
                    <td>${formatDate(p.date)}</td>
                    <td>${p.home_team}</td>
                    <td>${p.away_team}</td>
                    <td>${(p.predicted_home_win * 100).toFixed(1)}%</td>
                    <td>${p.market_home_win ? (p.market_home_win * 100).toFixed(1) + '%' : '—'}</td>
                    <td>${p.home_ml || '—'}</td>
                    <td>${p.away_ml || '—'}</td>
                    <td>${p.correct ? '✅' : '❌'}</td>
                </tr>`).join('')}
            </tbody>
        </table>
    `;
}
```

**Moneyline formatting:**

```javascript
function formatML(ml) {
    if (!ml) return '—';
    const num = parseInt(ml);
    return num > 0 ? `+${num}` : `${num}`;
}
```

**Sortable header helper:**

```javascript
function sortableHeader(label, col) {
    const arrow = accSortCol === col ? (accSortDir === 'asc' ? ' ▲' : ' ▼') : '';
    return `<th style="cursor:pointer;" data-sort-col="${col}">${label}${arrow}</th>`;
}
```

**Delegated event listeners (survive re-renders):**

Since `renderAccTable()` replaces the container's innerHTML, inline `onclick` handlers and direct `addEventListener` on header cells get destroyed on each render. Use delegated events on the container:

```javascript
// Attach ONCE to the container (not to individual header cells)
document.getElementById('acc-table-container').addEventListener('click', (e) => {
    const th = e.target.closest('th[data-sort-col]');
    if (th) {
        const col = th.dataset.sortCol;
        if (accSortCol === col) { accSortDir = accSortDir === 'asc' ? 'desc' : 'asc'; }
        else { accSortCol = col; accSortDir = col === 'date' ? 'desc' : 'asc'; }
        renderAccTable(currentPredictions);
    }
});

// Filter inputs — also delegated, because the entire container is re-rendered
document.getElementById('acc-table-container').addEventListener('input', (e) => {
    if (e.target.id === 'acc-home-filter' || e.target.id === 'acc-away-filter') {
        renderAccTable(currentPredictions);
    }
});
```

**Key design decisions:**
- Default sort is **date descending** (newest games first) — users care about recent performance most
- Moneyline columns show raw American odds format (`+150`, `-120`) — users understand this natively
- Filtering is live (re-renders on every keystroke) — dataset is small enough (typically <500 games) that this is instant
- Delegated events on the container element survive re-renders — no need to re-attach after `innerHTML` replacement

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| No completed games in corpus | `/api/accuracy/mlb` returns 404 | Pipeline hasn't ingested completed games; check `game_results` evidence items and filter by `status == 'completed'` |
| Team name mapping missing | Table shows raw team IDs | Load team names from standings evidence item before rendering predictions |
| Division by zero | `ZeroDivisionError` in Brier/log loss | Check `len(games) > 0` before computing metrics |
| Ratings missing for some teams | `KeyError` on `ratings[team_id]` | Use `.get()` with default rating `{"mu": 1500.0, "phi": 350.0, "sigma": 0.06}` |
| All predictions in one bucket | Calibration chart has one tall bar | This is normal with small samples — the chart format still renders correctly |
| Score format inconsistency (home team first) | Calibration showing wrong team as home | Ensure the schedule feed always stores home team as first-listed. If NCAA/neutral-site, document the convention. |
| **Moneyline not showing** | Table shows `—` for all ML columns | Verify `market_odds_map` stores `dict` values with `home_ml`/`away_ml` keys, not just a `float` probability. The struct changed from `dict[tuple, float]` to `dict[tuple, dict]`. |
| **Table sort resets on re-render** | Clicking a column header sorts once, then next click does nothing | Use delegated `addEventListener` on the container (not inline `onclick` on `<th>`), because `innerHTML` replacement destroys direct listeners on header cells. |
| **Filter inputs lose focus** | Typing in the Home filter works but cursor jumps | After `renderAccTable()` replaces innerHTML, the filter input is a new DOM node. The delegated `input` event listener on the container handles re-renders, but the input regains focus automatically from the `value=` attribute. If focus management is needed, save `document.activeElement.id` before render and `.focus()` after. |

## "After Tuning" Calibration Comparison View

When a Monte Carlo calibration sweep has been run, the accuracy page can show a side-by-side comparison of current metrics vs what they'd be under the optimal HFA value found by calibration.

### Backend pattern

```python
# src/api/routes/accuracy.py
# Add calibration_after field to AccuracyReport response

@router.get("/accuracy/{sport}", response_model=AccuracyReport)
async def get_accuracy(sport: str):
    report = _compute_accuracy(sport)

    # Load latest calibration results (if any)
    cal_rows = await corpus.async_load_mc_calibration(sport.lower())
    if cal_rows:
        best = min(cal_rows, key=lambda r: r.get("brier_score", 1.0))
        report.calibration_after = {
            "hfa_value": best["hfa_value"],
            "brier_score": best["brier_score"],
            "log_loss": best["log_loss"],
            "accuracy": best["accuracy"],
        }

    return report
```

### Frontend pattern

Show a comparison card below the main metrics grid when `calibration_after` data exists:

```javascript
if (report.calibration_after) {
    const ca = report.calibration_after;
    const brierDelta = (report.brier_score - ca.brier_score).toFixed(4);
    const brierImprove = brierDelta > 0;
    html += `
    <div class="stat-card" style="border-left: 3px solid var(--accent);">
      <div class="stat-label">After Tuning (HFA=${ca.hfa_value})</div>
      <div>Brier: ${ca.brier_score} (${brierImprove ? '↓' : '↑'}${brierDelta})</div>
      <div>Accuracy: ${ca.accuracy}%</div>
    </div>`;
}
```

**Key rule:** `calibration_after` is nullable — when no calibration has been run, the field is absent and the comparison card doesn't render. Graceful degradation, same as all MC features.
