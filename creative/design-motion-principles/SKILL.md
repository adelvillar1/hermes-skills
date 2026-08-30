---
name: design-motion-principles
description: "Create or audit purposeful motion and interaction design."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Motion, Animation, UI, Audit]
    related_skills: [design-engineering, impeccable, anti-ai-slop]
---

# Design Motion Principles

Build and audit motion through three designer lenses: Emil Kowalski (restraint), Jakub Krehel (subtle polish), and Jhey Tompkins (playful CSS innovation). Two modes: **Create** (build purposeful animations) and **Audit** (review motion and produce HTML reports with looping demos).

## When to Use

- Adding motion to a component, page, or flow.
- Reviewing existing animations for slop, excess, or missing purpose.
- Deciding which motion personality fits a product context.

## Three Lenses

- **Emil Kowalski:** restraint, speed, purpose. Best for productivity tools. Answers: *Should this animate at all?*
- **Jakub Krehel:** subtle production polish, professional refinement. Best for shipped consumer apps. Answers: *Is this subtle and polished enough?*
- **Jhey Tompkins:** playful experimentation, CSS innovation. Best for creative sites and kids apps. Answers: *What could this become?*

## Context Mapping

| Context | Primary Lens | Secondary Lens |
|---|---|---|
| Productivity tool | Emil | Jakub |
| Kids app | Jakub | Jhey |
| Creative portfolio | Jakub | Jhey |
| Marketing | Jakub | Jhey |
| SaaS dashboard | Emil | Jakub |
| Mobile app | Jakub | Emil |
| E-commerce | Jakub | Emil |

## The Frequency Gate

- Rare (monthly): delightful welcome animation.
- Occasional (daily): subtle, fast.
- Frequent (100s/day): no animation or instant.
- Keyboard-initiated: never animate.

## Duration

- Emil / productivity: under 300ms, 180ms ideal.
- Jakub / polish: 200-500ms.
- Jhey / creative: whatever serves the effect.

## Measured Motion Data (empirical calibration)

Measured from real 30fps clips of top-earning iOS apps; source: github.com/Appllama/top-welcome-screens (docs/MOTION_SPEC.md). When in doubt about timing, trust measured numbers over intuition.

| App | Measured behavior |
|---|---|
| Duolingo | 2.667s total. Mascot blink = ~167ms (0.400-0.567s). Splash face scales down; page expands through a circular mask. |
| Strava | 5.13s static logo + spinner, then hard cut — no transition. |
| MyFitnessPal | 8.87s loader; copy swaps "Updating..."→"Loading..." with NO dissolve; hard cut to carousel at 7.33s. |
| Yazio | 1.73s; five objects enter at ~66ms stagger (1167, 1233, 1300, 1367, 1467ms) with Easing.out(Easing.back(1.5)) and alternating rotation (+20, -13, +18, +24, -18deg). |
| Hallow | Background interpolates #9F3BE9 → #9240E0 over ~234ms; one scale pulse travels across loader dots. |
| Speak & Learn | Logo rotates/grows 0.1-0.97s; welcome page slides in from right with strong ease-out. |
| onX Hunt / SCRL | Static splash then hard cut; SCRL reveals bg/awards/copy/CTA with separate ease-out opacities. |
| Perplexity | NO entrance animation — reference set had only a still; renders final state immediately. |

**Rules these numbers teach:**

