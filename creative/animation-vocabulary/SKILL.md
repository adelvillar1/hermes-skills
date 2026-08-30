---
name: animation-vocabulary
description: "Reverse-lookup glossary for vague motion descriptions."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Animation, Motion, Glossary, Naming, Communication]
    related_skills: [design-motion-principles, design-engineering, design-spec-agent-prompts]
---

# Animation Vocabulary

Turn a vague description of a motion or effect ("the bouncy thing when a popover opens", "the iOS rubber-band scroll") into the precise term, so the user knows what to ask an AI or designer for. Adapted from Emil Kowalski's `animation-vocabulary` skill (github.com/emilkowalski/skills). For **naming** an effect, not designing or building one — that's `design-motion-principles` / `design-engineering`.

## When to Use

- User asks "what's it called when…" about a motion effect.
- User describes an effect loosely and wants the right word to prompt an AI/designer.
- You need the precise term to write a `design-spec-agent-prompts` prompt or grep a codebase.

## Instructions

1. **Read for intent, not keywords.** Users describe what they *see* or *feel* ("springy", "slides off", "draws itself in"), not the technical name. Map the sensation to the glossary below.
2. **Quote the glossary verbatim.** The descriptions are authoritative — use them as-is, don't paraphrase.
3. **Disambiguate close terms.** When two compete (*Clip-path* vs *Mask*, *Pop in* vs *Bounce*, *Shared element transition* vs *Layout animation*), contrast them so the user can pick.
4. **When nothing matches exactly,** name the closest term and say plainly it's an approximation, or describe the effect in the glossary's vocabulary (e.g. "that's a *stagger* of *scale-in* entrances").
5. **Stay within this glossary.** If a term genuinely isn't here, say so rather than inventing one — though you may explain the concept using these words.
6. **Keep it tight.** A naming question wants a name, not an essay. Lead with the term; expand only if asked.

## Output Format

```
**Term** — One-line definition.

Close alternates (if any):
- **Alternate 1** — how it differs.
```

## Examples

**Feel-based:** "What's it called when a popover seems to grow out of the button you clicked instead of from its middle?"
→ **Origin-aware animation** — An element animates out of its trigger, like a popover growing from the button that opened it instead of from its own center which is the default in CSS.

**Disambiguation:** "The thing where one image turns into another image."
→ **Morph** — One shape smoothly turns into another shape, e.g. Dynamic Island.
Close alternates: **Crossfade** (simply fade over each other in the same spot); **Shared element transition** (travels and transforms from one position into another).

**Physics feel:** "That iOS scroll where it resists and snaps back when you pull too far."
→ **Rubber-banding** — Resistance and snap-back when you drag past a boundary (the iOS overscroll feel).

## Glossary

### Entrances & Exits
- **Fade in / Fade out** — Element appears or disappears by changing opacity.
- **Slide in** — Element enters by sliding in from off-screen (left, right, top, or bottom).
- **Scale in** — Element grows from smaller to full size as it appears, often paired with a fade.
- **Pop in** — Element appears with a slight overshoot, like it bounces into place.
- **Reveal** — Content is uncovered gradually, often by animating a clip-path or mask.
- **Enter / Exit** — The animation an element plays when it's added to or removed from the screen.

### Sequencing & Timing
- **Keyframes** — Defined points in an animation (0%, 50%, 100%) that the browser fills the gaps between.
- **Interpolation / Tween** — Generating all the in-between frames between a start and end value.
- **Stagger** — Animate several items one after another with a small delay between each, creating a cascade.
- **Orchestration** — Deliberately timing multiple animations so they feel like one coordinated motion.
- **Delay** — Time before an animation starts.
- **Duration** — How long an animation takes.
- **Fill mode** — Whether an element keeps its first or last frame's styles before/after the animation (e.g. forwards).
- **Stepped animation** — An animation divided into discrete steps, like a countdown timer.

### Movement & Transforms
- **Translate** — Move an element along the X or Y axis.
- **Scale** — Make an element bigger or smaller.
- **Rotate** — Spin an element around a point.
- **Skew** — Slant an element along the X or Y axis.
- **3D tilt / Flip** — Rotate in 3D space (rotateX / rotateY) to add depth.
- **Perspective** — How strong the 3D effect looks — lower value exaggerates depth.
- **Transform origin** — The anchor point a scale or rotation grows or spins from.
- **Origin-aware animation** — Element animates out of its trigger instead of its own center (the CSS default).

### Transitions Between States
- **Crossfade** — One element fades out as another fades in, in the same spot.
- **Continuity transition** — A change that keeps the user oriented by visually connecting before and after.
- **Morph** — One shape smoothly turns into another shape, e.g. Dynamic Island.
- **Shared element transition** — Element travels and transforms from one position into another (thumbnail → card).
- **Layout animation** — When an element's size or position changes, it animates to the new spot instead of snapping.
- **Accordion / Collapse** — A section smoothly expands and collapses its height.
- **Direction-aware transition** — Content slides one way going forward and the opposite way going back.

### Scroll
- **Scroll reveal** — Elements fade or slide into place as they enter the viewport.
- **Scroll-driven animation** — Progress tied directly to scroll position.
- **Parallax** — Background and foreground move at different speeds while scrolling.
- **Page transition** — Animation when navigating from one page or route to another.
- **View transition** — The browser morphs between two states or pages, connecting shared elements.

