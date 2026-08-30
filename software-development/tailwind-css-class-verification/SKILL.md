---
name: tailwind-css-class-verification
description: "Verify Tailwind CSS classes exist in the production build before claiming a UI element is done. Catches silently purged arbitrary-value classes."
version: 1.0.0
---

# Tailwind CSS Class Verification

## When to Use

- After writing Tailwind classes that use arbitrary values with CSS variables: `bg-[var(--token)]`, `text-[var(--token)]`, `border-[var(--token)]`
- After adding any new UI element that uses Tailwind classes and the element must be visually visible
- Before claiming a visual feature is "done" when you can't visually verify it yourself
- When a user reports "element is invisible" or "button not showing" on a deployed page

## The Problem

Tailwind's content scanner generates CSS rules for classes it finds in source files. However, **arbitrary-value classes with CSS variables (`bg-[var(--token)]`) can be silently purged** — the class exists in your JSX, the CSS variable exists in `globals.css`, but Tailwind never generates the `.bg-\[var\(--token\)\]` CSS rule in the production bundle. The element renders with no background, no border, no text color — **completely invisible**.

This is NOT caught by:
- `tsc --noEmit` (TypeScript doesn't check CSS)
- `vitest` / `jest` (tests don't render CSS)
- Source-level grep (the class IS in your source — it just never makes it to the bundle)

## Verification Procedure

### Step 1: Check if the CSS variable exists

```bash
grep -e "TOKEN_NAME:" app/globals.css
# e.g., grep -e "--bg-glass:" app/globals.css
```

If 0 matches: the token doesn't exist. Use a real token or a Tailwind built-in color.

### Step 2: Check if the generated CSS rule exists in the built bundle

After `pnpm run build`:

```bash
# For arbitrary-value classes:
python3 -c "
import re
with open('.next/static/css/MAIN_CSS_FILE.css') as f:
    css = f.read()
# Check if the class was generated
pattern = r'\.bg-\\\[var\(--bg-glass\)\]'
if re.search(pattern, css):
    print('✅ Class generated')
else:
    print('❌ Class PURGED — not in bundle')
"

# For pre-defined utility classes:
grep -c "\.bg-glass{" .next/static/css/MAIN_CSS_FILE.css
# If 1: the class exists, safe to use
```

### Step 3: Verify on the deployed bundle (if you can curl staging)

```bash
# Find the CSS file
CSS_URL=$(curl -sS https://staging.example.com/page | grep -oE '/_next/static/css/[^"]*\.css' | head -1)

# Fetch and check
curl -sS "https://staging.example.com${CSS_URL}" > /tmp/deployed.css
grep -c "\.bg-glass{" /tmp/deployed.css
```

## Custom Color Token Key Typos (the `ink2` vs `ink-2` trap)

A second, **distinct** silent-failure mode from arbitrary-value purging: when a custom color is defined in `tailwind.config.ts` with a **hyphenated key**, Tailwind generates utilities with the hyphen, but code that omits the hyphen silently emits nothing.

Example (this repo, 2026-07-08 landing deep dive):
- `tailwind.config.ts` defines `colors: { 'ink-2': '#244254' }` → generates `text-ink-2`, `bg-ink-2`, etc.
- Code uses `text-ink2` (no hyphen) → **no utility class is generated**. The element inherits `color` from its parent (usually the primary `ink` `#0a2230`) instead of the intended `#244254`. No error, no warning, `tsc` clean, page looks "fine" — just slightly higher contrast than designed.

This differs from arbitrary-value purging (where `--token` is undefined): here the token exists, but the **class name doesn't match the key**. It also looks like a real token, so it escapes visual review.

**Detection (whole-repo grep):**
```bash
# List every custom color token key defined in the Tailwind config
grep -oE "'(ink|paper|accent|sage|mute|line|bg)(-[0-9a-z]+)?'" tailwind.config.ts
# For each hyphenated key (e.g. 'ink-2'), grep the app for the no-hyphen variant
grep -rno "text-ink2\b" app/ lib/   # any hit is a bug; correct is text-ink-2
```
Run this whenever you (a) add a new hyphenated custom color, or (b) audit a UI surface for subtle contrast/theme bugs. A single typo typically repeats across many files (this one appeared in ~50 files), so fix it repo-wide in one pass, not per-component.

**Scope check before "fixing":** confirm the class truly generates nothing by grepping the built CSS for `.text-ink2{` — it won't exist. Then replace `ink2` → `ink-2` across the repo. Do NOT hand-edit a few files and assume the rest are fine.

## Rules of Thumb

1. **Prefer pre-defined utility classes** (`.bg-glass`, `.text-white`, `.border-gold`) over arbitrary-value classes (`bg-[var(--bg-glass)]`). They're more likely to be in the bundle.

2. **If you MUST use an arbitrary value**, verify it in the built CSS bundle before claiming the feature is done.

3. **Never trust the source file alone** — the source has the class, but Tailwind's content scanner decides what goes in the bundle. The bundle is the truth.

4. **An undefined CSS variable evaluates to `unset`**, which for `background-color` means **transparent**. The element is in the DOM, correctly positioned, clickable — but invisible. This is the worst kind of bug because structural checks pass.

## Quick Checklist

Before claiming a visual UI element is done:
- [ ] All CSS tokens referenced in `var(--token)` exist in `globals.css`
- [ ] All Tailwind classes (especially arbitrary-value) exist in the built `.next/static/css/*.css` bundle
- [ ] If you can curl staging: the deployed CSS bundle contains the classes
- [ ] If you can't visually verify: explicitly state "I cannot verify the visual outcome — you need to look at it"

## Pitfalls

- **`bg-[var(--bg-glass)]/90` with opacity modifier** — the `/90` suffix makes it even less likely to be generated. Prefer `bg-glass` without opacity, or use an inline `style` attribute if you need exact opacity control.
- **Different CSS files for different routes** — Next.js can split CSS into multiple files. Check the file loaded by the specific page, not just the global one.
- **Cached bundles** — if the CSS hash hasn't changed after a push, the deploy didn't rebuild. Check `last-modified` headers or compare file hashes before verifying against a stale bundle.
- **Custom token key typos (`text-ink2` ≠ `text-ink-2`)** — a hyphenated `colors` key in `tailwind.config.ts` generates hyphenated utilities only. `text-ink2` emits no rule and silently inherits the parent color. Whole-repo grep for the no-hyphen variant; it usually repeats across many files. See "Custom Color Token Key Typos" above.