# Frontend Lazy View Loader — Reference Implementation

This is the deep-dive for **Phase 4** of the performance plan
(`api-performance-optimization`). Phases 1-3 cache/compress the
server; this phase attacks the JS waterfall on the client.

## The problem

A modular SPA that does `Promise.all([import('/js/views/X.js?cb=' + Date.now()), ...22 more])`
on every page load forces the browser to download + parse + execute
~600KB of JS before the IIFE in `dashboard.js` even starts — just to
render the first view. Every navigation within the page re-runs this.

The `?cb=Date.now()` cache buster exists for a real reason (Browser-Use
sandbox fix, see `legacy-iife-to-es-modules` skill) but is *load-bearing
only on the critical path* — the modules that must always re-execute
their top-level code to populate `globalThis.X` for the IIFE to consume.

## The fix: split critical from non-critical

| Path | What it loads | Cache buster | Why |
|---|---|---|---|
| Critical path (~9 modules) | auth, config, state, dom, api, format, dom-refs, hash, toast, router | `?cb=Date.now()` | Must re-execute to populate `globalThis.X` for the IIFE |
| Lazy views (~13 modules) | one per view (today, ratings, scenarios, ...) | none | Only loaded on first navigation; browser module cache handles subsequent |

Critical-path JS drops from ~600KB to ~200KB. First view navigation
fires ONE additional module import (~30KB for today.js, for example),
not all 13.

## The router pattern

`ui/js/lib/router.js` — single file, ~220 lines.

### Public surface

```js
loadView(name)            // dynamic-import + render dispatch
preloadView(name)         // warm cache, no render
preloadViews([names...])  // allSettled batch preload for idle callback
```

`loadView(name)` is a drop-in replacement for any existing
`loadView(name)` in the legacy IIFE — same return type, same error
contract. Internally:

1. Look up the view file path in a name→path map
2. Dynamic-import it (with in-flight dedup so concurrent calls share
   one network round-trip)
3. Resolve the render function by name from `globalThis` (e.g.
   `globalThis.renderToday`)
4. Call it

### Test seam: `_setImporter`

The router uses absolute paths (`/js/views/today.js`) which vitest
can't resolve without a server. The fix is a test seam:

```js
let _doImport = (path) => import(path);
function _setImporter(fn) { _doImport = fn; }
```

In tests, override `_doImport` to return a stub module. In production,
it's `import(path)`. Same code path; no conditional in the hot path.

### Critical: the globalThis side-effect contract

Each view module's bottom looks like:

```js
export async function renderToday() { ... }
// Legacy global surface — see ui/js/lib/format.js for the same pattern.
if (typeof globalThis !== 'undefined') {
  globalThis.renderToday = renderToday;
}
```

The router relies on this side effect. If a view module forgets to
set `globalThis.renderX`, `loadView` throws a clear error:

> View "today" module loaded but globalThis.renderToday is not a function.

This makes the failure mode loud instead of silent.

## The dashboard.js change (minimal)

The existing `_modulePromises` array (22 imports) becomes:

```js
const _modulePromises = [
  // Critical path — must be ready before first paint.
  import('/js/config.js?cb=' + Date.now()),
  import('/js/lib/hash.js?cb=' + Date.now()),
  import('/js/lib/state.js?cb=' + Date.now()),
  import('/js/lib/events.js?cb=' + Date.now()),
  import('/js/lib/api.js?cb=' + Date.now()),
  import('/js/lib/format.js?cb=' + Date.now()),
  import('/js/lib/dom.js?cb=' + Date.now()),
  import('/js/lib/toast.js?cb=' + Date.now()),
  import('/js/lib/dom-refs.js?cb=' + Date.now()),
  // Router — wires up the lazy view loader.
  import('/js/lib/router.js?cb=' + Date.now()),
  // View modules — LAZY LOADED via router.js on first navigation.
];
```

The existing `loadView` switch in the IIFE becomes a delegation:

