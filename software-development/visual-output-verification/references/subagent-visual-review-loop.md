# Subagent vision-blindness — parent-judged visual review loop

From the mahjong VTT "a renderer build" renderer build, 2026-08-17.

## The constraint

subagent dispatch subagents cannot vision-review their own renders — the auxiliary
vision model rejects image payloads (confirmed by a subagent's own report). A
subagent building a 3D scene, atlas, or UI can verify structure (build green,
files on disk, pixel stats) but cannot judge whether it *looks* right.

## The working split

1. **Parent owns visual judgment.** Take screenshots (your browser tool /
   capture_screenshot), inspect with native vision, compare against a committed
   concept render. Generate 1–2 target-look concept images BEFORE dispatching
   build work and commit them under `docs/design/<slug>/` — they become the
   acceptance reference for every later art pass.
2. **Subagent self-verifies numerically.** Give explicit measurable acceptance
   targets it CAN check without eyes:
   - region mean luminance ranges (e.g. felt center 90–150, rim ≥ 35, frame 25–60)
   - clipping caps (<3% of felt pixels above 240 = no blown hotspot)
   - dominant-channel hue checks (G > R,B on felt mean color = reads green)
   verified via Playwright screenshot + a small pixel-sampling script.
3. **Clean-frame mode in the app** (`?shot=1` hides overlays) so beauty shots are
   deterministic.

## Iteration discipline

- First renders are always rough — budget at least one repair round-trip per
  visual phase. (P3 room failed its first review on 4 of 5 art axes: glossy
  quilted-looking felt, void-dark exposure, unreadable rim, invisible lamp prop.)
- When sending a subagent a repair pass, describe failures in MATERIAL terms with
  concrete knob directions, not adjectives. Good: "felt reads as glossy quilted
  glass — increase texture repeat to 6–8, force roughness floor ~0.9, cut
  envMapIntensity to 0.1, tint toward deep emerald". Bad: "make it look softer".
- Numeric gates catch gross failures, not taste. The parent re-shoots and judges
  after every subagent visual task.

## Adjacent lesson: SVG atlas cell bleed

Hand-authored SVG texture atlases: any cell art that draws outside its cell rect
(e.g. diagonal lattice lines spanning negative coordinates) bleeds into
neighboring cells unless wrapped in a per-cell `<clipPath>`. Found as red hatch
lines over a joker face — source was the *adjacent* back-cell's lattice.
