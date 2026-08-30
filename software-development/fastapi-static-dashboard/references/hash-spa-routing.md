# Hash-Based SPA Routing for Vanilla JS Dashboards

## When to Use

When a vanilla JS dashboard (no React/Vue/Angular) has multiple views and drill-down pages (e.g., team detail), but page refresh always resets to the default view. Users can't share links, browser back/forward is broken, and bookmarking doesn't work.

## The Problem

A typical vanilla JS dashboard initializes like:

```javascript
function init() {
  initNavigation();
  initFilters();
  setView('ratings');  // Always starts on ratings
}
```

Every refresh loses the user's place. There's no URL state. Back button does nothing useful.

## The Pattern: Hash-Based Routing

Use `window.location.hash` (not `pushState` with paths) for vanilla JS dashboards. Hash routing doesn't trigger page reloads, doesn't require server-side catch-all routes, and works with static file serving.

### Route Design

```
#/ratings                    → main view
#/scenarios                  → main view
#/schedule                   → main view
#/team/{sport}/{id}          → team detail
#/team/{sport}/{id}/history  → team detail tab
#/game/{sport}/{idx}         → match modal
```

### Core Implementation

```javascript
// Parse hash into route object
function parseHash() {
  const hash = window.location.hash.slice(1) || '';
  const parts = hash.split('/').filter(Boolean);
  if (!parts.length) return { view: 'ratings', team: null, tab: null, game: null };

  if (parts[0] === 'team' && parts.length >= 3) {
    return { view: null, team: { sport: parts[1].toUpperCase(), id: parts[2] }, tab: parts[3] || 'overview', game: null };
  }

  if (parts[0] === 'game' && parts.length >= 3) {
    return { view: null, team: null, tab: null, game: { sport: parts[1], idx: parseInt(parts[2], 10) } };
  }

  const validViews = ['ratings', 'scenarios', 'schedule', 'accuracy', 'pipeline'];
  if (validViews.includes(parts[0])) {
    return { view: parts[0], team: null, tab: null, game: null };
  }

  return { view: 'ratings', team: null, tab: null, game: null };
}

// Update hash without triggering popstate
function setHash(hash) {
  if (window.location.hash.slice(1) === hash) return;
  history.pushState(null, '', '#' + hash);
}

// Navigation functions (these both update hash AND trigger render)
function navigateToView(view) {
  setHash(view);
  state.selectedTeam = null;
  setView(view);
}

function navigateToTeam(sport, teamId, tab) {
  const hash = tab ? `team/${sport.toLowerCase()}/${teamId}/${tab}` : `team/${sport.toLowerCase()}/${teamId}`;
  setHash(hash);
  state.selectedTeam = { id: teamId, sport: sport.toUpperCase() };
  renderTeamDetail(state.selectedTeam);
}
```

### Init with Hash Restoration

```javascript
function init() {
  initNavigation();
  initFilters();
  restoreFromHash();
  window.addEventListener('popstate', () => restoreFromHash());
}

function restoreFromHash() {
  const route = parseHash();

  if (route.team) {
    state.selectedTeam = { id: route.team.id, sport: route.team.sport };
    state.detailTab = route.tab || 'overview';
    renderTeamDetail(state.selectedTeam);
    return;
  }

  if (route.game) {
    state.league = route.game.sport.toUpperCase();
    setView('schedule');
    // Wait for async data, then show modal
    const check = () => {
      if (scheduleGames.length > route.game.idx) {
        showMatchDetail(route.game.idx);
      } else {
        requestAnimationFrame(check);
      }
    };
    requestAnimationFrame(check);
    return;
  }

  setView(route.view || 'ratings');
}
```

### Preventing Hash Update Loops

When restoring from hash (page load or popstate), the render functions will try to update the hash again via `navigateToTeam()` etc. Use a flag to prevent this:

