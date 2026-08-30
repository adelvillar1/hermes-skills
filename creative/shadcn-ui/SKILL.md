---
name: shadcn-ui
description: Add, search, fix, and compose shadcn/ui components.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [UI, React, Components, Tailwind]
---

# shadcn/ui

Add, search, fix, debug, and compose shadcn/ui components using the project's own package runner.

## Get project context

Run the shadcn CLI through `terminal` to read project config:

```bash
npx shadcn@latest info --json
```

Key fields: `aliases`, `isRSC`, `tailwindVersion`, `tailwindCssFile`, `style`, `base`, `iconLibrary`, `resolvedPaths`, `framework`, `packageManager`, `preset`.

Open a component's docs with:

```bash
npx shadcn@latest docs <component>
```

## Principles

- Search existing components first with `npx shadcn@latest search`.
- Compose, don't reinvent: a Settings page is Tabs + Card + form controls.
- Use built-in variants before writing custom styles.
- Use semantic tokens (`bg-primary`, `text-muted-foreground`) and never raw color values.

## Critical rules

### Styling
- Use `className` for layout, not styling.
- No `space-x`/`space-y`; use `gap`.
- Use `size-*` for equal width and height.
- Use `truncate` shorthand.
- No manual `dark:` color overrides; rely on semantic tokens.
- Use `cn()` for conditional classes.
- No manual `z-index` on overlays.

### Forms
- Use `FieldGroup` + `Field`, never a raw `div` with `space-y`.
- Use `InputGroup` with `InputGroupInput`/`InputGroupTextarea`.
- Buttons inside inputs belong in `InputGroup` + `InputGroupAddon`.
- Use `ToggleGroup` for 2-7 choices.
- Group related fields with `FieldSet` + `FieldLegend`.
- Mark `data-invalid` on `Field` and `aria-invalid` on the control.

### Composition
- Place items inside their Group (`SelectItem` inside `SelectGroup`, etc.).
- Use `asChild`/`render` for custom triggers.
- `Dialog`, `Sheet`, and `Drawer` always need a `Title` (sr-only if hidden).
- Compose full `Card` structure.
- `Button` has no `isPending`; compose with `Spinner` + `disabled`.
- `TabsTrigger` must be inside `TabsList`.
- `Avatar` always needs `AvatarFallback`.

### Prefer components over custom markup
- `Alert` for callouts, `Empty` for empty states, `sonner` for toasts, `Separator` instead of `hr`, `Skeleton` for loading, `Badge` instead of custom spans.

### Icons
- Add `data-icon` on icons inside `Button`.
- Do not add sizing classes to icons inside components.
- Pass icons as objects, not string keys.

### CLI
- Never decode preset codes manually. Use `npx shadcn@latest preset decode/url/open/resolve`.

## Component selection

- Inputs: `Input`, `Select`, `Combobox`, `Switch`, `Checkbox`, `RadioGroup`, `Textarea`, `InputOTP`, `Slider`.
- Selection: `ToggleGroup`.
- Data display: `Table`, `Card`, `Badge`, `Avatar`.
- Navigation: `Sidebar`, `NavigationMenu`, `Breadcrumb`, `Tabs`, `Pagination`.
- Overlays: `Dialog`, `Sheet`, `Drawer`, `AlertDialog`.
- Feedback: `sonner`, `Alert`, `Progress`, `Skeleton`, `Spinner`.
- Utilities: `Command`, `Chart`, `Empty`, `Tooltip`, `Menubar`.
