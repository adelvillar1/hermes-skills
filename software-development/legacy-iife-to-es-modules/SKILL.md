---
name: legacy-iife-to-es-modules
title: Refactor a Legacy IIFE Monolith to ES Modules
description: Migrate a single-file vanilla-JS application (one giant IIFE or a tower of `<script>` tags) into multiple ES-module files WITHOUT a build step and WITHOUT rewriting call sites that span the module/IIFE boundary. Covers the dual-export bridge pattern, twelve specific pitfalls that break it (the IIFE hoisted-block recursion that causes "Maximum call stack size exceeded", strict-mode bare-identifier references, post-migration bare Auth.authFetch instead of api() wrapper, the load-order dynamics between modules and the legacy IIFE, and forgetting to register a new lib module in the _modulePromises loader array), and the IIFE-body-via-dynamic-import fallback when the standard module load order fails.
triggers:
  - User says "extract this into modules" or "split this monolithic JS file" or "convert to ES modules"
  - Project has a single multi-thousand-line .js file (typically loaded via `<script src=...>`) that needs modularization
  - Refactor plan calls for moving sections of one big file into separate files
  - Codebase uses a non-module pattern (IIFE, var, top-level const) that needs to coexist with new ES modules
  - Multiple `onclick="..."` handlers or template-literal event handlers reference functions by bare name
---

# Refactor a Legacy IIFE Monolith to ES Modules

## What this skill is for

You have a single vanilla-JS file (often 3,000-10,000 lines) that runs as a classic script. It defines functions at the top level inside an IIFE, exposes a public API on `window.dashboard` (or similar namespace), and gets inline `onclick="dashboard.foo()"` handlers in template-literal HTML. The user wants to extract sections into separate ES-module files — but **without a build step, without a framework, and without breaking the existing 21+ inline `onclick` handlers** that depend on a stable `window.dashboard.X` namespace.

This is the "plain ES modules, no build step" approach from a typical 11-PR refactor plan. It is fundamentally different from "rewrite in React with a bundler."

## The bridge: dual-export pattern

Each new module exports its functions **twice** — once as a real ES-module named export, and once as a `globalThis.X = X` side effect. This lets:

1. The IIFE read the new helpers via `const helper = _lookupGlobal('helper')` at the top of its body (giving them local `const` bindings so all 4,000+ existing bare-identifier references keep working unchanged).
2. The inline `onclick="dashboard.foo()"` handlers keep working because the helpers are on `globalThis` (and `window.dashboard = { foo: globalThis.foo, ... }`).
3. New code in the modules can use `import { helper } from './helper.js'` properly.

```js
// ui/js/lib/format.js (new module)
export function escapeHtml(str) { /* ... */ }
export function formatDate(str) { /* ... */ }

// Legacy global surface for the existing IIFE in dashboard.js.
// The IIFE aliases these via `const x = _lookupGlobal('x')` at the
// top of its body, then uses `escapeHtml(...)` etc. as bare
// identifiers throughout.
if (typeof globalThis !== 'undefined') {
  globalThis.escapeHtml = escapeHtml;
  globalThis.formatDate = formatDate;
}
```

```js
// ui/js/dashboard.js (IIFE top — added 38 lines of aliases)
const _lookupGlobal = (key) => globalThis[key];
const els = _lookupGlobal('els');
const state = _lookupGlobal('state');
const escapeHtml = _lookupGlobal('escapeHtml');
const formatDate = _lookupGlobal('formatDate');
// ... etc
```

For a copy-paste starting point, see `templates/dashboard-js-iife-wrapper.js` — it shows the exact wrapper structure (Promise.all → IIFE → catch) for the monolith, with placeholder names for the modules.

## The eight pitfalls (all observed in production refactors)

### Pitfall 1: Format.js-style namespace exposure

A new module's `globalThis.X = X` block accidentally wraps everything in a namespace object:

```js
// WRONG — IIFE's `_lookupGlobal('escapeHtml')` returns undefined
globalThis.Format = { escapeHtml, formatDate, timeAgo, ... };
```

```js
// RIGHT — each helper is its own globalThis property
globalThis.escapeHtml = escapeHtml;
globalThis.formatDate = formatDate;
```

Symptom: `escapeHtml is not a function` (or similar) when the IIFE calls a helper. **Always verify by checking `typeof globalThis.X` in the browser console for EVERY function the IIFE aliases.** See `references/format-js-pitfall-recipe.md` for the full 2-hour debugging transcript this skill was built from, plus a 30-second diagnostic snippet you can paste into DevTools after any refactor.

### Pitfall 2: `const X = { ... }` in a classic script is invisible from a module

A legacy library file (e.g. `auth.js`) declares `const Auth = { ... }` at the top level of a classic script. Per HTML spec, top-level `const` in classic scripts is a lexical binding that does NOT attach to `window`. A new ES module that does `window.Auth.authFetch(...)` gets `TypeError: window.Auth is not defined`.

Fix: add an explicit assignment at the end of the legacy file:

```js
// at the end of auth.js (classic script)
if (typeof window !== 'undefined') {
  window.Auth = Auth;
}
```

Symptom: `api(): window.Auth is not available. Load auth.js first.` even though `auth.js` is loaded first in the HTML.

### Pitfall 3: Module load order race + browser sandbox quirks

The HTML spec says "classic scripts that follow module scripts in source order wait for the modules to finish." This is true in Chrome/Firefox/Safari. But:

- **Sandbox/automation browsers (e.g. Browserbase, Browser-Use)** sometimes reject `<script type="module" src="...">` in the body in ways that don't surface as errors — the modules' side effects silently never run, and `globalThis.X` is undefined when the IIFE starts.
- **Browser module cache** persists across page loads in a session. If you deploy a new version of `format.js` and reload, the browser returns the cached version from dynamic `import()`, and the new side effects never re-run.
- **Lazy-loaded view modules are even more vulnerable.** When the IIFE uses a router that dynamic-imports view files on first navigation, the browser caches the resolved module record. If you edit `ui/js/views/today.js`, a normal page reload may not re-fetch it — the module cache returns the old version. This makes your CSS/HTML/JS fixes appear to have no effect, leading to long "why didn't my fix work?" debugging sessions.

