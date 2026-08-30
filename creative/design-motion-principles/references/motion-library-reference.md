# Motion Library Reference (motion.dev distilled)

Source: https://motion.dev — the Motion library (formerly Framer Motion), MIT core, trusted by Framer/Figma. React, vanilla JS (`motion/mini`), and Vue. Docs: https://motion.dev/docs. Examples (410+ AI-ready): https://motion.dev/examples. Motion UI (production sections): https://motion.dev/ui. MotionScore (performance audit): https://score.motion.dev. AI Kit (agent context pack): https://motion.dev/ai-kit.

This reference holds the library-specific implementation knowledge that complements the measured timings (SKILL.md Measured Motion Data) and the design tokens (SKILL.md Motion Design Tokens section).

## Spring configuration

```js
import { animate } from "motion/mini";
import { spring } from "motion";

animate(element, { transform: "translateX(100px)" }, { type: spring, bounce: 0.3, duration: 0.8 });
```

- **Time options:** `duration` (default 800ms); `visualDuration` (seconds) overrides it — the time for the motion to *visually* reach target, with the "bouncy bit" after. Use visualDuration to coordinate springs with other timed animations.
- **Bounce:** 0 (no bounce) to 1 (extremely bouncy). Default 0.25. **A named choice, not an accident.**
- **Physics:** damping (default 10; 0 = oscillates forever), mass (default 1; higher = more lethargic), stiffness (default 1; higher = more sudden), velocity (default = current), restSpeed (0.1), restDelta (0.01).
- **CSS spring generation:** `element.style.transition = "all " + spring(0.5)` — generate production CSS transitions from spring physics directly. Use when you need spring feel without a JS animation loop.

## Easing functions

Named: `easeIn`, `easeOut`, `easeInOut`, `backIn/backOut/backInOut` (overshoot), `circIn/circOut/circInOut`, `anticipate`, `linear`, `steps`, `cubicBezier`.

- **cubicBezier:** precise control — `cubicBezier(.35,.17,.3,.86)`. Motion's AI Kit can generate new curves.
- **steps:** spec-compliant CSS steps easing — `steps(4)` or `steps(4, "start")`; pass progress through another easing first for non-linear step distribution.
- **Modifiers:** `reverseEasing(fn)` flips in→out; `mirrorEasing(fn)` turns in→in-out. Build the reverse of a custom curve without re-authoring.

## Scroll: the two fundamental types

1. **Scroll-triggered** — animation fires when element enters/leaves viewport (fade-ins, reveals). `whileInView` prop or `useInView` hook. Pooled IntersectionObserver = low overhead.
2. **Scroll-linked** — animation values tied directly to scroll position (parallax, progress bars, storytelling). `useScroll` + `useTransform`. Runs on native `ScrollTimeline` where possible = hardware accelerated.

**Scroll-triggered essentials:**
```jsx
<motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.8 }} />
```
- `viewport={{ once: true }}` = plays only the first time in view (use for everything non-repeating).
- `viewport={{ root: scrollRef }}` = custom scroll container.
- `useInView(ref)` sets state for any element, not just motion components.
- `viewport.amount` = how much of the element must be visible (0.8 = 80%).

**Scroll-linked essentials:**
```jsx
const { scrollYProgress, scrollY, scrollX, scrollXProgress } = useScroll();
const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 });
// reading progress bar: <motion.div style={{ scaleX, originX: 0 }} />
```
- **Detect scroll direction:** `useMotionValueEvent(scrollY, "change", ...)` — diff against `scrollY.getPrevious()`. Classic use: hide header scrolling down, show scrolling up.
- **Smooth scroll values:** pass through `useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 })` — the standard smoothing config.
- **Transform to any value:** `useTransform(scrollYProgress, [0,1], ["blur(0px)", "blur(10px)"])`.
- **Track element through viewport:** `useScroll({ target: ref, offset: ["start end", "end start"] })` — progress = element's journey through visible space.
- **Parallax rule:** background layers move SLOWER (smaller y range), foreground FASTER (larger range) — depth illusion.
- **Horizontal scroll section:** tall outer container (`height: 300vh`) → `position: sticky` inner → `useTransform(scrollYProgress → x)`. Taller container = slower horizontal feel.
- **Text scroll (marquee lines moving opposite to scroll):** `useTransform(() => scrollY.get() * -1)` + Ticker component, alternate `reverse` per line.

## AnimatePresence (exit animations)

`<AnimatePresence>` keeps elements alive so they can animate OUT of the DOM (`exit={...}`). Essential for lists, modals, page transitions — without it, removal is instant. Modern versions also handle `propagate` for nested exit animations.

## Layout animation

`layout` prop animates between any two layouts automatically (shared element transitions, reordering). `layoutId` (in the cookbook) is the shared-element variant. Use for: lists reordering, accordion height morphs, active-tab indicators.

## Independent transforms

Animate `x`, `y`, `rotate`, `scale` on the same element without wrappers: `{ rotate: 15, x: "50%" }`. Key enabler for the S-tier compositor-only animations (transform/opacity don't trigger layout/paint).

## animateView() — View Transition API wrapper (core, free)

Motion's `animateView()` fixes View Transition API's rough edges — animates between two states including `border-radius` morphs on cropped layers. Use for page transitions and state morphs where the native API is too painful. Motion UI's "page transitions" section is built on it.

## MotionScore methodology (performance grading)

Audits any URL via score.motion.dev or CLI (`npx motionscore <url> --threshold A`); grades every animation S–F, four categories each scored independently then combined:

1. **Animations** — CSS/WAAPI/JS-driven; flags layout-triggering properties, off-screen work, large paint surfaces, slow CSS variable inheritance.
2. **Scroll animations** — ScrollTimeline, ViewTimeline, IntersectionObserver patterns, JS scroll handlers.
3. **Thrashing** — layout/style thrashing from interleaved DOM reads+writes during mount and animation frames.
4. **GPU pressure** — compositor layer count, texture memory, overlap-promoted layers, persistent `will-change` declarations.

Tiers: S = compositor-only; A = main thread, no paint; B = S/A + measurements; C = triggers paint; D = triggers layout; F = per-frame thrashing.

**MotionScore Guard:** GitHub Action / CI command that audits every PR, comments grades, fails the build below threshold. The "gate animation performance in CI" pattern.

## Motion UI (production sections)

26+ sections / 38+ components, each **performance-graded with MotionScore**, drop-in to any design system via shadcn tokens (`defineTheme` from `@motion/ui-theme`). Sections: hero (editorial stagger, parallax layers), pricing (price morphs), testimonials (logo tickers, coverflow), bento grids, stats (scroll-in counters), navigation (mega menus, scroll-aware shrinking headers), CTA (magnetic banners), footers, page transitions (curtains), FAQ, overlays (sheets, toasts), buttons (hold-to-confirm, multi-state), lists (swipeable rows, notification stacks), loaders (skeleton shimmer handoff). The `defineTheme` tokens are the canonical spring token set (see SKILL.md Motion Design Tokens).

## AI Kit (agent workflow worth copying)

Motion ships an AI Kit: sends the latest docs, 410+ example sources, performance audits, and production-ready CSS springs directly to your agent (MCP server usable by Cursor/Claude/any MCP agent). Includes `search-motion-codex` returning full multi-file paste-ready source. Lesson for our own agent workflows: package the *exact reference material an agent needs* (docs + examples + audit results + token values) into one queryable bundle — same philosophy as the `design-spec-agent-prompts` skill but for library knowledge.
