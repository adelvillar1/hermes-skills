# Step-change city look (not more boxes)

User bar (2026-08-17, simcityclone): incremental renderer polish is not enough. "Not tied to any architecture. I want this to look beautiful."

## What actually moved the screenshot

1. **Authored 3D, not generated boxes.** Kenney City Kit (CC0) GLBs: suburban houses, commercial + skyscrapers, industrial. Drop under `public/kenney/{suburban,commercial,industrial}/`.
2. **Texture siblings.** Kenney GLBs request `Textures/colormap.png` relative to the `.glb`. Extract `Models/GLB format/Textures/colormap.png` into each kit folder. Symptom if missing: `THREE.GLTFLoader: Couldn't load texture Textures/colormap.png` and untextured/pink meshes.
3. **Fit trees separately.** `Box3` fit to ~2.7 is right for a 3-tile building. Same target on Kenney trees eats the skyline. Trees: fit ~1.15.
4. **Golden-hour light + HUD recedes.** ACES, low warm sun, fog that matches sky. Atlas off by default. Paper HUD translucent. The city is the product.
5. **Hard-reload after kit load.** Terrain gen and Zustand map live at module scope; `?v=` query so Vite + store re-run.

## Downloads that worked

- Suburban (OGA): `https://opengameart.org/sites/default/files/kenney_city-kit-suburban_2.0.zip`
- Commercial: Kenney page "Continue without donating" zip (versioned media URL on kenney.nl)
- Industrial: same pattern

Load with `GLTFLoader` from `three/addons/loaders/GLTFLoader.js`. Clone + `castShadow` on meshes.

## What did not move the shot

More canvas sprites, SVG tiles, 16×16 Micropolis blit without an ID map, extra civic boxes, extra cars. Those are deltas on a wrong art stack.

Related: `sprite-rendering-notes.md`, `city-builder-hud.md`, `playfield-capture.md`.
