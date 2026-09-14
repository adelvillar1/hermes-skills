---
name: brand-palette-migration
description: Extract brand colors from assets; migrate UI tokens.
---

# Brand Palette Migration

Derive a UI color palette from brand assets (logos, brand marks, marketing images) and migrate a design-token system onto it — with the colors **measured, not eyeballed**, and the migration **verified, not assumed**.

This is the class of work where a company's brand marks and its product UI have drifted into two different color systems, and someone decides to reconcile them.

## When to Use

- "Suggest a palette based on these logos" / "match the UI to our brand"
- Migrating a design system from one palette to another
- Any task where a color value must be *derived from an image* rather than chosen
- Auditing an existing palette's contrast before a rebrand

## The core discipline

**Measure the source, verify the result.** Two specific claims:

1. **Extract colors from pixels, not from a vision read.** A vision pass over a logo gives approximate hexes that are fine for orientation and wrong in the last two digits — `#337AB7` vs actual `#3474AC`, `#FFFF00` vs actual `#FFDF3F`. Those digits matter when the value becomes a token that ships. Sampling the actual pixels is cheap and exact; see `references/logo-color-extraction.md`.
2. **Compute every contrast ratio before proposing a pairing.** WCAG 2.1 is arithmetic — do it in code over the real token table, never by eye and never by trusting that "brand colors must be fine."

## The three findings that shape every migration

### 1. Brand accent colors almost always FAIL as text

A logo accent is chosen to pop against the logo's own background — often dark, often as a large shape. In a UI it becomes a link, an icon, a label, on a light surface. The logo's warm accent measured **1.29:1** on paper: unusable at any size.

**Fix:** sweep the brand hue downward in lightness until it clears 4.5:1, and keep the raw brand value as a separate **fill-only** token. Worked example (logo yellow `#FFDF3F`, hue ~50°):

| Step | Hex | On paper | Verdict |
|---|---|---|---|
| Raw brand | `#FFDF3F` | 1.29 | unusable |
| | `#C9860A` | 2.96 | still fails |
| | `#A8760B` | 3.89 | large text only |
| **Ship this** | **`#9C6A08`** | **4.56** | **AA** |

The raw value is not discarded — it becomes `--signal`, valid as a fill behind dark text (8.53:1) and as a hero color on dark surfaces. Naming it distinctly is what stops the next developer from shipping a 1.29:1 heading.

### 2. Token values are duplicated as hardcoded literals in remap/override blocks

This is the migration killer, and it is invisible until it ships half-broken.

Tailwind v3 bakes hex into opacity variants at build time and **cannot resolve a CSS variable into an `rgba()` alpha channel**. So codebases that remap a theme (a `[data-theme]` / `[data-flag]` override layer) hand-write the alpha variants:

```css
/* globals.css — a SECOND copy of the accent, as literals */
html[data-harbor="true"] .bg-gold\/10 { background-color: rgba(226, 122, 63, 0.10); }
html[data-harbor="true"] .border-gold\/30 { border-color: rgba(226, 122, 63, 0.30); }
/* ...~16 siblings... */
```

**Changing only `:root` leaves every `/10`–`/50` variant on the old color.** Solid accent goes gold, tinted accents stay terracotta, and no single grep for the token name catches it.

**Always:** grep the old hex *and* its `rgba()` triple before declaring a migration done. Both forms.

```bash
grep -rn "e27a3f\|226, 122, 63" app/globals.css tailwind.config.ts
```

Expected: 0 matches. Any hit escaped the sweep.

Full trap list, including the visual-regression blind spot: `references/token-migration-pitfalls.md`.

### 3. Broad-but-subtle changes cannot be reviewed as a diff

Shifting neutrals from green-grey to blue-grey touches every surface in the app and reads as "nothing much" in any single file. A reviewer sees 40 files of one-line changes and approves — then sees the app and hates it.

**Ship design sample pages first, as an approval gate, before touching app code.** Not as documentation after the fact — as the thing that gates the work.

## Workflow

