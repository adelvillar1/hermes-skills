# CSS Grid Layout Assertions (Playwright)

> Screenshots show a layout *looks* right; computed-style + geometry assertions *prove* it is right. Use this recipe when a feature's AC is a specific grid structure (N columns × M rows, column-major fill, per-page slot numbering) — especially for big-screen display boards where "looks roughly like a grid" hides fill-direction bugs.

## Why not screenshots alone

A column-major grid that's accidentally filling row-major (or wrapping to implicit columns) can look plausible in a screenshot at a glance — the 2026-08-10 "horizontal strip" regression was exactly this: `grid-auto-flow: column` without explicit `grid-template-rows` wraps every row into a new column, producing one long horizontal strip instead of a 2-column board. `npm run build` passes, the page renders, and only geometry catches it.

## The three-layer check

```python
# Layer 1 — computed style: flow direction + explicit track counts
style = page.evaluate(
    "() => { const el = document.querySelector('.db-grid'); const cs = getComputedStyle(el); "
    "return { flow: cs.gridAutoFlow, cols: cs.gridTemplateColumns.split(' ').length, "
    "rows: cs.gridTemplateRows.split(' ').length } }"
)
assert style == {"flow": "column", "cols": 4, "rows": 6}, style
# Note: gridTemplateColumns/Rows serialize as resolved px tracks — count the
# space-separated values, don't compare the raw string.

# Layer 2 — geometry: bounding boxes prove the fill direction
ys = page.evaluate(
    "() => [...document.querySelectorAll('.dslot')].slice(0, 8).map(e => {"
    " const r = e.getBoundingClientRect();"
    " return { pos: e.querySelector('.pos').textContent.trim(), x: Math.round(r.x), y: Math.round(r.y) } })"
)
# Column-major: slots 1..ROWS share one x (same column), increasing y.
# Slot ROWS+1 jumps to a new column (larger x) back at the first row's y.
assert all(s["x"] == ys[0]["x"] for s in ys[:6])
assert ys[6]["x"] > ys[0]["x"] and ys[6]["y"] == ys[0]["y"]
assert ys[0]["y"] < ys[1]["y"] < ys[2]["y"]

# Layer 3 — DOM order = slot order (grid-auto-flow places items in DOM order,
# so reading .pos text in selector order gives the slot sequence directly)
board = page.eval_on_selector_all(
    ".dslot.filled",
    "els => els.map(e => [e.querySelector('.pos').textContent.trim(), "
    "e.querySelector('.who').childNodes[0].textContent.trim()])",
)
```

## What each layer catches

| Bug | Screenshot | Computed style | Geometry |
|-----|-----------|----------------|----------|
| Missing explicit rows (horizontal strip) | maybe | ✅ rows ≠ expected | ✅ |
| Row-major instead of column-major fill | hard to tell | ✅ flow | ✅ slot 7 below slot 1, not beside |
| Wrong column count | maybe | ✅ cols | ✅ |
| Wrong data order (e.g. newest-first vs oldest-first) | need known data | — | — (assert text against seeded known order) |
| Per-page slot numbers not resetting | need 2 pages | — | — (paginate, assert `.pos` restarts at 1) |

## Seed-then-assert for data order

For order-sensitive displays, seed via the API with *known, distinguishable* values first (students named W01..W26 dismissed in a fixed order), then assert the rendered text sequence against the expected permutation. Exercise the compensating-action path too (undismiss + re-dismiss one entity mid-list → assert it moved to the end), which proves the display consumes the folded state, not a cached copy.

## Companion to screenshots

Still take the screenshot (`page.screenshot(full_page=True)`) and inspect it — assertions prove structure, only eyes catch contrast, clipping, and crowding (e.g. a 29px/800-weight name overflowing its slot). The two checks are complementary, not interchangeable.

## Reference instance

the school-dismissal SaaS walker display rehearsal, 2026-08-17: `/tmp/e2e_walker_display_browser.py` (not committed) verified a 24-slot, 4×6 column-major board with per-page numbering, pagination reset, and clear-clamp using exactly these layers against a seeded throwaway school on staging.
