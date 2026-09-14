# Rolling PR Execution: Per-View Extraction at the Controller Level

The pattern observed across PR3.1–PR3.8 + PR4 of `docs/plans/2026-06-10-frontend-modular-refactor.md` (extracting 13 views, ~150-650 LOC each, all using the same architecture). Use this checklist when dispatching the next micro-PR in a similar series.

## Per-PR dispatch template (paste into `subagent dispatch` `context`)

```
Background: This is PR3.N of the modular dashboard refactor. PR3.1-3.N-1 (commits <list>) all succeeded. Apply the same pattern to <view> view.

Working directory: /path/to/project

CRITICAL LESSONS to apply (do not skip):
1. Verify EVERY import name is actually exported by the target module.
   A bad import (e.g. importing `displayTeamName` from `format.js` when
   it's a true global from `team-display.js`) makes the dynamic
   import() in dashboard.js's wrapper REJECT, which prevents the IIFE
   from ever starting. The symptom: modules load (globalThis.state
   etc. are set), window.dashboard is undefined, console is clean.
   Diagnostic: `Object.keys(globalThis).filter(k => /render/.test(k))`
   to see which view's render function is undefined.
2. Replace bare-identifier references to true globals
   (LEAGUE_LABELS, getShortName, displayTeamName, Auth) with
   `globalThis.X` accessors. Modules are strict mode — bare references
   to true globals throw ReferenceError even when the global is set
   on `window` by a classic script.
3. The shared-state mirror pattern (PR3.5/3.6): if the view has
   module-level state shared with other modules (e.g. _scheduleGames,
   _accSort, _accFilter), declare it as module-level let in the new
   view file AND mirror on globalThis at the bottom:
   `globalThis._scheduleGames = _scheduleGames;`
4. globalThis.<renderFn> = <renderFn> at the bottom of the new file
   (the IIFE's loadView switch calls renderFn() as a bare identifier).
5. No <script type="module" src="..."> tags in dashboard.html.
6. The new view file is added to the _modulePromises array in
   dashboard.js (with ?cb=Date.now() cache buster) — the view is NOT
   pre-loaded by the HTML.
7. Remove the corresponding `globalThis.X = X;` line from the
   IIFE's hoisted-exports block in dashboard.js. Leaving it in
   place will overwrite the module's real implementation with the
   IIFE's stub and cause infinite recursion the first time the
   view is loaded. See main SKILL.md Pitfall 7.

Template files to read:
- ui/js/views/<simplest prior view>.js (e.g. ratings.js for PR3.1)
- ui/js/views/<most similar prior view>.js (e.g. schedule.js for shared state)

Steps:
1. Find `async function render<View>()` in dashboard.js
2. Create ui/js/views/<view>.js following the ratings.js pattern
3. Update dashboard.js:
   - add to _modulePromises
   - remove the function body, keep a stub `function X() { return globalThis.X(); }`
   - remove globalThis.X = X from hoisted exports
   - audit window.dashboard = { ... } for shorthand properties that
     reference symbols you removed (use explicit `X: globalThis.X`)
4. Test: node -c, vitest run (100 pass), pytest -q (914 pass)
5. Visual QA: click <View> in sidebar, view renders, console 0 errors

Report back. Do NOT commit. Do NOT push.
```

## Controller-level workflow after each subagent returns

