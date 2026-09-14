# Frontend Module-Cache and Dropdown Pitfalls

Real-world patterns from debugging a dashboard dropdown that would not open despite correct code.

## Scenario

Dashboard uses lazy ES-module view loading. A `today.js` view module renders a compact league-selector strip with a "More ▾" overflow button. The overflow menu is `position: absolute` inside a scrolling flex row (`overflow-x: auto`).

Symptoms:
- Clicking the More button does nothing.
- The live DOM shows stale `onclick` attributes even though the fetched source file is new.
- CSS changes (fixed positioning, z-index) appear to have no effect.

## Root causes and fixes

### 1. Lazy module cache hides edits

The router was loading view modules without a cache buster. Browser module cache can return a stale module even when `fetch()` of the same URL returns the new source text.

**Fix:** add `?cb=${Date.now()}` to dynamic view imports:

```js
const cacheBustedPath = `${path}?cb=${Date.now()}`;
const mod = await import(cacheBustedPath);
```

Also use cache-busters on all critical-path imports during active development. The `?cb=Date.now()` pattern is already required for Browser-Use sandboxes, but it is equally important for local dev servers that don't send strong cache headers.

### 2. `overflow-x: auto` clips absolutely positioned children

A dropdown menu inside `position: absolute` but nested under a scrolling container with `overflow-x: auto` may be clipped or fail to escape the container's bounds.

**Fix:** move the menu outside the scrolling container and use `position: fixed` with coordinates computed from the trigger's `getBoundingClientRect()`:

```html
<div class="league-pills-wrap">
  <div class="league-pills league-pills--compact">
    <button class="league-pill">All</button>
    <button class="league-pill">MLB</button>
    ...
    <button type="button" id="leagueMoreBtn">More ▾</button>
  </div>
  <div id="leagueOverflowMenu" class="league-overflow-menu" style="display:none">
    <button class="league-pill">La Liga</button>
    ...
  </div>
</div>
```

```js
function openOverflow() {
  const rect = leagueMoreBtn.getBoundingClientRect();
  menu.style.position = 'fixed';
  menu.style.top = `${rect.bottom + 6}px`;
  menu.style.left = `${Math.min(rect.left, window.innerWidth - menuMinWidth)}px`;
  menu.style.zIndex = '100';
  menu.style.display = 'flex';
}
```

```css
.league-overflow-menu {
  position: fixed;
  z-index: 100;
  display: none;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-standard);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  min-width: 160px;
  width: max-content;
}
```

### 3. Inline `onclick` on dynamically injected elements is fragile

Inline `onclick="fn()"` on HTML injected via `innerHTML` can fail to bind correctly in some browser automation contexts or when the global function name is reassigned after module load.

**Fix:** use a real `<button type="button">` and bind a direct event listener after insertion:

```js
const btn = document.getElementById('leagueMoreBtn');
btn.addEventListener('click', (e) => {
  e.stopPropagation();
  toggleMenu();
});
```

### 4. CSS syntax errors silently disable downstream rules

A missing `}` in a preceding rule caused the browser to skip the entire `.league-overflow-menu` block and related styles. No console error was surfaced.

**Fix:** validate CSS after editing near rule boundaries. Use a CSS linter or at minimum grep for balanced braces in the edited region:

```bash
# Quick brace-balance check around a region
cd ui/css && python3 -c "
import re
text = open('dashboard.css').read()
start = text.find('.league-pills-wrap')
region = text[max(0,start-500):start+1500]
print('braces balanced:', region.count('{') == region.count('}'))
"
```

### 5. Verify the executing module, not just the fetched source

`fetch('/js/views/today.js').then(r => r.text())` showed new code, but the executing module was stale. The fetched text is not proof the runtime module is fresh.

**Fix:** inspect live DOM attributes or call functions that only exist in the new module:

```js
// Check the live onclick attribute of the injected element
document.getElementById('leagueMoreBtn').getAttribute('onclick');

// If it doesn't match the new source, the module cache is stale.
```

## Verification checklist for dynamic dropdowns

1. Source file contains the new markup/JS/CSS.
2. Dynamic import uses a cache buster in development.
3. Dropdown is outside any `overflow: hidden/auto` ancestor or uses `position: fixed`.
4. Trigger is a real `<button type="button">` with a direct `addEventListener`.
5. CSS around the dropdown has balanced braces and no syntax errors upstream.
6. Live DOM matches the new source before considering the feature working.
