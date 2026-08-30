# Injury-Based Scenario Generation

Generate scenario branches from live injury data for sports prediction dashboards. Each game gets 3-4 scenario branches based on the actual injury situations of both teams.

## When to Use

- The dashboard shows upcoming games and you want scenario-aware predictions
- Real injury data is available in the evidence corpus (from ESPN API or similar)
- You want to model "what if" branches: players return early, injuries worsen, status quo
- The user asks "what about injury-based scenarios?" or "can we do something with injuries?"

## Architecture

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  ESPN Injury    │────▶│  Corpus DB          │────▶│  Schedule       │
│  API            │     │  (injury_report)    │     │  Endpoint       │
└─────────────────┘     └─────────────────────┘     └────────┬────────┘
                                                             │
                                                             ▼
                                                      ┌─────────────────┐
                                                      │  _generate_     │
                                                      │  injury_        │
                                                      │  scenarios()    │
                                                      └────────┬────────┘
                                                               │
                                                               ▼
                                                      ┌─────────────────┐
                                                      │  Response       │
                                                      │  (scenarios     │
                                                      │   per game)     │
                                                      └─────────────────┘
```

## Backend Implementation

### 1. Add `scenarios` field to Pydantic model

```python
# src/api/models.py
class NextGameProbability(BaseModel):
    game_id: str
    date: str
    home_team: MatchupTeam
    away_team: MatchupTeam
    home_win_prob: float
    away_win_prob: float
    tie_prob: float
    confidence: str
    factors: Dict[str, Any]
    risk_adjusted: Optional[Dict[str, Any]] = None
    scenarios: Optional[List[Dict[str, Any]]] = None  # NEW
```

### 2. Implement scenario generator

```python
# src/api/routes/schedule.py

def _generate_injury_scenarios(
    home_id: str,
    away_id: str,
    home_injuries: list[dict],
    away_injuries: list[dict],
    home_injury_sev: float,
    away_injury_sev: float,
    base_prob: float,
    adjusted_prob: float,
) -> list[dict]:
    """Generate scenario branches based on injury situations."""
    scenarios = []

    # Scenario 1: Key players return early
    if home_injuries or away_injuries:
        early_return_impact = 0.03
        if home_injuries and away_injuries:
            desc = f"Both teams dealing with injuries. If {home_id} key players return sooner than expected, home win probability increases by ~{early_return_impact*100:.0f}%."
        elif home_injuries:
            desc = f"{home_id} has {len(home_injuries)} players injured. Early returns could boost home win probability by ~{early_return_impact*100:.0f}%."
        else:
            desc = f"{away_id} has {len(away_injuries)} players injured. Early returns could reduce home win probability by ~{early_return_impact*100:.0f}%."

        scenarios.append({
            "name": "Key Players Return Early",
            "description": desc,
            "impact": "positive" if home_injuries else "negative",
            "probability_shift": early_return_impact if home_injuries else -early_return_impact,
            "key_players": [i.get("player_name", "") for i in (home_injuries or away_injuries)[:3]],
            "likelihood": "moderate" if (home_injury_sev + away_injury_sev) > 0.3 else "low",
        })

    # Scenario 2: Injury situation worsens (home team)
    worsening_impact = 0.04
    if home_injuries:
        scenarios.append({
            "name": "Home Team Injuries Worsen",
            "description": f"{home_id} already has {len(home_injuries)} players out. If additional players go down or existing injuries extend, home win probability could drop by ~{worsening_impact*100:.0f}%.",
            "impact": "negative",
            "probability_shift": -worsening_impact,
            "key_players": [i.get("player_name", "") for i in home_injuries[:3]],
            "likelihood": "moderate" if home_injury_sev > 0.4 else "low",
        })

    # Scenario 3: Injury situation worsens (away team)
    if away_injuries:
        scenarios.append({
            "name": "Away Team Injuries Worsen",
            "description": f"{away_id} already has {len(away_injuries)} players out. If their situation deteriorates further, home win probability could rise by ~{worsening_impact*100:.0f}%.",
            "impact": "positive",
            "probability_shift": worsening_impact,
            "key_players": [i.get("player_name", "") for i in away_injuries[:3]],
            "likelihood": "moderate" if away_injury_sev > 0.4 else "low",
        })

    # Scenario 4: Status quo (always present)
    scenarios.append({
        "name": "Injury Status Quo",
        "description": f"Current injury situation holds. {home_id}: {len(home_injuries)} out. {away_id}: {len(away_injuries)} out. Probability remains at current adjusted level of {adjusted_prob*100:.1f}%.",
        "impact": "neutral",
        "probability_shift": 0.0,
        "key_players": [],
        "likelihood": "high",
    })

    # Scenario 5: Star player absence impact (MLB-specific)
    if home_injuries or away_injuries:
        star_injuries = [i for i in (home_injuries + away_injuries)
                        if any(kw in i.get("injury_description", "").lower()
                               for kw in ["elbow", "shoulder", "tommy john", "acl", "fracture"])]
        if star_injuries:
            scenarios.append({
                "name": "Star Player Absence Impact",
                "description": f"Key players with significant injuries: {', '.join(i.get('player_name', '') for i in star_injuries[:2])}. Their absence creates matchup advantages that could shift probability by ~5%.",
                "impact": "negative" if any(i in home_injuries for i in star_injuries) else "positive",
                "probability_shift": -0.05 if any(i in home_injuries for i in star_injuries) else 0.05,
                "key_players": [i.get("player_name", "") for i in star_injuries[:3]],
                "likelihood": "high",
            })

    return scenarios
