# browser automation harness vs Playwright — screenshot capture discrepancy

From the mahjong VTT a renderer build renderer build, 2026-08-17.

## The problem

`your browser tool` + `your screenshot tool` from the browser automation CLI can return
**all-black screenshots** of a WebGL/R3F canvas even when the scene is rendering
correctly. The screenshot file exists, has the right dimensions, but every pixel
reads as the background color (~[16, 18, 15] in the PNG).

This is NOT a scene bug — it's a compositing/timing issue in the browser automation
harness's screenshot path. The WebGL canvas composites asynchronously and the
harness may capture before the compositor finishes, or the harness's screenshot
method doesn't properly capture WebGL canvas content.

## Diagnosis

When `your screenshot tool` returns a plausible file path but pixel analysis
shows uniform near-black across the ENTIRE frame (not just dark regions):

1. **Check the WebGL context directly** — `gl.readPixels` at center returns
   [0,0,0,0] (cleared buffer, not preserved). This confirms the harness can't
   see the rendered frame.
2. **Cross-check with Playwright** — `npx playwright screenshot --browser chromium
   --viewport-size 1280,720 --wait-for-timeout 6000 'http://localhost:PORT/'
   /tmp/shot.png` captures the scene correctly (felt [117, 110, 74] vs harness
   [16, 18, 15]).

## The fix

**Use `npx playwright screenshot` for all WebGL/R3F visual verification.** The
browser automation harness (`your browser tool` / `your screenshot tool`) is fine for DOM
inspection and interaction, but unreliable for WebGL canvas screenshots.

### Playwright screenshot + pixel analysis recipe

```bash
# 1. Capture (one command, no script needed)
npx playwright screenshot --browser chromium \
  --viewport-size 1280,720 \
  --wait-for-timeout 6000 \
  'http://localhost:4174/?shot=1' /tmp/scene.png

# 2. Pixel analysis (Python + Pillow)
python3 -c "
from PIL import Image
img = Image.open('/tmp/scene.png')
w, h = img.size

def reg(img, cx, cy, rw, rh):
    r = img.crop((max(0,cx-rw//2), max(0,cy-rh//2), min(w,cx+rw//2), min(h,cy+rh//2)))
    p = list(r.getdata())
    n = len(p)
    R = sum(x[0] for x in p)//n; G = sum(x[1] for x in p)//n; B = sum(x[2] for x in p)//n
    return f'RGB=({R},{G},{B}) lum={int(0.299*R+0.587*G+0.114*B)}'

print(f'felt:   {reg(img, w//2, int(h*0.55), 300, 200)}')
print(f'overall:{reg(img, w//2, h//2, int(w*0.7), int(h*0.7))}')
"
```

### When the browser automation harness IS useful

- DOM inspection (`js('document.title')`, element text, AX tree)
- Clicking and typing in interactive pages
- Console error collection
- Network request monitoring
- Anything that doesn't need to capture the rendered WebGL frame

### Additional gotcha: `preserveDrawingBuffer`

R3F's `<Canvas>` does not set `preserveDrawingBuffer: true` by default. Even
with Playwright, if you try to `gl.readPixels` from within the page JS after
the render loop, you'll get [0,0,0,0] because the buffer was already cleared.
For in-page pixel sampling, add `preserveDrawingBuffer: true` to the Canvas
`gl` prop. But for Playwright's external screenshot, this is NOT needed —
Playwright captures the composited page, not the GL buffer directly.

## Related

- `references/subagent-visual-review-loop.md` — parent-judged visual review
  loop for subagent-built scenes (subagents can't vision-review their output)