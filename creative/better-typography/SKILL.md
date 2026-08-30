---
name: better-typography
description: "Web typography: fonts, scales, spacing, wrapping, details."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Design, Typography, CSS, Reference]
    category: creative
    upstream: jakubkrehel/skills (MIT)
---

# Web Typography

Ported from `jakubkrehel/skills` (`better-typography`). It covers web typography end-to-end: choosing and pairing typefaces, configuring variable fonts and OpenType features, building a type scale, line-height and letter-spacing by role, wrapping and measure, smart punctuation, and the small details (underlines, selection, inputs, contrast) that make text feel considered. It does **not** prescribe a font family - it gives rules for working with whatever the project already uses.

**Match the project's styling system.** Before suggesting or writing any fix, check how the codebase styles things and express every change in that system: Tailwind utilities in a Tailwind project, plain declarations in CSS, CSS Modules, styled-components or StyleX. The cheat sheet in `references/css-cheat-sheet.md` maps every declaration to its Tailwind equivalent. Never introduce a second styling approach just to apply a typography fix.

## When to Use

- Picking or pairing typefaces, configuring variable fonts, or setting up a type scale.
- Styling text in components - underlines, selection, placeholders, carets, truncation.
- Reviewing frontend code for typography (line-height, measure, wrapping, weight choices).
- Any mention of: typography, fonts, font formats, woff2, variable fonts, font-weight, opentype, font-feature-settings, letter-spacing, line-height, type scale, tabular numbers, text-wrap, truncation, line clamp, underlines, text-decoration, text selection, iOS input zoom, font smoothing, text contrast, measure, line length, text-box, smart punctuation, drop cap.

## Prerequisites

None. The skill is self-contained knowledge. Pull upstream source for cross-reference via `terminal` `curl -sSL https://raw.githubusercontent.com/jakubkrehel/skills/main/skills/better-typography/SKILL.md`.

## How to Run

- Load this skill: `read the SKILL.md for '`better-typography`' via your harness's skill loader`.
- For each topic, the matching `references/` file has the deep dive + CSS / Tailwind examples.
- Always start by checking the project's existing styling system. Pick the column that matches: declaration for plain CSS / CSS Modules / styled-components / StyleX, utility for Tailwind.

## Quick Reference

| Category | When to use | Reference |
| --- | --- | --- |
| Choosing fonts | Font categories, pairing, formats, typeface anatomy | `references/choosing-fonts.md` |
| Variable fonts & OpenType | Axes, weights, tabular numbers, stylistic sets | `references/variable-fonts-and-opentype.md` |
| Spacing & sizing | Type scale, line-height, letter-spacing, text trimming | `references/spacing-and-sizing.md` |
| Wrapping & punctuation | Measure, wrapping, truncation, smart punctuation, RTL | `references/wrapping-and-punctuation.md` |
| Details & accessibility | Underlines, selection, forms, decorative text, contrast | `references/details-and-accessibility.md` |
| CSS cheat sheet | Quick lookup of every property covered, with Tailwind equivalents | `references/css-cheat-sheet.md` |

## Core Principles

