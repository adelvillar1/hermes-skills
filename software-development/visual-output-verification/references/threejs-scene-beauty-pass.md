# Three.js scene beauty pass — why procedural cities read as programmer art

From simcityclone (2026-08-25): after a full pivot to a vendored spline world
(terrain, rivers, bridges) plus a hand-crafted procedural building library,
stills still disappointed. Diagnosis pattern that generalizes:

## The fault is almost never geometry

Geometry craft (cornices, quoins, parapets) does not save a scene lit like a
tech demo. When a user says "the visual layer falls short," audit these layers
in order — each is cheaper than rebuilding assets:

1. **Lighting** — default directional sun + standard materials = flat noon look.
   Fix: ACES tone mapping (`renderer.toneMapping = ACESFilmicToneMapping`),
   tuned exposure, warm/cool key-vs-sky balance, soft shadow tuning
   (map size, radius/bias).
2. **Materials** — flat color palettes read as unlit even on MeshStandardMaterial.
   Add roughness/metalness discipline and subtle procedural noise/detail maps
   (canvas-generated keeps a no-GLB-assets rule). Crevice darkening / SSAO if perf allows.
3. **Atmosphere** — distance fog matched to palette, real sky (gradient or
   three/examples Sky), bloom on emissives, subtle vignette/grade.
   "Emissive windows at noon" looks weak; emission must ramp against darkness.
4. **Density & composition** — sparse showcase buildings on an empty world read
   as a demo. Cities wow when dense and cluttered along streets.
5. Only then: more geometry/detail work.

## Reference-driven gate

Pick 2–3 reference images (e.g. Townscaper, Workers & Resources, an ArtStation
render) BEFORE iterating. Acceptance = "recognizably in that family," not
"looks okay." Vague quality bars produce endless unsatisfying rounds.

## Ordering rule

Do the beauty pass BEFORE building sim features on top: pure sim logic is
invisible, but every screenshot taken during later phases compounds either
excitement or disappointment. Also: run code-quality reviews AFTER the visual
wow-gate iteration settles — review churn on visuals you're about to change is waste.
