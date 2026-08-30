# Risk Appetite Adjustment for Sports Predictions

Adjust win probabilities based on user risk profile (conservative / balanced / aggressive). Applied on top of scenario-adjusted base probabilities.

## When to Use

- Sports betting / prediction dashboards where users want different probability thresholds
- Any forecasting UI where "how sure do I need to be before acting?" varies by user
- Building a tiered recommendation system (hold / standard / chase upside)

## API Design

Add a `risk` query parameter to the schedule endpoint:

```python
@router.get("/{sport}", response_model=ScheduleResponse)
async def get_schedule(
    sport: str,
    risk: str = Query("balanced", description="Risk appetite: conservative, balanced, aggressive"),
):
    risk_lower = risk.lower()
    if risk_lower not in ("conservative", "balanced", "aggressive"):
        risk_lower = "balanced"
    results = _compute_probabilities(games, ratings, sport_lower, risk_lower)
```

## Risk Profile Math

### Conservative
- **Goal:** Only bet on clear favorites with low uncertainty
- **Formula:** `adjusted = 0.5 + (base - 0.5) * (1 - shrink)` where `shrink = 0.3 + 0.4 * uncertainty`
- **Bet threshold:** Edge > 8% (probability > 58% or < 42%)
- **Label:** "Hold unless clear favorite"

### Balanced (default)
- **Goal:** Standard edge with slight uncertainty discount
- **Formula:** `adjusted = 0.5 + (base - 0.5) * (1 - 0.05 * uncertainty)`
- **Bet threshold:** Edge > 3% (probability > 53% or < 47%)
- **Label:** "Standard edge"

### Aggressive
- **Goal:** Chase upside — amplify underdog edges, especially when uncertain
- **Formula:**
  - Underdog (`base < 0.5`): `adjusted = base * (1 + 0.25 * uncertainty)`
  - Favorite (`base >= 0.5`): `adjusted = 0.5 + (base - 0.5) * (1 + 0.1 * uncertainty)`
- **Bet threshold:** Edge > 5% (probability > 45% or < 55%)
- **Label:** "Chase upside"

### Uncertainty Factor

Derived from Glicko-2 rating deviation (phi):

```python
avg_phi = (phi_home + phi_away) / 2
uncertainty = min(1.0, avg_phi / 350)  # 0 = certain, 1 = max uncertainty
```

Higher phi = more unknown about the teams = more impact from risk profile.

## Response Enrichment

Add `risk_adjusted` object to each game:

```json
{
  "home_win_prob": 0.516,
  "risk_adjusted": {
    "profile": "aggressive",
    "base_probability": 0.515,
    "adjusted_probability": 0.516,
    "uncertainty": 0.465,
    "edge": 0.016,
    "recommendation": "bet",
    "label": "Chase upside",
    "expected_value_proxy": 0.032
  }
}
```

## Frontend Integration

### Risk Selector UI

Three pill buttons in the view header, persisted to `localStorage`:

```html
<div style="display: flex; gap: 6px; background: var(--bg-surface); padding: 4px; border-radius: 8px;">
  <button onclick="setRiskProfile('conservative')" id="risk-conservative">Conservative</button>
  <button onclick="setRiskProfile('balanced')" id="risk-balanced">Balanced</button>
  <button onclick="setRiskProfile('aggressive')" id="risk-aggressive">Aggressive</button>
</div>
```

### State Management

```javascript
let riskProfile = localStorage.getItem('riskProfile') || 'balanced';

function setRiskProfile(profile) {
  riskProfile = profile;
  localStorage.setItem('riskProfile', profile);
  // Update active button style
  document.querySelectorAll('.risk-btn').forEach(btn => {
    btn.style.background = 'transparent';
    btn.style.color = 'var(--text-muted)';
  });
  document.getElementById(`risk-${profile}`).style.background = 'var(--accent)';
  document.getElementById(`risk-${profile}`).style.color = 'white';
  // Re-render
  renderUpcoming(document.getElementById('content'));
}
```

### Game Card Badge

Show risk label + recommendation on each card:

```javascript
${g.risk_adjusted ? `
  <span style="${g.risk_adjusted.recommendation === 'bet' 
    ? 'background: rgba(16,185,129,0.12); color: var(--success);' 
    : 'background: rgba(255,255,255,0.03); color: var(--text-muted);'}"
  >${g.risk_adjusted.label} · ${g.risk_adjusted.recommendation.toUpperCase()}</span>
` : ''}
```

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Probabilities go negative | Aggressive profile pushes underdog below 0 | Clamp to [0.05, 0.95] after adjustment |
| All recommendations "pass" | Conservative profile too strict | Verify edge threshold matches use case (8% may be too high for some sports) |
| Risk param ignored | API always returns balanced | Validate `risk` param in endpoint; default to "balanced" on invalid input |
| Frontend doesn't persist selection | Selector resets on page reload | Store in `localStorage` and read on init |
| Badge styling inconsistent | Green "BET" not visible | Use CSS variables for colors; ensure contrast against dark background |