1. **Serve the right format.** Use `.woff2` (Brotli compression, broadly supported) on the web. `.woff` is a fallback only for very old browsers; `.ttf` and `.otf` are raw desktop formats with no web compression.
2. **Properties over raw tags.** When a CSS property exists, use it. `font-weight: 650` instead of `font-variation-settings: "wght" 650`, `font-optical-sizing: auto` instead of `"opsz"`, `font-variant-numeric: tabular-nums` instead of `font-feature-settings: "tnum" 1`. Properties keep working when a non-variable fallback renders. Reserve raw-tag properties for custom axes (`"GRAD" 80`) and niche features (`"ss01" 1`) that have no property of their own.
3. **No fake weights.** When a weight or style is not loaded, the browser synthesizes it. That is a safety mechanism, not a feature. Set `font-synthesis: none` so missing files fail visibly instead of rendering a faked bold or italic.
4. **Fewer fonts, sizes and weights.** Rarely use more than three fonts. Weight and size define hierarchy, but overusing them hurts readability quickly. Pair for contrast, not similarity: a serif headline with a sans body reads as deliberate, two near-identical sans-serifs read as a mistake.
5. **Type scale with semantic names.** Define a small set of sizes and deviate from it as little as possible. Hard-coded sizes without a system break down at scale. For solo projects, default names like `text-sm` work fine as long as the usage rules are clear. On a team, name sizes by use (`text-body-sm`), not by size, so the rules stay consistent.
6. **Line-height by role.** Headings tighter, around `1.1`. Body copy `1.5` to `1.6`. Prefer unitless values so line-height scales with the font size; fixed values like `24px` do not.
7. **Letter-spacing by size.** Large headings often look better with slightly negative letter-spacing. Small uppercase labels need a little positive letter-spacing so letters do not feel crowded. Body copy at reading sizes needs neither.
8. **Cap the measure.** Long lines make it hard for the eye to find the next line. Cap long-form text around 60-75 characters per line. Any unit works: `65ch` measures characters directly, and a pixel or rem cap is just as good - at a `16px` body size the range lands roughly between `560px` and `680px` depending on the font, so Tailwind's `max-w-xl` or `max-w-2xl` fit. What matters is that a cap exists and the resulting line length sits in range.
9. **Wrap deliberately.** `text-wrap: balance` distributes text evenly across lines: use it on headings. `text-wrap: pretty` avoids leaving a single short word on the final line: use it on descriptions. Skip both in long-form text: browsers ignore `balance` past a few lines anyway, and evening out a whole paragraph wastes space and makes it harder to read. `overflow-wrap: break-word` where long words, links or IDs could escape the container. `white-space: nowrap` on labels and badges where a line break looks broken.
10. **Tabular numbers on changing values.** Digits have different widths by default, so timers, counters and prices shift layout as they update. Apply `font-variant-numeric: tabular-nums` to any value that changes.
11. **Truncate without losing content.** Single line: `text-overflow: ellipsis` with `overflow: hidden` and `white-space: nowrap`. Multiple lines: `line-clamp`. Truncation hides content, so if the missing text matters, keep the full value reachable in a tooltip or expanded view.
12. **Write copy naturally, style with CSS.** Store text in natural case and control presentation with `text-transform`, so redesigns never require rewriting copy. Use smart punctuation: curly quotes in prose (straight quotes in code), an en dash for ranges like `2010-2020`, an em dash to set off a thought, the single ellipsis character, `&nbsp;` to keep values like `16 px` together and `&shy;` to control where long words may break.
13. **Underlines from the font.** Default underlines sit wherever the browser decides. Pull position and thickness from the font's own metrics with `text-underline-position: from-font` and `text-decoration-thickness: from-font`, or tune manually. `text-decoration-style` draws the line dotted, dashed or wavy. Unless the only thing animating is a color change, build the underline as a separate element instead of using `text-decoration`.
14. **Inputs at 16px on mobile.** iOS Safari zooms the whole page when an input's text is smaller than `16px`. Keep input text at `16px` on mobile viewports (`text-base sm:text-sm`). Avoid the `maximum-scale=1` viewport meta: Safari ignores it for pinch zoom, but every other browser honors it and blocks zooming, which fails WCAG.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| `font-variation-settings: "wght" 650` | `font-weight: 650` (raw tag breaks on fallback fonts) |
| Faux bold/italic on missing weights | `font-synthesis: none` |
| `font-size: 24px` for body | Use a type-scale variable |
| Hardcoded `line-height: 24px` | Unitless value `line-height: 1.5` |
| `text-wrap: balance` on paragraphs | `balance` only on headings; skip on long-form |
| Wide paragraphs without a measure cap | `max-w-2xl` or `max-w-[65ch]` |
| Input `< 16px` on mobile | `text-base sm:text-sm` pattern |
| `maximum-scale=1` viewport meta to fix iOS zoom | Don't - responsive input size is the fix; the meta breaks WCAG 1.4.4 |
| Three near-identical sans-serifs | Pair for contrast (serif headline + sans body), not similarity |
| `letter-spacing: 0.05em` on body copy | Reserve positive tracking for small uppercase labels |
| Plain `text-decoration: underline` | `text-underline-position: from-font` + `text-decoration-thickness: from-font` |
| Curly quotes missing in prose | Smart punctuation - curl quotes, en/em dash, ellipsis char |
| `margin-left: 8px` in mixed-direction UIs | `margin-inline-start: 8px` |

## Procedure

1. **Identify the styling system.** Read `package.json` for Tailwind / styled-components / StyleX. Pick the column to express every change in.
2. **Identify the typography concern.** Is it font choice, scale, spacing, wrapping, or detail? Match to the reference file.
3. **Pull the reference file** via `read_file` from `references/` for full examples and Tailwind mappings.
4. **Apply the principle.** Use `references/css-cheat-sheet.md` as the lookup table for declaration -> Tailwind utility conversion.
5. **Verify in the project's stack.** Run a build / reload and confirm the change renders in the right style.
6. **Review in groups.** When reviewing many typography issues, group them by concern (scale, line-height, measure, wrapping, punctuation) rather than file.

## Pitfalls

- **Do not introduce a second styling approach.** Tailwind project -> utilities; plain CSS -> declarations. The fix must match the project's existing system.
- **Do not hand-edit type scale values.** If a size doesn't fit the scale, change the scale or the use, not the size.
- **Do not skip `font-synthesis: none`.** Without it, missing weights fake-bold silently and break the typography.
- **Do not use raw font-variation-settings for axes that have a property.** `font-weight`, `font-optical-sizing`, `font-variant-numeric` etc. all exist - use them.
- **Do not exceed `text-pretty` on long-form paragraphs.** It wastes space.
- **Do not use `text-align: justify`** in interfaces. Reserve for editorial layouts only.
- **Do not write copy in ALL CAPS to "style" it.** Use `text-transform: uppercase` + `letter-spacing: 0.05em` instead, so the underlying text is still editable.
- **Do not use `text-decoration` for animated underlines** beyond color. Build a separate element and animate it.
- **Do not use straight quotes in prose.** Curl them. (Keep straight quotes in code.)
- **Do not use `maximum-scale=1`.** The responsive input size is the only fix for iOS Safari zoom.
- **Do not assume RTL when fixing direction.** Use logical properties (`margin-inline-start`, `padding-inline-end`, `text-align: start`) by default; physical properties break in RTL.
- **Variable fonts are not always smaller.** One or two weights -> static files can win. Several weights, optical sizes, custom axes -> variable wins.

## Verification

- The fix is expressed in the project's styling system (Tailwind utilities in a Tailwind project, declarations elsewhere). No mixed styles.
- Any changed font-size follows the type scale (no magic numbers).
- Any changed font-weight has a loaded file backing it (no fake-bold).
- Long-form text has a measure cap in the 60-75 char range (560-680px at 16px body).
- Inputs that take focus on mobile viewports are at least 16px.
- Curly quotes, en/em dashes, ellipsis character appear in prose where appropriate.
- No `transition: all` - specific properties only.
- When reviewing, the diff is presented in the project's chosen style column (CSS declaration OR Tailwind utility), not mixed.