```bash
# 1. Verify files
git status --short
wc -l ui/js/dashboard.js ui/js/views/<view>.js

# 2. Verify imports
for f in ui/js/views/<view>.js; do
  echo "=== $f imports ==="
  grep "^import " "$f"
done

# 3. Verify each import name is in target's exports
# (manual check — read the target module's export block)

# 4. Bare-identifier sweep — find any true-global references
# that should be globalThis.X in the new module
grep -nE "\b(LEAGUE_LABELS|TEAM_ABBREVS|displayTeamName|getShortName|normalizeTeamName|Auth)\b" ui/js/views/<view>.js \
  | grep -v "globalThis\." | grep -v "typeof " | grep -v "^.*://"

# 5. Quick test run (no need to delegate this)
./node_modules/.bin/vitest run 2>&1 | tail -3
pytest -q --tb=line 2>&1 | tail -2

# 6. Hoisted-block audit — verify the IIFE's hoisted-exports block
# does NOT have a `globalThis.<view-render-func> = <view-render-func>` line
# (the module sets this itself; the hoisted block would overwrite
# it with the IIFE's stub, causing infinite recursion)
grep -n "globalThis\.<view>\|globalThis\.render<View>" ui/js/dashboard.js \
  | grep -v "function " | head -10

# 7. window.dashboard shorthand audit — any shorthand properties
# in the window.dashboard = { ... } block that reference symbols
# the controller just removed? Run a controller-side check:
#   - List all shorthand properties in the namespace block
#   - For each, verify there's a function declaration with that name
#     in dashboard.js's IIFE (NOT a globalThis.X reference, since
#     shorthand resolves the bare identifier in IIFE scope).

# 8. Visual QA — controller does this directly, NOT via subagent
# (subagent visual QA failed repeatedly because the browser's auth
# session expired between subagent turns)
#   a. Navigate to login.html, log in as admin@example.com / test-password
#   b. Navigate to dashboard.html
#   c. Click the <View> button in the sidebar
#   d. your screenshot tool to confirm content rendered
#   e. browser_console to confirm 0 errors

# 9. Commit and push
git add ui/js/dashboard.js ui/js/views/<view>.js
git commit -m "refactor(frontend): PR3.N — extract <View> view

PR3.N of docs/plans/2026-06-10-frontend-modular-refactor.md.

[2-3 sentence summary]

dashboard.js: <before> -> <after> lines (-N).

[Notes on any non-obvious moves, e.g. shared state mirrored,
helper extraction, bad-import bugs found and fixed]

Visual QA: <view> renders correctly (<1 line of evidence>).
0 console errors.

Tests: 100 vitest, 914 pytest, 0 failed.

Refactor progress: N of 11 PRs done. dashboard.js at <LOC> lines."
git push origin main
```

## Why controller does visual QA, not subagent

Observed in PR3.3 (Scenarios) and PR3.4 (Divergence): the subagent's
visual QA step failed because the browser's auth session expired
between the subagent's `subagent dispatch` turn and the visual-QA step.
The subagent would `try { login('admin@example.com', ...); ... } catch
{ failed }` and report "visual QA incomplete." The controller had
to re-do the visual QA anyway. Save the round-trip: have the
controller do the visual QA directly. Subagent handles file
extraction + tests; controller handles commit + push + visual QA.

## Time budget per PR (rolling, final)

| PR | LOC moved | Subagent | Visual QA | Commit/Push | Total |
|---|---|---|---|---|---|
| PR3.1 Ratings | 99 | 4 min | 2 min | 1 min | ~7 min |
| PR3.2 Calibration | 154 | 5 min | 1 min | 1 min | ~7 min |
| PR3.3 Scenarios | 198 | 8 min | 2 min | 1 min | ~11 min |
| PR3.4 Divergence | 72 | 6 min | 4 min (bug fix) | 1 min | ~11 min |
| PR3.5 Schedule | 123 | 7 min | 2 min | 1 min | ~10 min |
| PR3.6 Accuracy | 382 | 10 min (timeout, finished) | 2 min | 1 min | ~13 min |
| PR3.7 Team Detail | 27 (orchestrator only) | 10 min (timeout) | 5 min | 1 min | ~16 min |
| PR3.8 Pipeline | 326 | 10 min (timeout) | 2 min | 1 min | ~13 min |
| PR4 Today + admin | 1064 (5 files) | 10 min (timeout) | 30 min (multi-bug) | 1 min | ~41 min |

Average ~10 min per PR when subagent succeeds. Budget 15-20 min for
the first few to absorb the import-verification overhead and the
subagent visual-QA failure mode. Budget 30-60 min for the FINAL PR
(the one that closes the loop) — even with successful subagent
work, expect at least 30 minutes of "wrap it all up" work:
hoisted-block audit, bare-identifier sweep, window.dashboard
shorthand audit, and latent-bug fixes from new data paths.

## 8 lessons that emerged across PR3.1–PR4

1. **The subagent's "removed globalThis.X from hoisted block" step is
   silently skipped when the function is being moved to a new module
   that already does its own `globalThis.X = X`.** The subagent
   thinks "I don't need to update the hoisted block because the new
   module handles it" but the hoisted block has OTHER view functions
   that the subagent didn't notice. Result: dashboard.js has
   duplicate `globalThis.renderX = renderX` lines (one in the hoisted
   block, one in the new module) — harmless but messy. Fix: in the
   controller workflow, after each PR, `grep -c "globalThis\.<view>"
   ui/js/dashboard.js ui/js/views/<view>.js` and verify the hoisted
   block in dashboard.js does NOT have the view's renderX line.

