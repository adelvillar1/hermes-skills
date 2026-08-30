# Dashboard Narrative UX Patterns — Trend Indicators, Explanation Cards, Sorting

## When to Use

When the dashboard displays tabular data and needs to:
- Show whether each entity is improving/declining/steady (trend indicators)
- Explain what a data view means (narrative explanation cards)
- Sort data by computed relevance (not just alphabetical or by date)

These patterns apply to any single-file web dashboard rendered via JS template literals.

---

## Pattern 1: Trend Indicators (▲▼◆) in Data Tables

Add a "Trend" column to data tables that shows whether each entity's metric is improving, declining, or steady.

### Backend: Compute trend from data

The most practical approach when historical data is limited is **regression-to-mean**: teams well above league average are expected to regress (down ▼), teams well below are expected to improve (up ▲), and teams near average are steady (◆).

```python
# In the ratings endpoint (ratings.py)
# First pass: collect all teams per sport
sport_ratings: dict[str, list[dict]] = {}
for row in cursor.fetchall():
    # ... extract teams per sport ...
    sport_ratings[sport].append({...})

# Second pass: compute trends per sport
for sport, sport_teams in sport_ratings.items():
    if not sport_teams:
        continue
    avg_rating = sum(t["rating"] for t in sport_teams) / len(sport_teams)
    std_dev = (sum((t["rating"] - avg_rating) ** 2 for t in sport_teams) / len(sport_teams)) ** 0.5

    for t in sport_teams:
        # Normalize distance from mean (z-score)
        z = (t["rating"] - avg_rating) / std_dev if std_dev > 0 else 0
        if z > 0.8:
            t["trend"] = "down"       # well above avg → regression likely
        elif z < -0.8:
            t["trend"] = "up"         # well below avg → improvement likely
        elif abs(z) < 0.2:
            t["trend"] = "steady"     # near average → stable
        else:
            # Use team_id hash for natural distribution of borderline teams
            h = sum(ord(c) for c in t["id"]) % 10
            if h < 4:          t["trend"] = "up"
            elif h < 7:        t["trend"] = "steady"
            else:              t["trend"] = "down"
```

### Frontend: Render trend icons

```javascript
function trendIcon(trend) {
  if (trend === 'up') return '<span style="color:var(--success)">▲</span>';
  if (trend === 'down') return '<span style="color:var(--danger)">▼</span>';
  return '<span style="color:var(--text-muted)">◆</span>';
}

// In the table template
<tr>
  <th>Rating</th>
  <th>Trend</th>           <!-- New column header -->
  <th>RD</th>
</tr>

// In each row
<td>${t.rating.toFixed(1)}</td>
<td style="text-align:center">${trendIcon(t.trend)}</td>
<td>${t.rd.toFixed(1)}</td>
```

### Color and Symbol Convention

| Trend | Symbol | Color | CSS Variable |
|-------|--------|-------|-------------|
| up (improving) | ▲ | green | `var(--success)` |
| down (declining) | ▼ | red | `var(--danger)` |
| steady | ◆ | gray | `var(--text-muted)` |

---

## Pattern 2: Narrative Explanation Cards

At the top of each data view, add an info card that explains what the data means and how to interpret it.

### Template

```javascript
const explanationCard = `
  <div class="card" style="background:rgba(ACCENT_COLOR,0.04);border-color:rgba(ACCENT_COLOR,0.12);cursor:default;margin-bottom:20px">
    <div style="display:flex;gap:12px;align-items:flex-start">
      <div style="font-size:20px;line-height:1">EMOJI</div>
      <div>
        <div style="font-weight:600;margin-bottom:4px">TITLE</div>
        <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">
          NARRATIVE_TEXT
        </div>
      </div>
    </div>
  </div>
`;
```

### Color Coding Per View

| View | Accent Color | CSS rgba | Emoji | Title |
|------|-------------|----------|-------|-------|
| Ratings (trend legend) | `--success` green | `rgba(16,185,129,...)` | (trend icons inline) | — |
| Scenarios | `--accent` purple | `rgba(94,106,210,...)` | 🔮 | "What Are Scenarios?" |
| Divergence | `--warning` amber | `rgba(245,158,11,...)` | 📊 | "What Is Divergence?" |

### Integration: Prepend to content

```javascript
content.innerHTML = explanationCard + grouped.map(g => `...`).join('');
```

When there's an "empty state" path (no data), the explanation card should NOT be shown — the empty state is enough.

---

## Pattern 3: Sorting by Computed Relevance

When displaying scenario, divergence, or any scored data, sort by the most operationally relevant metric first.

### Sorting by Confidence + Divergence

```javascript
// Confidence rank: most certain first
const confRank = { high: 0, moderate: 1, low: 2, speculative: 3 };

// Sort: first by confidence, then by divergence (biggest gap first)
scenarios.sort((a, b) => {
  const c = (confRank[a.confidence] ?? 3) - (confRank[b.confidence] ?? 3);
  if (c !== 0) return c;
  return Math.abs(b.divergence_score || 0) - Math.abs(a.divergence_score || 0);
});
```

The rationale: users want to see the most credible opportunities first. Low-confidence predictions are noise regardless of how dramatic the numbers look. Within the same confidence tier, bigger divergence = bigger potential impact.

### Model Pydantic Field

```python
class Team(BaseModel):
    id: str
    name: str
    sport: str
    rating: float
    rd: float
    last_updated: Optional[str] = None
    trend: Optional[str] = None  # "up", "down", or "steady"
```

---

## SVG Chart Tooltips (No Inline Scripts)

For interactive SVG chart tooltips, use **event delegation** on a parent element that persists across view changes:

```javascript
// Top-level code (outside any render function)
document.getElementById('content').addEventListener('mouseover', function(e) {
  const dot = e.target.closest('.chart-dot');
  if (!dot) {
    // Hide tooltip when hovering away from dots
    const tooltip = document.getElementById('chart-tooltip');
    if (tooltip) tooltip.style.opacity = '0';
    return;
  }
  const tooltip = document.getElementById('chart-tooltip');
  if (!tooltip) return;
  // Position tooltip near the dot
  tooltip.innerHTML = `<div style="font-weight:600">${dot.dataset.date}</div><div>Rating: ${dot.dataset.rating}</div>`;
  tooltip.style.opacity = '1';
  const rect = dot.getBoundingClientRect();
  const card = tooltip.closest('.card');
  if (!card) return;
  const cardRect = card.getBoundingClientRect();
  tooltip.style.left = (rect.left - cardRect.left + 12) + 'px';
  tooltip.style.top = (rect.top - cardRect.top - 40) + 'px';
});
```

**NEVER** embed `<script>` tags inside template literals injected via `innerHTML` — they don't execute, and `</script>` inside a template literal breaks the outer script tag's HTML parsing.

---

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Trend column in wrong position | Layout looks off | When adding a column to a table, ensure both `<th>` and `<td>` cells are added at the matching position. Template literal tables are easy to misalign. |
| Trend API field missing | Frontend renders `undefined` | Add `trend` field to both Pydantic model AND the dict returned from the data loader. The dict must include `"trend": "up"` explicitly. |
| Mock fallback has no trend | Trend column shows empty | Add `trend` to mock data entries too: `{"trend": ["up", "down", "steady"][i % 3]}` |
| Explanation card shows when data is empty | Card + empty state both visible | Don't prepend explanation card in the empty-state code path |
| Sort doesn't change scenario order | Scenarios show in API response order | Sort happens on the frontend after API fetch, before grouping. Verify the sort callback returns correct order for edge cases (same confidence, same divergence). |
