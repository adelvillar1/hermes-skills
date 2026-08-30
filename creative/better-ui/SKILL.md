---
name: better-ui
description: "UI polish: surfaces, animations, performance."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Design, UI, Motion, Animation, Reference]
    category: creative
    upstream: jakubkrehel/skills (MIT)
---

# UI Polish

Ported from `jakubkrehel/skills` (`better-ui`). Design engineering principles for making interfaces feel polished: surfaces (border radius, optical alignment, shadows, image outlines, hit areas), animations (interruptible, enter/exit, contextual icons, scale on press), and performance (transition specificity, `will-change`). It does **not** prescribe a framework - the rules adapt to vanilla CSS, Tailwind, Motion (Framer Motion), or any combination.

Typography is covered by the `better-typography` skill - use that for anything text-related. Colors are covered by `better-colors`. This skill focuses on the *feel* of an interface.

## When to Use

- Building UI components, reviewing frontend code, implementing animations.
- Hover states, shadows, borders, micro-interactions, enter/exit animations, any visual detail work.
- Mentions of: UI polish, design details, "make it feel better", "feels off", stagger animations, border radius, optical alignment, image outlines, box shadows, hit area, focus rings.

## Prerequisites

None. The skill is self-contained. Check the project's `package.json` to know whether Motion / Framer Motion is installed - that changes which animation pattern to recommend. Pull upstream source for cross-reference via `terminal` `curl -sSL https://raw.githubusercontent.com/jakubkrehel/skills/main/skills/better-ui/SKILL.md`.

## How to Run

- Load this skill: `read the SKILL.md for '`better-ui`' via your harness's skill loader`.
- For each topic, the matching `references/` file has the full code examples (CSS, Tailwind, Motion where applicable). Read them with `read_file` when you need the complete snippet.
- When reviewing or generating UI changes, present the output as a **markdown table with `Before` and `After` columns** - one row per change, grouped by principle heading.

## Quick Reference

| Category | When to use | Reference |
| --- | --- | --- |
| Surfaces | Border radius, optical alignment, shadows, image outlines, hit areas | `references/surfaces.md` |
| Animations | Interruptible animations, enter/exit transitions, icon animations, scale on press | `references/animations.md` |
| Performance | Transition specificity, `will-change` usage | `references/performance.md` |

## Core Principles

### Surfaces

1. **Concentric border radius.** Outer radius = inner radius + padding. Mismatched radii on nested elements is the most common thing that makes interfaces feel off. Exception: when padding exceeds 24px, treat layers as separate surfaces and pick each radius independently.
2. **Optical over geometric alignment.** When geometric centering looks off, align optically. Buttons with icons use `icon-side padding = text-side padding - 2px`. Play-button triangles shift slightly right. Asymmetric icons (stars, carets, arrows) are best fixed in the SVG itself.
3. **Shadows over borders.** For buttons, cards, and containers that use a border for depth or elevation, replace it with a subtle layered `box-shadow`. Shadows adapt to any background since they use transparency; solid borders don't. Do not apply this to dividers (`border-b`, `border-t`) or any border whose purpose is layout separation.
4. **Image outlines.** Add a subtle `1px` outline with low opacity for consistent depth. The color must be pure black in light mode (`oklch(0 0 0 / 0.1)`) and pure white in dark mode (`oklch(1 0 0 / 0.1)`) - never a near-black like slate, zinc, or any tinted neutral. A tinted outline picks up the surface color underneath it and reads as dirt on the image edge. Use `outline` not `border` so layout is unaffected.
5. **Minimum hit area.** Interactive elements need a 44x44px hit area for touch / mobile contexts. In desktop interfaces, use at least 40x40px. Extend with a pseudo-element if the visible element is smaller. Never let hit areas of two elements overlap.

### Animations

