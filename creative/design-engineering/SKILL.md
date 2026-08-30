---
name: design-engineering
description: "Polish UI components with design-engineering motion and details."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [UI, Animation, Frontend, Polish]
    related_skills: [design-motion-principles, impeccable, ui-ux-pro-max]
---

# Design Engineering

Apply Emil Kowalski-style design engineering to frontend UI: invisible details, animation decisions, component patterns, and polish that make interfaces feel right.

## When to Use

- Refining animation, easing, duration, and interaction details.
- Building or auditing buttons, popovers, tooltips, modals, drawers.
- Diagnosing why a UI feels cheap or sluggish.

## Core Philosophy

Taste is trained, not innate. Unseen details compound. Beauty is leverage.

## Animation Decision Framework

1. **Should this animate?** Frequency gate: 100+/day = none; tens/day = reduce; occasional = standard; rare = delight. Never animate keyboard-initiated actions.
2. **Purpose:** valid = spatial consistency, state indication, explanation, feedback, preventing jarring changes. Invalid = "looks cool" + frequent.
3. **Easing:** use custom cubic-bezier curves. Entering = ease-out; moving/morphing = ease-in-out; hover/color = ease; constant = linear. Never use ease-in on UI.
4. **Speed:** button press 100-160ms; tooltips/popovers 125-200ms; dropdowns 150-250ms; modals/drawers 200-500ms. Keep UI animations under 300ms.

## Key Curves

```css
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

## Spring Animations

Use for drag, "alive" elements, and interruptible gestures. Keep bounce subtle (0.1-0.3). Example:

```js
{ type: "spring", duration: 0.5, bounce: 0.2 }
```

Springs maintain velocity when interrupted; CSS keyframes restart from zero.

## Component Patterns

- Buttons: `transform: scale(0.97)` on `:active` for tactile feedback.
- Never animate from `scale(0)` — start from `scale(0.9)` with opacity.
- Popovers: set `transform-origin` from the trigger, not center.
- Modals: keep centered.
- Tooltips: first appearance delayed + animated; subsequent appearances instant.
- Prefer CSS transitions over keyframes for interruptible UI.
- Use `filter: blur(2px)` to mask imperfect transitions.
- Use `@starting-style` for entry without JavaScript.

## Performance

Only animate `transform` and `opacity`. Framer Motion `x`/`y` shorthand is not hardware-accelerated — use full `transform` strings. CSS animations run off the main thread; use WAAPI for programmatic animations.

## Accessibility

- Honor `prefers-reduced-motion`: reduce quantity and intensity, not zero — keep opacity and color transitions.
- Gate hover styles behind `@media (hover: hover) and (pointer: fine)`.

## Review Checklist

- [ ] `transition: all` → specify exact properties.
- [ ] `scale(0)` → start from `scale(0.95)` or higher.
- [ ] `ease-in` on UI → `ease-out` or custom curve.
- [ ] Popover `transform-origin: center` → trigger origin.
- [ ] Keyboard action animated → remove animation.
- [ ] Duration >300ms → reduce.
- [ ] Hover without media query → add `hover`/`pointer` media.
- [ ] Keyframes on rapid elements → use transitions.
- [ ] Framer Motion `x`/`y` under load → use full `transform`.
- [ ] Same enter/exit speed → make exit faster.
- [ ] All elements appear at once → stagger 30-80ms.
