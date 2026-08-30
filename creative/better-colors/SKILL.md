---
name: better-colors
description: "OKLCH color workflow: convert, palette, contrast."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Design, Color, OKLCH, Tailwind, Reference]
    category: creative
    upstream: jakubkrehel/skills (MIT)
---

# OKLCH Colors

Ported from `jakubkrehel/skills` (`better-colors`). It teaches an OKLCH-first color workflow for web projects: convert hex/rgb/hsl to oklch, generate scales, check contrast (APCA + WCAG 2), handle gamut boundaries, and theme with Tailwind v4. It does **not** ship a color picker or conversion tool — it encodes the rules so the agent applies them correctly when writing or reviewing CSS, Tailwind config, or design-token definitions.

To explore interactively: `https://oklch.fyi`.

## When to Use

- The user mentions `oklch`, color conversion, palette generation, contrast ratio, gamut, display p3, design tokens, hue drift, chroma, or dark mode colors.
- The user is generating a Tailwind v4 `@theme` block, designing a scale (50-950), or wiring up dark mode.
- Reviewing existing CSS: hex/rgb/hsl in new code, HSL palette ramps with hue drift, failing contrast, high chroma without gamut check, P3 colors without sRGB fallback.
- The user wants to derive a dark palette from a light palette (or vice versa) without hand-picking each step.

## Prerequisites

None. The skill is self-contained knowledge. To explore the live playground: open `https://oklch.fyi` in a browser via `browser_navigate`. To pull the upstream source for reference: `terminal` `curl -sSL https://raw.githubusercontent.com/jakubkrehel/skills/main/skills/better-colors/SKILL.md`.

## How to Run

- Load this skill: `read the SKILL.md for '`better-colors`' via your harness's skill loader`.
- For deeper lookup tables and conversion recipes, read the files in `references/` (4 files: color-conversion, palette-generation, accessibility-contrast, gamut-and-tailwind).
- When reviewing or generating color changes, present the output as a **markdown table with `Before` and `After` columns** — every change in one row, no prose-style "Before:/After:" lists outside the table.

## Quick Reference

| Category | When to use | Reference |
| --- | --- | --- |
| Conversion | Hex/rgb/hsl to oklch | `references/color-conversion.md` |
| Palettes | Generate scales, multi-hue, dark mode | `references/palette-generation.md` |
| Contrast | APCA/WCAG checks, fixing failing contrast | `references/accessibility-contrast.md` |
| Gamut & Tailwind | P3 fallbacks, `@theme` scales, gamut clamping | `references/gamut-and-tailwind.md` |

## Why OKLCH

- **Perceptual uniformity.** Equal L steps = equal brightness. `oklch(0.5 ...)` is visually mid. HSL's `lightness: 50%` varies wildly by hue.
- **Stable hue.** HSL blue shifts toward purple as lightness changes. OKLCH hue stays constant across the full lightness range.
- **Independent chroma.** Chroma is an absolute measure of colorfulness that doesn't depend on lightness. HSL saturation does.
- **Finite gamut.** Not every oklch value maps to a displayable sRGB color. High-chroma values at certain hues will clip — gamut awareness is required.

## OKLCH Syntax

```
oklch(L C H)
oklch(L C H / alpha)
```

| Channel | Range | Description |
| --- | --- | --- |
| L (Lightness) | 0-1 | 0 = black, 1 = white. Perceptually uniform. |
| C (Chroma) | 0-~0.4 | Colorfulness. 0 = gray. Max depends on L and H. |
| H (Hue) | 0-360 | Hue angle in degrees. |
| alpha | 0-1 | Optional transparency. Slash syntax. |

```css
oklch(0.637 0.237 25.331)
oklch(0.8 0.05 200 / 0.5)
```

**Formatting:** L and C use 3 decimal places, H uses up to 3. Drop trailing zeros. Format `-0` as `0`. Browser support: Baseline 2023, 96%+ global coverage.

## Key Thresholds

| Rule | Value |
| --- | --- |
| Light/dark boundary | L > 0.6 = light background -> use dark text |
| Lightness gap (light bg) | Foreground L < 0.45 when background L > 0.85 |
| Lightness gap (dark bg) | Foreground L > 0.75 when background L < 0.25 |
| Hue drift threshold | > 10° spread across palette steps = visible drift |
| APCA normal text | abs(Lc) >= 60 to pass, >= 75 for pass+ |
| WCAG 2 normal text | 4.5:1 AA, 7:1 AAA |
| Contrast fix | Adjust L only - chroma has negligible effect |

## Core Principles

