---
name: apple-design
description: "Apple's fluid-interface design principles for the web."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Design, Apple, Motion, Gesture, Springs, Typography]
    related_skills: [design-motion-principles, design-engineering, animation-vocabulary]
---

# Apple Design

How Apple builds interfaces that stop feeling like a computer and start feeling like an extension of you. Distilled from Apple's WWDC design talks — chiefly *Designing Fluid Interfaces* (WWDC 2018) — and translated into the web platform (CSS, Pointer Events, `requestAnimationFrame`, spring libraries like Motion/Framer Motion). Adapted from Emil Kowalski's `apple-design` skill (github.com/emilkowalski/skills).

**The through-line:** an interface feels alive when motion starts from the current on-screen value, inherits the user's velocity, projects momentum forward, and can be grabbed and reversed at any instant. Springs are the tool that makes all of this natural, because they are inherently interruptible and velocity-aware.

## When to Use

- Building or reviewing gesture-driven UI: drag, swipe, sheets, drawers, carousels.
- Choosing spring parameters (damping/response vs mass/stiffness/damping).
- Momentum/interruptible transitions, velocity handoff, rubber-banding.
- Translucent materials, depth, typography (optical sizing, tracking, leading).
- Reduced-motion design and the design foundations (feedback, spatial consistency, restraint).

## 1. Response — kill latency

The moment lag appears, the feeling of directness "falls off a cliff."

- **Respond on pointer-down, not on release.** Highlight a button the instant it's pressed.
- **Be vigilant about every latency:** debounces, artificial timers, transition waits, the ~300ms tap delay.
- **Feedback must be continuous *during* the interaction**, not just at the end. For a drag/slider/drawer, update the UI 1:1 with the pointer the whole way.

```css
.button:active {
  transform: scale(0.97);
  transition: transform 100ms ease-out;
}
```

## 2. Direct manipulation — 1:1 tracking

