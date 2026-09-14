# Format.js namespace pitfall — full reproduction and fix

This is the exact debugging sequence that ate ~2 hours of a 4-hour refactor session. Captured here so a future agent can skip it.

## Symptom

After extracting `escapeHtml`, `formatDate`, `groupByLeague`, etc. into a new `ui/js/lib/format.js` module, the dashboard's Ratings view shows "Failed to load data" and the browser console has the empty `{ "message": "" }` error pattern.

A `console.error` injected into the IIFE's `loadView` catch block reveals:

```
[PR2-DEBUG] loadView catch: escapeHtml is not a function TypeError: escapeHtml is not a function
    at renderTopPicksSection (dashboard.js:2735:206)
    at renderToday (dashboard.js:2611:26)
    at async loadView (dashboard.js:150:23)
```

Note: the error is in `renderToday` (called on initial dashboard load), not in `renderRatings` (the view the user clicked into). The user clicks Ratings, but `loadView('today')` was already called by `init()` on first load and threw, so the content area is showing the "Failed to load data" empty state from the earlier failed call.

## Diagnose in 30 seconds

In the browser console on the dashboard page:

```js
// Check which functions are missing
typeof globalThis.escapeHtml        // "undefined" — bug
typeof globalThis.formatDate        // "undefined" — bug
typeof globalThis.groupByLeague     // "undefined" — bug
typeof globalThis.escapeHtml        // "function" — correct

// Check if they're in a namespace
typeof globalThis.Format            // "object" — namespace exists
typeof globalThis.Format?.escapeHtml // "function" — there it is
```

If `Format.X` is a function but `X` directly is undefined, the module used the namespace pattern and forgot the individual exports.

## Root cause

`ui/js/lib/format.js` (PR1 implementation) exposed helpers ONLY under a namespace:

```js
if (typeof globalThis !== 'undefined') {
  globalThis.Format = {
    escapeHtml, formatDate, timeAgo, absoluteTimestamp,
    trendIcon, posChangeBadge, confidenceBadge,
    groupByLeague, leagueBadgeClass, LEAGUE_ORDER, CONFIDENCE_TOOLTIPS,
  };
}
```

The IIFE in `dashboard.js` does `const escapeHtml = _lookupGlobal('escapeHtml')` at the top, which returns `undefined` because the helper is nested under `Format`.

## Fix

Add individual `globalThis.X = X` lines alongside the namespace export. Keep the namespace for backwards compatibility (other code may use it).

```js
if (typeof globalThis !== 'undefined') {
  // PR-N: expose each helper directly on globalThis so the IIFE's
  // _lookupGlobal('X') aliases resolve. The Format namespace is kept
  // for backwards compatibility but isn't required by the IIFE.
  globalThis.escapeHtml = escapeHtml;
  globalThis.formatDate = formatDate;
  globalThis.timeAgo = timeAgo;
  globalThis.absoluteTimestamp = absoluteTimestamp;
  globalThis.trendIcon = trendIcon;
  globalThis.posChangeBadge = posChangeBadge;
  globalThis.confidenceBadge = confidenceBadge;
  globalThis.groupByLeague = groupByLeague;
  globalThis.leagueBadgeClass = leagueBadgeClass;
  globalThis.LEAGUE_ORDER = LEAGUE_ORDER;
  globalThis.CONFIDENCE_TOOLTIPS = CONFIDENCE_TOOLTIPS;
  // Backwards-compat: keep the namespace too.
  globalThis.Format = {
    escapeHtml, formatDate, timeAgo, absoluteTimestamp,
    trendIcon, posChangeBadge, confidenceBadge,
    groupByLeague, leagueBadgeClass, LEAGUE_ORDER, CONFIDENCE_TOOLTIPS,
  };
}
```

## The browser cache trap that compounds the fix

After applying the fix, the browser may STILL show the old behavior because:

1. The `<script type="module" src="/js/lib/format.js">` tag in `dashboard.html` loaded the old version of format.js on the FIRST page load. That module is now in the browser's module cache.
2. The IIFE's `Promise.all([import('/js/lib/format.js')])` returns the cached module object. ES modules cache by URL — the cached module's top-level code already ran, with the old side effects.
3. So `globalThis.escapeHtml` is still undefined, even though the new file is on disk.

Three options, in order of preference:

### Option A: Cache buster (recommended)

```js
// dashboard.js — top of file
const _modulePromises = [
  import('/js/lib/format.js?cb=' + Date.now()),
  // ... other modules with the same buster
];
```

Forces the browser to re-fetch on every page load. Simple, predictable.

### Option B: Remove the `<script type="module" src="...">` tags

If `dashboard.html` doesn't preload the modules, the IIFE's dynamic import is the only loader. The browser's module cache only has the version the IIFE loaded.

### Option C: Clear the module cache manually

`chrome://settings/clearBrowserData` → "Cached images and files" → restart browser. Painful, but works.

## Diagnostic snippet to keep handy

Save this as a bookmarklet or run in the browser console after any IIFE→module refactor:

```js
// Returns an object listing which dual-exported helpers are missing
// on globalThis. Each missing one is a Pitfall 1 violation in the
// corresponding module.
(() => {
  const EXPECTED = [
    'escapeHtml', 'formatDate', 'timeAgo', 'absoluteTimestamp',
    'trendIcon', 'posChangeBadge', 'confidenceBadge',
    'groupByLeague', 'leagueBadgeClass', 'LEAGUE_ORDER', 'CONFIDENCE_TOOLTIPS',
    'els', 'state', 'api', 'toast', 'showToast', 'parseHash', 'setHash',
    'initNavigation', 'initFilters', 'setView', 'setLeague',
    'setRatingsSort', 'buildQuery', 'navigateToView', 'navigateToTeam',
    'restoreFromHash', 'copyAnchorLink', 'copyTeamLink', 'initBackToTop',
    'initKeyboardShortcuts', 'showKbdHelp', 'KEYBOARD_CHORDS',
    'skeleton', 'emptyState', 'setupTableSort', 'sortBy',
  ];
  return EXPECTED.reduce((acc, k) => {
    if (typeof globalThis[k] === 'undefined') acc.missing.push(k);
    return acc;
  }, { missing: [] });
})();
```

If `missing` is non-empty, the IIFE's `_lookupGlobal` aliases will be `undefined` and bare references inside function bodies will throw at call time.
