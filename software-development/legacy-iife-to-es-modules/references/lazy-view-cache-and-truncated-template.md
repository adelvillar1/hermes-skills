# Lazy view module cache-busting and corrupted-template debugging

Companion reference for `legacy-iife-to-es-modules` SKILL.md, Pitfall 3. Captures the specific debugging sequence from 2026-06-14 when the dashboard `More ▾` overflow menu appeared to be ignored and the league pill strip only rendered `All` and `More`.

## Symptom

- Dashboard loads successfully, no console errors.
- The league pill strip only shows `All` and `More` — the top-league pills (MLB, NFL, etc.) are missing.
- Clicking `More` either does nothing or refreshes the page; no overflow dropdown appears.
- Browser-Use shows the More button's `onclick` attribute as `dashboard.setLeague('MLB')` even though the source file was edited to use `dashboard.toggleLeagueOverflow`.

## Root cause (two interacting problems)

1. **Module cache**: the router's lazy view loader (`ui/js/lib/router.js`) was importing view files without a cache buster. After editing `ui/js/views/today.js`, the browser kept executing an older cached version. The live DOM showed old `onclick` handlers and old markup.
2. **Corrupted template literal**: during an earlier edit, a `read_file` response returned a truncated line (`...[truncated]`) and that literal string was written back into the source file. The file parsed successfully, but the league-pill `.map()` produced broken HTML because the template contained `...[truncated]`:

```js
${TOP_LEAGUES.map(l => `
  <button class="league-pill ..." onclick="dashboard.setLeague('${l}')" ...[truncated]
`).join('')}
```

This is valid JavaScript but produces a template string that ends with `...[truncated]`, so each mapped button was malformed and effectively only the initial literal text plus a broken button appeared. The symptom is "module loaded but data is wrong" rather than a syntax error.

## Fix

### Step 1: add cache buster to lazy view imports

In `ui/js/lib/router.js`:

```js
async function _importView(name) {
  if (_loaded.has(name)) return _loaded.get(name);
  if (_inFlight.has(name)) return _inFlight.get(name);
  const path = _VIEW_FILES[name];
  if (!path) throw new Error(`Unknown view: ${name}`);
  const cacheBustedPath = `${path}?cb=${Date.now()}`;
  const p = _doImport(cacheBustedPath)
    .then((mod) => { _loaded.set(name, mod); _inFlight.delete(name); return mod; })
    .catch((err) => { _inFlight.delete(name); throw err; });
  _inFlight.set(name, p);
  return p;
}
```

### Step 2: verify source file is not corrupted

After any edit where `read_file` showed `...[truncated]`, read the exact bytes:

```bash
python3 -c "
with open('ui/js/views/today.js') as f:
    for i, line in enumerate(f, 1):
        if 60 <= i <= 66:
            print(i, repr(line))
"
```

Look for literal `...[truncated]` in any template literal. If present, rewrite the surrounding markup from a known-good source or from git history.

### Step 3: wire interactive handlers immediately

If an interactive handler (e.g., the `More` button) is wired inside a deferred callback (`requestIdleCallback`, `setTimeout`, `Promise.then` after data fetch), the user can click it before the wiring runs. Move the wiring to immediately after the DOM element is inserted:

```js
els.content.innerHTML = pillsHtml + ...;
wireLeagueOverflowToggle(); // not inside requestIdleCallback
```

Use a guard to prevent double-wiring:

```js
function wireLeagueOverflowToggle() {
  const btn = document.getElementById('leagueMoreBtn');
  const menu = document.getElementById('leagueOverflowMenu');
  if (!btn || !menu || btn.dataset.wired === 'true') return;
  btn.dataset.wired = 'true';
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    e.preventDefault();
    window.dashboard.toggleLeagueOverflow();
  });
}
```

## Diagnostic snippet for this specific case

In the browser console after reproducing:

```js
// Is the executing file stale?
fetch('/js/views/today.js?cb=' + Date.now())
  .then(r => r.text())
  .then(t => console.log(
    'has toggleLeagueOverflow:', t.includes('toggleLeagueOverflow'),
    'has truncated marker:', t.includes('...[truncated]')
  ));

// What does the live button look like?
const b = document.getElementById('leagueMoreBtn');
console.log({ tag: b?.tagName, onclick: b?.getAttribute('onclick'), wired: b?.dataset.wired });
```

If `toggleLeagueOverflow` is in the fetched source but the live button still has `onclick="dashboard.setLeague('MLB')"`, the module cache is stale. If `...[truncated]` is in the fetched source, the file itself is corrupted.

## Lesson

When a fix appears to have no effect after editing a lazy-loaded ES module:
1. First suspect module cache, not logic.
2. Add a cache buster and hard-reload.
3. Then verify the file on disk is not corrupted by a truncated read — the file may parse but produce wrong output.
4. Only then debug the runtime behavior.
