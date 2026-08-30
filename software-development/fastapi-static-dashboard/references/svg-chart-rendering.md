# SVG Chart Rendering in Vanilla-JS Dashboards

Render SVG sparkline/line charts inside JS template literals for data dashboards. This technique avoids any library dependency (Chart.js, D3, Recharts) and works in a single-file dashboard.

## Pattern

### 1. Compute chart geometry

```javascript
const ratings = history.map(h => h.rating);
const minR = Math.min(...ratings) - 20;    // padding below lowest point
const maxR = Math.max(...ratings) + 20;    // padding above highest point
const range = maxR - minR || 1;
const width = 800;   // viewBox width (scales to 100% via CSS)
const height = 200;  // viewBox height
const pad = 40;      // margin for axis labels
const chartW = width - pad * 2;
const chartH = height - pad * 2;
```

### 2. Build point coordinates

```javascript
const points = ratings.map((r, i) => {
  const x = pad + (i / (ratings.length - 1 || 1)) * chartW;
  const y = pad + chartH - ((r - minR) / range) * chartH;
  return `${x},${y}`;
}).join(' ');

const areaPoints = `${pad},${pad + chartH} ${points} ${pad + chartW},${pad + chartH}`;
```

### 3. Generate grid lines and labels

```javascript
const gridLines = [];
for (let i = 0; i <= 4; i++) {
  const y = pad + (i / 4) * chartH;
  const val = Math.round(maxR - (i / 4) * range);
  gridLines.push(`<line x1="${pad}" y1="${y}" x2="${pad + chartW}" y2="${y}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4,4"/>`);
  gridLines.push(`<text x="${pad - 8}" y="${y + 4}" text-anchor="end" fill="var(--text-faint)" font-size="10">${val}</text>`);
}
```

### 4. Render the SVG

```javascript
const svgChart = `
  <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;max-height:280px;" preserveAspectRatio="xMidYMid meet">
    <defs>
      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.25"/>
        <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
      </linearGradient>
    </defs>
    ${gridLines.join('')}
    <polygon points="${areaPoints}" fill="url(#areaGrad)"/>
    <polyline points="${points}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <!-- Interactive dots for tooltips -->
    <circle cx="${x}" cy="${y}" r="4" fill="var(--accent)" stroke="var(--bg-panel)" stroke-width="2" class="chart-dot" data-rating="${r.toFixed(1)}" data-date="${formatDate(date)}"/>
  </svg>
  <div id="chart-tooltip" style="position:absolute;background...;pointer-events:none;opacity:0;transition:opacity 0.15s;z-index:10;"></div>
`;
```

## Event Delegation for Tooltips (instead of inline `<script>`)

**DO NOT** embed `<script>` tags inside template literals that get injected via `innerHTML`. Scripts inserted via `innerHTML` don't execute, and `</script>` inside a template literal breaks the outer `<script>` tag's HTML parsing.

**DO** use event delegation on a parent element that always exists:

```javascript
// At top level of the script (outside any render function)
document.getElementById('content').addEventListener('mouseover', function(e) {
  const dot = e.target.closest('.chart-dot');
  if (!dot) {
    const tooltip = document.getElementById('chart-tooltip');
    if (tooltip) tooltip.style.opacity = '0';
    return;
  }
  const tooltip = document.getElementById('chart-tooltip');
  if (!tooltip) return;
  tooltip.innerHTML = '<div style="font-weight:600">' + dot.dataset.date + '</div><div>Rating: ' + dot.dataset.rating + '</div>';
  tooltip.style.opacity = '1';
  const rect = dot.getBoundingClientRect();
  const card = tooltip.closest('.card');
  if (!card) return;
  const cardRect = card.getBoundingClientRect();
  tooltip.style.left = (rect.left - cardRect.left + 12) + 'px';
  tooltip.style.top = (rect.top - cardRect.top - 40) + 'px';
});
```

## Critical Pitfalls

### 🚨 `</script>` inside template literal breaks HTML parsing

When a JavaScript template literal (backtick string) contains the string `</script>`, the HTML parser interprets it as closing the outer `<script>` tag **even though it's inside a JS string**. The rest of the script is treated as HTML.

**Symptom:** The entire script silently fails. The content div shows its placeholder text. `typeof setView` returns `"undefined"`. No console error visible because the parser error prevents script execution entirely.

**Prevention:** Never include `<script>` or `</script>` inside a template literal that's within a `<script>` tag. Use event delegation instead.

### 🚨 Extra `</div>` and `}` from patching template-literal HTML

When patching an HTML file where the JavaScript contains template literals with HTML (multiple `</div>`, `${...}`, nested backticks), each patch can introduce:
- Extra closing tags (`</div>`) that create "Unexpected token '}'" JS errors
- Extra braces that close nothing
- Misaligned template literal closures

**Prevention:** After every patch on template-literal-heavy files, re-read the patched area and count opening/closing braces and divs. Verify by loading the page in a browser, not by static analysis alone.

### SVG viewBox vs CSS sizing

The SVG `viewBox` sets the coordinate system; CSS `width:100%; height:auto` makes it responsive. `preserveAspectRatio="xMidYMid meet"` ensures the aspect ratio is maintained. Without this, the chart may stretch or compress.

### Duplicate IDs from rendering the same chart multiple times

If two charts use the same `<linearGradient id="areaGrad">` or `<div id="chart-tooltip">`, the second instance takes precedence (HTML IDs must be unique). For multiple charts, either:
- Generate unique IDs per chart (`areaGrad-${teamId}`)
- Or ensure only one chart is visible at a time (tab-based navigation, which is the common case)