- **Never invent unsupported motion.** If the reference has no clip, render the final state — do not fabricate an entrance.
- **Hard cuts are legitimate premium motion.** Static splash → cut → content beats a forced transition (Strava, MFP, onX all cut).
- **Copy swaps need no dissolve** (MFP's "Updating..."→"Loading...").
- **Stagger rhythm recipe:** ~66ms between elements, Easing.out(Easing.back(1.5)), alternate rotation direction per element for an organic feel.
- **Micro-details:** a mascot blink is ~167ms; a background color shift is ~234ms.

## The Golden Rule

The best animation goes unnoticed. If users comment "nice animation!" on every interaction, it's too prominent.

## AI-Slop Motion Patterns to Flag

- Pulsing indicators (always flag).
- Blur-everywhere entrances (flag ≥3 identical blur entrances).
- Hover-scale-on-everything (flag ≥3 identical scales).
- Stagger-spam-on-every-list (flag ≥2 lists with stagger).
- Bouncy springs on utility actions (always flag bounce >0 on utilities).
- Uniform fade-in (flag ≥4 identical entrances).
- Motion-on-mount for static content (flag text/nav elements).

## Motion Cookbook

- **Enter:** opacity + translateY + blur.
- **Exit:** subtler than enter.
- **Custom easing:** essential, never defaults.
- **Spring:** `{ type: "spring", duration: 0.45, bounce: 0 }` for polish.
- **Stagger:** ~66ms per element, alternate rotation direction per element, `Easing.out(Easing.back(1.5))` for organic entrances.
- **Shadows over borders** in light mode.
- **oklch** for gradients.
- **clip-path** for reveals (inset, hardware-accelerated).
- **@property** for typed CSS variables.
- **layoutId** for shared element transitions.
- **Velocity-based dismissal:** threshold >0.11.
- **Damping** at boundaries.

## Web Motion Recipes (proven values)

Source: github.com/DavidHDev/react-bits (45k★, 165+ animated components, MIT + Commons Clause; also reactbits.dev). These are implementation-proven patterns for web (motion/GSAP), complementing the measured iOS data above. Full catalog + distilled code in `references/web-motion-recipes.md`.

- **Multi-step blur reveal** (the "expensive" entrance): blur(10px)→blur(5px)→blur(0px) with opacity 0→0.5→1 and y ±50→±5→0. Two intermediate steps, not one — the extra blur(5px)/opacity 0.5 frame is what reads as premium vs a generic fade. Per-element delay = index × ~200ms.
- **Trigger-once scroll animation:** IntersectionObserver with `observer.unobserve()` on first intersection — fires once, then stops observing (performance). `threshold: 0.1`, `rootMargin: '0px'`.
- **Scroll-driven in AND out (GSAP):** `ScrollTrigger.create({ once: true, onEnter })` for entrance; add a `disappearAfter`/`disappearDuration` tail to animate content back out (reverse, scale 0.8, opacity to initial) — the "content scrolls away" pattern.
- **Tilt card spring tuning:** `{ damping: 30, stiffness: 100, mass: 2 }` — heavy, smooth tilt; rotation = offset from center ÷ half-dimensions × amplitude (14° typical). Caption/counter-motion follows **pointer velocity** (`-velocityY * 0.6`) — follow-through sells the effect.
- **`willChange: 'transform, filter, opacity'`** on animated nodes — compositor hint, keeps blur/transform animations off the main thread.
- **Effect vocabulary (pick by mood):** text = BlurText, DecryptedText, SplitText, CountUp, CircularText, VariableProximity, TrueFocus, WarpText; cursor = BlobCursor, GhostCursor, SwarmCursor, TargetCursor, ClickSpark; background = Aurora, Beams, DotField, DotGrid, Threads, Topography, Waves, Ferrofluid, Dither; card = TiltedCard, SpotlightCard, BounceCards, Stack, BorderGlow. When a user says "make it memorable", pick from the catalog instead of inventing.
- **Tools worth knowing:** reactbits.dev Shape Magic (generate clip-path code for inner rounded corners between shapes — export as SVG/React/clip-path), Texture Lab (noise/dithering/ASCII textures), Background Studio (animated backgrounds exportable as video/image/code).

## Motion Design Tokens (production springs)

Source: motion.dev (the Motion library, formerly Framer Motion; MIT core) and its Motion UI theme (`motion.theme.ts`). These are the named, production-tuned spring values Motion's own design system ships with — use them as your default motion tokens instead of inventing springs. `defineTheme` object verbatim:

```ts
transitions: {
  snap:   { stiffness: 1218, damping: 70 },  // instant, utilitarian (menus, tiny reveals)
  ui:     { stiffness: 305,  damping: 33 },  // default: menus, cards, reveals
  gentle: { stiffness: 110,  damping: 20 },  // soft, slow
  lively: { stiffness: 622,  damping: 17 },  // playful, bouncy
  ambient:{ stiffness: 43,   damping: 13 },  // floating, background
},
stagger: { tight: 0.04, base: 0.08, relaxed: 0.15 },   // seconds between elements
travel:  { hover: 4, enter: 24, section: 48 },          // px of travel per context
reducedMotion: "calm",
```

**Rules from these tokens:**
- **Pick a spring by context:** `snap` for utility actions (matches the Frequency Gate — frequent = near-instant), `ui` for default component motion, `lively` for celebratory/fun, `ambient` for background ambience, `gentle` for slow reveals. Don't default everything to one spring.
- **Bounce is a named choice, not an accident:** `bounce: 0.25` is Motion's default; `0` = no bounce, `1` = extremely bouncy. `lively` (damping 17) is the sanctioned "playful" value — use it deliberately, flag it everywhere else (see AI-slop: bouncy springs on utility actions).
- **`visualDuration` beats `duration` for springs:** set the time (seconds) for the bulk of the motion to *visually* reach target; the "bouncy bit" happens after. Easier to coordinate with other timed animations than raw spring physics.
- **Stagger defaults: 0.04 tight / 0.08 base / 0.15 relaxed seconds.** Note: this is *seconds*, and tighter than the ~66ms Yazio measured — but Yazio's was per-object entrance with travel; these are for list/grid stagger. For grid reveals use `tight` (0.04s = 40ms), for hero copy use `relaxed`.
- **Travel defaults:** hover 4px, enter 24px, section 48px. Scale travel to context — don't slide a hover state 48px.
- **`reducedMotion: "calm"`** is a real config value — a whole "calm" variant of the motion tokens, not just a boolean flag. Design reduced-motion as a *slower gentler theme*, not an on/off switch.

## beUI Motion Tokens (purpose-named implementations)

Source: github.com/starc007/ui-components (beUI, beui.dev; 123 motion components + agent interfaces, MIT, shadcn-registry, active 2026-08). Where motion.dev gives personality tokens, beUI gives purpose-named implementation springs from `lib/ease.ts` reused across all components — pick by purpose, never invent a spring:

| Purpose | Token value |
|---|---|
| Press feedback (tappables) | `SPRING_PRESS` {500, 30, m0.6} |
| Content swaps (label/icon slots) | `SPRING_SWAP` {460, 30, m0.55} |
| Overlay panel entrances | `SPRING_PANEL` {420, 40, m0.5} |
| Shared-layout glides (pills/indicators) | `SPRING_LAYOUT` {360, 32, m0.6} |
| Cursor-follow (magnetic/tilt/dock) | `SPRING_MOUSE` {200, 15, m0.3} |
| Dragged handles/fills (critically damped) | `SPRING_GLIDE` {700, 50, m0.5} |
| Drawers/sheets (tween beats spring) | `EASE_DRAWER` [0.32, 0.72, 0, 1] @ 0.5s |
| Weighty layout indicator (slight overshoot) | {170, 24, m1.2} |
| Blur-swap slots (label/icon swap) | blur(8px) 0.2s easeInOut; roll blur(3px) 0.14s |

Key recipes: blur-swap slots animate `filter` not layout (SWAP blur 8px / 0.2s easeInOut, width at 220ms); bottom sheets use a fully-damped tween not a spring, asymmetric `dragElastic {top 0.02, bottom 0.4}`, fling dismiss; the whole catalog is agent-readable (`beui.dev/llms.txt`, `/r/{slug}/raw`, shadcn `@beui/{slug}`). Full values + pattern catalog: `references/beui-motion-recipes.md`. The agents-category (~20 AI-interface components) distilled separately into the `ai-interface-design` skill.

## MotionScore performance tiers (audit rubric)

Source: score.motion.dev (MotionScore) — audits any URL/CLI, grades every animation S–F, and flags the four failure classes: layout-triggering props, off-screen work, large paint surfaces, slow CSS variable inheritance. This is the objective performance half of any motion audit (the AI-slop list above is the taste half). When reviewing motion, grade each animation:

| Tier | Meaning | Action if violated |
|---|---|---|
| S | Compositor-only (transform/opacity) — never interrupted by main thread | The goal |
| A | Main thread but no paint | Fine |
| B | S/A-tier but needs style/layout measurements | Acceptable for size-dependent effects |
| C | Triggers paint (background-color, box-shadow, filter) | Flag; prefer transform/opacity |
| D | Triggers layout (width, height, top, left) | Flag hard; animate transforms instead |
| F | Per-frame style/layout thrashing (interleaved read/write) | 🔴 Bug — restructure |

**The four audited classes:** Animations (CSS/WAAPI/JS-driven; flag layout-triggering properties), Scroll animations (ScrollTimeline vs IntersectionObserver vs JS scroll handlers), Thrashing (interleaved DOM reads/writes during mount/frames), GPU pressure (compositor layer count, texture memory, overlap-promoted layers, persistent will-change declarations).

## Audit Mode Output

Produce an HTML report with looping CSS/JS demos of each flagged animation, severity, and recommended fix. Use `browser_navigate` and `browser_snapshot` to verify behavior in a live browser.

### Escalation triggers — flag these on sight (Emil review bar)

From emilkowalski/skills `review-animations`. These are automatic findings, not judgment calls:

- `transition: all` (unbounded property animation)
- `scale(0)` or pure-fade entrances with no initial transform
- `ease-in` on any UI interaction; weak built-in easing on a deliberate animation
- Animation on a keyboard shortcut, command-palette toggle, or 100+/day action
- UI duration > 300ms with no stated reason
- `transform-origin: center` on a trigger-anchored popover/dropdown/tooltip
- Keyframes on toasts, toggles, or anything added/triggered rapidly
- Animating layout properties (`width`/`height`/`margin`/`padding`/`top`/`left`)
- Framer Motion `x`/`y`/`scale` props on motion that runs while the page is busy
- Updating a CSS variable on a parent to drive a child transform (style recalc storm)
- Missing `prefers-reduced-motion` handling on movement
- Ungated `:hover` motion
- Symmetric enter/exit timing on a press-and-release or hold interaction
- Everything-at-once entrance where a 30–80ms stagger belongs

**Remedial preference hierarchy** (propose fixes in this order): 1) delete the animation (high-frequency/no purpose/keyboard) → 2) reduce it (shorter, smaller, fewer properties) → 3) fix easing → 4) fix origin/physicality → 5) make interruptible → 6) move to GPU → 7) asymmetric timing → 8) polish → 9) accessibility & cohesion.

