# Scenarios Endpoint Wiring

Wire injury-based scenario generation into the `/api/scenarios` endpoint and the Scenarios dashboard tab. Reuses the same infrastructure as the schedule endpoint — no duplication.

## When to Use

- The user wants the Scenarios tab to show real data instead of static mock data
- The user asks to "wire scenarios into the scenarios endpoint" or "add scenarios to the scenarios tab"
- Injury data is already flowing through the schedule endpoint and you want to expose it as a standalone view

## Architecture

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  Corpus DB      │────▶│  /api/scenarios     │────▶│  Scenarios Tab  │
│  (schedule,     │     │  (reuses schedule   │     │  (expandable    │
│   ratings,      │     │   loaders +         │     │   cards with    │
│   injuries)     │     │   scenario gen)     │     │   divergence,   │
│                 │     │                     │     │   base/adjusted)│
└─────────────────┘     └─────────────────────┘     └─────────────────┘
```

## Backend: `/api/scenarios`

### 1. Extend Pydantic model

```python
# src/api/models.py
class ScenarioResult(BaseModel):
    id: str
    team_id: str
    team_name: str
    sport: str
    scenario_type: str
    divergence_score: float
    confidence: str
    created_at: str
    game_id: Optional[str] = None          # NEW
    opponent: Optional[str] = None         # NEW
    scenarios: Optional[List[Dict[str, Any]]] = None  # NEW
    base_probability: Optional[float] = None          # NEW
    adjusted_probability: Optional[float] = None      # NEW
```

### 2. Rewrite endpoint to use real data

```python
# src/api/routes/scenarios.py
from fastapi import APIRouter, Query
from typing import List, Optional
from src.api.models import ScenarioResult
from src.api.routes.schedule import (
    _load_schedule_from_corpus,
    _load_ratings_from_corpus,
    _load_injuries_from_corpus,
    _compute_injury_severity,
    _generate_injury_scenarios,
)
from src.elo_engine import Glicko2Engine, SportSpecificElo, Glicko2Rating
from src.elo_adapter import EloScenarioAdapter
import math

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