The defensive fix: **wrap the entire IIFE body in a `Promise.all([import(...)])` chain inside dashboard.js**, and use a per-load cache buster on ALL dynamic imports — including the lazy view imports in the router:

```js
// dashboard.js — critical lib modules, loaded up front
const _modulePromises = [
  import('/js/config.js?cb=' + Date.now()),
  import('/js/lib/hash.js?cb=' + Date.now()),
  import('/js/lib/state.js?cb=' + Date.now()),
  // ... etc
];
Promise.all(_modulePromises).then(() => {
  (function() {
    'use strict';
    // ... legacy IIFE body ...
  })();
}).catch(e => console.error('PRx: failed to load dashboard lib modules:', e));
```

```js
// ui/js/lib/router.js — lazy view loader, also cache-busted
async function _importView(name) {
  if (_loaded.has(name)) return _loaded.get(name);
  if (_inFlight.has(name)) return _inFlight.get(name);
  const path = _VIEW_FILES[name];
  if (!path) throw new Error(`Unknown view: ${name}`);
  const cacheBustedPath = `${path}?cb=${Date.now()}`;
  const p = _doImport(cacheBustedPath)
    .then((mod) => { /* ... */ });
  // ...
}
```

Then **remove** the `<script type="module" src="...">` tags from `dashboard.html`. The IIFE's dynamic imports are the only loader.

`?cb=Date.now()` forces the browser to actually re-fetch the module on every page load and re-run its top-level side effects, even if a stale version is in the module cache. This is especially important during development and Browser-Use verification of view files.

**Important caveat — `?cb=Date.now()` is NOT enough if the module content is broken inside the file itself.** When a file is edited with `read_file`/`patch` tools and the line shown is truncated, the truncated text (`...[truncated]`) can be accidentally written back into the file. The resulting file is valid JS (it parses) but contains literal `...[truncated]` in a template literal. The browser then runs this corrupted file, and symptoms look like "module loaded but output is wrong" rather than a syntax error. Always `sed`/read the exact bytes after a patch if the source window was truncated; do not trust a `read_file` result that ends with `...[truncated]` to be a faithful copy of the file.

Symptom: dashboard.html loads, `window.dashboard` is `undefined`, console shows `els is not defined` at some line in the IIFE that uses a bare `els.X` reference. (Or: after deploying a fix to a view file, the dashboard still uses the old version — e.g., a changed `onclick` attribute still shows the old handler in the live DOM, or a rendered list is missing items because a `.map()` template literal contains literal `...[truncated]`.)

### Pitfall 4: Init-function side effects fire after the namespace is built

The original IIFE had a structure like:

```js
function init() {
  // sets window.dashboard, wires up listeners, calls render()
}
window.dashboard = { /* built using bare-identifier references */ };
// classic-script entry: init() runs on DOMContentLoaded
```

When you extract `window.dashboard` builders, you change the order: now `globalThis.X = X` (for IIFE-only functions) needs to fire BEFORE `window.dashboard = { X: globalThis.X, ... }`. But the natural place for those exports is inside `init()` (which runs on DOMContentLoaded, AFTER the IIFE top-level `window.dashboard = { ... }` block has already been evaluated with `undefined` values).

Fix: **hoist the `globalThis.X = X` block to IIFE top-level, right after `function init() { ... }` is declared**. This way it runs synchronously when the IIFE executes, before `window.dashboard` is built.

```js
function init() { /* ... uses bare `loadView`, `renderRatings` ... */ }

// PR-N hoisted export block: expose IIFE-only functions on globalThis
// BEFORE the window.dashboard = { ... } block runs.
globalThis.loadView = loadView;
globalThis.renderRatings = renderRatings;
// ... 20 more

window.dashboard = {
  loadView: globalThis.loadView,
  renderRatings: globalThis.renderRatings,
  // ...
};
```

Symptom: `window.dashboard.X` exists as a key but its value is `undefined`. Test by doing `Object.keys(window.dashboard).filter(k => typeof window.dashboard[k] !== 'function')` in the browser console.

### Pitfall 5: Bad import name in a dynamically-loaded view file kills the whole IIFE

After you switch to the "wrap the IIFE in `Promise.all([import(...)])`" pattern from Pitfall 3, the dashboard's IIFE body only runs if **every** import in the `_modulePromises` array resolves successfully. This includes the view files you're extracting (`/js/views/ratings.js`, `/js/views/calibration.js`, etc.).

