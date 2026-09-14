# Design-Token Compliance Audit

Workflow for auditing a frontend commit/PR against a token-based design system
(`DESIGN.md` + a tokens file such as `tokens.css`). Use whenever the repo has a
design system and the review brief includes "design-system compliance" or a hard
rule like "never hardcode hex in new CSS."

## Audit order

1. **Read the design docs FIRST** — `DESIGN.md` (rules, do/don't, component
   specs) and the tokens file (token names + values). Do this before reading the
   diff. You need the token vocabulary to audit; you can't flag a wrong token you
   don't know exists.
2. Get the diff for the CSS/style files and the component files.
3. Run the **negative grep** (hardcoded literals) and the **positive grep**
   (token usage).
4. Audit the **structural rules** the doc spells out (typography, buttons, cards,
   surface modes, motion).
5. Report **PASS/FAIL per rule** with file:line evidence, kept separate from
   subjective craft notes.

## Grep recipes

### Hardcoded color literals (must be ZERO in added lines)

```bash
git diff <base> <head> -- 'apps/**/styles.css' 'apps/**/*.tsx' \
  | grep -E '^\+' \
  | grep -nE '#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\('
```

Any hit = violation. `color-mix()` is allowed only when its inputs are
`var(--token)` (e.g. `color-mix(in srgb, var(--brass) 30%, transparent)`).

### Positive token usage (confirm the RIGHT tokens per surface)

```bash
git diff <base> <head> -- apps/**/styles.css \
  | grep -E '^\+' \
  | grep -oE 'var\(--[a-z0-9-]+\)' | sort | uniq -c | sort -rn
```

Then cross-check against the design doc's per-surface rules. A component can be
hex-free and still use the *wrong* tokens. Typical rules:

- Premium/showcase card = parchment tokens (`--paper` bg, `--paper-ink` text)
- Shell/standard cards = walnut (`--ink-1` bg, `1px solid --line`, radius 10px)
- Primary button = brass fill + `--brass-ink` text, radius 6px, hover lightens
- Section labels = display font, uppercase, letter-spacing ~0.16em

## Structural rules to audit (from a typical DESIGN.md)

- **Typography role split:** display font for headings/labels only, body font for
  content. Never paragraph body in the display face; never a panel title in the
  body face.
- **Buttons:** specified fill/text/radius, visible hover state, disabled state.
- **Cards:** specified bg/border/radius/padding.
- **Surface modes:** which surfaces use which material (e.g. parchment is the
  only light surface; don't mix materials on one surface).
- **Motion:** hover feedback on all interactive elements; `prefers-reduced-motion`
  respected; no decorative animation on "still" surfaces.

## Report shape

```
## PASS (nits: ...)   — or —   ## FAIL: <specific issue>

### Design-System Compliance
| # | Check | Result |
|---|-------|--------|
| 1 | No hardcoded hex/rgb/hsl | ✅/❌ + evidence |
| 2 | <surface> uses <material> tokens | ... |
...

### Code Quality
(react hooks / error handling / a11y / null-state / types / typecheck)

### Nits (non-blocking)
1. ...
```

## Pitfall: empty grep ≠ clean

If the diff is piped through a wrapper/formatter that re-indents `+` prefixes
(e.g. to `  +`) and compacts/truncates output, `grep '^\+'` returns nothing and
`grep -c '^+'` returns 0 even on hundreds of added lines — a false "no
violations." Before trusting an empty result, confirm the anchor matches the
actual format (`grep -cE '^\s*\+'`) or read the changed file directly with
`read_file`. See SKILL.md pitfall on diff grep anchors.
