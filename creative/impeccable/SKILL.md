---
name: impeccable
description: "Design, critique, audit, and polish production frontend UI."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [UI, Design, Audit, Frontend]
    related_skills: [design-engineering, design-motion-principles, anti-ai-slop]
---

# Impeccable

Design, critique, audit, and polish production-grade frontend interfaces. Covers hierarchy, accessibility, motion, typography, spacing, theming, and live browser iteration.

## When to Use

- Crafting a new UI from scratch.
- Critiquing or auditing an existing design or implementation.
- Polishing spacing, color, type, motion, or layout.

## Sub-Commands

craft, shape, init, document, extract, critique, audit, polish, bolder, quieter, distill, harden, onboard, animate, colorize, typeset, layout, delight, overdrive, clarify, adapt, optimize, live.

## Color Rules

- Verify contrast: body text ≥4.5:1, large text ≥3:1, placeholders ≥4.5:1.
- Gray text on a colored background looks washed out — use a darker shade of the background's hue.
- Avoid default purple/blue gradients and glowing edges.

## Typography Rules

- Cap body line length at 65-75ch.
- Do not pair similar fonts; pair on a contrast axis.
- Hero ceiling: `clamp()` max ≤6rem.
- Display letter-spacing ≥ -0.04em.
- Use `text-wrap: balance` on h1-h3 and `text-wrap: pretty` on prose.

## Layout Rules

- Vary spacing for rhythm.
- Cards are lazy — use only when they are truly the best pattern.
- Flexbox for 1D, Grid for 2D.
- Responsive grids: `repeat(auto-fit, minmax(280px, 1fr))`.
- Maintain a semantic z-index scale.

## Motion Rules

- Motion must be intentional, not an afterthought.
- Do not animate CSS layout properties.
- Use ease-out with exponential curves.
- Reduced motion is not optional.
- One staggered list is fine; uniform stagger on every section is the tell.

## Interaction Rules

- Dropdowns inside `overflow: hidden` get clipped — use dialog/popover API or a portal.
- Gate hover behind `@media (hover: hover) and (pointer: fine)`.

## Absolute Bans

- Side-stripe borders.
- Gradient text as a default.
- Glassmorphism as a default.
- Hero-metric template.
- Identical card grids.
- Tiny uppercase tracked eyebrow on every section.
- Numbered section markers (01/02/03) as default.
- Text overflow.

## AI Slop Test

If someone could say "AI made that" without doubt, it has failed.

- First-order check: if the theme and palette are guessable from the category alone, rework.
- Second-order check: if the aesthetic is guessable from the category plus anti-references, it is the trap one tier deeper.

## Fix Priority

When upgrading an existing project, apply changes in this order for maximum visual impact with minimum risk (derived from taste-skill redesign-skill, Leonxlnx, MIT):

1. **Font swap** — biggest instant improvement, lowest risk.
2. **Color palette cleanup** — remove clashing or oversaturated colors.
3. **Hover and active states** — makes the interface feel alive.
4. **Layout and spacing** — proper grid, max-width, consistent padding.
5. **Replace generic components** — swap cliché patterns for modern alternatives.
6. **Add loading, empty, and error states** — makes it feel finished.
7. **Polish typography scale and spacing** — the premium final touch.

## Live Iteration

Use `browser_navigate` + `browser_vision` to inspect the rendered UI. Iterate on the rendered output rather than the static source. For large changes, use `browser_click` and `browser_type` to test interactions directly.

## Verification Checklist

- [ ] Contrast verified for body, large, and placeholder text.
- [ ] Body line length capped at 65-75ch.
- [ ] Layout uses Flexbox for 1D and Grid for 2D.
- [ ] Motion is purposeful and reduced-motion friendly.
- [ ] No absolute bans present.
- [ ] AI slop test passed (theme and palette not generic).
- [ ] Live browser inspected and iterated.