@router.get("", response_model=List[ScenarioResult])
async def get_scenarios(
    sport: Optional[str] = Query(None, description="Filter by sport: MLB, NFL, NBA"),
    team: Optional[str] = Query(None, description="Filter by team name (partial match)"),
):
    sport_lower = (sport or "mlb").lower()
    sport_upper = sport_lower.upper()

    # Load data from corpus (same as schedule endpoint)
    games = _load_schedule_from_corpus(sport_lower)
    ratings = _load_ratings_from_corpus(sport_lower)
    injuries_by_team = _load_injuries_from_corpus(sport_lower)

    # Seed engine (same as schedule endpoint)
    base_engine = Glicko2Engine()
    for team_id, data in ratings.items():
        base_engine._ratings[team_id] = Glicko2Rating(
            mu=data["mu"], phi=data["phi"], sigma=data["sigma"]
        )
    engine = SportSpecificElo(sport_lower, base_engine)
    adapter = EloScenarioAdapter(sport_lower, engine)

    results = []
    for game in games:
        home_id = game.get("home_team_id", "")
        away_id = game.get("away_team_id", "")

        home_rating = ratings.get(home_id, {"mu": 1500.0, "phi": 350.0, "name": home_id})
        away_rating = ratings.get(away_id, {"mu": 1500.0, "phi": 350.0, "name": away_id})

        # Skip if team filter doesn't match
        if team:
            team_lower = team.lower()
            if team_lower not in home_rating.get("name", "").lower() and \
               team_lower not in away_rating.get("name", "").lower():
                continue

        # Compute probabilities (same as schedule endpoint)
        home_prob = engine.win_probability(home_id, away_id, venue="home")
        home_injuries = injuries_by_team.get(home_id, [])
        away_injuries = injuries_by_team.get(away_id, [])
        home_injury_sev = _compute_injury_severity(home_injuries)
        away_injury_sev = _compute_injury_severity(away_injuries)

        injury_adjustment = (away_injury_sev - home_injury_sev) * 0.15
        adjusted_home_prob = max(0.05, min(0.95, home_prob + injury_adjustment))

        # Confidence (same as schedule endpoint)
        scenario_score = max(0.0, min(1.0, 1.0 - abs(home_prob - adjusted_home_prob) * 5))
        avg_phi = (home_rating.get("phi", 350) + away_rating.get("phi", 350)) / 2
        confidence = adapter.calibrate_confidence(scenario_score, avg_phi)

        # Generate scenarios (same as schedule endpoint)
        scenarios = _generate_injury_scenarios(
            home_id, away_id, home_injuries, away_injuries,
            home_injury_sev, away_injury_sev, home_prob, adjusted_home_prob
        )

        # Only include games with meaningful scenarios
        if not scenarios or len(scenarios) <= 1:
            continue

        # Home team perspective
        results.append(ScenarioResult(
            id=f"scen-{home_id}-{game.get('game_id', '')}",
            team_id=home_id,
            team_name=home_rating.get("name", home_id),
            sport=sport_upper,
            scenario_type="Injury Impact",
            divergence_score=round(abs(injury_adjustment), 3),
            confidence=confidence,
            created_at=game.get("date", ""),
            game_id=game.get("game_id", ""),
            opponent=away_rating.get("name", away_id),
            scenarios=scenarios,
            base_probability=round(home_prob, 3),
            adjusted_probability=round(adjusted_home_prob, 3),
        ))

        # Away team perspective
        results.append(ScenarioResult(
            id=f"scen-{away_id}-{game.get('game_id', '')}",
            team_id=away_id,
            team_name=away_rating.get("name", away_id),
            sport=sport_upper,
            scenario_type="Injury Impact",
            divergence_score=round(abs(injury_adjustment), 3),
            confidence=confidence,
            created_at=game.get("date", ""),
            game_id=game.get("game_id", ""),
            opponent=home_rating.get("name", home_id),
            scenarios=scenarios,
            base_probability=round(1.0 - home_prob, 3),
            adjusted_probability=round(1.0 - adjusted_home_prob, 3),
        ))

    return results
```

## Frontend: Scenarios Tab

Replace the static mock-data rendering with real scenario cards:

```javascript
async function renderScenarios(container) {
  container.innerHTML = '<div class="view-title">Scenario Simulation</div>';

  let url = `${API_BASE}/scenarios`;
  const params = [];
  if (selectedLeague) params.push(`sport=${selectedLeague}`);
  if (selectedTeams.length > 0) params.push(`team=${selectedTeams.map(t => t.name).join(',')}`);
  if (params.length) url += '?' + params.join('&');

  try {
    const res = await fetch(url);
    const scenarios = await res.json();

    if (!scenarios || scenarios.length === 0) {
      container.innerHTML += '<p style="color: var(--text-muted)">No injury-based scenarios available.</p>';
      return;
    }

    container.innerHTML += `
      <div class="card-grid">
        ${scenarios.map(s => `
          <div class="card" style="cursor: pointer;" onclick="toggleScenarioCard('${s.id}')">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div>
                <div class="card-title">${s.team_name}</div>
                <div class="card-meta">${s.scenario_type} · vs ${s.opponent || 'TBD'} · ${s.sport}</div>
              </div>
              <span class="confidence-badge confidence-${s.confidence}">${s.confidence}</span>
            </div>
            <div style="margin-top: 12px; display: flex; gap: 16px; align-items: center;">
              <div>
                <div style="font-size: 11px; color: var(--text-faint);">Divergence</div>
                <div class="card-score" style="font-size: 18px; margin-top: 2px;">${(s.divergence_score * 100).toFixed(1)}%</div>
              </div>
              <div>
                <div style="font-size: 11px; color: var(--text-faint);">Base Prob</div>
                <div style="font-size: 18px; font-weight: 600; color: var(--text-primary); margin-top: 2px;">${(s.base_probability * 100).toFixed(0)}%</div>
              </div>
              <div>
                <div style="font-size: 11px; color: var(--text-faint);">Adjusted</div>
                <div style="font-size: 18px; font-weight: 600; color: var(--accent-light); margin-top: 2px;">${(s.adjusted_probability * 100).toFixed(0)}%</div>
              </div>
            </div>

            <div id="scenario-detail-${s.id}" style="display: none; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-subtle);">
              ${s.scenarios ? s.scenarios.map(scen => `
                <div style="margin-bottom: 12px; padding: 12px; background: var(--bg-surface); border-radius: 8px;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 13px; font-weight: 600; color: var(--text-primary);">${scen.name}</span>
                    <span style="font-size: 11px; padding: 3px 8px; border-radius: 4px; ${scen.impact === 'positive' ? 'background: rgba(16,185,129,0.15); color: var(--success);' : scen.impact === 'negative' ? 'background: rgba(239,68,68,0.15); color: var(--danger);' : 'background: rgba(255,255,255,0.05); color: var(--text-muted);'}">${scen.impact}</span>
                  </div>
                  <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 8px;">${scen.description}</div>
                  <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <span style="font-size: 11px; color: var(--text-faint);">Shift: ${scen.probability_shift > 0 ? '+' : ''}${(scen.probability_shift * 100).toFixed(0)}%</span>
                    <span style="font-size: 11px; color: var(--text-faint);">Likelihood: ${scen.likelihood}</span>
                    ${scen.key_players && scen.key_players.length > 0 ? `
                      <span style="font-size: 11px; color: var(--text-faint);">Players: ${scen.key_players.join(', ')}</span>
                    ` : ''}
                  </div>
                </div>
              `).join('') : '<p style="color: var(--text-muted); font-size: 12px;">No scenario branches available.</p>'}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    console.error('Failed to load scenarios:', err);
    container.innerHTML += '<p style="color: var(--text-muted)">Failed to load scenarios.</p>';
  }
}