"Touch and content should move together." When the user drags something, it must stay glued to the pointer — and respect the offset from *where they grabbed it* (snapping to the element's center breaks the illusion).

- Use Pointer Events with `setPointerCapture` so tracking continues even when the pointer leaves bounds.
- Track a short **velocity/position history** (last few `pointermove` events) — you need velocity at release.

## 3. Interruptibility — the single most important principle

"The thought and the gesture happen in parallel." Every animation must be interruptible and redirectable at any moment.

- **Never lock out input during a transition.**
- **Always animate from the *presentation* (current) value, never the target value.** On interrupt, read the live on-screen transform and start from there; starting from the logical/target value causes a visible jump.
- **Avoid CSS transitions and `@keyframes` for anything gesture-driven** — they can't be smoothly grabbed and reversed mid-flight. Springs animate from the current value by default.
- **When a gesture reverses, blend velocity — don't hard-cut it.** A velocity discontinuity is a "brick wall." Pick a spring library that carries velocity through a re-target.
- **Decompose 2D motion into independent X and Y springs.** A single spring on 2D distance desyncs when X and Y have different velocities.

## 4. Behavior over animation — use springs

"Animation is a conversation between you and the object, not something prescribed by the interface." A pre-scripted, fixed-duration animation can't respond to new input; a spring can.

Apple deliberately replaced the physics triplet (mass/stiffness/damping) with two designer-friendly parameters:

- **Damping ratio** — controls overshoot. `1.0` = critically damped, no bounce, smooth settle. `< 1.0` = overshoots and oscillates. Lower = bouncier.
- **Response** — how quickly the value reaches the target, in seconds. Lower = snappier. **Not "duration"** — a spring has no fixed duration; its settle time emerges from the parameters.

**Defaults:** start most UI at damping `1.0` (critically damped). Add bounce (damping ~`0.8`) **only when the gesture itself carried momentum** (flick, throw, drag release).

**Concrete values Apple ships:**

| Interaction | Damping | Response |
| --- | --- | --- |
| Move / reposition (e.g. PiP) | `1.0` | `0.4` |
| Rotation | `0.8` | `0.4` |
| Drawer / sheet | `0.8` | `0.3` |

**Web mapping (Motion/Framer Motion):** the `bounce` + `duration` spring API maps closely to Apple's damping + response. Safe house style: `damping: 1.0` springs everywhere by default; reserve bounce for momentum-driven physical interactions.

```js
// Critically damped default (no overshoot)
animate(el, { y: 0 }, { type: 'spring', bounce: 0, duration: 0.4 });
// Momentum interaction — a little bounce, only because a flick preceded it
animate(el, { y: target }, { type: 'spring', bounce: 0.2, duration: 0.4 });
```

## 5. Velocity handoff — the seam between drag and animation

When a gesture ends, the animation must **continue at the finger's exact velocity**, so there's no visible seam. Pass the pointer's release velocity as the spring's initial velocity.

Some spring APIs want **relative** velocity — normalize by the remaining distance to the target:

```
relativeVelocity = gestureVelocity / (targetValue − currentValue)
```

Example: element at `y=50`, target `y=150` (100px to go), finger moving 50px/s → initial spring velocity = `50/100 = 0.5`. Framer Motion/Motion take absolute px/s directly (`velocity` option).

## 6. Momentum projection — animate to where the gesture is *going*

"Take a small input and make a big output." Don't snap to the nearest boundary from the *release point* — use velocity to **project the resting position** (like scroll deceleration), then snap to the target nearest that projected point.

Apple's exact projection function (from *Designing Fluid Interfaces* sample code):

```js
// decelerationRate ≈ 0.998 for normal scroll feel; 0.99 for snappier
function project(initialVelocity /* px/s */, decelerationRate = 0.998) {
  return (initialVelocity / 1000) * decelerationRate / (1 - decelerationRate);
}
const projectedEndpoint = currentPosition + project(releaseVelocity);
const target = nearestSnapPoint(projectedEndpoint);
animateSpringTo(target, { velocity: releaseVelocity });
```

Note: the physics-textbook `v²/(2·decel)` is *not* what Apple ships — use the exponential-decay form above. This is the standard behavior in good bottom-sheets and carousels (Vaul, Embla).

## 7. Spatial consistency — symmetric paths, anchored origins

"If something disappears one way, we expect it to emerge from where it came."

- **Enter and exit along the same path** (panel slides in from right → dismisses to the right).
- **Anchor interactions to their source** — set `transform-origin` to the trigger.
- **Mirror the easing on reversible transitions** — use inverse cubic-bézier control points for the two directions.

## 8. Hint in the direction of the gesture

Humans predict a final state from a trajectory. Intermediate motion should telegraph where things are going (Control Center modules "grow up and out toward your finger").

## 9. Rubber-banding — soft boundaries

At an edge, resist progressively instead of stopping hard. Apply damping that increases the further past the boundary the user drags:

```js
function rubberband(overshoot, dimension, constant = 0.55) {
  return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
}
```

## 10. Gesture design details (the "feel" checklist)

- **Tap:** highlight on touch-*down* (instant), commit on touch-*up*. ~10px hysteresis/hit padding; allow cancel-by-dragging-away-and-back.
- **Drag/swipe:** require a small movement threshold (~10px) before committing to a direction, then track 1:1.
- **Detect all plausible gestures in parallel** from the first move, then cancel the losers once intent is clear. Avoid recognizers that only report a *final* state — they throw away the continuous tracking you need for feedback.
- **Minimize disambiguation delays.** Double-tap detection delays single taps; only pay that cost where double-tap truly exists.

## 11. Frame-level smoothness

Smoothness is about *what's in the frames*, not just the frame rate. Keep per-frame positional change below the perception threshold to avoid strobing.

## Typography (Apple's optical-sizing approach)

- **Tracking is size-specific, never fixed:** tighten large display text (≈ `-0.02em`), body near `0`, never loosen.
- **Leading** scales with the text size.
- Use **optical sizing** (variable fonts) so small text gets more open shapes.

## Materials & Depth

- **Translucent chrome** (`backdrop-filter`) with content scrolling *under* — the layer stack communicates hierarchy.
- **Depth** is communicated by layers moving at different rates (parallax), not by fake shadows.

## The 8 Design Principles (Apple's foundations)

1. **Clarity** — Text legible at every size; iconography precise; decor restrained.
2. **Deference** — UI helps users understand and interact with content, never competes with it.
3. **Depth** — Separate layers of visual hierarchy to communicate importance.
4. **Simplicity — not minimalism.** Strip the unnecessary so the core purpose shines. Be concise (plain language, no jargon) and clear (hierarchy — order, spacing, contrast — so the most important thing is the most obvious). Sometimes *adding* context simplifies.
5. **Craft.** Uncompromising attention to detail builds trust. Every spacing, timing, and alignment value is a deliberate choice you can defend.
6. **Delight.** The result of getting the others right, not confetti tacked on top. Decide the emotion you want people to feel (calm, confident, excited) and reinforce it.

Tactical rules:
- **Feedback comes in four kinds:** status, completion, warning, error. Confirm meaningful actions, expose ongoing status, warn before problems, validate inline (not on submit).
- **Wayfinding:** every screen answers: Where am I? Where can I go? What's there? How do I get out? Never trap the user.
- **Grouping & mapping:** proximity implies relationship; place a control near what it affects and arrange controls to mirror what they change. If you need a label to explain a control, the mapping is weak.
- **Direct, specific labels beat safe generic ones** ("Progress", "Library" not "Home").

## Reduced Motion

`prefers-reduced-motion`: **cross-fade, not slide/spring.** Tone down or remove motion; keep opacity/color transitions (gentler, not zero).

## Process

- **Prototype interactively — an interactive demo is worth "a million static designs."**
- **Design interaction and visuals together** — "You shouldn't be able to tell where one ends and the other begins."
- **Test with real people in real context**; review motion in slow motion / frame-by-frame with fresh eyes.

## Quick Reference

| Need | Technique | Concrete value |
| --- | --- | --- |
| Default UI spring | Critically damped, no overshoot | `damping 1.0`, `response 0.3–0.4` |
| Momentum / flick spring | Under-damped, slight bounce | `damping ~0.8`, `response 0.3–0.4` |
| Gesture → spring velocity | Hand off release velocity | `gestureVelocity / (target − current)` if normalized |
| Flick landing point | Project momentum | `current + (v/1000)·d/(1−d)`, `d ≈ 0.998` |
| Interrupt cleanly | Start from presentation (live) value | read the on-screen transform |
| Avoid reversal "brick wall" | Carry velocity through re-target | spring that blends velocity |
| Reversible transition | Mirror the easing curve | inverse cubic-bézier |
| Decide reverse vs. commit | Use velocity **sign**, not position | at release |
| 1:1 drag | Pointer Events + capture | respect the grab offset |
| Feedback | On pointer-down, continuous | never only at the end |
| Boundary | Rubber-band, don't hard-stop | progressive resistance |
| Translucent chrome | `backdrop-filter` layer | content scrolls under |
| Type tracking | Size-specific, never fixed | tighten large text (`-0.02em`), body near `0` |
| Reduced motion | Cross-fade, not slide/spring | `@media (prefers-reduced-motion)` |

## Source & Attribution

Adapted from Emil Kowalski's `apple-design` skill (github.com/emilkowalski/skills). Knowledge originates from Apple's WWDC design talks — chiefly *Designing Fluid Interfaces* (WWDC 2018). Translated for the web; not an Apple-affiliated project.
