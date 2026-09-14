# Water, buildings, and bridges

City-builder playfield rules proven on the Three.js Charter map.

## Placement

- Zones (3×3), civic, trees, parks, rail, pipes, power: **dry ground only**.
- Harbor: **shore**, not the water tile.
- Road on open water: only if both ends hit land and the wet run is **≤ 4 tiles**. Store as `BRIDGE` (this project: tile 49). Regular road stays 48.
- Bulldoze a bridge → restore river (21), not dirt.
- Validate **before** charging the budget.

## Terrain

- Paint water first. Then trees only on `!isWet`.
- Showcase `set()` must skip wet tiles. Roads over water go through the bridge helper, not a blind `setTile(48)`.
- River: float centerline + distance width (not a 3-tile Manhattan zigzag). Overlapping water **planes**, not boxes.

## Draw

- Bridge tiles are wet underneath: include them in the water sheet, then draw a raised deck + pier.
- `ShaderMaterial` water on `InstancedMesh` needs `instanceMatrix` (see `webgl-shader-craft` / `references/instanced-shader-material.md`).
- Cars treat `road || bridge` as pavement.

## Verify

Screenshot after start: no Kenney house or tree standing in the channel; at least one raised crossing with water visible under the deck.