2. **Helpers in renderX that are ONLY used by renderX should be moved
   to the new file.** Plan said "RenderSchedule: has
   _scheduleGames shared state" but the actual code had `miniHistogram`
   and `renderEdgeFooter` helpers that were only used by Schedule.
   Moving them with Schedule kept the monolith lean. Controller
   check: `grep -c "<helperName>" ui/js/dashboard.js` should be 0
   after the PR (for view-specific helpers).

3. **Some view functions are >600 lines** (Team Detail at 614 LOC
   in the new file). Plan said split them, but splitting within a
   single PR is more risk than reward. Flag for a future "team-detail
   split" PR rather than blocking the current one. **Same applies
   to Pipeline (580 LOC) and Today (633 LOC)** — the controller
   shipped them as-is.

4. **The "rolling PR" pattern is itself a new class of work** that
   should probably have its own skill — but for now, the per-PR
   dispatch template + the controller-level workflow above is
   sufficient. If you do this more than 3 times in a session, the
   pattern is mature enough to write a `rolling-pr-execution` skill.

5. **Subagent timeouts on big views are a real failure mode.** When
   the subagent's first attempt times out after 600s, the filesystem
   has 80% of the work. The controller finishes the remaining 20%
   (mostly: remove the function from dashboard.js, remove the hoisted
   export line, audit for shorthand references) in 5-10 minutes with
   2-3 patch calls. Don't re-dispatch; the second attempt will re-do
   the same exploration and hit the same cap.

6. **After a controller-finishes-the-20% session, audit the
   `window.dashboard = { ... }` block for missing shorthand
   references before committing.** The subagent's partial edits can
   quietly remove a local function declaration (`function setDetailTab`,
   `function switchRosterTab`, etc.) that the namespace block still
   references via shorthand (`setDetailTab,`). Shorthand
   `setDetailTab,` resolves to `window.dashboard.setDetailTab =
   setDetailTab;` — if `setDetailTab` no longer exists in IIFE
   scope, the assignment throws `ReferenceError: setDetailTab is not
   defined`, the IIFE exits before completing, and `window.dashboard`
   is `undefined` with no console error visible (the outer
   `.catch()` only logs the rejected `Promise.all`, not the
   synchronous throw inside the `.then()`).

   **Diagnostic (after `window.dashboard` is `undefined` but modules
   load fine):**
   ```js
   // 1. Wrap the window.dashboard = { ... } block in try/catch
   try { window.dashboard = { setDetailTab, ... } } catch (e) { window.__err = e.message; }
   // 2. window.__err in console names the missing symbol
   ```

   **Fix:** convert shorthand entries to explicit references for any
   moved function: `setDetailTab: globalThis.setDetailTab` (if the
   module owns it) or restore the IIFE-local `function setDetailTab() {...}`
   declaration. Don't leave shorthand for functions that might be
   missing.

7. **The single biggest trap of a multi-PR view-extraction series:
   the IIFE's hoisted-exports block MUST be reduced as view-modules
   are added, or it will silently overwrite the module's real
   implementation with a recursive stub.** This is the lesson PR4
   surfaced (see main SKILL.md Pitfall 7). The hoisted block is meant
   to expose IIFE-only functions on `globalThis` so the
   `window.dashboard = { ... }` block can read them. But once a
   function moves to a view module, the IIFE's local `function X`
   becomes a stub `return globalThis.X()`. The hoisted block's
   `globalThis.X = X` then overwrites the module's real
   implementation with the stub. Symptom: "Maximum call stack size
   exceeded" the first time `loadView(<view>)` runs.

   **Audit step the controller MUST do after every view extraction:**
   ```bash
   # For each view that has been extracted to ui/js/views/X.js,
   # verify the hoisted block in dashboard.js does NOT have its
   # globalThis.X = X line.
   for view in ratings calibration scenarios divergence schedule accuracy team-detail pipeline today match-detail domains users corpus; do
     echo "=== $view ==="
     grep "globalThis.${view}" ui/js/dashboard.js || echo "  (no assignment — good)"
   done
   ```
   For each view file's `renderX` and any other globally-exposed
   functions, the corresponding `globalThis.X = X;` line must be
   removed from dashboard.js's hoisted block. The IIFE keeps the
   local stub function declaration, but the hoisted block skips
   the assignment.