If any of those view files have a bad `import` statement — e.g. `import { displayTeamName } from '../lib/format.js'` when `format.js` doesn't export `displayTeamName` (it's a true global from `team-display.js`, not an export of format.js) — the dynamic import() **rejects synchronously**. `Promise.all()` rejects. The `.then()` callback never fires. The IIFE never runs. **`window.dashboard` is undefined** with **no console error** (the rejection is swallowed by the `.catch()` block, which only logs `"PRx: failed to load dashboard lib modules:"` — easy to miss if you didn't think to look for it).

**Symptom that distinguishes this from Pitfall 1/3:** modules still load (`globalThis.state`, `globalThis.els`, `globalThis.escapeHtml` are all set), but the IIFE body never runs. `window.dashboard` is `undefined`. The console is clean. `init()` never gets called. No navigation works.

## Diagnostic snippet (paste into browser console after the symptom appears)

**Important:** Browser-Use sessions often hide console output from the snapshot — the `.catch(e => console.error(...))` handler runs but the message isn't visible. Before running any diagnostic, temporarily add `window.__promiseErr = e.message` to the `.catch()` handler in dashboard.js. This makes the error visible via `window.__promiseErr` in the console expression evaluator.

```js
// 0. First check if Promise.all rejected (catch handler stored the error)
window.__promiseErr || 'no promise error'

// 1. Is the IIFE running? window.dashboard should be set.
typeof window.dashboard
// If 'undefined', the IIFE body never finished.
  els: typeof globalThis.els,
  escapeHtml: typeof globalThis.escapeHtml,
  formatDate: typeof globalThis.formatDate,
  Auth: typeof window.Auth,
  renderToday: typeof globalThis.renderToday  // from views/
})

// 2. If lib modules load but a view is 'undefined', the bad import is in
// that view file. Open the file and check each import name against the
// target's `export { ... }` block.

// 3. To find the EXACT error (the browser swallows it in .catch()):
// Temporarily add error capture to dashboard.js's .catch():
// .catch(e => { window.__promiseErr = e.message + ' @ ' + (e.stack||'').split('\n').slice(0,5).join(' | '); })
// Then check: window.__promiseErr
```

**Key insight for diagnosis:** the `.catch()` handler on the `Promise.all` wrapper is the ONLY place the error surfaces. The default handler only does `console.error(...)` which is easy to miss — especially in Browser-Use sessions where console output may not be visible in the snapshot. Always add `window.__promiseErr = ...` to the catch handler when debugging, and check it from the console via expression evaluation.

**Vitest regression-test caveat — happy-dom shadows `fs`.** If you add a vitest file that reads source files via `import { readFileSync } from 'fs'` (or `'node:fs'`), the test silently fails with `readFileSync is not a function` because happy-dom (vitest's default browser-like env) shadows the `fs` module with its own (browser-like) shim that lacks `readFileSync`. The error is also silent in the vitest reporter — it shows as a "Failed Suites" entry without listing the test name, and a file that imports `fs` may show zero test runs in the count (the suite fails before any `it` runs). **Fix:** bypass the shadow with `const _fs = eval('require')('fs');` at the top of the test file, then use `_fs.readFileSync(...)`. Verified empirically: importing `fs` directly gives the happy-dom stub; `eval('require')('fs')` gives the real Node module. The same pattern works for any built-in Node module that happy-dom shadows.

**Fix:** before writing any view file's `import` block, open the target lib module and **verify each name in the target's `export { ... }` block**. A common mistake pattern: helpers from `team-display.js` (`displayTeamName`, `getShortName`, `normalizeTeamName`) and `config.js` (`teamName`) are **true globals** loaded as classic scripts before `dashboard.js`. They are NOT exports of `format.js` even though they're imported there. Use them as bare identifiers (no `import` statement) or import from the actual source.

**Prevention:** in the controller's per-PR dispatch context, include this line: "Before writing any view file's import block, open the target lib module and verify each name is in its `export { ... }` block. Common mistake: importing `displayTeamName` from `format.js` — it's a global from `team-display.js`." This is the difference between a 5-minute PR and a 30-minute debugging session.

### Pitfall 6: Shared view-level state needs a globalThis mirror

When a view extracts successfully but other modules still need to read its module-private state, the dual-export pattern alone is not enough. Module-level `let` bindings are not visible to other modules — they're inside the module's lexical scope. Other modules (or inline event handlers) that read `globalThis._scheduleGames` get `undefined`.

**Common case:** the Schedule view had `let _scheduleGames = [];` and `let _currentMatchIdx = -1;` at the top of the IIFE. The hash router's `restoreFromHash()` (now in `ui/js/lib/hash.js`) reads `globalThis._scheduleGames` to find the right game after a hash-driven reload. The match-detail modal (still in dashboard.js) reads `globalThis._currentMatchIdx` to know which game to render.

**Fix:** declare the state as module-level `let` in the new view file AND mirror it on `globalThis` at the bottom of the file:

```js
// ui/js/views/schedule.js
let _scheduleGames = [];
let _currentMatchIdx = -1;

export async function renderSchedule() {
  // ... reads/writes _scheduleGames
}

// Legacy global surface — mirror shared state so other modules
// (hash.js's restoreFromHash, the match-detail modal) can find it.
if (typeof globalThis !== 'undefined') {
  globalThis.renderSchedule = renderSchedule;
  globalThis._scheduleGames = _scheduleGames;
  globalThis._currentMatchIdx = _currentMatchIdx;
}
```

The mirror captures the *binding* at the time `globalThis.X = X` runs. Mutations through the variable (which is what `let _scheduleGames = []; _scheduleGames.push(...)` does) are seen by readers of `globalThis._scheduleGames` because they point to the same object/array. For primitive values (numbers, strings) the mirror does NOT auto-update — those need a setter or wrapper. For shared arrays/objects, the mirror works.

**The Accuracy view's shared state** (`_accSort`, `_accFilter`) is also object-shaped (`{col, dir}` and a filter string) so the mirror works. If a future view needs to share a primitive, the pattern needs to extend to `Object.defineProperty` with a getter, or the shared state should be an object from the start.

### Pitfall 7: The IIFE's hoisted block can OVERWRITE the module's real implementation with a stub-recursive copy (causes "Maximum call stack size exceeded")

The dual-export pattern from this skill is:

```js
// module: sets the real implementation
globalThis.renderToday = renderToday;

// IIFE stub: delegates to the module
function renderToday() { return globalThis.renderToday(); }
```

These two coexisting in the same page is **correct** — that's the whole pattern. The IIFE's `loadView()` calls the stub as a bare identifier, the stub calls `globalThis.renderToday`, the module's real function runs. One level of indirection.

**The bug:** the IIFE's "hoisted exports" block (the section that mirrors IIFE-local functions to `globalThis` for `window.dashboard` to read) sometimes ALSO does `globalThis.renderToday = renderToday;` — and the IIFE's local `renderToday` is the STUB (not the real implementation). So the hoisted block overwrites the module's real function with the stub. Then the stub calls `globalThis.renderToday()` which is the stub itself → infinite recursion → browser throws `RangeError: Maximum call stack size exceeded` → `loadView` rejects → `window.dashboard` namespace is set, but no view actually renders, and any "load" of a view dumps the toast and the empty-state.

**Order of operations that creates the trap:**

1. `_modulePromises` resolves → all modules evaluate, each does `globalThis.renderToday = renderToday;` (real)
2. IIFE starts (the `.then()` callback fires)
3. IIFE's hoisted block runs: `globalThis.renderToday = renderToday;` ← **STUB**, overwriting the real one
4. IIFE's `window.dashboard = { renderToday: globalThis.renderToday, ... }` reads the stub
5. `init()` runs; `loadView('today')` calls `await renderToday()` (IIFE-local stub)
6. Stub calls `globalThis.renderToday()` which is now the stub → **infinite recursion**

**The diagnostic catch (rejection-stack style):**

```js
} catch (err) {
  window.__loadErr = err.message + ' @ ' + (err.stack || '').split('\n').slice(0, 8).join(' | ');
  toast(err.message);
  els.content.innerHTML = emptyState('Failed to load data');
}
```

The stack will show `renderToday at dashboard.js:NNN` repeating — pointing at the IIFE's stub line, not the module.

**The fix:** in the IIFE's hoisted block, **drop the `globalThis.X = X;` lines for any symbol that is now provided by a view module.** The module already set it; the hoisted block must not overwrite. The comment in the hoisted block should read:

```js
// PR-N hoisted exports — only set the symbols that are still
// IIFE-local implementations. The view modules (today.js,
// match-detail.js, etc.) set their own globals on globalThis;
// overwriting them here would replace the real implementation
// with the IIFE's stub, causing infinite recursion.
globalThis.loadView = loadView;     // still IIFE-local
globalThis.copyTeamLink = copyTeamLink;  // still IIFE-local
// (renderToday, renderDomains, renderUsers, renderCorpus, showMatchDetail,
//  closeMatchDetail, etc. are now set by their view modules.)
```

**Why this isn't caught by `node -c`:** the file is syntactically valid. The recursion is a runtime symptom that only triggers when `loadView('today')` actually runs.

**Variant A — IIFE's own `loadView` clobbers a router's `loadView` (the lazy-loader refactor pattern).** When you introduce a `lib/router.js` whose sole job is to own `globalThis.loadView` (it dynamic-imports view modules and dispatches to the right `renderX`), the IIFE's hoisted block must NOT also assign `globalThis.loadView = loadView`. The IIFE may still have a *local* `loadView` function (for skeleton/filter/try-catch wrapping), but that function's body should `await globalThis.loadView(view)` (delegating to the router's version). If the hoisted block also writes `globalThis.loadView = loadView`, the IIFE's own `loadView` clobbers the router's, and the IIFE's `loadView` then calls itself via `globalThis.loadView` → infinite recursion → `RangeError: Maximum call stack size exceeded`. Symptom is identical to the stub-clobber case above, but the regression is *introduced* by a new module that owns `loadView`, not by an extraction. Fix: in the IIFE's hoisted block, comment out `globalThis.loadView = loadView;` and leave a marker comment naming the module that owns it. The IIFE's local `loadView` stays in place — it just no longer advertises itself on `globalThis`.

**Regression-test recipe (proven in 2026-06-11, eloci-scenario-lab lazy-view-loader PR).** Add a vitest file that parses the IIFE source and asserts the offending `globalThis.X = X;` line is absent. Three assertions minimum:

1. The bad line is gone from the IIFE source (regex match).
2. The IIFE's local `loadView` still delegates to `globalThis.loadView` (positive regex match — guards against an over-aggressive cleanup that removes the delegation too).
3. The module that now owns the name (e.g. `ui/js/lib/router.js`) does the `globalThis.X = X` assignment — sanity check that the new owner is wired up.

```js
// ui/js/lib/__tests__/regression.test.js (proven pattern)
import { describe, it, expect } from 'vitest';

const _fs = eval('require')('fs');  // bypass happy-dom's fs shadow
const IIFE_PATH = 'ui/js/dashboard.js';
const NEW_OWNER_PATH = 'ui/js/lib/router.js';

describe('loadView clobber regression', () => {
  const src = _fs.readFileSync(IIFE_PATH, 'utf8');

  it('IIFE does NOT overwrite globalThis.loadView (would recurse into its own loadView)', () => {
    const re = /^\s*globalThis\.loadView\s*=\s*loadView\s*;?\s*$/m;
    expect(
      src.match(new RegExp(re.source, 'gm')),
      'globalThis.loadView = loadView would clobber the router version and cause infinite recursion',
    ).toBeNull();
  });

  it('IIFE loadView() delegates to globalThis.loadView (not to itself directly)', () => {
    expect(src).toMatch(/await\s+globalThis\.loadView\s*\(/);
  });

  it('router.js sets globalThis.loadView so the IIFE delegation has a target', () => {
    const owner = _fs.readFileSync(NEW_OWNER_PATH, 'utf8');
    expect(owner).toMatch(/globalThis\.loadView\s*=\s*loadView/);
  });
});
```

**Verification step when adding this test:** deliberately re-introduce the bad line (`globalThis.loadView = loadView;`), confirm the test fails with the expected error, then revert. If the test doesn't fail, the regex is too permissive — tighten it until a real re-introduction breaks it. The `eval('require')('fs')` trick is required because happy-dom (vitest's test environment) shadows the `fs` module with its own (browser-like) shim that lacks `readFileSync`; without it, the test silently throws at module-evaluation and vitest reports 0 tests run with no error message.

### Pitfall 8: Misleading comments lead to dropping required `globalThis` exports

During sequential PRs in a large modular refactor, a function may remain IIFE-local while an outdated comment claims it has been moved to a view module. For example, a hoisted comment might state: `(selectTeam, closeTeamDetail are all set by their view modules — don't overwrite.)` 

If an agent trusts this comment and omits the `globalThis.selectTeam = selectTeam;` assignment (assuming the view module did it), `globalThis.selectTeam` remains `undefined`. As a result, the `window.dashboard` namespace binds it to `undefined`, breaking inline `onclick="dashboard.selectTeam(...)"` handlers with a silent `TypeError: dashboard.selectTeam is not a function`.

**Fix:** When updating the hoisted exports block during a sequential refactor, **always verify against the actual file contents** whether a function is truly defined in a view module or if it still resides in the IIFE. If it is in the IIFE, it MUST have a `globalThis.X = X;` assignment before the `window.dashboard` namespace object is constructed. Update the comment to accurately reflect the current reality, not the planned reality.

### Pitfall 9: Bare-identifier references to true globals throw `ReferenceError` in module strict mode

The legacy IIFE worked because classic scripts treat unresolved identifiers as globals. ES modules are strict mode — bare `LEAGUE_LABELS` throws `ReferenceError: LEAGUE_LABELS is not defined` even if a classic script earlier in the page set `window.LEAGUE_LABELS`.

**Common real globals loaded as classic scripts** (NOT exports of any module):

| Symbol | Source script | Type |
|---|---|---|
| `LEAGUE_LABELS` | `config.js` | plain object |
| `TEAM_ABBREVS` | `config.js` | plain object |
| `displayTeamName` | `team-display.js` | function |
| `getShortName` | `team-display.js` | function |
| `normalizeTeamName` | `team-display.js` | function |
| `Auth` | `auth.js` | namespace |
| `toast` | `lib/toast.js` (or as global from auth.js) | function |

When you extract a view to a new ES-module file, every template-literal reference like `${LEAGUE_LABELS[league]}` or `${getShortName(team)}` needs to be converted to `${globalThis.LEAGUE_LABELS[league]}` or `${globalThis.getShortName(team)}`. The `globalThis.X` access works in strict mode because `globalThis` is always defined; the property lookup returns the real global that the classic script set on `window`.

**`typeof X !== 'undefined'` is a safe pattern** for guarding before use, but it's verbose. The convention in this refactor is: `globalThis.X || DEFAULT` for objects, and `globalThis.X?.()` for functions. This avoids the bare-reference trap entirely.

**Special case for `globalThis._X = globalThis._X()` (the bug-from-Pitfall-7 trigger):** schedule.js sets `globalThis._currentMatchIdx = -1` (a number). The new match-detail.js tried to do `globalThis._currentMatchIdx = globalThis._currentMatchIdx();` — calling the global as a function. That throws `TypeError: globalThis._currentMatchIdx is not a function`. Fix: call the local accessor `_getCurrentMatchIdx()` instead.

**Symptom:** `Promise.all()` rejects with `TypeError: globalThis._X is not a function` or `ReferenceError: LEAGUE_LABELS is not defined` at some line in the module's top-level evaluation. The IIFE never starts. `window.dashboard` is `undefined`. All view-render calls fail with "Failed to load data."

**Prevention:** when extracting a view, do a one-pass sweep of all bare identifiers that aren't imports or local declarations. Anything that the IIFE used to resolve via the global scope (true globals) needs to be `globalThis.X` in the module.

### Pitfall 12: New lib module not registered in `_modulePromises` — `globalThis.X is not a function`

After the IIFE migration is complete and `dashboard.js` uses the `Promise.all(_modulePromises)` loader pattern (per Pitfall 3), **any new lib module added to `ui/js/lib/` MUST also be added to the `_modulePromises` array**. The HTML `<script type="module">` tags were deliberately removed — `dashboard.js`'s dynamic imports are the ONLY loader. If a module isn't in the array, it never loads, its `globalThis.X` exports never fire, and any view that calls `globalThis.X()` gets:

```
TypeError: globalThis.signalBarsHTML is not a function
    at renderEdgeFooter (today.js?cb=...:603:27)
    at renderMatchCard (today.js?cb=...:570:9)
```

This TypeError cascades — it kills the entire view render. No game cards show. The page is blank.

**Real example (2026-06-16, ELO Scenario Lab):** A new `ui/js/lib/signalBars.js` module was created with the correct dual-export pattern (`globalThis.signalBarsHTML = signalBarsHTML`). It was used by `today.js` and `schedule.js` via `globalThis.signalBarsHTML(...)`. But the module was never added to `_modulePromises` in `dashboard.js`. The module file existed on disk, was served correctly by the static file server, but was never imported by anything. Result: `TypeError` on page load, all game cards disappeared.

**The fix:**

```js
// dashboard.js — add the new module to the _modulePromises array
const _modulePromises = [
  import('/js/config.js?cb=' + Date.now()),
  import('/js/lib/hash.js?cb=' + Date.now()),
  // ... existing modules ...
  import('/js/lib/dom-refs.js?cb=' + Date.now()),
  import('/js/lib/signalBars.js?cb=' + Date.now()),  // ← ADD THIS LINE
  import('/js/lib/router.js?cb=' + Date.now()),
];
```

**Prevention checklist when adding any new `ui/js/lib/*.js` file:**
1. ✅ Module has the dual-export block (`globalThis.X = X`)
2. ✅ Module is added to `_modulePromises` in `dashboard.js`
3. ✅ Module is imported (if needed) by any view that uses it directly
4. ✅ `grep -c 'moduleName' dashboard.js` returns ≥ 1 (the import line)

**Why this is easy to miss:** The module file is syntactically valid, exports correctly, and works in isolation. The bug only manifests at runtime when a view calls `globalThis.X()`. Static analysis won't catch it — there's no import statement to validate because the caller uses the `globalThis` bridge, not a direct import. The module simply doesn't exist in the browser's module graph because nothing imports it.

### Pitfall 11: Extracted view modules keep stale API endpoint references

When you move a view out of the IIFE into `ui/js/views/`, the module often copies its API calls verbatim. If the backend routes were renamed or reorganized — or if the view was copied from code that used a different convention — the module will call a URL that returns 404. Because most fetch wrappers catch errors and return empty defaults, the symptom is "this admin page shows no data" rather than a clear error.

**Detection:**
- A view renders its empty state even though data exists in the backend.
- Network tab shows 404 for `GET /api/pipeline/*` or similar.
- The backend route file defines the same resource under a different prefix, e.g. `/api/admin/*`.

**Fix:**
1. Read the backend route file and list the real URLs.
2. Update every `api('/api/old/...')` call in the view to the correct path.
3. Adapt to the actual response shape (list vs wrapped object, `row_count` vs `rows`, etc.).
4. Verify with `curl` or `TestClient`, not just by reloading the UI.

**Prevention:** During any view extraction, grep the source for `api(`, `fetch(`, `Auth.authFetch(` and record the URLs. Before merge, compare that list to the backend router. Add a `TestClient` regression test that asserts the endpoint exists and returns the shape the view consumes.

See `references/modular-refactor-stale-api-endpoints.md` for the full 2026-06-15 ELO Scenario Lab case study.

## The "load order" debug recipe

When the dashboard appears blank and `window.dashboard` is undefined, the most likely causes are Pitfall 1, 3, or 4. Diagnose in this order:

1. **Browser console — does it have a JS error?** If yes, fix the error first. If empty: probably Pitfall 3.
2. **`typeof window.dashboard`** — if `undefined`, the IIFE threw before reaching the assignment. The error is in the IIFE body BEFORE the namespace block.
3. **`Object.keys(window.dashboard).filter(k => typeof window.dashboard[k] !== 'function')`** — if non-empty, those are Pitfall 4 (hoist the export).
4. **`typeof globalThis.X` for each aliased function** — if any are `undefined` AFTER a hard reload, it's Pitfall 1 (the module doesn't expose that function individually). For example: `globalThis.escapeHtml === undefined` but `globalThis.Format?.escapeHtml` is a function → format.js uses the namespace pattern instead of direct globalThis.

## Naming and architecture conventions

- **Module files live under `ui/js/lib/`** (or `ui/js/views/` for view code). Top-level config/consts can live directly in `ui/js/` (e.g. `config.js`).
- **Dual-export pattern in EVERY new module.** Every new file should have, at the bottom:

  ```js
  if (typeof globalThis !== 'undefined') {
    globalThis.foo = foo;
    globalThis.bar = bar;
  }
  ```

  This is the contract. Skipping it is Pitfall 1 in waiting.

- **Backward-compat namespace exports are fine.** If a previous PR put everything under `globalThis.Foo = { ... }` (a namespace), keep it AND add the individual `globalThis.foo = foo` lines. The IIFE uses the individual ones; old callers can use the namespace.

- **Test files go in `ui/js/lib/__tests__/`** (or `ui/js/lib/views/__tests__/`). Use vitest + happy-dom for any module that touches `document`, `localStorage`, or `URLSearchParams`. Use `vi.hoisted(() => { ... })` to populate the DOM BEFORE the module imports (since the module's top-level `els` cache runs at import time).

- **Add tests for EVERY module's exported functions.** A common mistake is to extract a module without writing tests. The whole point of the refactor is to make the code testable — so test it.

### Pitfall 9: Post-migration code uses bare `Auth.authFetch` instead of the `api()` wrapper

After the migration is complete and all views are ES modules, someone adds a new function to a view module and writes `Auth.authFetch('/api/foo', { method: 'POST' })` — the exact pattern that worked in the old IIFE. In strict-mode ES modules, bare `Auth` is a `ReferenceError`. The function's try/catch silently swallows the error, so the button appears to do nothing.

**Root cause:** the developer (human or agent) copied the pattern from old IIFE code without checking whether the module has a better alternative.

**The fix pattern — `api()` wrapper:** Most projects that complete this migration end up with a thin `api()` helper in `lib/api.js` that wraps `window.Auth.authFetch` with proper error handling. The helper is imported in every view module:

```js
// lib/api.js — the canonical authenticated-fetch wrapper
async function api(path, options = {}) {
  if (!window.Auth?.authFetch) throw new Error('api(): window.Auth not available');
  const res = await window.Auth.authFetch(path, options);
  if (!res.ok) { /* throw with status + body */ }
  return res.json();
}
export { api };
```

```js
// views/pipeline.js — CORRECT: uses imported api()
import { api } from '../lib/api.js';
async function triggerPipeline() {
  await api('/api/pipeline/trigger', { method: 'POST' });
  toast('Pipeline triggered', 'success');
}
```

```js
// views/pipeline.js — WRONG: bare Auth is ReferenceError in strict mode
async function triggerPipeline() {
  const res = await Auth.authFetch('/api/pipeline/trigger', { method: 'POST' });
  // ...
}
```

**Symptom:** button click appears to do nothing. Console shows `ReferenceError: Auth is not defined` briefly (or not at all if the catch block swallows it silently). No network request is made.

**Prevention:** after the migration, audit ALL view modules for bare `Auth.authFetch` calls. Replace with the imported `api()` helper. The `api()` helper should be the ONLY way views make authenticated requests. Add a lint rule or a grep check to CI:

```bash
grep -rn 'Auth\.authFetch' ui/js/views/ && echo "FAIL: use api() instead" || echo "OK"
```

**Why this is easy to miss:** the bug only manifests at runtime (click the button). Static analysis (`node -c`, TypeScript) won't catch it because `Auth` could be a legitimate module-level variable. The grep check above is the reliable guard.

### Pitfall 10: Global navigation helpers call lazy view renderers before the module is loaded

After the migration, the router lazy-loads view modules on first navigation (`/js/views/today.js`, `/js/views/team-detail.js`, etc.). Each view module sets `globalThis.renderToday`, `globalThis.renderTeamDetail`, etc. as a side effect. But code that is NOT the router — especially the hash-router helpers `navigateToTeam()` and `restoreFromHash()` — may call those globals directly:

```js
// lib/hash.js — WRONG: renderTeamDetail may be undefined
function navigateToTeam(sport, teamId) {
  setHash(`team/${sport}/${teamId}`);
  if (typeof globalThis.renderTeamDetail === 'function') {
    globalThis.renderTeamDetail({ id: teamId, sport });
  }
}
```

If the user has never visited the team-detail view, `globalThis.renderTeamDetail` is `undefined`. Clicking a team in the ratings table, or loading a direct `#team/mlb/ STL` URL, updates the hash but the page stays on the current view.

**The fix:** expose a `loadModule(name)` helper on the router that imports a view module without rendering, and make the hash-router helpers await it:

```js
// lib/router.js
async function loadModule(name) { return _importView(name); }

if (typeof globalThis !== 'undefined') {
  globalThis.Router = { loadView, preloadView, preloadViews, loadModule };
}
```

```js
// lib/hash.js
async function navigateToTeam(sport, teamId) {
  setHash(`team/${sport}/${teamId}`);
  await globalThis.Router?.loadModule?.('team-detail');
  if (typeof globalThis.renderTeamDetail === 'function') {
    globalThis.renderTeamDetail({ id: teamId, sport });
  }
}
```

Same pattern for `restoreFromHash()` when restoring `#team/...` or `#game/...` hashes: load `team-detail` or `match-detail` before calling `renderTeamDetail` / `showMatchDetail`.

**Symptom:** team/match clicks or direct deep links "do nothing" — the URL hash changes, but the content does not navigate. No console error because the `typeof` guard silently skips the missing renderer.

**Prevention:** whenever a non-router caller invokes a `globalThis.renderX` or `globalThis.showX` that is owned by a lazy view module, make that caller responsible for loading the module first, or preload the module at app startup for any view that can be reached by deep link.

**Variant B — IIFE's own stub delegating to a lazy module needs fallback loading (2026-06-16).** The dashboard.js IIFE has local stub functions like `showMatchDetail()` that delegate to `globalThis.showMatchDetail()` (owned by the lazy-loaded `match-detail.js`). When a user clicks a game card on the Schedule view (their first interaction), `match-detail.js` hasn't been imported yet — the router only loads it on view navigation. The stub calls `globalThis.showMatchDetail(gameIdx)` which is `undefined` → `TypeError` → click does nothing.

**Fix:** the IIFE stub must lazy-load the module before calling the global:

```js
function showMatchDetail(gameIdx) {
  if (typeof globalThis.showMatchDetail === 'function') {
    return globalThis.showMatchDetail(gameIdx);
  }
  // Lazy-load the match-detail module on first click
  globalThis.loadView?.('match-detail').then(() => {
    globalThis.showMatchDetail?.(gameIdx);
  }).catch(() => {});
}
```

This applies to ANY IIFE stub that delegates to a `globalThis.X` where `X` is defined in a lazy-loaded view module. The `typeof` check is the guard; the `loadView` fallback is the safety net. **Prevention:** audit all IIFE stubs that delegate to `globalThis.X` where `X` is defined in a lazy-loaded view module. Each one needs the typeof guard + loadView fallback pattern.

### Pitfall 14: Response cache middleware serves stale static JS files

Even with the `?cb=Date.now()` cache-buster on dynamic `import()` calls, the response cache middleware can serve stale static JS files via ETag 304s. The `?cb=` query parameter busts the browser's HTTP cache, but if the server's response cache middleware intercepts the request and returns a cached ETag, the browser sends `If-None-Match` and gets `304 Not Modified` back — serving the old JS body forever.

This is the same bug pattern as the accuracy page ETag issue: the `_should_bypass()` function in the response cache middleware checks `_NEVER_CACHE_PATH_PREFIXES` but static files like `/js/lib/signalBars.js` don't match any prefix — they pass through to the cache layer.

**Symptom:** You push updated JS code, verify the file is served correctly via `curl`, but the browser still runs the old version even after a hard refresh. The `X-Cache` header shows `HIT-LRU-304`.

**Fix:** Bypass the response cache for all static file extensions:

```python
# response_cache.py — _should_bypass()
if path.startswith("/js/") or path.startswith("/css/") or path.endswith(".js") or path.endswith(".css") or path.endswith(".html"):
    return True
```

AND add `Cache-Control: no-cache, must-revalidate` to static files via a `StaticFiles` subclass:

```python
# main.py
class _NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        resp = await super().get_response(path, scope)
        if path.endswith((".js", ".css", ".html")):
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        return resp

app.mount("/", _NoCacheStaticFiles(directory="ui", html=True), name="ui")
```

AND bump the `dashboard.html` script tag with a version parameter to break the current stale browser cache:

```html
<script src="/js/dashboard.js?v=2"></script>
```

**Three layers must be fixed:** (1) response cache bypass, (2) Cache-Control header, (3) HTML script tag cache-buster. Missing any one layer allows stale JS to persist.

**Prevention:** When adding a new `ui/js/lib/*.js` module, verify `curl -sI http://localhost:8000/js/lib/newModule.js | grep Cache-Control` returns `no-cache, must-revalidate`.

### Pitfall 15: Async data load doesn't trigger re-render — cache sync gap

When a view renders cards that depend on async-loaded stats (e.g., historical accuracy from `/api/signals/{sport}`), the async loader must store data in the SAME location the renderer reads from. A common pattern:

```js
// preloadSignalStats stores in _signalStatsCache (internal Map)
// signalBarsHTML reads from globalThis._signalStats (different object)
// → hist accuracy never appears even after data loads
```

**Fix:** The async loader must write to BOTH the internal cache (for dedup) AND `globalThis._signalStats` (for the renderer):

```js
async function preloadSignalStats(sport) {
  const data = await loadSignalStats(sport);
  // Store where the renderer reads from
  if (!globalThis._signalStats) globalThis._signalStats = {};
  globalThis._signalStats[sport] = data;
  // Trigger re-render
  if (typeof globalThis.renderSchedule === 'function') {
    globalThis.renderSchedule();
  }
}
```

**AND** the view must NOT `await` the stats load before rendering cards — that blocks the entire view for 10-30 seconds on production. Cards should render immediately without the data, then re-render when stats arrive:

```js
// BAD — blocks card rendering for 10-30s
const sportStats = await globalThis.loadSignalStats?.(sportLower);

// GOOD — fire async, render immediately, re-render when data arrives
globalThis.preloadSignalStats?.(sportLower);
const data = await api(`/api/schedule/${sportLower}?days_ahead=5`);
// cards render now (without hist accuracy)
// preloadSignalStats triggers re-render when stats arrive
```

**Symptom:** Cards never render (blocked by await), OR cards render but hist accuracy text never appears (cache sync gap).### Pitfall 13: `window.dashboard` namespace captures `undefined` for lazy-loaded functions

Even after fixing the IIFE stub (Variant B), `window.dashboard` can still be broken. The namespace object is built at init time:

```js
window.dashboard = {
  showMatchDetail: globalThis.showMatchDetail,  // ← undefined at this point!
  closeMatchDetail: globalThis.closeMatchDetail, // ← also undefined
  // ...
};
```

At init time, `globalThis.showMatchDetail` is `undefined` because `match-detail.js` is lazy-loaded and hasn't been imported yet. The VALUE `undefined` is captured permanently. Later, when `match-detail.js` loads and sets `globalThis.showMatchDetail = showMatchDetail`, the `window.dashboard.showMatchDetail` property still holds the old `undefined` value. Clicking a card calls `dashboard.showMatchDetail(idx)` → `TypeError: dashboard.showMatchDetail is not a function`.

**Fix:** make the namespace property a live delegate function that reads `globalThis.X` at call time, not at init time:

```js
window.dashboard = {
  showMatchDetail: function(idx) {
    if (typeof globalThis.showMatchDetail === 'function') {
      return globalThis.showMatchDetail(idx);
    }
    globalThis.loadView?.('match-detail').then(() => {
      globalThis.showMatchDetail?.(idx);
    }).catch(() => {});
  },
  closeMatchDetail: function() { return globalThis.closeMatchDetail?.(); },
  // ... functions still in the IIFE can use shorthand (they exist at init time)
  navigateToTeam: globalThis.navigateToTeam,
  setLeague: globalThis.setLeague,
};
```

**Rule:** any `window.dashboard` property that delegates to a function owned by a lazy-loaded module MUST be a live delegate function (not a captured value). Functions that remain IIFE-local can use the shorthand `globalThis.X` pattern since they exist at init time.

**Diagnostic:** `Object.keys(window.dashboard).filter(k => typeof window.dashboard[k] !== 'function')` — if any lazy-loaded function shows as `undefined`, it needs the live delegate pattern.

This was Pitfall 10 Variant C in the earlier version of this skill; it has been renumbered for clarity.

## Common mistakes beyond the eight pitfalls

- **Removing the old function body but leaving the comment marker** — leaves duplicate declarations in the IIFE. Run `node -c` on dashboard.js after every edit and resolve the first syntax error that pops up.
- **Forgetting that `<script type="module" src="...">` in `<body>` (not `<head type="module">`) is rejected by some sandboxes** — use the dynamic-import-in-IIFE approach from Pitfall 3 universally.
- **Building the `window.dashboard` namespace with shorthand property syntax** — `window.dashboard = { setLeague, ... }` — fails because the bare identifiers no longer exist in IIFE scope. Use `window.dashboard = { setLeague: globalThis.setLeague, ... }` instead.
- **Calling helper functions that the IIFE still has locally** — e.g. `els.X` where `els` is a cached Proxy from the new dom-refs.js module. Make sure `els` is the new Proxy, not a leftover from the old `const els = { ... }` in the IIFE.
- **Subagent creates the new view file but doesn't remove the originals from the monolith** — This happened in 3 of 9 dispatches during the ELO Scenario Lab refactor. The subagent writes the full `ui/js/views/xyz.js` with all functions and `globalThis.X = X`, but times out before deleting the corresponding functions from `dashboard.js`. The result: duplicate function declarations (IIFE-local and module) with the same name. In non-strict mode V8 this is not an error — the later declaration wins — but if the later one is the IIFE stub, you get Pitfall 7 (infinite recursion). **Always verify the monolith actually shrank** after a subagent reports completion. If `wc -l dashboard.js` didn't change, the subagent only did 80% of the job.
- **Extracting a function can surface latent infinite recursion in pre-existing code** — When `renderTopPicksSection` was extracted to `today.js`, the recursion guard `if (!honest.length) return renderTopPicksSection([], totalGamesScanned);` (which called itself with empty `[]`) caused "Maximum call stack size exceeded" in production. This bug existed in the original monolith but was never triggered because the data path didn't produce empty `honest` until the view was extracted and a new fetch path was introduced. **After extracting any function that has self-recursive calls, check whether the recursion has a proper base case.** Look for patterns like `return self(...)` with modified arguments that don't guarantee convergence.

## When to use this skill vs `refactor-safely`

- **`refactor-safely`**: dependency-graph analysis, dead-code detection, planning a refactor. Use BEFORE starting.
- **`legacy-iife-to-es-modules`**: implementation patterns and pitfalls. Use DURING the refactor.
- **`subagent-driven-development`**: methodology (warmup → plan → delegate_task → 2-stage review). Use to GOVERN the refactor.

This skill complements, does not replace, either of those.

## End-to-end worked example (PR1 → PR4, two sessions)

The original ELO Scenario Lab frontend modular refactor (`docs/plans/2026-06-10-frontend-modular-refactor.md`) extracted 7 lib modules (PR1) + 5 utility expansions (PR2) + 13 view modules (PR3.1–PR3.8 + PR4) from a 4,500-line `dashboard.js` IIFE. The full sessions that followed this skill's patterns are documented in:

- `docs/recaps/SESSION-RECAP-2026-06-10-frontend-refactor-pr1.md` (PR1)
- `docs/recaps/SESSION-RECAP-2026-06-10-frontend-refactor-pr2.md` (PR2)
- `docs/recaps/SESSION-RECAP-2026-06-10-frontend-refactor-pr3-pr4.md` (PR3.1–PR4)

The PR3+PR4 session surfaced three new pitfalls (7, 8, and the controller-finish-20% pattern) that aren't in any pre-existing skill — all captured in the SKILL.md and `references/rolling-pr-execution-checklist.md` updates from June 2026.

The end result of the full refactor:

- `dashboard.js`: 4,500 → 1,324 lines (–70.6%)
- 7 new lib files + 13 new view files (lib/, views/)
- 3 new test files in lib/__tests__/: 100 vitest tests pass
- 914/914 pytest tests pass
- All views render with 0 browser console errors
- The dashboard now has a clean, fully modular architecture: each view is a self-contained ES module that imports from `lib/`. Adding a new view is a one-file change in `ui/js/views/`.

## Reference files

- `references/format-js-pitfall-recipe.md` — full 2-hour debugging transcript for Pitfall 1, plus a 30-second diagnostic snippet to paste into DevTools after any IIFE→module refactor
- `references/lazy-view-cache-and-truncated-template.md` — 2026-06-14 case study: missing league pills and a non-working More button caused by module-cache staleness + a corrupted template literal
- `references/lazy-view-renderer-preload.md` — 2026-06-14 case study: team/match clicks did nothing because `navigateToTeam`/`restoreFromHash` called `globalThis.renderTeamDetail`/`showMatchDetail` before the lazy view modules were loaded
- `references/rolling-pr-execution-checklist.md` — per-PR dispatch template, controller-level workflow, time budget, 8 lessons for executing 5+ view-extraction micro-PRs in sequence (the pattern that emerged during PR3.1–PR4 of the ELO Scenario Lab refactor), and a one-shot "wrap-up audit" script that catches all the cleanup work the subagent is most likely to have missed
- `templates/dashboard-js-iife-wrapper.js` — copy-paste starting point for the monolith wrapper (Promise.all → IIFE → catch)