1. **Extract** the brand palette from the source images. `scripts/extract_palette.py` — k-means over fully-opaque pixels, plus region isolation for wordmarks. See `references/logo-color-extraction.md` for the two artifacts that silently corrupt results (transparency flattening, anti-alias phantoms).
2. **Measure** contrast for every intended pairing. `scripts/check_contrast.py` — WCAG 2.1 ratios over the candidate token table, with AA/AAA verdicts.
3. **Derive** the token set. Split each brand color by role: text-safe variant (darkened to pass) vs fill-only variant (raw brand value). Record both.
4. **Sweep for duplication** before planning: find every place the old values exist as literals — `:root`, `tailwind.config.*`, CSS override blocks, hardcoded hex in components, inline `style` props, inline SVG `fill`/`stroke`. Count them; the plan's shape depends on the number.
5. **Build sample pages as the gate.** Self-contained HTML using the real token values, captured to PNG at desktop + mobile. Full page compositions, not swatch strips — the point is to see the neutral shift in context.
6. **Then** migrate tokens at every source of truth (see pitfalls), then clean up the sites tokens cannot reach.
7. **Verify** in three layers: build/type/lint pass, behavior test suites pass, and a real headless-browser contrast check over the rendered DOM.

## Reuse the existing mockup pipeline

Before building a sample-page harness, check whether the project already has one. Established design systems usually ship with a `handoff/` or `design-references/` bundle containing render harnesses and token files. Look for:

```bash
find . -maxdepth 2 -iname "*mockup*" -o -maxdepth 2 -iname "*design*" -o -maxdepth 2 -iname "*handoff*" | grep -v node_modules
grep -rli "mockup" docs/recaps/*.md 2>/dev/null
```

Rebuilding a pipeline that already exists is a real mistake, not a time cost. Extend it.

## Deliverable shape

A palette proposal is not a table of hexes. It contains:

- The **extracted source colors** with their provenance (which image, what share of pixels) — so the user can check the extraction
- The **derived token table** with old → new and the computed ratio for each role
- A **rendered swatch/sample sheet** the user can actually look at
- **Explicit naming of what changed and why** (e.g. "accent darkened to pass AA") — an unexplained value change reads as an error

## Pitfalls

- **Do not trust a vision read for final hex values.** Use it for orientation, verify with pixel sampling. The last two digits matter once a value becomes a token.
- **Do not use a raw brand accent as a text color.** Measure first. Assume it fails until the arithmetic says otherwise.
- **Do not change only `:root`.** Grep both the hex and the `rgba()` triple. Opacity-variant override blocks are the #1 silent escape.
- **Do not assume visual regression tests protect you.** In a mass palette change every baseline changes by design, so the suite reports nothing useful and a genuine layout break hides inside the update. Review each regenerated baseline individually.
- **Do not blanket-replace every hardcoded hex.** Some are chart series, status semantics, or third-party brand colors with their own constraints. Audit and justify; document intentional exceptions.
- **Do not skip dark mode scoping.** A light-mode palette migration is already large. Say explicitly that dark mode is out of scope rather than half-doing it — dark surfaces have a different contrast problem entirely.
- **Do not present the change as a diff and call it reviewable** when the change is broad-but-subtle. Sample pages exist for exactly this.
- **Check for tone collisions after the change.** A new warm accent can collide with an existing `amber`/`warning` status tone. Both warm, both on badges, no longer distinguishably different. Verify they separate.

## Verification

Layered — no single layer is sufficient:

```bash
# 1. Contrast: computed, not perceived (catches hard failures)
python3 scripts/check_contrast.py

# 2. Duplication sweep: both literal forms
grep -rn "<old-hex>\|<old-rgb-triple>" <css files>

# 3. Build + types
pnpm run build && pnpm run lint && npx tsc --noEmit

# 4. Behavior suites pass (they assert behavior, not pixels)
# 5. Visual baselines regenerated AND individually reviewed
```

Plus a headless-browser pass computing computed-style contrast per text node on the rendered DOM — this catches pairs that exist only after cascade resolution, which no static token-table check can see.

## Reference files

- `references/logo-color-extraction.md` — pixel extraction method, the transparency artifact, the anti-alias phantom, region isolation for wordmarks
- `references/token-migration-pitfalls.md` — the remap-block trap, visual-regression blind spot, tone collisions, source-of-truth enumeration
- `scripts/extract_palette.py` — k-means palette extractor over opaque pixels
- `scripts/check_contrast.py` — WCAG 2.1 ratio matrix with AA/AAA verdicts