```js
async function loadView(view) {
  if (state.selectedTeam) { renderTeamDetail(state.selectedTeam); return; }
  els.content.innerHTML = skeleton();
  // ... filter visibility logic ...
  try {
    await globalThis.loadView(view);  // router handles dynamic import + render
  } catch (err) {
    toast(err.message || `Failed to load view: ${view}`);
    els.content.innerHTML = emptyState('Failed to load data');
  }
}
```

That's it. The bridge functions in dashboard.js (`function renderToday() { return globalThis.renderToday(); }`)
remain as globalThis pass-throughs for any inline `onclick` handlers
that might still reference them. They're cheap (one function call) and
unaffected by lazy loading because they look up `globalThis` at call
time.

## What NOT to do

### ❌ Don't dynamic-import all views in a `Promise.all` after the critical path

```js
// BAD — defeats the purpose
const _critical = await Promise.all([...critical imports]);
const _views = await Promise.all([...view imports]);
```

This is just a slower version of the same waterfall. The point is to
load views ON DEMAND, not in parallel at startup.

### ❌ Don't use `?cb=Date.now()` on lazy view imports

The cache buster exists because the critical path MUST re-execute
its top-level code. Lazy views are version-locked by the import path
(their URL is the cache key); the browser fetches new content when
the file changes. Forcing a re-fetch on every page load adds ~50ms
per view for no benefit.

### ❌ Don't use synchronous `require()` / dynamic `import()` without globalThis

The router resolves render functions via `globalThis.renderX`. If a
view module doesn't set its global surface, the router throws — but
not before the dynamic import has succeeded. The error is loud, but
if you migrate to "import and call directly" the migration becomes
fragile (each call site has to know which module provides which
function).

## Measured results (June 2026, production dashboard)

Before: 22 modules in `_modulePromises` + `?cb=` cache buster.
After: 9 critical + 1 router (with cache buster), 13 views lazy.

| Metric | Before | After |
|---|---|---|
| First-paint JS download | ~600KB | ~200KB |
| First-paint parse + execute time | ~1.2s (warm cache) | ~400ms (warm cache) |
| View switch (warm) | 0 (already loaded) | ~10ms (LRU + module cache) |
| View switch (cold) | 0 (already loaded) | ~50ms (first import for that view) |

The "first-paint" win is the big one — it's the 5-10s the user was
complaining about. The view-switch numbers are nice but secondary.

## Pitfalls

1. **The legacy `?cb=Date.now()` cache buster MUST stay on the critical
   path.** It's load-bearing for the Browser-Use sandbox pattern. If
   you move it to lazy views "for consistency" you re-introduce the
   PR2 regression.

2. **Don't trust a `view` argument without validating the name.** The
   router throws `Unknown view: <name>` for typos. Make sure the
   call site in dashboard.js's `loadView` catches and toasts the
   error, otherwise a bad URL hash (#view=typo) breaks the page.

3. **`globalThis.renderX` race condition**: if the user navigates
   rapidly (Today → Schedule → Today) before the first import
   resolves, the in-flight Map dedup ensures only one import fires.
   But if you naively write:
   ```js
   if (typeof globalThis.renderX === 'function') {
     globalThis.renderX();
   } else {
     import(...).then(() => globalThis.renderX());
   }
   ```
   you race. The router's `_importView` always awaits the import
   before resolving, so the call site can be `await loadView(name)`
   and trust that `globalThis.renderX` is populated by the time it
   runs.

4. **Test seam `_setImporter` is required for vitest** because the
   vitest happy-dom environment can't resolve absolute `/js/...`
   paths. Don't try to make the path relative; the production app
   needs absolute paths (the dashboard can be served at any prefix).

5. **Don't add the `?cb=` cache buster to lazy view imports "for
   consistency"**. Lazy views don't need it (the browser's module
   cache handles updates via the file's mtime/ETag, not the URL).
   Adding it costs ~50ms per first-navigation for no benefit.
