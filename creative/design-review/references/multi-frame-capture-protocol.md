# Multi-Frame Capture Protocol for Animation Audits

When auditing 3D scenes, motion graphics, or any artifact whose state changes meaningfully over time, a single screenshot is structurally incomplete. You can't audit motion, transitions, state-machine outputs, or behavior that only manifests at specific cycle points. This reference gives the protocol + a Playwright script template.

## Why one screenshot is not enough

A 3D scene with a state machine typically has 4-6 distinct visual states:
1. **Pre-animation / resting state** — baseline
2. **Trigger event just past** — entry into the new state
3. **Mid-cycle** — peak activity, all elements visible at once
4. **Late-cycle / crowding** — completion behavior, overlap handling
5. **Right before reset** — the "look at all of this" moment

A screenshot at t=3s on a 16s loop has a ~1-in-5 chance of catching each state. You'll miss most of them and audit based on the transition between two of them.

## Capture protocol

5-8 frames at deliberate cycle points. Choose times that map to known state transitions, not arbitrary intervals. For a 16-second loop with these known states:
- t=1.5s → just past loop start, before trigger
- t=4.0s → trigger event just past, entry into new state
- t=7.0s → mid-cycle, peak activity
- t=11.0s → late cycle, crowding
- t=14.0s → near complete
- t=17.0s → right before / during reset

Adjust the number of frames based on the artifact's complexity. A linear animation needs 3; a state machine with N branches needs roughly 2×N.

## Script template (Python Playwright)

```python
"""Capture N frames at deliberate cycle points for an animation audit."""
import sys
from playwright.sync_api import sync_playwright

HTML_PATH = '/absolute/path/to/file.html'

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1400, 'height': 900})
    page = context.new_page()

    # Capture page errors so a JS bug doesn't silently invalidate the audit
    errors = []
    page.on('pageerror', lambda err: errors.append(f'[pageerror] {err.message}'))
    page.on('console', lambda msg: errors.append(f'[{msg.type}] {msg.text}')
            if msg.type == 'error' else None)

    page.goto(f'file://{HTML_PATH}', wait_until='load', timeout=15000)

    # Edit the frame list to match your artifact's cycle points
    frames = [
        (1.5,  'frame-01-baseline.png'),
        (4.0,  'frame-02-trigger.png'),
        (7.0,  'frame-03-mid-cycle.png'),
        (11.0, 'frame-04-late-cycle.png'),
        (14.0, 'frame-05-near-complete.png'),
        (17.0, 'frame-06-reset.png'),
    ]

    for target_s, fname in frames:
        elapsed = page.evaluate('performance.now() / 1000')
        wait_ms = max(100, int((target_s - elapsed) * 1000))
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=f'/tmp/{fname}', full_page=False)
        print(f'captured {fname} at ~{target_s}s')

    if errors:
        print('=== ERRORS ===')
        for e in errors:
            print(e)
    else:
        print('no page errors')

    browser.close()
```

Two details that matter:

- **Compute wait time against `performance.now()`** rather than sleeping for the full target duration. This way if a frame took longer than expected (slow page load, GC pause), the next capture adjusts. Otherwise frames drift.
- **Always listen for `pageerror`.** A 3D scene with a state machine is exactly the kind of code that has a runtime `ReferenceError` lurking in a frame transform (see the "dt is not defined" class of bug). If you don't catch it, the rAF loop dies silently and you screenshot a black canvas thinking the design is broken when actually the code is broken.

## What to look for in each frame

For each captured frame, ask:
- **Are all expected elements visible?** (helicase, polymerases, new strands, etc.) Missing elements → code bug.
- **Are colors and labels readable?** Color collision is the #1 visual hierarchy failure mode.
- **Is depth/perspective working?** (e.g., are the two strands at the right distance, are polymerases oriented along the strand tangent?) If not → quaternion or anchor math bug.
- **Any clipping or overlap?** Things inside other things where they shouldn't be, or 3D objects poking through 2D HUD elements.
- **Does the visual *story* match the *labels*?** If the legend says "Okazaki fragments" but you can't actually see distinct fragments, the design is failing to teach what it claims to teach.

## Pair with the audit dimensions

For each frame, score the 5 dimensions:
- **Philosophy Alignment** — does the frame feel like part of a coherent visual language, or is it mixing 3 unrelated styles?
- **Visual Hierarchy** — what does your eye land on first? Is that what should be the focal point?
- **Craft Quality** — alignment, spacing, color system consistency. Easy to score from a still.
- **Functionality** — the frame shows state X; is state X actually being depicted correctly? (Requires knowing the state machine.)
- **Innovation** — does the design bring something to the table that a textbook diagram doesn't?

A single-frame audit is biased toward the *visible* dimensions (philosophy, hierarchy, craft). Multi-frame audit catches *functionality* bugs (state machine outputs) and *innovation* gaps (signature moments that only appear in motion).

## Interactivity test (separate pass)

Beyond the cycle captures, run an interactivity test to verify pause/play/explode/reset still works AFTER your audit-identified bugs are fixed:

```python
errors = []
page.on('pageerror', lambda err: errors.append(f'[pageerror] {err.message}'))

page.goto(...)
page.wait_for_timeout(2000)
page.keyboard.press('Space')  # pause
page.wait_for_timeout(500)
page.screenshot(path='/tmp/test-paused.png')
page.keyboard.press('KeyE')   # explode
page.wait_for_timeout(500)
page.screenshot(path='/tmp/test-exploded.png')

# Resume + recombine
page.keyboard.press('Space')
page.keyboard.press('KeyE')
page.wait_for_timeout(500)

print('errors:', errors if errors else '(none)')
```

If the interactivity test produces pageerror events your cycle captures missed, you have a bug that only manifests when a specific state is entered via keypress (e.g., a `dt` recompute that breaks when the animation loop has been running for a while).

## Cropping for vision analysis

For vision_analyze to read tiny in-scene text, crop the relevant region first:

```python
import subprocess
subprocess.run(['sips', '-c', '200', '300',  # height, width in pixels
                '/tmp/full.png', '--out', '/tmp/crop.png'], check=True)
```

Vision's OCR is unreliable on tiny 3D-scene text. Cropping brings the pixels-per-character ratio up to something readable. If the text is still unclear, **scale the label 2-3× larger** in the source code rather than trying to compensate with better prompts.

## Anti-pattern: trusting one screenshot

If your audit only has one frame in the evidence section, it doesn't matter how many times you ran `vision_analyze` on it — you've audited one moment, not the artifact. A design review that says "I see a yellow helicase and two purple polymerases" based on a single t=3s screenshot is structurally less rigorous than the same review based on 6 frames at deliberate cycle points, even if the single frame happens to be a "good" moment.
