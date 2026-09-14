---
name: visual-output-verification
description: Build visual output. Verify with screenshots, never assume.
---

# Visual Output Verification

## Trigger

Use this skill whenever you are:
- Building or modifying a game renderer, UI component, or canvas/SVG visualization
- Writing code that produces visual output (sprites, tiles, charts, layouts)
- Making changes to colors, shapes, positioning, or visual styling
- Working with pixel art, tile maps, or any raster/vector rendering

## Core Principle

**Code correctness ≠ visual correctness.** A renderer can execute perfectly and still produce ugly, broken, or misleading visuals. The only way to know if visuals look right is to *look at them*.

## Workflow

### 1. Render to a File

```javascript
const buffer = canvas.toBuffer('image/png');
fs.writeFileSync('/tmp/output.png', buffer);
```

Or use Playwright for browser-based work:

```javascript
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.goto('http://localhost:3000');
await page.waitForTimeout(2000);
await page.screenshot({ path: '/tmp/screenshot.png' });
```

### 2. Inspect with your vision tool

Ask specific questions: "What do the buildings look like?" not "Does this look good?"

### 3. Iterate

First renders are always rough. Fix based on visual feedback, not assumptions.

## Pitfalls

- **"It Renders" Trap:** Code runs, pixels produced, you declare it done. User sees colored rectangles. Fix: screenshot + your vision tool.
- **16×16 Trap:** Too small for recognizable shapes. Fix: go larger or use real assets.
- **Headless Trap:** You can't see the browser, so you assume. Fix: always produce a file and inspect.
- **Programmatic Trap:** Algorithmic sprites look worse than hand-crafted. Fix: use real sprite sheets for critical visuals.

## Screenshot capture: browser automation harness vs Playwright

**browser automation harness (`your browser tool` / `your screenshot tool`) can return
all-black screenshots of WebGL/R3F canvases** even when the scene renders
correctly. For all WebGL/Three.js/R3F visual verification, use
`npx playwright screenshot` instead. See
[`references/browser-harness-vs-playwright.md`](references/browser-harness-vs-playwright.md)
for the diagnosis pattern and Playwright + Pillow pixel-analysis recipe.

## Reviewing a hand-crafted SVG when the browser is unavailable

When you hand-craft an SVG (e.g. a new line icon or a small standalone graphic) and need to
SEE it before committing, the usual paths can both fail:

- **ImageMagick renders SVG blank/unreliable.** `magick file.svg out.png` produces an
  empty or broken raster when there's no librsvg delegate — it chokes on `scale()`
  transforms inside `<g>` and errors out on `<text>` (`unable to read font`). Do NOT trust
  a blank output; if the bytes are tiny (~1KB) it almost certainly rasterized nothing.
- **Browser harness can be degraded** (the macOS "Allow remote debugging?" prompt leaves
  `your browser tool` permission-blocked), so `your screenshot tool` can't render the SVG either.

**Working fallback: macOS Quick Look rasterizes SVG natively and is always available:**
`qlmanage -t -s 800 -o /tmp file.svg` → writes `/tmp/file.svg.png`, then `your vision tool`
that PNG. (Drop any `<text>`/`<label>` elements first — Quick Look renders the paths fine
but the font you can't control; remove labels and remember their order.)
This is for hand-drawn glyphs/small SVGs. For full web pages use `npx playwright screenshot`
(above), not `qlmanage`.

## Proving layout structure (not just eyeballing it)

When an AC is a specific grid structure (N columns × M rows, column-major
fill, per-page numbering), screenshots alone miss fill-direction and
track-count bugs that render "plausible." Use the Playwright computed-style +
bounding-box assertion recipe in
[`references/css-grid-layout-assertions.md`](references/css-grid-layout-assertions.md)
— three layers (computed style, geometry, DOM order) plus seed-then-assert
for data-order-sensitive displays.

## Static-file QA when the browser harness is degraded (2026-08-26, the project-cockpit app)

When a deliverable is a static HTML file (or any file:// page) and `your browser tool`
is permission-blocked by the macOS "Allow remote debugging?" prompt, Playwright
works directly — but two setup realities apply:

- **Playwright browsers may not be installed yet** (`Executable doesn't exist at
  .../ms-playwright/...`). Fix, don't abandon: `python3 -m playwright install chromium-headless-shell`
  (~90MB, one time), then the standard sync API works.
- **Scroll-position reads can silently return 0** in a default-height viewport
  because the page doesn't scroll at all — a "before == after, no scroll reset"
  conclusion is then vacuous. Force a small viewport (`viewport={"width":900,"height":500}`)
  to make the page actually scrollable before testing scroll-preservation behavior.
- **Sidebar elements can be `display:none` below the responsive breakpoint**
  (v1 used `@media (max-width:900px)`), so `#change`/`#reset` clicks time out with
  "element is not visible." At desktop width (≥1200px) they're visible. Match the
  viewport to the breakpoint you're testing, not a one-size default.

- **16×16 tiles:** Use sprite sheets from open-source projects (MIT licensed)
- **32×32+:** Can generate with care
- **Isometric:** Use SVG or pre-rendered sprites