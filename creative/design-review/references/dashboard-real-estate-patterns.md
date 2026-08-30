# Dashboard Real-Estate Patterns

When auditing or redesigning a data-dense dashboard page (team detail, analytics overview, portfolio summary), watch for these specific real-estate anti-patterns that waste vertical space and dilute information density.

## Hero Section Density

- [ ] **Narrative prose that duplicates stat tiles.** If the hero says "The Yankees are surging — +47 in the last 7 days" and a tile below says "7-Day: +47", the prose is redundant. Remove it — the tile is scannable, the prose is not.
- [ ] **Decorative gradients/backgrounds that carry zero information.** A `linear-gradient` behind the hero adds visual noise without data. Strip it.
- [ ] **Oversized avatars.** A 64px circle with 2 initials is decoration, not function. Shrink to 40-48px, use a square with `border-radius: 8px` for a more utilitarian look.
- [ ] **Actions (Share/Back) competing with primary info.** If actions are secondary, make them icon-only buttons (12px SVG) with `title` attributes, not text buttons.

## Chart Hygiene

- [ ] **Area fill under simple line charts.** The gradient fill between the line and the x-axis is decorative noise. Use a line only, or remove the chart entirely if the same information is in pills/tiles.
- [ ] **Redundant timeline below the chart.** A "last 10 periods" dot row below an area chart adds nothing the chart already shows. Remove one or the other.
- [ ] **Chart taller than 140px for a single metric.** A 220px-tall SVG for a rating-over-time line is excessive. Shrink to 100-120px, add outcome markers (W/L dots on the line) if the data supports it.

## Card vs List Layout

- [ ] **Sparse cards when rows would do.** If each card has 4 lines of text and generous padding, a compact row (avatar + name + stat + bar) shows 2× the items in the same space. Use rows for homogeneous data, cards for heterogeneous.
- [ ] **Series rendered as separate cards.** 3 sequential games vs the same opponent should be one row: "vs Tigers — 3 games (Jun 10-12)". Group by `opponent_id` before rendering.

## Gauge Over-Engineering

- [ ] **Custom gauge components for a single number.** A track + fill + marker + labels + value for "+4.2%" is visual noise. A single stat row with a colored arrow communicates the same thing in 20px of height.
- [ ] **Only showing the first item when multiple exist.** If the data has N divergence items, show all N (in a compact table) or explicitly say "Showing 1 of N" — don't silently drop data.

## Tab & Table Design

- [ ] **Auto-generated narrative paragraphs inside tabs.** "X leads the offense with a .OPS OPS" is generic, often wrong, and pushes the actual table below the fold. Remove narratives; the table is the content.
- [ ] **Tabs with almost no content.** A "Bullpen" tab with one number and a bar wastes a whole tab. Merge it into an adjacent tab (e.g., show bullpen WAR as a summary row above the rotation table).
- [ ] **Tables without scan lines.** Every row looking identical makes it hard to track across columns. Add zebra striping (`tbody tr:nth-child(even) { background: rgba(255,255,255,0.015) }`) or at minimum a hover state.

## Scenario / What-If Surfaces

- [ ] **Bulky cards for simple items.** A 300px-wide card with title, description, shift bar, and key players for each scenario is overkill when the user wants to scan 5-10 scenarios. Use compact rows with accordion expand.
- [ ] **Description text that wraps unevenly.** Long descriptions make cards different heights, breaking grid alignment. Truncate or accordion.

## Navigation & Wayfinding

- [ ] **Long scroll with no jump links.** A 2000px+ page needs section anchors and a sticky TOC or jump links. Add `id` attributes to each section and wire them into the sticky header.
- [ ] **Sticky header that only shows the team name.** If the header is fixed, make it useful: add jump links (Overview | Form | Schedule | Roster | Scenarios) that smooth-scroll to anchors.

## Verified Patterns from ELO Scenario Lab Redesign (2026-06-10)

These specific changes saved ~500-700px of vertical real estate on a typical team detail page:

| Before | After | Space Saved |
|--------|-------|-------------|
| 64px circular avatar + narrative paragraph + 5 stat tiles stacked | 44px square avatar + name + stats inline in one row | ~180px |
| 220px area chart + 10-dot timeline below | 120px line chart with W/L markers, no timeline | ~140px |
| 3 opponent cards (260px each, grid) | 5 compact rows (avatar + name + % + date) | ~200px |
| Gauge with track/fill/marker/labels (~200px) | Single stat row with arrow + badges (~40px) | ~160px |
| 4 tabs including nearly-empty Bullpen tab | 3 tabs, bullpen merged into Rotation as summary bar | ~60px tab bar + content |
| 3 scenario cards (300px min, uneven heights) | 5 accordion rows (compact, uniform) | ~200px |
| No section anchors, no TOC | Sticky header with 5 jump links | N/A (navigation) |
