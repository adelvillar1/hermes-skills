# Tokenizing an Existing React Native / Expo App — Field Notes

Practical patterns for migrating a React Native app with hardcoded colors to a centralized token file. Complements `mobile-design-system` by focusing on the retrofit path, not greenfield scaffolding.

## When to use

- App already has screens with inline `backgroundColor: '#fff'`, `color: '#6b7280'`, etc.
- You want a single `tokens.ts` (or `theme.js`) file without a full component-library refactor.
- You need the migration to be safe under TypeScript + Expo path aliases (`@/design/tokens`).

## Token file shape

Create one file under the design-system path. The screens from this session used:

```ts
// src/design/tokens.ts
export const colors = {
  backgroundDefault: '#0b0f17',
  backgroundPanel: '#121827',
  backgroundSubtle: '#1a2236',
  backgroundElevated: '#1f2940',
  textPrimary: '#f4f6f8',
  textSecondary: '#b8c0cc',
  textMuted: '#7f8aa3',
  textFaint: '#56607a',
  textNumeric: '#e4e8ef',
  textInverse: '#ffffff',
  accent: '#6472d6',
  accentHover: '#7683e8',
  success: '#22c786',
  warning: '#f2a20c',
  danger: '#e94e4e',
  borderStandard: 'rgba(255,255,255,0.07)',
  borderSubtle: 'rgba(255,255,255,0.04)',
};

export const space = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 };
export const radius = { sm: 4, md: 8, lg: 12 };
export const type = {
  size: { xs: 10, sm: 12, md: 16, lg: 24, xl: 32 },
  weight: { regular: '400', medium: '500', semibold: '600', bold: '700' },
};
```

Key decisions:
- Export as a namespace (`import * as Tokens from '@/design/tokens'`) so migration diffs are mechanical and search/replace-safe.
- Keep the object structure flat and grouped by CSS-concept (`colors`, `space`, `type`, `radius`). Deep nesting makes inline StyleSheet refs noisy.
- Use `textInverse` instead of `white` so dark/light theme flips are one-line changes later.

## Import convention

Use `import * as Tokens from '@/design/tokens';` at the top of every screen. Avoid default exports for the token object — tree-shaking is irrelevant here, but namespaced imports read clearly inside `StyleSheet.create`.

## Migration order

1. Create `tokens.ts` with the full palette.
2. Migrate the **highest-traffic screens first** — the ones users see every session. In this project that was `TodayFeed`, `ScheduleBrowse`, `TeamRatings`, `Favorites`, `AuthLogin`.
3. Run a hardcoded-color grep after every 2-3 screens to catch regressions early.
4. Leave `textInverse` for button text, badge text, or anything that sits on an accent/success/danger background. Do not use `textPrimary` on top of `accent`.

## Common inline-style categories to replace

- `backgroundColor: '#fff'` → `Tokens.colors.backgroundDefault` (or `backgroundPanel` for cards)
- `color: '#6b7280'`, `'#9ca3af'` → `Tokens.colors.textMuted`
- `color: '#374151'` → `Tokens.colors.backgroundElevated` (if used as a muted background)
- `borderColor: '#e5e7eb'` → `Tokens.colors.borderSubtle`
- `fontSize: 24`/`28` → `Tokens.type.size.lg`
- `fontWeight: '700'` → `Tokens.type.weight.bold`
- `padding: 24` → `Tokens.space.md`
- `borderRadius: 8` → `Tokens.radius.md`

## TypeScript gotchas

- If you have a `fontVariant: ['tabular-nums']` style, it is still valid under `TextStyle`; keep it for numeric tables.
- Path alias `@/design/tokens` must be resolvable by Metro / Expo. Verify the file exists and `tsconfig.json` maps `@/*` to `src/*`.

## Verification commands

Run from the mobile app source directory:

```bash
# Hardcoded hex colors outside the token file
find src/screens src/design -type f \( -name '*.tsx' -o -name '*.ts' \) \
  -exec grep -Hn 'backgroundColor.*#\|color.*#\|borderColor.*#\|borderBottomColor.*#' {} +

# Should only print token.ts definitions. If screens still appear, keep migrating.
```

Optional tighter check after migration:

```bash
grep -rn "#[0-9a-fA-F]\{3,8\}" src/screens src/components src/design
# Expect output only from src/design/tokens.ts
```

## Pitfalls

- **Do not replace `#fff` used for text on colored buttons with `textPrimary`.** If the button background is `accent`, use `textInverse` — otherwise the color is not semantic and will break in a light theme.
- **Placeholder text color** (`placeholderTextColor`) is also a token; don't leave it hardcoded.
- **`StyleSheet.create` accepts variables** — you don't need to switch to `useTheme` hooks. The migration is a direct value swap.
- **Don't rename token keys mid-migration.** Stability of names (`md`, `lg`, `textMuted`) is more important than perfect semantics; finish the migration first, then rename if necessary.
- **One token file is enough for a small app.** Don't split into `colors.ts`, `spacing.ts`, `typography.ts` until the token surface exceeds ~150 lines or multiple platforms consume it.

## When to stop

When:
- `grep` shows no hardcoded colors in screens/components
- `tokens.ts` is the only file with hex literals
- Tests (vitest / jest / tsc) still pass
- The app renders without obvious contrast regressions in Expo web or Simulator

Stop. Further polish (custom fonts, shared `<Card>` component, dark/light toggle) belongs in a follow-up session.