**Verdict discipline:** Block if any feel-breaking regression, animation on keyboard/high-frequency action, `scale(0)`/`ease-in` on UI, or non-GPU animation with an easy GPU fix. Otherwise Approve. When unsure whether motion feels right, recommend reviewing in slow motion / frame-by-frame with fresh eyes rather than guessing.

### The "find opportunities" gate (restraint filter)

From emilkowalski/skills `find-animation-opportunities` — use when asked "what could be animated here?" / "make this feel more alive." It's a filter as much as a finder: **a short list of high-conviction opportunities beats a long wishlist.**

Every candidate must survive all four questions:
1. **Frequency** — 100+/day: reject, no animation ever. Tens/day: reject or near-imperceptible. Occasional: eligible. Rare/first-time: eligible (delight budget).
2. **Purpose** — must be named: feedback, spatial consistency, state indication, preventing a jarring change, explanation, or delight (only at rare tier). "It looks cool" is not on the list.
3. **Speed** — must fit the budgets (UI under 300ms). If it only "works" as slow/showy, it fails.
4. **Function** — decoration on functional, information-dense UI hinders. Data the user is reading should not move for style.

**Hunt seams:** pressable elements with no `:active` state; content that teleports (conditional renders, expanding sections); panels/menus with no connection to their trigger; dismissables that exit a different way than they entered; grids/lists that pop in all at once; draggables that snap with no physics; rare high-emotion moments rendered flat.

