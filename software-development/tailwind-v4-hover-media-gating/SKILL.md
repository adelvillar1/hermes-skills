---
name: tailwind-v4-hover-media-gating
description: "Use when gating Tailwind v4 hover behind media queries."
---

# Tailwind v4 hover-media gating

## When to use
When you want every `hover:` utility to apply only on hover-capable devices (no stuck hover states on touch) in a Tailwind CSS **v4** project, via a single site-wide gate.

## The trap (proven 2026-08-12, synapticweb)

`@custom-variant hover (@media (hover: hover) and (pointer: fine));` **silently breaks the site**:

1. It drops the `:hover` pseudo-class — compiled output is `@media (hover:hover) and (pointer:fine){.hover\:x{...}}`, so every hover style applies **permanently** on desktop. Hover states die as states.
2. It silently drops `group-hover` utilities from the build (count 0 in the emitted CSS), because v4 derives `group-hover` from the `hover` variant.

No build error, no warning — only inspecting the built CSS catches it. Static screenshots look ~normal (cards render slightly "hovered"), so visual smoke misses it too.

## The fix — block form with nested selector + @slot

```css
@custom-variant hover {
  @media (hover: hover) and (pointer: fine) {
    &:hover {
      @slot;
    }
  }
}

@custom-variant group-hover {
  @media (hover: hover) and (pointer: fine) {
    &:is(:where(.group):hover *) {
      @slot;
    }
  }
}
```

The single-line paren form with a nested block (`@custom-variant hover (@media ... { &:hover { @slot; } });`) is ALSO broken — it emits `@slot;` literally ("Unknown at rule: @slot" Turbopack warning) and drops the utilities. Only the block form works.

## Verification (mandatory — grep the BUILT css, not the source)

```bash
CSS=$(ls -t .next/static/chunks/*.css | head -1)
grep -o ':hover' "$CSS" | wc -l          # expect > 0 (14 for a small site)
grep -c 'group-hover' "$CSS"              # expect >= number of group-hover: utilities used
grep -o '@media (hover:hover) and (pointer:fine){[^{]*:hover{' "$CSS" | head -1
# expect: @media (hover:hover) and (pointer:fine){.hover\:border-white\/15:hover{
```

Correct shape: the media query wraps a selector that STILL contains `:hover`.

## Note on variant stacking

`group-hover:opacity-100` re-defined as above keeps the group reference (`:where(.group):hover *`). If a project also uses `group-hover:` with other pseudo-classes (e.g. `group-focus`), those need their own custom variants — they are separate built-ins.

## Sibling trap: docs/markdown pollute the utility bundle

Tailwind v4 automatic content detection scans **all text files in the project** — including `docs/**/*.md`. A plan or recap that quotes class strings (e.g. `hover:shadow-[0_0_40px_-12px_rgba(...)]`, `transition-all`) gets those utilities generated into the production CSS even though no markup uses them. Symptom: `grep -rn "some-class" src/` is clean but the built CSS still contains it. Exclude docs explicitly (v4.1+):

```css
@source not "../../docs";   /* path relative to the CSS file holding the @import */
```

Also watch for scratch dirs created by reviewers/tests (e.g. `tmp-review/` fixtures with old markup) — they get scanned too.
