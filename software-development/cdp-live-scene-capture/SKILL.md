---
name: cdp-live-scene-capture
description: Capture WebGL frames via Chrome CDP without Playwright.
---

# CDP Live-Scene Capture

Drive a real Chrome tab over the Chrome DevTools Protocol to capture frames **or in-page MediaRecorder videos** from a live WebGL/three.js scene when Playwright is not installed. Still frames: scene opts in via a query param (e.g. `?og=1`) and publishes a PNG data URL on `window`. Demo videos: page records `canvas.captureStream` and publishes `window.__dfDemoVideo` as a data URL; the capture script chunk-extracts it to WebM then ffmpeg to MP4.

## When to Use

- Generating an og:image / social card from the real rendered scene (never an SVG/CSS mockup).
- Recording the D&D VTT project cast demos (board/terrain + minis + spells) via `scripts/capture-demo-video.mjs`.
- Any live-browser capture where `your browser tool`/Playwright is unavailable (no `node_modules/.bin/playwright`).
- Re-shooting a hero/landing capture after a scene change (committed script: `scripts/df-hero-og-capture.mjs`).

## Prerequisites

- Dev server running: `npm run dev -- --port 5199 --strictPort` (via `terminal`, background).
- Chrome with a debug port: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir=/tmp/df-chrome-profile` (background).
- `ws` package available (monorepo root has it — the script does `import WebSocket from "ws"`).
- The scene must opt in: `createDemoScene(mount, { capture: { onReady } })` wired from the page, gated on the `?og=1` query param, publishing `window.__dfHeroOg = <4K data URL>` after all assets load.

## How to Run

1. Start the dev server + Chrome CDP (see ## Prerequisites).
2. Still: invoke `node scripts/df-hero-og-capture.mjs` through the `terminal` tool.
3. Demo video: invoke `node scripts/capture-demo-video.mjs <board|terrain> <out.webm>` through the `terminal` tool, then ffmpeg to MP4.

## Quick Reference

```bash
# CDP endpoint is up
curl http://localhost:9222/json/version
# Open a tab pointed at the capture page (PUT, not GET)
curl -X PUT "http://localhost:9222/json/new?http://localhost:5199/?og=1"
# Still-frame og capture
node scripts/df-hero-og-capture.mjs
# Cast-demo video (MediaRecorder on canvas.captureStream)
node scripts/capture-demo-video.mjs terrain /tmp/df-demo/terrain.webm
ffmpeg -y -i /tmp/df-demo/terrain.webm -c:v libx264 -crf 18 -pix_fmt yuv420p docs/demo-outputs/demo-terrain-cast.mp4
# Optional: cheaper ice/VFX during demo — page defaults vfxQuality=low; force full with &vfxQuality=high
```

## Procedure

### A — og:image still

1. Start the dev server and Chrome with CDP (both via `terminal` background). Verify: `curl http://localhost:5199/` → 200, `curl http://localhost:9222/json/version` → Chrome version.
2. Run `node scripts/df-hero-og-capture.mjs` (via `terminal`). It opens the capture URL, polls for `window.__dfHeroOg` (up to 60s), downscales to 1200×630 in-page via canvas, then chunk-extracts both data URLs to `/tmp/df-og/hero-og-4k.png` and `/tmp/df-og/og-image-1200.png`.
3. QC the result: open the 4K frame for the user, verify dims with `sips -g pixelWidth -g pixelHeight /tmp/df-og/og-image-1200.png` → 1200×630.
4. Install: `cp /tmp/df-og/og-image-1200.png <public-dir>/og-image.png`, commit.
5. Clean up: kill the dev server and Chrome background processes (`process` tool) if you started them only for this job.

### B — cast-demo WebM → MP4 (board / terrain)

1. Same Vite `:5199` + Chrome CDP `:9222` prerequisites.
2. Page: `demo-cast.html?mode=board|terrain&record=1` — records ~15s via MediaRecorder, sets `window.__dfDemoVideo` (data URL).
3. Run `node scripts/capture-demo-video.mjs <mode> <out.webm>` via `terminal`. Polls until `__dfDemoVideo` length > 1000, chunk-extracts to WebM.
4. Convert: `ffmpeg -y -i <out.webm> -c:v libx264 -crf 18 -pix_fmt yuv420p docs/demo-outputs/demo-<mode>-cast.mp4`.
5. QC: extract frames with ffmpeg (`-ss` at spell times: fire ~1.8s, lightning ~5.0s, ice ~8.7s, beam ~12.3s) and inspect with `your vision tool`.
6. **Readiness gates in the page:** do not start recording until minis **and** (terrain mode) `terrainReady` **and** `propsReady` — otherwise obstacles/minis pop in mid-clip.

## Pitfalls

- **CDP `Runtime.evaluate` return values are size-limited.** Multi-MB video data URLs must be extracted in chunks — a single evaluate of the whole data URL can silently fail.
- **`awaitPromise: true` + `returnByValue: true`** are required on every evaluate that returns a promise or object; without them you get `exceptionDetails` or undefined.
- **The capture must be opt-in in the scene.** Gate on a query param and fire once after the last async asset lands.
- **`your browser tool` fails without a Chrome debug port.** Check `curl localhost:9222/json/version` first.
- **Downscale stills in-page, not server-side.** The script's `drawImage` path is the proven one for og:image.
- **Keep a 4K source** for future re-shoots so minor crops never require re-running the capture.
- If `CAPTURE NEVER FIRED`, read the scene's capture block with `read_file` (locate via `search_files` for `__dfDemoVideo` or `__dfHeroOg`) to confirm readiness (`minisLoaded`, `terrainReady`, `propsReady`).
- **Framing looks “cornered” but camera math is fine:** check `renderer.setSize(w,h,false)` + retina DPR — see skill `threejs-retina-setsize-framing`. Always `setSize(w, h, true)` for full-bleed demos.
- **Expensive spells (ice) stall recording:** demo defaults to low VFX detail; pass `vfxQuality=high` only when you need full spikes. Geometry counts must scale with quality, not only particle buffers.

## Verification

- Run `skill loader (name="cdp-live-scene-capture")` to reload the full procedure.
- Still: `sips -g pixelWidth -g pixelHeight /tmp/df-og/og-image-1200.png` → `1200 x 630`.
- Video: `docs/demo-outputs/demo-terrain-cast.mp4` exists and QC frames show terrain + minis + at least one spell.
- The scene still runs normally WITHOUT the query param (no capture fires in a plain session).