1. **Convert, don't restructure.** Replace hex/rgb/hsl values with oklch equivalents; leave gradient interpolation methods, third-party config inputs, and CSS keywords (`currentColor`, `inherit`, `initial`, `unset`, `transparent`) untouched.
2. **Lightness fixes contrast.** When text/UI fails contrast on a background, adjust the foreground's oklch L channel only. Chroma has negligible effect.
3. **Same C%, not same absolute C.** For multi-hue palettes, use the same chroma percentage (of each hue's max) so vividness reads consistent. Same absolute C makes some hues look duller than others.
4. **Derive dark mode, don't hand-pick.** Reverse the L mapping of the light palette: `--color-50` swaps with `--color-950`. Works because oklch is perceptually uniform.
5. **Clamp chroma to gamut.** High chroma at certain L/H clips in sRGB. Clamp to the max for that L/H/space. Peak hue shifts with lightness (purple at L=0.5, magenta at L=0.7, green at L=0.9; cyan is consistently lowest).
6. **P3 needs an sRGB fallback.** Wrap P3 enhancements in `@media (color-gamut: p3)`. For very old browsers without oklch support, use `@supports (color: oklch(0 0 0))`.
7. **Tailwind v4 `@theme` uses oklch natively.** Its default palette is already oklch. Custom themes should match. Opacity modifiers (`bg-brand-500/50`) work with oklch and compile to slash syntax.

## Review Output Format

Always present color changes as a markdown table with **Before** and **After** columns. Include **every color that was changed** — not just a subset. Never list findings as separate "Before:" / "After:" lines outside of a table.

| Before | After |
| --- | --- |
| `color: #3b82f6` | `color: oklch(0.623 0.188 259.815)` |
| Same absolute C across hues | Same C% of each hue's max chroma |
| No sRGB fallback for P3 color | `@media (color-gamut: p3)` wrapper |

Each row is a self-contained change the developer can act on independently.

## Common Mistakes

| Issue | Fix |
| --- | --- |
| Hex/rgb/hsl color in new code | Convert to `oklch()` |
| HSL palette ramp with hue drift | Rebuild with constant oklch hue |
| Failing contrast (check foreground vs its background using APCA) | Adjust oklch L channel, keep C and H |
| High chroma without gamut check | Clamp to max chroma for the L/H in sRGB |
| Same absolute C across different hues | Use same C% (percentage of max) for consistent vividness |
| P3 color without sRGB fallback | Add `@media (color-gamut: p3)` pattern |
| Dark mode with hand-picked colors | Derive from light palette by reversing L mapping |
| Hex in Tailwind v4 `@theme` | Convert to oklch values |
| Alpha with comma syntax | Use slash: `oklch(L C H / alpha)` |

## Procedure

1. **Identify the change shape.** Are you converting one color, generating a scale, fixing contrast, or wiring dark mode? Each has a single canonical pattern - see the matching reference file.
2. **Pull the reference file.** For full conversion recipes and gamut tables, `read_file` the matching entry in `references/`. Do not memorize thresholds; cite the table.
3. **Convert with bulk rules.** When migrating an entire file: replace hex and `rgb()`/`rgba()`/`hsl()`/`hsla()` calls, leave gradient function shells intact (only convert color stops within), leave CSS keywords untouched, preserve comments and formatting.
4. **Apply the lightness gap rule first.** For any contrast fix, change only L. Verify with APCA Lc (>= 60 pass, >= 75 pass+) or WCAG 2 ratio (4.5:1 AA, 7:1 AAA) for the actual text-vs-background pair.
5. **Clamp chroma if high.** If C exceeds the max for the L/H/space in sRGB, reduce C while keeping L and H constant. Reference the per-hue max table in `references/gamut-and-tailwind.md`.
6. **For multi-hue palettes, normalize to C%.** Different hues have different max chroma. Pick one chroma percentage (e.g. 80% of max) and apply uniformly.
7. **For Tailwind v4 themes**, define the scale with `--color-{name}-{step}` variables inside `@theme`. Use slash syntax for opacity modifiers (`bg-brand-500/50`).
8. **Output the diff as a table.** One row per change, with `Before` and `After` columns. Group by category (Conversion, Contrast, Gamut) if reviewing many.

## Pitfalls

- **Do not rewrite gradients.** Only convert the color stops inside `linear-gradient(...)` etc. The interpolation method stays the same.
- **Do not introduce hex/rgb in new code.** Even when oklch feels verbose, prefer it for new CSS - the consistency across the codebase matters more than the verbosity.
- **Do not adjust chroma to fix contrast.** It does not work. Adjust L.
- **Do not use comma alpha syntax.** `oklch(0.5 0.2 30, 0.5)` is invalid. Use slash: `oklch(0.5 0.2 30 / 0.5)`.
- **Do not trust `text-box` with oklch - they are independent.** Text trimming and color spaces do not interact.
- **Do not pair Tailwind v4 syntax with v3 `tailwind.config.js`.** `@theme` blocks only exist in v4. v3 still uses the JS config and does not understand oklch natively.
- **Tailwind's `outline-black/10` / `outline-white/10` are not oklch-generated but they are equivalent** to `oklch(0 0 0 / 0.1)` / `oklch(1 0 0 / 0.1)` for outline use. Don't convert outlines just to "be consistent" - it's noise.
- **APCA Lc is signed.** Positive = light text on dark; negative = dark text on light. Compare `abs(Lc)` against the threshold.
- **Display P3 covers ~50% more colors than sRGB.** Every sRGB color exists in P3; not every P3 color exists in sRGB. The clamping direction matters.
- **Do not generate dark mode by hand-picking colors.** Always derive by reversing L mapping of the light palette - the perceptual uniformity guarantee is what makes this safe.

## Verification

- A live `browser_navigate` to `https://oklch.fyi` confirms the L/C/H axes and the gamut boundary visually.
- For any contrast fix, recompute APCA Lc or WCAG 2 ratio on the actual text-on-background pair after the change.
- For any palette generation, verify all 9 (or 11) steps land in sRGB gamut by checking that C is at-or-below the per-hue max for each step's L.
- For Tailwind v4 `@theme`, the project compiles and the custom utilities resolve (`bg-brand-500`, `text-brand-200/60`, etc.).
- The diff for any review is a markdown table - not prose, not bullet lists.
