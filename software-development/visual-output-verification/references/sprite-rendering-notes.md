# Sprite Rendering Approaches — Tradeoffs and Recommendations

## The Problem

Programmatically generating small sprites (16×16) results in unrecognizable colored rectangles. Buildings, roads, and trees need actual detail to be readable.

## Approaches Tried

### 1. Programmatic Canvas Sprites (current)
- **How:** Generate `HTMLCanvasElement` per tile variant, cache them, draw with `ctx.drawImage()`
- **Pros:** Fast at runtime, no external assets needed
- **Cons:** 16×16 is too small for recognizable shapes. Algorithmic patterns look mechanical.
- **Verdict:** Acceptable for prototyping, not for polished visuals.

### 2. Pixel Art Pattern Maps
- **How:** Define sprites as 16×16 string arrays where each char maps to a color
- **Pros:** Easy to edit, compact representation
- **Cons:** Still limited by 16×16 resolution. Char-to-color mapping is lossy.
- **Verdict:** Slightly better than pure programmatic, still not great.

### 3. Larger Tile Sizes (32×32 or 64×64)
- **How:** Increase `TILE_SIZE` and draw more detailed sprites
- **Pros:** Much more room for recognizable detail
- **Cons:** More pixels to define, larger memory, needs zoom for large maps
- **Verdict:** Recommended for hand-crafted pixel art.

### 4. Real Sprite Assets (recommended for production)
- **How:** Use sprite sheets from open-source projects
- **Best sources:**
  - **3d.city** (MIT) — 3D models + textures from micropolisJS engine
  - **OpenSC2K** — SimCity 2000 asset extraction
  - **Lincity-NG** — Detailed 2D sprites for all building types
- **Pros:** Hand-crafted, recognizable, consistent style
- **Cons:** License compliance, asset pipeline
- **Verdict:** Use this for anything user-facing.

## Recommendation

For a polished SimCity clone:
1. **Use 3D.city's approach** — Three.js renderer with micropolisJS simulation core (MIT)
2. **Or use 32×32 hand-drawn sprites** with proper pixel art tools
3. **Never ship 16×16 programmatic sprites** — they're unrecognizable at that size

## Key Insight

**Visual verification is mandatory.** Writing rendering code without seeing the output is like painting with your eyes closed. Always screenshot + your vision tool.
