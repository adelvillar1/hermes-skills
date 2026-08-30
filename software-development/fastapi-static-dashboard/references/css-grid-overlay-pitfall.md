# CSS Grid Layout Debugging — Overlay Div Breaking Grid

## Session Context

2026-05-15: Dashboard layout broken — sidebar showed correctly at 240px, but main content was also 240px wide and positioned at `left: 0` instead of `left: 240px`. Team data rendered into `#content` but was invisible due to being squashed into the sidebar track.

## Root Cause

The `.overlay` div (mobile sidebar backdrop) sat between `<nav class="sidebar">` and `<div class="main">` in the DOM. With `display: block` (default for divs), it became an implicit grid item, consuming the `1fr` track. The `.main` div became the third grid item and got pushed to a new row.

## HTML Structure That Broke

```html
<div class="app">           <!-- grid: 240px 1fr -->
  <nav class="sidebar">...</nav>     <!-- grid item 1: 240px -->
  <div class="overlay"></div>       <!-- grid item 2: 1fr ← BREAKS -->
  <div class="main">...</div>       <!-- grid item 3: new row -->
</div>
```

## Fix Applied

Added `style="display:none"` to the overlay div (it only shows on mobile when sidebar is open):

```html
<div class="overlay" id="overlay" style="display:none"></div>
```

Alternative fixes that would also work:
1. Place overlay INSIDE sidebar as a child
2. Use `position: fixed` with `display: none` by default
3. Add explicit `grid-column: 2` to `.main`

## Verification

```javascript
// Before fix:
document.querySelector('.main').getBoundingClientRect()  // {left: 0, width: 240}

// After fix:
document.querySelector('.main').getBoundingClientRect()  // {left: 240, width: 1040}
```

## Lesson

When a grid container has children that aren't explicitly placed with `grid-column`/`grid-row`, they become implicit grid items in source order. A `display: block` sibling between two intended grid items will consume a track and break the layout. Always either:
- Hide non-visible elements (`display: none`)
- Place them outside the grid (`position: fixed`)
- Explicitly assign grid tracks to all children