function toggleScenarioCard(scenarioId) {
  const el = document.getElementById(`scenario-detail-${scenarioId}`);
  if (el) {
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
  }
}
```

## Design Decisions

1. **Reuses schedule infrastructure** — same loaders, same computation, same scenario generator. No code duplication.
2. **Filters healthy games** — only returns games with injuries (scenarios length > 1). Keeps the tab focused on actionable scenarios.
3. **Dual perspective** — both home and away team get their own `ScenarioResult` per game. Each has their own base/adjusted probability.
4. **Click-to-expand** — cards show summary metrics (divergence, base, adjusted) and expand to show full scenario branches.
5. **Same scenario structure** — the `scenarios` array uses the same schema as the schedule endpoint, so the frontend can reuse rendering logic.

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Static mock data still showing | Scenarios tab shows Yankees/Dodgers/Chiefs/Celtics samples | Replace the hardcoded `scenarios = [...]` list with corpus query + computation |
| Empty scenarios tab | "No injury-based scenarios available" even when injuries exist | Check that `_generate_injury_scenarios()` returns length > 1; verify corpus has injury data |
| Missing game_id/opponent | Cards show "vs TBD" | Ensure `game_id` and `opponent` are set in `ScenarioResult` constructor |
| Probability mismatch | Base + adjusted don't match schedule endpoint | Use the same computation logic — copy from schedule endpoint or extract shared function |
| Cards not clickable | Clicking does nothing | `toggleScenarioCard()` must be in global scope (not inside another function) |
| Detail panel won't hide | Clicking again doesn't collapse | Check `display` toggle logic: `'none' ? 'block' : 'none'` |

## Verification

```bash
# Check scenarios endpoint returns real data
curl -s "http://localhost:8080/api/scenarios?sport=mlb" | python3 -m json.tool | head -40

# Check it filters by team
curl -s "http://localhost:8080/api/scenarios?sport=mlb&team=Yankees" | python3 -m json.tool | grep team_name

# Verify it's not mock data (should show actual team IDs like PIT, COL, NYM)
curl -s "http://localhost:8080/api/scenarios?sport=mlb" | python3 -m json.tool | grep '"id"' | head -5
```
