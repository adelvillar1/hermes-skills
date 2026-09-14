# City-builder HUD bar

Use when building or judging SimCity-class chrome. Tiles stay in `sprite-rendering-notes.md`.

## What "done" looks like

- Map is the full viewport. HUD overlays it. Do not shrink the canvas to leftover space (`innerWidth - 130`).
- Tools are geometric SVG (or a real icon set), grouped (survey / ways / works / zones / civic). No emoji as icons.
- Surfaces: paper, ink, desk wood, brass. Zone colors for R/C/I. Not GitHub-dark, not gold-glow "SIMCITY", not blue `#4a90d9` pills.
- Panels are side sheets (ledger, census, charts), not centered glass modals.
- Dials that fit: high density (~7), low motion (~3). The map moves; the desk does not.

## Verify in this order

1. Screenshot the briefing / title. Check: no trademark splash, no emoji CTA.
2. Click through into play. Screenshot the HUD.
3. Confirm the tool rail sits *under* the status bar and every civic tool is reachable (2-column rail or scroll — do not clip stadium/airport/plant).
4. Open ledger/census. Confirm paper sheet, not a dark modal.
5. Stop. If the map is still dirt rectangles, that is a renderer job, not another HUD rewrite.

## Product name

Do not ship the word SIMCITY on the title. Use a municipal name (this project: Charter).
