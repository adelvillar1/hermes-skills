---
name: threejs-webgpu-pitfalls
description: Use when debugging Three.js WebGPU/TSL rendering code.
---

# Three.js WebGPU / TSL Pitfalls (r185 era)

Hard-won rules from shipping a WebGPU city-builder. Each was a real multi-hour bug; none are hypothetical.

## Module imports — never deep-import `three/src/*`

Deep-importing e.g. `three/src/renderers/common/extras/PMREMGenerator.js` instantiates a **second copy of the node system** alongside the `three/webgpu` bundle. Two incompatible node-class hierarchies → runtime failures like `Cannot read properties of null (reading 'If')`.

- Always import node-system classes (`RenderPipeline`, `PMREMGenerator`) from **`'three/webgpu'`**.
- Check `three/package.json` exports before assuming a subpath resolves (`./src/*` IS exported, which makes the mistake easy).
- If @types/three lacks the export, extend your local structural stub instead of deep-importing.
- The common/node `PMREMGenerator` (three/webgpu) accepts any Renderer; the classic `'three'` build's PMREMGenerator only drives WebGLRenderer.

## Post-processing composition

- `bloom(node)` output **replaces** its input — a pipeline whose outputNode is just the bloom texture renders pure black. Compose additively per official pattern: `sceneColor.add(bloomPass)`.
- Build effects one at a time with FPS measurement. Real costs seen: full-res GTAO cost ~35% FPS; `resolutionScale = 0.5` recovered it with no visible loss at gameplay zoom.
- TRAA: rejected for ghosting on moving vehicles/foliage; SMAA is the safe AA fallback.
- Wrap each stage attach in try/catch and retry down a stage ladder (full → drop AO → drop bloom → bare pass). Never let a failing effect kill the render loop.
- Beware adapter limits: fragment-stage sampled textures/samplers default to 16 and often cannot be raised (`adapter.limits.maxSamplersPerShaderStage` may BE 16). Adding scene.environment (IBL) adds ~1 sampler to every PBR material — audit which material sits closest to the ceiling before enabling IBL. Background-only PMREM is the zero-sampler-cost alternative.
- `PostProcessing` is deprecated since r183 → use `RenderPipeline`.
- SkyMesh PMREM bakes much darker than the live skydome renders — lift the sun position for the bake (proportionally, preserving preset differences; a hard floor makes all low-sun presets identical) and/or raise `scene.backgroundIntensity`.

## Grammar/authoring placement (Z-up pre-tilt)

Procedural building grammars authored Z-up then tilted at the root have axis traps:
- `localM(x, y, z)` maps cell-grid coordinates onto Y (across-width horizontal) and z onto HEIGHT. Swapping them places parts floating or buried.
- Slope placement (dormers on gables): measure depth from the RIDGE line, not from a part origin; height = ridge − pitch·depth. A dormer buried 95% below the slope plane reads as "nothing placed".
- Verify placements by reading instanceMatrix array elements [12],[13],[14] of the InstancedMesh in a live page probe, not by trusting placement math.

## Merged geometry material groups

`merged(parts)` without `useGroups=true` paints ALL sub-geometry with one material. Thin detail parts (support arms, braces) become invisible when they share the fabric/wall color. Fix: `merged(parts, true)` + return a material ARRAY from the registry case, and remember the registry must supply an entry for EVERY group index added.

## Node harness vs browser canvas

Canvas-baked textures using `document.createElement('canvas')` crash tsx smoke tests (`document is not defined`). Fallback chain: browser `<canvas>` → optional `canvas` npm package via require → stub canvas with null ctx (skip painting; geometry-only harnesses still pass).

## Vision-QC loop guardrail

Vision models fail on small details at full-frame zoom: they hallucinate missing parts that are actually sub-pixel, and misread downscaled JPEG crops. Before iterating geometry fixes off a vision verdict: capture a native-resolution crop of the exact region, and cross-check claims against live instance counts (`instanceMatrix.array`) — one model claimed "no dormers" while the scene had 2 dormer instances correctly placed. Cap tuning loops at ~3 rounds of the same critique; hand the tiebreaker to the user's eyes.