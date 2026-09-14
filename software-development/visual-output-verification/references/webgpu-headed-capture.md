# WebGPU / heavy-3D evidence capture — headed, focused, parity-measured

Playbook from the simcityclone spline-world pivot (2026-08-20). Applies to Three.js
WebGPURenderer scenes, TSL node materials, or any GPU-heavy canvas where headless
defaults break down. Symptoms look like app bugs; they are capture-harness artifacts.

## Symptom → cause → fix

| Symptom | Cause | Fix |
|---|---|---|
| Screenshots show stale/empty scene although app state proves the content exists (e.g. `getStats()` says roadCount 1 but the PNG shows no road) | Headless Chromium renders WebGPU via SwiftShader at ~1 FPS; Playwright's frame-stability wait starves | Run HEADED (`chromium.launch({ headless: false })`) on the host's real GPU. Never use headless for WebGPU evidence |
| Headed screenshots still byte-identical across actions (same MD5), or FPS reads ~39-42 when the app should vsync at 60 | macOS/Chrome throttle rAF in unfocused or occluded windows | Focus the window before capture: `await page.bringToFront()` AND activate the app bundle — get it via `chromium.executablePath().replace(/^(.*\.app).*$/, '$1')` then `open -a <bundle>` |
| `osascript … set frontmost of (first process whose name contains "Chromium")` fails with `-1719 Invalid index` | Playwright's macOS browser process is named "Google Chrome for Testing", not "Chromium" | Match "Chrome", or skip System Events and use `open -a` on the bundle path (works, no accessibility permission prompt) |

## Measuring FPS honestly (parity harness)

Raw FPS numbers from a scripted browser are meaningless without calibration. The
harness that produced trustworthy numbers:

1. **Blank-page control** in the same window: `about:blank` rAF count should hit ~59-60
   focused (vsync). If the control is low, the environment is throttling — fix focus
   before trusting any app number.
2. **Warmup**: ≥8 s after boot before sampling — texture streaming and shader
   compilation depress cold readings (26.7 cold vs 42.3 warm for the same scene).
3. **Reference parity**: measure the upstream/reference build with the IDENTICAL
   harness and warmup. "Ours 42.3 vs upstream 44.7" is a verdict (parity, no shell
   regression); "ours is 42" is not.
4. Sample: 3 s rAF counter via `page.evaluate`, report `frames / 3`.

## Verify the capture, not just the app

- **MD5 consecutive stills** that should differ (`md5 out/*.png`). Byte-identical =
  throttled capture, not a frozen app.
- Distinguish before blaming app code: check app state directly (`window.__world.getStats()`)
  and check `document.visibilityState` — a `visible` page with low FPS is real; a
  throttled one is the harness.

## Supporting habits

- Playwright scripts must run from inside the project dir (module resolution); keep
  throwaway probes as `scripts/e2e/*.tmp.mjs` (gitignored) and delete after use.
- Wrap capture scripts in try/finally around `browser.close()` — a failed selector
  otherwise orphans a headed Chromium.
- Add a content assertion (`roadCount > 0`, exit non-zero) so evidence scripts catch
  silent regressions instead of just producing pictures.
- Cold dev-server first loads can 404 on assets mid-transform; re-run warm before
  reporting missing assets.