```javascript
function restoreFromHash() {
  window._restoringHash = true;
  // ... restore logic ...
  window._restoringHash = false;
}

// In showMatchDetail:
if (!window._restoringHash) {
  setHash(`game/${sport}/${gameIdx}`);
}
```

## Cross-Linking Team Names

### Making any entity name clickable

Wrap entity names in spans with navigation onclick:

```javascript
// In any render function that shows team names
`<span class="clickable-team" onclick="dashboard.navigateToTeam('${team.id}', '${sport}')">${escapeHtml(team.name)}</span>`
```

Use `event.stopPropagation()` when the clickable name is inside a parent with its own onclick (e.g., schedule cards that open a modal on click):

```javascript
`<span class="clickable-team" onclick="event.stopPropagation(); dashboard.navigateToTeam('${team.id}', '${sport}')">${name}</span>`
```

### CSS for clickable names

```css
.clickable-team {
  cursor: pointer;
  transition: color 0.15s;
  border-bottom: 1px dotted transparent;
}
.clickable-team:hover {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
```

### Required: team IDs in API responses

For cross-linking to work, API responses must include team IDs alongside team names. Check every endpoint that returns team names:

- Schedule games → `home_team.id`, `away_team.id`
- Accuracy predictions → add `home_team_id`, `away_team_id` to response dicts
- Scenarios → `team_id`, `opponent_id`
- Roster upcoming games → `opponent_id`

If the API only returns names, add the ID fields before implementing the cross-links.

## Navigation Assessment Methodology

When auditing a dashboard's navigation health, use a cross-view linkage matrix:

1. **List every view** in the app (Ratings, Scenarios, Schedule, Accuracy, Team Detail, etc.)
2. **For each view, list every entity reference** (team names, game cards, scenario cards)
3. **Check: is this reference clickable? Does it navigate to the entity's detail page?**
4. **Score each link**: ✅ Working, ❌ Dead (not clickable), ⚠️ Partial (clicks but wrong state)

### Example matrix

| Source View | Entity Reference | Target | Status |
|-------------|-----------------|--------|--------|
| Schedule card team names | Home/Away team | Team detail | ❌ Dead |
| Accuracy table teams | Home/Away team | Team detail | ❌ Dead |
| Match modal teams | Team names | Team detail | ❌ Dead |
| Team detail stat cards | "Scenarios: 2" | Scenarios tab | ❌ Dead |
| Ratings table rows | Team name | Team detail | ✅ Working |

### Priority ranking

- **P0**: URL persistence (hash router) — affects all views
- **P1**: Cross-linking primary entities (team names everywhere)
- **P2**: Team detail page enrichment (next game, clickable stat cards)
- **P3**: Cross-view deep links (scenario → game, pipeline → corpus)

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `pushState` with real paths | 404 on refresh — static file server doesn't know about `/team/mlb/nyy` | Use hash routing (`#/...`) instead |
| Modal hash restoration before data loads | `Cannot read property of undefined` when restoring game from URL | Use `requestAnimationFrame` polling or async await for data load |
| Hash update in render loop | URL flickers or `popstate` fires recursively | Use `_restoringHash` flag; `setHash` checks for same-hash no-op |
| Team ID with special chars | Broken onclick attributes | Sanitize IDs; use data attributes + event delegation instead of inline onclick |
| `stopPropagation` missing on nested clickables | Clicking team name in schedule card opens both team detail AND match modal | Add `event.stopPropagation()` to inner clickable handlers |
| API doesn't return team IDs | Cross-links pass `''` as team ID | Add `home_team_id`/`away_team_id` to API response dicts before implementing links |

## Verification Checklist

- [ ] Refresh on `#/scenarios` stays on scenarios view
- [ ] Refresh on `#/team/mlb/nyy/history` opens Yankees with history tab
- [ ] Browser back from team detail returns to previous view
- [ ] Direct-link `#/accuracy` in new tab opens accuracy view
- [ ] Clicking team name in schedule/accuracy/modal navigates to team detail
- [ ] URL updates correctly on every navigation
- [ ] No console errors on any route