```

### 3. Wire into probability computation

```python
def _compute_probabilities(games, ratings, sport, risk_profile="balanced"):
    # ... existing setup: seed engine, load injuries, compute base prob ...

    for game in games:
        # ... compute home_prob, adjusted_home_prob, injury_adjustment ...

        # Generate scenarios AFTER all adjustments are computed
        scenarios = _generate_injury_scenarios(
            home_id, away_id, home_injuries, away_injuries,
            home_injury_sev, away_injury_sev, home_prob, adjusted_home_prob
        )

        results.append(NextGameProbability(
            # ... existing fields ...
            scenarios=scenarios,  # NEW
        ))

    return results
```

## Frontend Implementation

### 1. Add scenario badge to game card

```javascript
// In the game card HTML template
${g.scenarios && g.scenarios.length > 0 ? `
  <span style="font-size: 11px; padding: 2px 8px; background: rgba(239,68,68,0.1); border-radius: 4px; color: var(--danger); cursor: pointer;" onclick="toggleScenarios('${g.game_id}')">
    ⚕ ${g.scenarios.length} scenarios
  </span>
` : ''}
```

### 2. Add expandable scenario panel

```javascript
// Hidden by default, toggled on click
${g.scenarios ? `
  <div id="scenarios-${g.game_id}" style="display: none; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-subtle);">
    ${g.scenarios.map(s => `
      <div style="margin-bottom: 10px; padding: 10px; background: var(--bg-surface); border-radius: 6px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <span style="font-size: 12px; font-weight: 600; color: var(--text-primary);">${s.name}</span>
          <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; ${s.impact === 'positive' ? 'background: rgba(16,185,129,0.15); color: var(--success);' : s.impact === 'negative' ? 'background: rgba(239,68,68,0.15); color: var(--danger);' : 'background: rgba(255,255,255,0.05); color: var(--text-muted);'}">
            ${s.impact}
          </span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 6px;">${s.description}</div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <span style="font-size: 10px; color: var(--text-faint);">Shift: ${s.probability_shift > 0 ? '+' : ''}${(s.probability_shift * 100).toFixed(0)}%</span>
          <span style="font-size: 10px; color: var(--text-faint);">Likelihood: ${s.likelihood}</span>
          ${s.key_players && s.key_players.length > 0 ? `
            <span style="font-size: 10px; color: var(--text-faint);">Players: ${s.key_players.join(', ')}</span>
          ` : ''}
        </div>
      </div>
    `).join('')}
  </div>
` : ''}
```

### 3. Add toggle function

```javascript
function toggleScenarios(gameId) {
  const el = document.getElementById(`scenarios-${gameId}`);
  if (el) {
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
  }
}
```

## Scenario Branch Types

| Name | Trigger | Impact | Probability Shift | Likelihood |
|------|---------|--------|-------------------|------------|
| Key Players Return Early | Any injuries on either team | Positive for home if home injured, negative if away injured | ±3% | Moderate/Low |
| Home Team Injuries Worsen | Home team has injuries | Negative for home | -4% | Moderate/Low |
| Away Team Injuries Worsen | Away team has injuries | Positive for home | +4% | Moderate/Low |
| Injury Status Quo | Always | Neutral | 0% | High |
| Star Player Absence Impact | Severe injuries (elbow, shoulder, ACL, fracture) | Depends on which team | ±5% | High |

## Design Decisions

1. **Scenarios are generated per game, not per team** — this keeps the UI focused on the matchup context
2. **Impact is always from home team's perspective** — simplifies the mental model (positive = good for home)
3. **Probability shifts are fixed estimates** — 3% for early returns, 4% for worsening, 5% for star absence. These are calibrated heuristics, not Monte Carlo simulations
4. **Likelihood is based on injury severity** — high severity = higher chance of further issues
5. **Key players are capped at 3** — keeps the UI clean while showing the most relevant names
6. **Star player detection uses keyword matching** — "elbow", "shoulder", "tommy john", "ACL", "fracture" in the injury description

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Scenarios missing from response | Frontend shows no scenario badge | Add `scenarios: Optional[List[Dict]]` to Pydantic model |
| Empty team_id in scenarios | Scenario description shows " has 9 players out" | Verify injury extractor maps team names correctly per sport |
| Scenario badge hidden | Games with injuries show no indicator | Only render when `g.scenarios && g.scenarios.length > 0` |
| Accordion won't open | Clicking badge does nothing | Ensure `toggleScenarios()` is defined in global scope and gameId matches |
| Duplicate scenarios | Same scenario appears twice | Check that generator doesn't append duplicates — each branch should have unique name |
| Probability shifts too large | Adjusted prob goes outside [0,1] | Shifts are applied to the *description* only; the actual adjusted_prob is already clamped |
| No player names shown | "Players:" field is empty | Verify `player_name` field exists in injury dict from extractor |

## Verification

```bash
# Check scenarios are in API response
curl -s "http://localhost:8080/api/schedule/mlb" | python3 -m json.tool | grep -c '"scenarios"'

# Check a specific game's scenarios
curl -s "http://localhost:8080/api/schedule/mlb" | python3 -m json.tool | grep -A20 '"scenarios"' | head -30

# Verify injury data is in corpus
sqlite3 .forecast/corpus.db "SELECT sport, category, COUNT(*) FROM evidence_items WHERE category = 'injury_report' GROUP BY sport;"
```