8. **When extracting the final view (the one with cross-module
   shared state, e.g. PR4's today.js + match-detail.js + the 3
   admin views), expect at least 30 minutes of "wrap it all up"
   work even after the subagent reports success.** The "wrap up"
   is: bare-identifier sweep across the new files (Pitfall 8),
   hoisted-block audit (Lesson 7), window.dashboard shorthand audit
   (Lesson 6), and the inevitable pre-existing latent bugs that
   surface when new data paths trigger them. PR4 surfaced a latent
   infinite-recursion in `renderTopPicksSection` that had been
   dormant in the original code forever — the new data path just
   happened to hit the empty-`honest` branch. This is the 20% the
   subagent never sees, and the controller should plan for it.

## Diagnostic snippet (paste into browser console after the symptom appears)

```js
// Is the IIFE running? window.dashboard should be set.
typeof window.dashboard
// If 'undefined', the IIFE body never finished.

// Are the modules loaded? If yes, the IIFE should be able to start.
['state', 'els', 'api', 'toast', 'formatDate', 'escapeHtml',
 'renderRatings', 'renderCalibration', 'renderScenarios',
 'renderDivergence', 'renderSchedule', 'renderAccuracy',
 'renderTeamDetail', 'renderPipeline', 'renderToday',
 'showMatchDetail', 'closeMatchDetail', 'renderDomains',
 'renderUsers', 'renderCorpus']
  .reduce((o, k) => { o[k] = typeof globalThis[k]; return o }, {})

// If modules are set but window.dashboard is undefined,
// the IIFE threw. Add a try/catch to dashboard.js to capture:
//   try { window.dashboard = {...} } catch (e) { window.__err = e.message; }
// then check window.__err in the console.

// If a specific renderX is undefined but other views are set,
// that view's file has a bad import. Open the file, check
// each import line against the target's `export { ... }` block.

// If window.dashboard is set but loadView('X') throws
// "Maximum call stack size exceeded", the IIFE's hoisted block
// has `globalThis.X = X` for an X that is now a stub. Audit:
//   grep "globalThis\.X" ui/js/dashboard.js
// and remove the assignment for any X whose function body
// in dashboard.js is now just `return globalThis.X()`.
```

## The "wrap-up audit" — one-shot script for the final PR

```bash
# Run this after the LAST view is extracted. Catches all
# the cleanup work that the subagent is most likely to have missed.

cd /path/to/project

# 1. Hoisted-block audit (Lesson 7)
echo "=== Hoisted block audit ==="
for view in ratings calibration scenarios divergence schedule accuracy team-detail pipeline today match-detail domains users corpus; do
  if grep -q "globalThis.${view}" ui/js/dashboard.js 2>/dev/null; then
    echo "  WARNING: dashboard.js has 'globalThis.${view}' (should be removed)"
    grep -n "globalThis.${view}" ui/js/dashboard.js
  fi
done

# 2. Bare-identifier sweep (Pitfall 8)
echo "=== Bare-identifier sweep ==="
for f in ui/js/views/*.js; do
  results=$(grep -nE "\b(LEAGUE_LABELS|TEAM_ABBREVS|displayTeamName|getShortName|normalizeTeamName|Auth)\b" "$f" \
    | grep -v "globalThis\." | grep -v "typeof " | grep -v "^.*://" || true)
  if [ -n "$results" ]; then
    echo "  $f: bare reference found"
    echo "$results"
  fi
done

# 3. window.dashboard shorthand audit (Lesson 6)
echo "=== window.dashboard shorthand audit ==="
# Pull out the namespace block and look for shorthand properties
# (entries without ':' before the comma/closing brace)
sed -n '/window\.dashboard = {/,/^  };/p' ui/js/dashboard.js \
  | grep -E "^\s+[a-zA-Z_]+,$" \
  | sed -E 's/^\s+([a-zA-Z_]+),.*/\1/' \
  | while read sym; do
    # Check if the symbol has a function declaration in dashboard.js
    if ! grep -q "^  function $sym\|^  async function $sym" ui/js/dashboard.js; then
      echo "  WARNING: shorthand '$sym,' in window.dashboard has no function declaration in dashboard.js"
    fi
  done

# 4. Test run
echo "=== Test run ==="
./node_modules/.bin/vitest run 2>&1 | tail -3
pytest -q --tb=line 2>&1 | tail -2
```

Each of these checks catches a specific failure mode observed in
PR3.1–PR4. Running them as a single script at the end of the final
PR is the difference between "shipped working" and "shipped with
three bugs to find in production."
