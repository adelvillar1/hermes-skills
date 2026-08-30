# Team-Centric Dashboard Pattern — League Grouping + Drill-Down

## When to Use

When the dashboard needs to be organized around leagues/sports and teams rather than generic data views. Users navigate by league first, then drill into individual teams for detailed analysis.

## Pattern Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar: Views (Ratings, Scenarios, Divergence, Schedule)  │
│  Topbar: League Filter + Team Search                        │
├─────────────────────────────────────────────────────────────┤
│  Main Content:                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  MLB        │  │  NBA        │  │  NFL        │        │
│  │  26 teams   │  │  8 teams    │  │  30 teams   │        │
│  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │        │
│  │  │Team 1 │  │  │  │Team 1 │  │  │  │Team 1 │  │        │
│  │  │Team 2 │  │  │  │Team 2 │  │  │  │Team 2 │  │        │
│  │  │ ...   │  │  │  │ ...   │  │  │  │ ...   │  │        │
│  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  Click any team → Team Detail Page                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  [Avatar] Team Name          [Back]                 │   │
│  │  Sport · ID · Rating · RD                           │   │
│  │  [Overview] [History] [Scenarios] [Divergence]      │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │   │
│  │  │ Rating │ │   RD   │ │ Trend  │ │Scenarios│       │   │
│  │  │ 1808.1 │ │ 176.3  │ │ +12.5  │ │   2     │       │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘       │   │
│  │  Recent History Table                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Backend Changes

### 1. Team History Endpoint Must Use Corpus Data

The `GET /api/teams/{sport}/{team_id}/history` endpoint must read from the same data source as the ratings endpoint (corpus DB), not mock data with different ID formats.

**Problem:** If ratings endpoint returns team IDs like `MIL`, `OKC` but history endpoint looks for `mlb-0`, `mlb-1`, drill-down will 404.

**Fix:**
```python
# src/api/routes/teams.py
@router.get("/{sport}/{team_id}/history", response_model=TeamDetail)
async def get_team_history(sport: str, team_id: str):
    # Try corpus first, then mock
    teams = _load_corpus_teams(sport)
    if not teams:
        teams = _load_mock_teams()
    
    team = next((t for t in teams if t["id"] == team_id), None)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Generate history, scenarios, divergence from team data
    ...
```

### 2. Group By League Helper

```javascript
function groupByLeague(items, sportKey = 'sport') {
  const groups = {};
  const order = ['MLB', 'NFL', 'NBA'];
  for (const item of items) {
    const sport = item[sportKey]?.toUpperCase() || 'OTHER';
    if (!groups[sport]) groups[sport] = [];
    groups[sport].push(item);
  }
  return order.filter(s => groups[s]).map(s => ({ sport: s, items: groups[s] }));
}
```

## Frontend Structure

### State Management

```javascript
const state = {
  view: 'ratings',        // current sidebar view
  league: '',             // topbar league filter
  teamFilter: '',         // topbar team search
  selectedTeam: null,     // { id, sport } when drilling down
  detailTab: 'overview',  // active tab on team detail
};
```

### Navigation Flow

1. **Sidebar click** → `state.selectedTeam = null` → load league-grouped view
2. **Team click** → `state.selectedTeam = { id, sport }` → load team detail
3. **Back button** → `state.selectedTeam = null` → return to previous view
4. **League filter change** → `state.selectedTeam = null` → reload current view

### Team Detail Page

```javascript
async function renderTeamDetail(team) {
  const detail = await api(`/api/teams/${team.sport.toLowerCase()}/${team.id}/history`);
  
  // Header with avatar, name, meta, back button
  // Tabs: Overview, History, Scenarios, Divergence
  // Tab content rendered based on state.detailTab
}

function setDetailTab(tab) {
  state.detailTab = tab;
  renderTeamDetail(state.selectedTeam);
}

function closeTeamDetail() {
  state.selectedTeam = null;
  state.detailTab = 'overview';
  loadView(state.view);
}
```

### Tab Content

**Overview:** Stat cards (Rating, RD, Trend, Scenarios count, Divergence alerts) + **next game preview** + recent history table
**History:** Full rating history with day-over-day changes
**Scenarios:** Team-specific scenarios grouped by opponent with confidence badges
**Divergence:** Baseline vs scenario ratings with visual magnitude bars + opportunity levels

### Overview Enrichment Patterns

#### Clickable Stat Cards

Make overview stat cards navigate to their corresponding tabs (e.g., clicking "Scenarios: 2" switches to the Scenarios tab):

```javascript
`<div class="stat-card clickable-stat" onclick="dashboard.setDetailTab('scenarios')">
  <div class="stat-label">Scenarios</div>
  <div class="stat-value">${detail.scenarios?.length || 0}</div>
  <div class="stat-hint">Click to view</div>
</div>`
```

```css
.clickable-stat { cursor: pointer; transition: border-color 0.15s; }
.clickable-stat:hover { border-color: var(--accent); }
.stat-hint { font-size: 10px; color: var(--text-faint); opacity: 0; transition: opacity 0.15s; }
.clickable-stat:hover .stat-hint { opacity: 1; }
```

#### Next Game Preview Card

Add a "Next Game" card below the stat grid, sourced from a `next_game` field on the team detail API response:

**Backend:** Compute from the first upcoming game in the team's schedule:
```python
# In GET /api/teams/{sport}/{team_id}/history
upcoming_games = [g for g in schedule if team_id in (g.get("home_team_id"), g.get("away_team_id"))]
next_game = None
if upcoming_games:
    g = upcoming_games[0]
    opponent_id = g.get("away_team_id") if g.get("home_team_id") == team_id else g.get("home_team_id")
    next_game = {
        "date": g.get("date", ""),
        "opponent_id": opponent_id,
        "opponent_name": ratings.get(opponent_id, {}).get("name", opponent_id),
        "venue": "home" if g.get("home_team_id") == team_id else "away",
        "game_id": g.get("game_id", ""),
    }
# Add to response: TeamDetail(... next_game=next_game)
```

