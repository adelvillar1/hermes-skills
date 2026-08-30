# Vision-QC loop and capture-script pitfalls

Condensed from a long era-variant iteration campaign (2026-08). These complement the SKILL.md guardrails with the session-specific detail.

## Vision-QC loop

- Vision models fail on small details at full-frame zoom: they hallucinate missing parts that are actually sub-pixel, and misread downscaled JPEG crops. Before iterating geometry off a vision verdict: capture a native-resolution crop of the exact region, and cross-check claims against live instance counts (`instanceMatrix.array` elements [12],[13],[14] per InstancedMesh) — one model claimed "no dormers" while the scene had 2 dormer instances correctly placed.
- Cross-model disagreement is diagnostic: when models contradict each other (or themselves between rounds on identical frames), trust whichever claim matches live scene data. Treat per-item claims as hypotheses, never verdicts.
- Downscale before upload (sips → JPEG ≤500KB) to dodge provider payload limits (raw 2–3MB PNGs get dropped mid-upload with BrokenPipeError), but re-verify any "not visible" verdict against a native-res crop of the exact region before acting — downscaling destroys exactly the sub-detail the review targets.
- Cap tuning loops at ~3 rounds of the same critique; hand the tiebreaker to the user's eyes. Vision models also flip verdicts between rounds on identical frames — a PASS then FAIL on unchanged geometry means the model, not the code.
- Provider endpoints used successfully: Ollama Cloud (`https://ollama.com/v1`, model gemma4:31b) and Kimi For Coding (`https://api.kimi.com/coding/v1`, model kimi-k2.6 — key prefix `sk-kimi-` routes there, NOT api.moonshot.ai which 401s). Kimi proved markedly more reliable on architectural detail claims. Expect HTTP 429 bursts; back off 45–120s and retry.
- Multi-image single-request review works (base64 JPEG array) but models often lose count of images; per-image requests give cleaner per-item verdicts, one combined request gives better comparative verdicts. Choose based on whether you need item-by-item or progression judgments.

## Capture script pitfalls (Playwright)

- Values used inside `page.evaluate` callbacks must be passed via the arg array (`evaluate(fn, [a,b])`) — closures over outer `const` objects throw `ReferenceError` inside the browser context.
- Spawn-scan loops (probe dry land cell-by-cell) pick different coordinates each run; if a review model reports buildings "missing" or "swapped", verify spawn positions didn't move before assuming a geometry regression.
- `page.evaluate(async () => { const THREE = await import('three') })` fails ("Failed to resolve module specifier") — the page context resolves specifiers differently. Read instance matrices via the raw `instanceMatrix.array` instead of constructing Matrix4 helpers in-page.

## Orphaned capture processes tank FPS

Playwright Chromium processes from timed-out/killed capture scripts accumulate silently and drag measured FPS from 60 → 7. If an FPS gate suddenly fails after previously passing: `pkill -f ms-playwright` then re-measure before touching any rendering code. Also check `mediaanalysisd` (macOS photo-analysis daemon) — it spikes CPU for minutes and resolves itself; wait rather than debug.

## Era-variant grammar lessons (procedural buildings)

- The grammar frame is Z-UP before root tilt: `localM(x, y, z)` maps cell.z → Y (across-width) and its z arg → HEIGHT. Slope placement (dormers): measure depth from the RIDGE line, height = ridge − pitch·depth. A dormer buried 95% below the slope reads as "nothing placed".
- Merged geometry without material groups paints all sub-parts one color — thin detail parts (arms, braces) become invisible when they match the host surface color. Use `merged(parts, true)` + a material ARRAY in the registry case for every group index.
- Era-gating props (AC units etc.) works cleanly as slot repurposing: keep the placement key, swap the builder + registry materials to era-appropriate content (flower boxes/shutters replaced AC units).