**Report format:** Part 1 = opportunities table (# | Location | Today | Purpose | Frequency | Suggested motion with exact values); Part 2 = **rejected candidates** (2–5 places considered and deliberately rejected, each with the gate question that killed it — this is what separates it from an animation wishlist); Part 3 = one-paragraph verdict with the single highest-leverage suggestion. Cap at 5–7 suggestions for a whole app.

## References

- `references/web-motion-recipes.md` — react-bits distilled: multi-step blur reveal, trigger-once scroll, GSAP in-and-out, tilt springs, effect vocabulary (react-bits)
- `references/motion-library-reference.md` — motion.dev distilled: spring config + visualDuration, easing functions + modifiers, scroll-triggered vs scroll-linked patterns, AnimatePresence, layout animation, animateView, MotionScore tiers, Motion UI tokens, AI Kit pattern

## Related Skills (Emil's repo — what we already have vs new)

From github.com/emilkowalski/skills (installable: `npx skills@latest add emilkowalski/skills`), 10 skills:

- **Already covered:** `emil-design-eng` → our `design-engineering`; `animate` → our `design-engineering`/`design-motion-principles`; `review-animations` → this skill's Audit Mode + escalation triggers above; `improve-animations` → our `ui-implementation-review` audit + `design-spec-agent-prompts` plans; `find-animation-opportunities` → the Gate above; `prototype` → our `sketch`/`claude-design`; `pick-ui-library` → our `tech-stack-evaluation`/`shadcn-ui`.
- **Added new:** `animation-vocabulary` (reverse-lookup glossary for vague motion descriptions — "what's it called when…") and `apple-design` (Apple's fluid-interface principles: damping/response springs, velocity handoff, momentum projection, rubber-banding, gesture feel, typography, 8 design principles).

## Verification Checklist

- [ ] Every animation has a purpose aligned with one lens.
- [ ] Frequency gate applied to the interaction.
- [ ] No motion on keyboard-initiated actions.
- [ ] Duration matches the chosen lens.
- [ ] AI-slop patterns checked and flagged.
- [ ] Reduced motion honored with fewer, gentler transitions.
