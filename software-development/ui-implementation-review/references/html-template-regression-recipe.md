# HTML Template Regression Recipe

> Session-specific detail from 2026-06-14 dashboard UI polish sprint.
>
> When a frontend view builds DOM by interpolating HTML strings inside JavaScript template literals, two failure modes are easy to ship silently: (1) the patch escapes angle brackets and the browser shows raw tags, and (2) a skeleton wrapper is replaced via `.innerHTML =` and ends up nested inside the real section markup.

## Failure mode 1: escaped angle brackets

### Symptom in browser

The page shows literal text like:

```
<div class="today-section" id="top-picks"> <div class="today-section-title"> Top Picks ...
```

### Root cause

The patch tool wrote `&lt;` and `&gt;` into the JavaScript source as `&amp;lt;` / `&amp;gt;` (or the file was edited with HTML-escaped literals). Because the code is a JavaScript string, those entities are not decoded; they are rendered as text.

### How to detect before shipping

```bash
# Any &lt; or &gt; inside a JS template literal is a red flag
grep -n "&lt;\|&gt;" ui/js/views/*.js
```

### Fix

Replace the escaped entities with real angle brackets in the source. For example, change:

```javascript
return `
  &lt;div class="today-section"&gt;
    &lt;div class="today-section-title"&gt;Top Picks&lt;/div&gt;
  &lt;/div&gt;
`;
```

To:

```javascript
return `
  <div class="today-section">
    <div class="today-section-title">Top Picks</div>
  </div>
`;
```

Always reload the browser and screenshot the affected section after patching HTML templates.

## Failure mode 2: nested skeleton wrapper

### Symptom in browser

Section-specific CSS or anchor links do not work. Inspecting the DOM shows:

```html
<div class="today-section" data-section="top-picks">
  <div class="today-section" id="top-picks">
    ...
  </div>
</div>
```

### Root cause

The skeleton shell is `<div class="today-section" data-section="top-picks">...</div>`, and the render helper also returns `<div class="today-section" id="top-picks">...</div>`. Using `.innerHTML =` on the wrapper keeps the outer `data-section` wrapper and nests the real section inside it.

### Fix

Replace the wrapper, do not replace its contents:

```javascript
const topPicksSection = els.content.querySelector('[data-section="top-picks"]');
if (topPicksSection) {
  const frag = document.createRange().createContextualFragment(topPicksHtml);
  topPicksSection.replaceWith(frag);
}
```

Use `.innerHTML =` only when the wrapper is a generic container whose children are being replaced, not when the wrapper itself should be removed.

## Verification script

Run against a local dev server:

```bash
#!/usr/bin/env bash
set -e
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8765 --log-level warning &
PID=$!
sleep 3
# Fetch the dashboard and fail if raw escaped tags appear
curl -sS http://localhost:8765/dashboard | grep -E '&lt;div class="today-section"' && {
  echo "FAIL: escaped today-section tag found in dashboard HTML"
  kill $PID
  exit 1
}
echo "OK: no escaped today-section tags in dashboard response"
kill $PID
```

Note: this catches escaped tags in the **initial HTML response**, not in dynamically-rendered JS output. For JS-rendered sections, use the browser screenshot check.

## Checklist

- [ ] Patched JS HTML template literals contain real `<` and `>`, not `&lt;` / `&gt;`.
- [ ] Skeleton wrappers are replaced with `replaceWith(DocumentFragment)`, not `.innerHTML =`.
- [ ] Browser screenshot of the affected section shows rendered UI, not raw tag text.
- [ ] Section anchors and CSS selectors still resolve to the expected element.
