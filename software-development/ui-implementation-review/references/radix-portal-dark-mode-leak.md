# Radix portal dark-mode leak — diagnosis & fix

A dark-mode redesign can look perfect on every page yet render **white dialogs, dropdowns, and alerts**. The cause is structural, not cosmetic: Radix UI portals overlay content to `document.body`, which sits *outside* any scoped `.dark` wrapper element.

## Why it happens

shadcn/ui components read color from CSS custom properties: `bg-background` → `hsl(var(--background))`, `bg-primary` → `hsl(var(--primary))`, etc. The dark palette is defined under a selector — either `:root` (whole-app dark) or `.dark` (class-strategy, toggleable).

Radix primitives (`Dialog`, `AlertDialog`, `Select`, `Sheet`, `Drawer`, `Popover`, `Tooltip`, `Command`, `Menubar`, `ContextMenu`, `DropdownMenu`, `HoverCard`) render their floating content through a **Portal** that mounts into `document.body` by default. That node is a sibling of your app root, not a descendant of it.

So if you theme dark by wrapping the console in `<div className="dark">…</div>`:

- Everything *inside* that div reads the `.dark` tokens → dark. ✅
- Every portaled overlay mounts into `<body>`, **outside** the div → it inherits the light `:root` tokens → white dialog on a charcoal console. ❌

The bug is invisible to:
- `tsc` / `next build` / `vite build` (no error)
- static page screenshots (no overlay is open)
- page-level visual review (same reason)

It is only visible when you actually open an overlay.

## Diagnosis

```bash
# 1. Where do the dark tokens live?
grep -n "\.dark\s*{\|:root\s*{" web/src/index.css web/src/app/globals.css

# 2. Which UI components portal to body? (these are the leak surface)
grep -rln "Portal" web/src/components/ui/

# 3. Is `dark` applied to <html>/<body>, or only to a scoped div?
grep -rn 'className="dark\|classList.add("dark")\|<html className' web/src
```

Decision: if the dark token block is under `.dark` AND that class is applied to a wrapper `<div>` (not `<html>`/`<body>`), every component found in step 2 renders LIGHT. That is a 🔴 bug.

Confirm live: open a dialog, a `Select` dropdown, and an `AlertDialog`; screenshot each; verify the overlay background is dark, not white.

## Fix

**Single-theme app (everything dark):** define the dark tokens on `:root`. Then both in-tree content and portaled overlays read the same tokens. You can drop the `dark` class entirely.

```css
/* index.css — before (leaks) */
:root { /* light tokens */ }
.dark { --background: 20 18% 7%; --foreground: 36 48% 94%; /* …dark… */ }

/* after (no leak) */
:root { --background: 20 18% 7%; --foreground: 36 48% 94%; /* …dark… */ }
```

**Toggleable / mixed app (light public site + dark console):** apply the class to `<html>` (or `<body>`), not a wrapper div, so portals — which mount under `<body>` — inherit it.

```tsx
// set per-route, e.g. in the admin layout effect
useEffect(() => {
  document.documentElement.classList.add('dark')
  return () => document.documentElement.classList.remove('dark')
}, [])
```

**Mixed app, can't toggle `<html>`:** define the dark tokens on `:root` globally and let the light surfaces override back to light via their own scoped class — but prefer the `<html>` toggle; it's the least surprising.

## Verification checklist (run on every theming change)

1. Build passes (necessary, not sufficient).
2. Open a `Dialog` → screenshot → dark?
3. Open a `Select` dropdown → screenshot → dark?
4. Open an `AlertDialog` → screenshot → dark?
5. Spot-check a `Popover`/`Tooltip` if the app uses them.
6. Confirm the light surfaces (if any) didn't regress — the `:root` change is global, so re-screenshot the public landing page and any other-theme surface.

## Case record (2026-08-01, the wine-club app)

Dark & immersive admin redesign put brand tokens under `.dark` and added `class="dark"` to the admin root div. 20 static screenshots + a full design review signed off clean. A follow-up pass opened the "New member" dialog, the status-filter `Select`, and the delete `AlertDialog` — all three were white boxes on charcoal. Fix: moved the dark token block to `:root, .dark` and removed the now-redundant `dark` class from the admin root. Re-verified all three overlays dark; member portal (own `.the wine-club app-portal` scope, zero shadcn imports) and public landing (custom-styled, no token classes) confirmed unaffected.