6. **Interruptible animations.** Use CSS transitions for interactive state changes - they can be interrupted mid-animation. Reserve keyframes for staged sequences that run once. CSS transitions adapt duration to remaining distance; keyframes restart from zero on re-trigger.
7. **Split and stagger enter animations.** Don't animate a single container. Break content into semantic chunks (title, description, buttons) and stagger each with ~100ms delay. For titles, consider splitting into individual words with ~80ms stagger. Combine `opacity`, `blur`, and `translateY` for the enter effect.
8. **Subtle exit animations.** Use a small fixed `translateY` (e.g. `-12px`) instead of full container height. Exit duration should be shorter than enter (150ms vs 300ms). Don't remove exit animations entirely - subtle motion preserves context.
9. **Contextual icon animations.** Animate icons with `opacity`, `scale`, and `blur` instead of toggling visibility. Use exactly these values: scale from `0.25` to `1`, opacity from `0` to `1`, blur from `4px` to `0px`. If the project has `motion` or `framer-motion`, use `transition: { type: "spring", duration: 0.3, bounce: 0 }` - bounce must always be `0`. If no motion library, keep both icons in the DOM (one absolute-positioned) and cross-fade with CSS transitions using `cubic-bezier(0.2, 0, 0, 1)`.
10. **Scale on press.** A subtle `scale(0.96)` on click gives buttons tactile feedback. Always use `0.96`. Never use a value smaller than `0.95` - anything below feels exaggerated. Add a `static` prop to disable it when motion would be distracting. Use CSS transitions for interruptibility.
11. **Skip animation on page load.** Use `initial={false}` on `AnimatePresence` to prevent enter animations firing on first render. Elements already in their default state should not animate in on page load - only on subsequent state changes. Don't apply this when the component relies on its `initial` prop to set up a first-time enter animation (page hero, loading state).

### Performance

12. **Never use `transition: all`.** Always specify exact properties: `transition-property: scale, opacity`. Tailwind's `transition-transform` covers `transform, translate, scale, rotate` and is the right utility when only transforms animate.
13. **Use `will-change` sparingly.** Only for `transform`, `opacity`, `filter`, `clip-path` - properties the GPU can composite. Never `will-change: all`. Only add when you notice first-frame stutter; each extra compositing layer costs memory.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Same border radius on parent and child | Calculate `outerRadius = innerRadius + padding` |
| Icons look off-center | Adjust optically with padding or fix SVG directly |
| Hard borders between sections (using border for depth) | Use layered `box-shadow` with transparency |
| Jarring enter/exit animations | Split, stagger, and keep exits subtle |
| Animation plays on page load | Add `initial={false}` to `AnimatePresence` |
| `transition: all` on elements | Specify exact properties |
| First-frame animation stutter | Add `will-change: transform` (sparingly) |
| Tiny hit areas on small controls | Extend with a pseudo-element to 44x44px for touch/mobile, or at least 40x40px in desktop UI |
| Scale on press below `0.95` | Use exactly `0.96` |
| Tinted image outline (`outline-slate-*`) | Use pure black / white: `outline-black/10`, `outline-white/10` |
| Toggling icon visibility (display: none) | Cross-fade with opacity + scale + blur |
| `bounce: 0.1` on icon spring | `bounce` must always be `0` for icon animations |
| `will-change: all` | Remove entirely - the browser composites GPU-friendly properties on its own |
| Adding `motion` / `framer-motion` just for icon transitions | Use the CSS cross-fade pattern instead - no dependency |

## Review Output Format

Always present changes as a markdown table with **Before** and **After** columns. Include every change you made - not just a subset. Never list findings as separate "Before:" / "After:" lines outside of a table. Group changes by principle using a heading above each table, and keep each row focused on a single diff so the reader can scan the whole list quickly.

### Example

#### Concentric border radius

| Before | After |
| --- | --- |
| `rounded-xl` on card + `rounded-xl` on inner button (`p-2`) | `rounded-2xl` on card (`8 + 8 = 16`), `rounded-lg` on inner button |
| `border-radius: 16px` on both nested surfaces | Outer `24px`, inner `16px` with `8px` padding |

#### Scale on press

| Before | After |
| --- | --- |
| `<button className="...">` | Added `active:scale-[0.96] transition-transform` |
| `scale(0.9)` on press | Raised to `scale(0.96)` - anything below `0.95` feels exaggerated |

Rows should cite the specific file and the specific property that changed when it isn't obvious from the snippet. If a principle was reviewed but nothing needed to change, omit that table entirely - empty tables add noise.

