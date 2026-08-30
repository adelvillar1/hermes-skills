# beUI Motion Recipes (implementation tokens)

Source: github.com/starc007/ui-components (beUI, beui.dev) — 123 motion components + ~20 agent-interface components + blocks, shadcn-registry format. MIT. Author: Saurabh Chauhan (@saurra3h). Active repo (last commit 2026-08-07).

Distilled 2026-08-08 into `design-motion-principles`. The distinct contribution: a shared, purpose-named motion token system (`lib/ease.ts`) reused across every component, plus component-typed recipes. Contrast react-bits (effect vocabulary) and motion.dev (personality tokens) — beUI is the "purpose → value" implementation layer.

## The token system (lib/ease.ts, verbatim values)

Purpose-named springs — pick by purpose, never invent a spring:

| Token | Value | Use |
|---|---|---|
| `EASE_OUT` | `[0.16, 1, 0.3, 1]` | default decelerate (CSS: `cubic-bezier(0.16, 1, 0.3, 1)`) |
| `EASE_IN_OUT` | `[0.77, 0, 0.175, 1]` | cross-fades |
| `EASE_DRAWER` | `[0.32, 0.72, 0, 1]` | sheets/drawers |
| `EASE_OUT_CSS` | `"cubic-bezier(0.16, 1, 0.3, 1)"` | inline-style transitions |
| `SPRING_PRESS` | `{stiffness 500, damping 30, mass 0.6}` | press feedback on tappable surfaces |
| `SPRING_SWAP` | `{stiffness 460, damping 30, mass 0.55}` | content swaps — label/icon slots trading places |
| `SPRING_PANEL` | `{stiffness 420, damping 40, mass 0.5}` | overlay panel entrances (modals/sheets summoned by pointer) |
| `SPRING_LAYOUT` | `{stiffness 360, damping 32, mass 0.6}` | shared-layout glides — pills, indicators, panels morphing between positions |
| `SPRING_MOUSE` | `{stiffness 200, damping 15, mass 0.3}` | cursor-follow physics — magnetic, tilt, dock |
| `SPRING_GLIDE` | `{stiffness 700, damping 50, mass 0.5}` | dragged handles/fills — critically damped so the value "follows the pointer butterily and never rebounds off an end" |

Masses < 1 + high damping = snappy, non-bouncy; springs are purpose-named so components reuse tokens instead of inventing physics.

## Component-typed recipes

- **Weighty layout-indicator spring (tabs):** `{stiffness 170, damping 24, mass 1.2}` — deliberately "weighty... a touch of overshoot" for the active-tab `layoutId` indicator. Contrast `SPRING_LAYOUT` (360/32/0.6) for lighter glides.
- **Blur-swap slots (action-swap):** label/icon swap via filter blur, not layout. `SWAP_BLUR = blur(8px)` for text/icon slots; `ROLL_BLUR = blur(3px)` for the roll variant; `BLUR_TRANSITION = {duration 0.2, ease easeInOut}`; roll exit `{0.14s, EASE_OUT}`; width morphs at `220ms EASE_OUT_CSS`; stagger = index × 0.5 (exit) / index × 1 (enter).
- **Drawer/bottom-sheet as tween, not spring:** "a long, fully-damped tween reads smoother than a spring on release" — `DRAWER = {duration 0.5, ease EASE_DRAWER}`. `dragElastic` asymmetric `{top 0.02, bottom 0.4}` (resists upward overscroll, rubber-bands downward), `dragMomentum false`, snap points default `[0.5, 0.92]`; strong downward fling → dismiss, −80px offset past current snap → next snap.
- **Blur enter/exit (tooltips/popovers):** spring spawn + blur on the surface, crisp content fades in on top (see gooey popover: SVG goo filter creates a liquid neck; content stays sharp).

## Catalog of patterns worth knowing by name

gooey popover (SVG goo filter liquid neck), morphing modal (panel height morphs between inner views with blur cross-fade), center-morph modal (surface unfolds from its exact center), dynamic island (bouncy shell resize + blur crossfades), cylinder carousel, wheel picker (iOS 3D drum on native momentum), bloom menu (iris-out from center with radially staggered items), morphing tabs (selected item grows into the content surface), expandable tabs, theme-toggle via View Transition API clip-path reveal (rect/circle/slats), shader backgrounds (mesh gradient, grain, warp, waves, voronoi, dot orbit), 17-variant loader, virtualized 10k-row table, bouncy accordion (weighted spring layout), pull-to-refresh (drag resistance, threshold feedback), OTP input (rolling digits, error shake, check draw), notification stack (springs from stacked summary into readable list).

## Agent-readable endpoints (consume without scraping)

beUI ships the whole library in agent-friendly form — reuse these when a build needs real components:

- Index (LLM list): `https://beui.dev/llms.txt` · JSON index: `https://beui.dev/r`
- Detail JSON (files, deps, source): `https://beui.dev/r/{slug}.json`
- Raw source: `https://beui.dev/r/{slug}/raw`
- Component markdown (LLM-facing spec): `https://beui.dev/components/{category}/{slug}.md`
- Install: `npx shadcn@latest add @beui/{slug}`

## License

MIT — free to copy/adapt (attribution per MIT terms). Contrast react-bits' MIT + Commons Clause.
