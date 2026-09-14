# Do not outsource inspection

User correction (city-builder / SimCity clone session): "you should be doing actual visual inspection and not just if the code would render okay."

## Rule

Never ask the user to open localhost and describe buildings, roads, or HUD. Capture a PNG (Playwright or canvas.toBuffer), then `your vision tool` with a specific question. Architecture answers to "is this the best visually?" are a miss.

## Recipe that actually got a playfield shot

1. Click through the briefing (`Open the city`), not the splash.
2. WebGL: `chromium.launch({ headless: true, args: ['--use-gl=angle', '--ignore-gpu-blocklist'] })`.
3. After GLSL/material edits, hard-reload (`?v=`). Vite HMR will not replace a compiled ShaderMaterial.
4. If the map is empty wilderness, seed a showcase strip before judging tiles.

See also `playfield-capture.md`. Custom `ShaderMaterial` on `InstancedMesh` must multiply `instanceMatrix` or water/ground vanish — `webgl-shader-craft` / `references/instanced-shader-material.md`.
