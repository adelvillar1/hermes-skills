# Web Motion Recipes (react-bits distilled)

Source: https://github.com/DavidHDev/react-bits — 45k★, 165+ animated React components (TextAnimations / Animations / Components / Backgrounds), each shipped in 4 variants (JS-CSS, JS-TW, TS-CSS, TS-TW). MIT + Commons Clause — free for personal and commercial use. Docs: https://reactbits.dev. Install via shadcn or jsrepo (`npx shadcn@latest add @react-bits/BlurText-TS-TW`).

Use: when building web motion, prefer these proven patterns/values over intuition. Combined with the measured iOS timings in the SKILL.md body, they cover both "what looks premium" (measured) and "how to build it" (recipes).

## Multi-step blur reveal (BlurText-style entrance)

The signature "expensive" text entrance. Key insight: **two intermediate steps, not one**.

- From: `{ filter: 'blur(10px)', opacity: 0, y: ±50 }` (direction top or bottom)
- Mid 1: `{ filter: 'blur(5px)', opacity: 0.5, y: ∓5 }`
- Mid 2 → To: `{ filter: 'blur(0px)', opacity: 1, y: 0 }`
- Per-element stagger delay: `(index * delay) / 1000` with `delay ≈ 200ms`
- Duration per segment ≈ 0.35s × (steps − 1); distribute with `times` array for even keyframe spacing
- Animate by words or letters; preserve word spacing with `\u00A0` (non-breaking space)
- `willChange: 'transform, filter, opacity'` on each animated span
- `onAnimationComplete` fires on the last element → chain next action

The intermediate blur(5px)/opacity 0.5 frame is what separates premium from a generic fade. A single fade-in (from → to) reads as default; the stepped keyframe reads as authored.

## Trigger-once scroll entrance (IntersectionObserver)

```js
const observer = new IntersectionObserver(
  ([entry]) => {
    if (entry.isIntersecting) {
      setInView(true);
      observer.unobserve(ref.current); // fires ONCE, then stops observing
    }
  },
  { threshold: 0.1, rootMargin: '0px' }
);
observer.observe(ref.current);
return () => observer.disconnect();
```

Rules: `threshold 0.1` is the default; unobserve after first fire (performance + no re-trigger); cleanup on unmount; inView gates `animate` while initial stays as `from` (so off-screen elements are pre-hidden).

## Scroll-driven in AND out (GSAP ScrollTrigger)

```js
gsap.registerPlugin(ScrollTrigger);
// entrance timeline
tl.to(el, { [axis]: 0, scale: 1, opacity: 1, duration: 0.8, ease: 'power3.out' });
// trigger
ScrollTrigger.create({ trigger: el, scroller, start: 'top 90%', once: true, onEnter: () => tl.play() });
// optional disappear tail after entrance
gsap.to(el, { [axis]: reverse ? distance : -distance, scale: 0.8, opacity: 0,
  delay: disappearAfter, duration: 0.5, ease: 'power3.in' });
```

Notes: defaults are distance 100, duration 0.8, ease `power3.out`, scale 1, opacity 0→1. Support a custom scroller container (`document.getElementById('snap-main-container')` fallback) for snap-scroll pages. Kill both ScrollTrigger and timeline on cleanup.

## Tilt card (motion springs + velocity follow-through)

```js
const springValues = { damping: 30, stiffness: 100, mass: 2 }; // heavy, smooth
// pointer move:
const offsetX = e.clientX - rect.left - rect.width / 2;
const rotationX = (offsetY / (rect.height / 2)) * -rotateAmplitude; // 14° typical
const rotationY = (offsetX / (rect.width / 2)) * rotateAmplitude;
// caption follow-through from pointer VELOCITY:
const velocityY = offsetY - lastY;
rotateFigcaption.set(-velocityY * 0.6);
```

Spring constants: `damping 30 / stiffness 100 / mass 2` for the tilt itself; `stiffness 350 / damping 30 / mass 1` for snappier caption rotation. Reset everything on mouse leave (rotate 0, scale 1, opacity 0). Always show a mobile warning — this effect is desktop-only.

## Effect vocabulary (pick by mood)

When a user says "make it memorable" or "add some flair", choose from the catalog instead of inventing:

- **Text:** BlurText, DecryptedText (decode-in), SplitText, CountUp, CircularText (rotating circular wordmark), VariableProximity (letters respond to cursor proximity), TrueFocus (focus-highlight text), WarpText, GradientText, EchoText, FoldText, FallingText, TextType
- **Cursor:** BlobCursor, GhostCursor, SwarmCursor (particle trail), TargetCursor, Crosshair, ClickSpark (click particle burst)
- **Background:** Aurora (blob gradient), Beams (light beams), DotField, DotGrid, Threads, WebThreads, Topography (contour lines), Waves, Ferrofluid, Dither, AcidSquares, Ballpit
- **Card:** TiltedCard, SpotlightCard (mouse-follow glow), BounceCards (fan-out), Stack (card pile), BorderGlow, DecayCard
- **Content:** AnimatedContent (scroll reveal w/ optional disappear), FadeContent, GradualBlur, ScrollReveal, StickerPeel
- **UI:** AccordionGallery, AnimatedList, Carousel, CircularGallery, Counter, CurvedInput, StaggeredMenu, Stepper, BubbleMenu, CardNav, CardSwap, ChromaGrid

## reactbits.dev creative tools

- **Shape Magic** — inner rounded corners between overlapping shapes → exports as SVG, React code, or **clip-path code**. Great for logo/illustration geometry.
- **Texture Lab** — 20+ texture effects (noise, dithering, ASCII) on images/video, high-quality export.
- **Background Studio** — animated backgrounds, customize + export as video/image/code.

## License note

MIT + Commons Clause: free for personal/commercial use, but you cannot sell the components themselves as a competing library. Fine for app code. (Contrast: top-welcome-screens is GPL-3.0 with strict branding-replacement requirements — always check the license before copying code into a product.)
