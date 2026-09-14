# Lazy view modules must be loaded before global renderer callers

**Project:** the ELO scenario lab  
**Date:** 2026-06-14  
**Related skill:** `legacy-iife-to-es-modules` (Pitfall 10)

## Symptom

Clicking a team in any view (Ratings, Today, Scenarios, Divergence) updated the URL hash to `#team/{sport}/{id}` but did **not** render the team detail page. Direct `#team/...` URLs behaved the same: hash set, content unchanged. No console error appeared.

## Root cause

After the frontend modular refactor, `team-detail.js` and `match-detail.js` were lazy-loaded by `ui/js/lib/router.js` on first navigation. Each module exports its renderer to `globalThis` as a side effect:

```js
// ui/js/views/team-detail.js
globalThis.renderTeamDetail = renderTeamDetail;
```

But `ui/js/lib/hash.js` — which handles `navigateToTeam()` and `restoreFromHash()` — called those globals directly without loading the modules first:

```js
function navigateToTeam(sport, teamId) {
  setHash(`team/${sport}/${teamId}`);
  if (typeof globalThis.renderTeamDetail === 'function') {
    globalThis.renderTeamDetail({ id: teamId, sport });
  }
}
```

If the user had not yet visited the team-detail view, `globalThis.renderTeamDetail` was `undefined`. The `typeof` guard silently skipped rendering, so the hash changed but the page stayed put.

## Fix

1. Added `loadModule(name)` to the router's public API so non-router callers can import a view module without triggering a render:

```js
// ui/js/lib/router.js
async function loadModule(name) { return _importView(name); }

globalThis.Router = { loadView, preloadView, preloadViews, loadModule };
```

2. Made `navigateToTeam()` and the `#team/...` / `#game/...` branches of `restoreFromHash()` await the module load before invoking the renderer:

```js
async function navigateToTeam(sport, teamId) {
  setHash(`team/${sport}/${teamId}`);
  await globalThis.Router?.loadModule?.('team-detail');
  if (typeof globalThis.renderTeamDetail === 'function') {
    globalThis.renderTeamDetail({ id: teamId, sport });
  }
}
```

## Verification

- Vitest: 113 passed
- Pytest: 932 passed, 7 skipped
- Browser: clicked a team row in the Ratings table → navigated to the Cardinals team detail page.

## Commit

`cc7b891` — fix(ui): load lazy team-detail/match-detail modules before rendering from hash or click

## Lesson

Any caller that invokes a `globalThis.renderX` or `globalThis.showX` owned by a lazy view module must ensure the module is loaded first. The `typeof` guard that silently skips an undefined renderer is the anti-pattern; replace it with an explicit preload, or preload deep-linkable views at app startup.