### Feedback & Interaction
- **Hover effect** — Visual change when the cursor moves over an element.
- **Press / Tap feedback** — A subtle scale-down when an element is clicked, so it feels physical.
- **Hold to confirm** — A progress effect that fills up while the user holds a button.
- **Drag** — Moving an element by grabbing it, often with momentum when released.
- **Drag to reorder** — Dragging items in a list to rearrange them, while the others shift to make room.
- **Swipe to dismiss** — Dragging an element off-screen to close it, like a drawer or toast.
- **Rubber-banding** — Resistance and snap-back when you drag past a boundary (the iOS overscroll feel).
- **Shake / Wiggle** — A quick side-to-side jitter signaling an error or rejected input.
- **Ripple** — A circle expanding from the point of a tap, confirming the press.

### Easing
- **Easing** — The rate at which an animation speeds up or slows down.
- **Ease-out** — Starts fast, ends slow. Default for most UI and anything responding to the user.
- **Ease-in** — Starts slow, ends fast. Usually avoided; can feel sluggish.
- **Ease-in-out** — Slow, fast, slow. Good for elements already on screen moving from A to B.
- **Linear** — Constant speed. Avoid for UI; reserve for spinners or marquees.
- **Cubic-bezier** — A custom easing curve you define for precise control.
- **Asymmetric easing** — Accelerates and decelerates at different rates; feels more alive than symmetric.

### Spring Animations
- **Spring** — Motion driven by physics (tension, mass, damping) rather than a set duration.
- **Stiffness / Tension** — How strongly the spring pulls toward its target. Higher = snappier.
- **Damping** — How quickly a spring settles. Lower = more bounce and oscillation.
- **Mass** — How heavy the animated element feels. More mass = slower, more sluggish.
- **Bounce** — A spring that overshoots and settles, adding playfulness.
- **Perceptual duration** — How long a spring *feels* finished, even though it keeps micro-settling underneath.
- **Momentum** — Motion that carries velocity, especially after a drag or interruption.
- **Velocity** — How fast and in which direction an element is moving. A spring carries it into the next animation when interrupted.
- **Interruptible animation** — Can be smoothly redirected mid-flight instead of finishing first.

### Looping & Ambient
- **Marquee** — Text or content that scrolls continuously in a loop.
- **Loop** — An animation that repeats, a set number of times or infinitely.
- **Alternate (yoyo)** — A loop that plays forward then reverses each iteration.
- **Orbit** — An element circling around another in a continuous path.
- **Pulse** — A gentle repeating scale or opacity change to draw attention.
- **Float** — A gentle, continuous up-and-down drift that makes a static element feel alive.
- **Idle animation** — Subtle motion that plays while an element is just sitting there.

### Polish & Effects
- **Blur** — A blur filter used to soften an element or mask tiny imperfections.
- **Clip-path** — Clipping an element to a shape, used for reveals, masks, before/after sliders.
- **Mask** — Hiding or revealing parts of an element using a shape or gradient — like clip-path, but with soft, fadeable edges.
- **Before / after slider** — A draggable divider that wipes between two overlaid images.
- **Line drawing** — An SVG path that draws itself in, like an invisible pen tracing it.
- **Text morph** — Text that animates character by character when it changes.
- **Skeleton / Shimmer** — A placeholder with a moving sheen shown while content loads.
- **Number ticker** — Digits rolling or counting up to a value.
- **Tabular numbers** — Fixed-width digits so numbers don't shift as they change. Essential for tickers/timers/counters.
- **Typewriter** — Text appearing one character at a time, as if being typed.

### Performance
- **Frame rate (FPS)** — Frames drawn per second. 60fps baseline for smooth motion; 120fps on newer displays.
- **Jank** — Visible stutter when the browser drops frames.
- **Dropped frame** — A frame the browser missed its deadline to draw.
- **Compositing** — Letting the GPU move or fade an element on its own layer without redoing layout or paint.
- **will-change** — A CSS hint that an element is about to animate, so the browser promotes it to its own layer.
- **Layout thrashing** — Animating properties (width, height, top, left) that force layout recalc every frame.

### Principles to Know
- **Purposeful animation** — Motion should serve a function — orient, give feedback, show relationships — not just decorate.
- **Anticipation** — A small wind-up in the opposite direction before a move.
- **Follow-through** — Parts of an element keep moving and settle slightly after the main motion stops.
- **Squash & stretch** — Deforming an element as it moves to convey weight and flexibility.
- **Perceived performance** — The right animation makes an interface feel faster, even when it isn't.
- **Frequency of use** — The more often a user sees an animation, the shorter and subtler it should be.
- **Spatial consistency** — Animating so an element keeps its identity and position across states.
- **Hardware acceleration** — Animating transform and opacity lets the GPU keep motion smooth.
- **Reduced motion** — Respecting the user's `prefers-reduced-motion` setting by toning down or removing motion.

## Source & Attribution

Adapted from Emil Kowalski's `animation-vocabulary` skill (github.com/emilkowalski/skills, installable via `npx skills@latest add emilkowalski/skills`). Glossary mirrors his `/vocabulary` page. Keep the two in sync if either changes.
