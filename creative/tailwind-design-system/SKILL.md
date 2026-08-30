---
name: tailwind-design-system
description: "Build scalable design systems with Tailwind CSS v4."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Tailwind, Design-System, CSS, Frontend]
    related_skills: [ui-styling, design-system, design-engineering]
---

# Tailwind Design System

Build scalable design systems with Tailwind CSS v4: CSS-first tokens, OKLCH theming, CVA components, dark mode, and v3-to-v4 migration patterns.

## When to Use

- Starting or maintaining a Tailwind CSS v4 design system.
- Migrating a Tailwind v3 system to v4.
- Building reusable, themeable components in React or similar frameworks.

## Key v4 Changes

- `tailwind.config.ts` → `@theme` in CSS.
- `@tailwind` directives → `@import "tailwindcss"`.
- `darkMode: "class"` → `@custom-variant dark`.
- `theme.extend.colors` → `@theme { --color-*: value; }`.
- `tailwindcss-animate` → CSS `@keyframes` inside `@theme` + `@starting-style`.

## Quick Start

```css
@import "tailwindcss";

@theme {
  --color-primary: oklch(0.55 0.2 250);
  --color-background: oklch(0.98 0.01 100);
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);

  @keyframes fade-in {
    from { opacity: 0; transform: translateY(0.25rem); }
    to { opacity: 1; transform: translateY(0); }
  }
}

@custom-variant dark (&:where(.dark, .dark *));
```

## Token Hierarchy

1. **Brand tokens:** raw brand values.
2. **Semantic tokens:** meaning mapped (background, foreground, danger, success).
3. **Component tokens:** applied to specific components (button-primary-bg).

## Component Architecture

Base → Variants → Sizes → States → Overrides.

Use `cva` (Class Variance Authority) for variant-driven components. In React 19, `forwardRef` is no longer needed.

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md font-medium",
  {
    variants: {
      variant: {
        default: "bg-primary text-white hover:bg-primary/90",
        outline: "border border-input bg-background hover:bg-accent",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3",
        lg: "h-10 px-6",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);
```

## Common Patterns

1. **CVA components:** `buttonVariants`, `asChild` with `Slot`, no `forwardRef` in React 19.
2. **Compound components:** `Card` with `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`.
3. **Form components:** `Input` with `error` prop, `aria-invalid`, `role="alert"`. Label with `cva`. Integrate with React Hook Form + Zod.
4. **Responsive grid:** `gridVariants` with `cols`/`gap` variants, `Container` with size variants.
5. **Native CSS animations:** `@keyframes`, `@starting-style`, `allow-discrete` transitions.
6. **Dark mode:** `ThemeProvider` with `localStorage`, `prefers-color-scheme`, and `theme-color` meta.

## Utilities

- `cn()` helper: `clsx` + `tailwind-merge`.
- `focusRing` utility for consistent focus rings.
- `disabled` utility for disabled states.

## Advanced v4

- `@utility` for custom utilities.
- `@theme inline` to reference other CSS variables.
- `@theme static` to always output tokens.
- Namespace overrides: `--color-*: initial`.
- `color-mix()` for alpha variants.
- Container queries via `@container`.

## v3 → v4 Migration Checklist

1. Replace `@tailwind` directives with `@import "tailwindcss"`.
2. Move `tailwind.config.ts` theme into `@theme` CSS.
3. Convert `darkMode: "class"` to `@custom-variant dark`.
4. Replace `tailwindcss-animate` with `@keyframes` + `@starting-style`.
5. Update color tokens to use `--color-*` namespaces.
6. Replace arbitrary `theme()` calls with CSS custom properties.
7. Audit plugins for v4 compatibility.
8. Update `content` paths if using `@source`.
9. Test dark mode override behavior.
10. Run the full UI test suite and verify no class regressions.

## Verification Checklist

- [ ] `@import "tailwindcss"` present and `@theme` defined.
- [ ] Semantic tokens use OKLCH or consistent color values.
- [ ] Components use `cva` with variant/size/state layers.
- [ ] `cn()` helper uses `clsx` + `tailwind-merge`.
- [ ] Dark mode works via `@custom-variant dark` and `.dark` class.
- [ ] Animations are native CSS, not plugin-dependent.
- [ ] Migration checklist applied when moving from v3.