**Frontend:**
```javascript
${detail.next_game ? `
<div class="card card-static">
  <div class="card-title" style="margin-bottom:12px">Next Game</div>
  <div class="next-game-card">
    <div class="next-game-team">${escapeHtml(detail.team.name)}</div>
    <div class="next-game-vs">vs</div>
    <div class="next-game-team">
      <span class="clickable-team" onclick="dashboard.navigateToTeam('${escapeHtml(detail.next_game.opponent_id)}', '${team.sport}')">${escapeHtml(detail.next_game.opponent_name)}</span>
    </div>
  </div>
  <div class="next-game-meta">${detail.next_game.date} · ${detail.next_game.venue === 'home' ? 'Home' : 'Away'}</div>
</div>` : ''}
```

### Divergence Magnitude Bars

Add colored proportional bars to the divergence table for quick visual scanning:

```javascript
`<div class="divergence-bar-wrap">
  <div class="divergence-bar ${d.divergence_pct > 5 ? 'bar-danger' : d.divergence_pct > 3 ? 'bar-warning' : 'bar-success'}"
       style="width: ${Math.min(d.divergence_pct * 10, 100)}%"></div>
</div>`
```

```css
.divergence-bar-wrap { width: 100%; height: 6px; background: var(--bg-surface); border-radius: 3px; overflow: hidden; }
.divergence-bar { height: 100%; border-radius: 3px; transition: width 0.3s; }
.bar-success { background: var(--success); }
.bar-warning { background: var(--warning); }
.bar-danger { background: var(--danger); }
```

### Grouped Scenarios by Opponent

Instead of a flat list, group scenarios by opponent/game to show all branches for one matchup together:

```javascript
function renderScenariosTab(detail) {
  const scenarios = detail.scenarios || [];
  if (!scenarios.length) return emptyState('No scenarios for this team');

  // Group by opponent or game_id
  const groups = {};
  for (const s of scenarios) {
    const key = s.opponent || s.game_id || 'unknown';
    if (!groups[key]) groups[key] = { opponent: s.opponent, scenarios: [] };
    groups[key].scenarios.push(s);
  }

  return Object.values(groups).map(g => `
    <div class="scenario-group">
      <div class="scenario-group-header">vs ${escapeHtml(g.opponent)}</div>
      <div class="scenario-inline">
        ${g.scenarios.map(s => `
          <div class="card">
            <div class="card-grid-3col">
              <div><div class="team-sport">Base</div><div class="card-value">${(s.base_prob*100).toFixed(0)}%</div></div>
              <div><div class="team-sport">Adjusted</div><div class="card-value" style="color:var(--accent-light)">${(s.adjusted_prob*100).toFixed(0)}%</div></div>
              <div><div class="team-sport">Divergence</div><div class="card-value">${(s.divergence_score*100).toFixed(1)}%</div></div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}
```

```css
.scenario-group { margin-bottom: 24px; }
.scenario-group-header { font-weight: 600; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle); }
.scenario-inline { display: flex; gap: 12px; flex-wrap: wrap; }
.scenario-inline .card { flex: 1; min-width: 200px; }
```

## League Section Styling

```css
.league-group { margin-bottom: 32px; }
.league-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 16px; padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.league-badge {
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; text-transform: uppercase;
}
.league-badge.mlb { background: rgba(94,106,210,0.15); color: var(--accent-light); }
.league-badge.nfl { background: rgba(16,185,129,0.15); color: var(--success); }
.league-badge.nba { background: rgba(245,158,11,0.15); color: var(--warning); }
```

## Click Targets

Every team row/card should be clickable:
- Ratings table rows → team detail
- Scenario cards → team detail  
- Divergence table rows → team detail
- Schedule game cards → home team detail

```javascript
// In render functions
tr onclick="selectTeam('${t.id}', '${t.sport}')"
// or
div class="card" onclick="selectTeam('${s.team_id}', '${s.sport}')"
```

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| History endpoint uses mock IDs | 404 when clicking team | Update endpoint to search corpus first, match by actual team ID |
| Team click doesn't navigate | Nothing happens on click | Ensure `selectTeam()` is in global scope (not inside module) |
| Back button missing | Stuck on team detail | Add back button with `onclick="closeTeamDetail()"` |
| Tab state lost on re-render | Always shows Overview after clicking tab | Store `state.detailTab` and pass to render function |
| League filter doesn't clear team detail | Shows team from wrong league | Set `state.selectedTeam = null` on league change |
| Stat cards overflow on mobile | Horizontal scroll or clipped content | Use `grid-template-columns: repeat(auto-fill, minmax(140px, 1fr))` |

## Verification

- [ ] Ratings view shows MLB section → NBA section (grouped by league)
- [ ] Each league section has badge, name, team count
- [ ] Clicking any team row opens team detail page
- [ ] Team detail shows avatar, name, sport, rating, RD
- [ ] Team detail has Back button that returns to previous view
- [ ] Team detail has 4 tabs: Overview, History, Scenarios, Divergence
- [ ] Overview tab shows stat cards + recent history table
- [ ] History tab shows full 30-day history with changes
- [ ] Scenarios tab shows team-specific scenarios
- [ ] Divergence tab shows baseline vs scenario comparison
- [ ] Tab switching works without full page reload
- [ ] League filter clears team detail and shows filtered leagues
- [ ] Team search filters within current view