## Review Checklist

- [ ] Nested rounded elements use concentric border radius
- [ ] Icons are optically centered, not just geometrically
- [ ] Shadows used instead of borders where appropriate
- [ ] Enter animations are split and staggered
- [ ] Exit animations are subtle
- [ ] Images have subtle outlines (pure black/white in OKLCH, not tinted)
- [ ] Buttons use `scale(0.96)` on press where appropriate
- [ ] `AnimatePresence` uses `initial={false}` for default-state elements
- [ ] No `transition: all` - only specific properties
- [ ] `will-change` only on transform/opacity/filter/clip-path, never `all`
- [ ] Interactive elements have 44x44px hit areas for touch/mobile, or at least 40x40px in desktop UI

## Procedure

1. **Identify the surface, animation, or performance concern.** Pick the matching `references/` file for full code examples.
2. **Detect the project's animation stack.** Read `package.json` for `motion` / `framer-motion`. If present, use the Motion patterns; otherwise stick to CSS.
3. **Apply the principle verbatim.** The values are opinionated and exact: `0.96` scale, `0.25`-to-`1` icon scale, `100ms` stagger delay, `blur(4px)` icon exit, `cubic-bezier(0.2, 0, 0, 1)`, `bounce: 0`. Do not deviate.
4. **Group changes by principle** in the review output - one heading per principle, one table per principle that had changes.
5. **Use the project's styling system.** Tailwind utilities in Tailwind projects; plain CSS elsewhere. Never mix.
6. **Skip empty sections.** If a principle was reviewed and nothing needed to change, omit the table entirely - empty tables add noise.

## Pitfalls

- **Do not deviate from the exact values.** `scale(0.96)`, `bounce: 0`, `blur(4px)`, `cubic-bezier(0.2, 0, 0, 1)`, 100ms stagger, 44x44px hit area. These are tuned; replacing them with "close enough" reintroduces the problem they fix.
- **Do not apply shadows-to-borders to dividers.** `border-b` / `border-t` for layout separation should stay as borders. Only depth-borders get shadow treatment.
- **Do not use tinted image outlines.** Slate, zinc, near-black, near-white, or any project accent - all wrong. Pure `oklch(0 0 0 / 0.1)` light, pure `oklch(1 0 0 / 0.1)` dark.
- **Do not apply `initial={false}` to first-time enter animations.** Page heroes, loading states, and staggered first-render sequences need their initial animation. `initial={false}` is only for elements in their default state on page load (icon swaps, toggles, tabs, segmented controls).
- **Do not add a motion library just for icon transitions.** The CSS cross-fade pattern works without any dependency. Only add Motion if the project already has it.
- **Do not use `will-change` preemptively.** Only when you see first-frame stutter. Each extra compositing layer costs memory; modern browsers are already good at optimizing.
- **Do not use `transition: all`.** It watches every property for changes and prevents browser optimizations. Specify exact properties.
- **Do not animate icon scale to anything other than `0.25`.** Not `0.5`, not `0.6`. The exact value is tuned for visual continuity.
- **Do not use full-height `translateY` for exits.** Use a small fixed `-12px` so exits stay subtle.
- **Do not force concentric radius when padding > 24px.** Treat them as separate surfaces with independently chosen radii.

## Verification

- The fix is expressed in the project's styling system (Tailwind utilities in a Tailwind project, plain CSS elsewhere, Motion components in a Motion project).
- Scale on press uses exactly `0.96`, not below.
- Icon animations use exactly `scale: 0.25` -> `1`, `opacity: 0` -> `1`, `blur(4px)` -> `blur(0px)`.
- Enter staggers use ~100ms between groups, ~80ms between words.
- Hit areas measure 44x44px on touch/mobile, 40x40px on desktop.
- Image outlines use `outline-black/10` light, `outline-white/10` dark - never tinted.
- No `transition: all` anywhere.
- `will-change` only on transform / opacity / filter / clip-path, never `all`.
- The review diff is a markdown table grouped by principle, not prose.
- The animation matches the project's stack: CSS-only when no Motion library, Motion patterns when `motion` or `framer-motion` is in `package.json`.
