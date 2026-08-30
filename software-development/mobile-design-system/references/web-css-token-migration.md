# Web + CSS Custom-Property Token Migration

Cross-platform token migration when a project has BOTH a vanilla-JS web dashboard (CSS custom properties) and a React Native / Expo mobile app (TypeScript tokens). Use alongside `tokenizing-existing-react-native-app.md`.

## When to use

- Project has a plain HTML/CSS/JS web surface and an Expo mobile surface.
- Both surfaces need the same palette, typography, and spacing.
- No shared build step exists — web is static files, mobile is Metro.

## Token contract shape

Use **two token files** that mirror each other:

| Web | Mobile |
|-----|--------|
| `ui/css/dashboard.css` `:root` block | `mobile/apps/expo-app/src/design/tokens.ts` |
| CSS custom properties (`--bg-deep`) | TypeScript exports (`colors.backgroundDefault`) |

Palette used in this session (ink/steel):

```css
:root {
  --bg-deep: #0b0f17;
  --bg-panel: #121827;
  --bg-surface: #1a2236;
  --bg-hover: #202b42;
  --bg-elevated: #1f2940;
  --text-primary: #f4f6f8;
  --text-secondary: #b8c0cc;
  --text-muted: #7f8aa3;
  --text-faint: #56607a;
  --text-numeric: #e4e8ef;
  --text-inverse: #0b0f17;
  --accent: #6472d6;
  --accent-hover: #7683e8;
  --accent-light: #9aa6f7;
  --border-subtle: rgba(255,255,255,0.04);
  --border-standard: rgba(255,255,255,0.07);
  --border-solid: #232a3d;
  --border-hover: #3a4760;
  --success: #22c786;
  --warning: #f2a20c;
  --danger: #e94e4e;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 12px;
}
```

Also add **semantic alpha tokens** so status backgrounds don't need hardcoded rgba:

```css
  --success-bg: rgba(34,199,134,0.12);
  --warning-bg: rgba(242,162,12,0.12);
  --danger-bg: rgba(233,78,78,0.12);
  --accent-bg: rgba(100,114,214,0.15);
```

## Web migration steps

1. **Rebuild `:root` in `dashboard.css`** with the full token set.
2. **Duplicate the `:root` block** into standalone pages (`index.html`, `login.html`, `register.html`) because they don't load `dashboard.css`.
3. **Replace hardcoded colors in CSS rules** with `var(--token)`.
4. **Replace inline styles in JS view modules** (`ui/js/views/*.js`) with token references:
   - JS template literals: `style="color:var(--text-muted)"`
   - Dynamic color maps: `const edgeColor = gap > 0.05 ? 'var(--success)' : 'var(--danger)'`
5. **Add `font-variant-numeric: tabular-nums`** to all numeric value classes so ratings/probabilities align.

## Mobile migration steps

See `tokenizing-existing-react-native-app.md`. The key point is to keep mobile token names conceptually aligned with CSS tokens:

| CSS | TS |
|-----|-----|
| `--bg-deep` | `colors.backgroundDefault` |
| `--bg-panel` | `colors.backgroundPanel` |
| `--text-muted` | `colors.textMuted` |
| `--text-numeric` | `colors.textNumeric` |
| `--radius-md` | `radius.md` |
| `--space-md` | `space.md` |

## Density rules (apply to both surfaces)

- Cards: 16px padding, 12px gaps.
- Section titles: 15px/600wt with muted inline subtitle.
- Numerics: tabular-nums everywhere.
- No gradients, no decorative heroes, no prose that duplicates visible stats.

## Verification commands

### Web drift check

```bash
grep -rnE "#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})" ui/js ui/css ui/*.html \
  | grep -v "ui/css/dashboard.css" \
  | grep -v "ui/index.html" \
  | grep -v "ui/login.html" \
  | grep -v "ui/register.html" \
  | grep -v "&#" | grep -v "#/team/" | grep -v "#/game/"
# Expect no output
```

### Mobile drift check

```bash
grep -rn "#[0-9a-fA-F]\{3,8\}" mobile/apps/expo-app/src \
  | grep -v "design/tokens.ts"
# Expect no output
```

### Standalone page token consistency

```bash
diff <(sed -n '/:root {/,/}/p' ui/index.html) <(sed -n '/:root {/,/}/p' ui/login.html)
diff <(sed -n '/:root {/,/}/p' ui/index.html) <(sed -n '/:root {/,/}/p' ui/register.html)
```

## Pitfalls

- **Do not change functional behavior during a token migration.** This is a visual refactor only; keep tests green.
- **Standalone pages drift apart quickly.** If the project has many unbundled HTML entry points, eventually extract a shared `ui/css/tokens.css` and load it with `<link>`.
- **JS views that generate inline styles** are the most common source of missed hardcoded colors. Search inside template strings, not just `.css` files.
- **`rgba(...)` inside JS template strings** also counts as hardcoded color. Replace with `var(--token)`.
- **Color fallbacks like `var(--text-inverse, #fff)` defeat the purpose.** Remove the fallback once the token is defined.

## Workaround: when `patch` tool keeps dropping the `path` argument

During large multi-file edits, the `patch` / `read_file` tool calls can silently drop the `path` argument and fail with `path required` or `expected str, bytes or os.PathLike object, not NoneType`. If the same patch region fails more than twice, switch immediately to `execute_code` with `hermes_tools.patch` / `hermes_tools.read_file`, or use `terminal` with a small Python script. This avoids a stuck tool loop and keeps the migration moving.

Example fallback:

```python
from hermes_tools import patch
patch('/path/to/file', 'old_string', 'new_string')
```

Or with plain Python + pathlib for complex regex replacements:

```python
from pathlib import Path
p = Path('ui/css/dashboard.css')
text = p.read_text()
text = text.replace('rgba(16,185,129,0.12)', 'var(--success-bg)')
p.write_text(text)
```

## When to stop

- Web: only token definitions and sport-tint blocks contain literal hex/rgba.
- Mobile: only `tokens.ts` contains literal hex.
- All tests pass (`pytest`, `pnpm test`, `tsc --noEmit`).
- Contract docs (`TECHNICAL-DOCUMENTATION.md`, `FUNCTIONAL-SPECIFICATIONS.md`) mention the token contract and density rules.
