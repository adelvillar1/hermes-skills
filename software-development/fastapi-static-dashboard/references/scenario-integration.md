# Scenario Integration for FastAPI Dashboards

Applying scenario adjustments (injuries, momentum, fatigue) to ELO predictions via the `EloScenarioAdapter` pattern.

## Architecture

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

## Implementation Pattern

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

## Key Design Decisions

1. **Adapter reuse:** `EloScenarioAdapter` wraps the same `SportSpecificElo` engine used for base probabilities, ensuring consistent HFA and rating math.

2. **Injury severity mapping:** ESPN injury statuses map to a 0-1 severity scale. The exact mapping should match the sport's impact model (e.g., MLB pitcher injuries have higher impact than NBA bench player injuries).

3. **Adjustment cap:** Probabilities are clamped to [0.05, 0.95] after adjustment to prevent 0% or 100% predictions (which are never realistic in sports).

4. **Scenario score normalization:** The adapter's `calibrate_confidence()` expects a score in [0, 1]. Compute as `1.0 - abs(delta) * scale_factor` where `scale_factor` normalizes the maximum expected divergence.

5. **Confidence thresholds:** The adapter uses phi thresholds (50/100/150) crossed with scenario score (>0.7, >0.5). High-confidence predictions require both low uncertainty AND low scenario divergence.

## Response Enrichment

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

## Frontend Integration

The dashboard's "Upcoming" tab fetches `/api/schedule/{sport}` and renders:
- Matchup cards with team names, ratings, and win percentages
- Color-coded probability bars (green >55%, yellow 45-55%, red <45%)
- Confidence badges (high/moderate/low/speculative)
- HFA factor tooltip
- Expandable "Scenario Details" showing base vs adjusted probability

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `AttributeError: 'BaseEloEngine' has no attribute '_ratings'` | Can't seed engine from corpus | Access via `engine.base._ratings` (concrete `Glicko2Engine` instance) |
| Confidence labels all "speculative" | Scenario score not normalized | Clamp score to [0,1] before `calibrate_confidence()` |
| Empty injury context | `KeyError` or zero adjustments | Verify `evidence_items` has `category = 'injury_report'` for the sport |
| Double-counting adjustments | Probabilities exceed [0,1] | Clamp to [0.05, 0.95] after each adjustment layer |
| ESPN injury field mismatch | `KeyError` on `details[0]` | NBA/NFL use `shortComment` at root; MLB nests in `details` — inspect actual response |
