# Capture the playfield, not the splash

When verifying a city builder (or any app with a title screen):

1. Playwright: click the start control (`Open the city`, etc.), wait for the canvas to paint, then screenshot.
2. Confirm the shot is the map: grass/water/roads present, not a single dark fill.
3. Ask vision a concrete question: "Are there roofs and road joins?" not "does it look good?"
4. Seed a small showcase district if the wilderness is empty — otherwise you will judge dirt.

The user treats "look at it" as mandatory. Architecture answers to "is this the best visually?" are a miss. Screenshot, then change.

Related: `city-builder-hud.md` (chrome), `sprite-rendering-notes.md` (tiles). Donor sheets still need an ID map — see `canvas-game-renderer` / `references/tile-id-and-density.md`.
