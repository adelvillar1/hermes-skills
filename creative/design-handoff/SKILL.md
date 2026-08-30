---
name: design-handoff
description: Generate developer handoff specs from designs.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags:
      - Design
      - Handoff
      - Specs
      - Documentation
---

# Design Handoff

Generate clear, implementation-ready developer handoff specs from a design.

## When to use

Use when asked to:

- "create a handoff spec"
- "document this design"
- "write dev specs for a design"
- "prepare a design for developers"

## What to include

- **Visual specs**: exact measurements, design token references, responsive breakpoints, component variants.
- **Interaction specs**: click/tap, hover, active, focus, transitions, gestures.
- **Content specs**: character limits, truncation, empty/loading/error states.
- **Edge cases**: minimum/maximum content, international text, slow connections, missing data.
- **Accessibility**: focus order, ARIA labels, keyboard interactions, screen reader behavior.

## Principles

- Do not assume anything; specify everything a developer needs.
- Use tokens, not raw values: `spacing-md` instead of `16px`.
- Show all states: default, hover, active, disabled, loading, error, empty.
- Explain the reasoning behind decisions when useful.

## Output format

Use Markdown with these sections:

1. **Overview**: purpose, scope, and context.
2. **Layout**: structure, spacing, alignment, measurements.
3. **Design Tokens Used** (table): token names and values.
4. **Components** (table): name, role, props, notes.
5. **States and Interactions** (table): state, trigger, visual change, animation.
6. **Responsive Behavior** (table): breakpoint, layout change, notes.
7. **Edge Cases**: content limits, empty/error states, loading, missing data.
8. **Animation / Motion** (table): property, duration, easing, reduced-motion fallback.
9. **Accessibility Notes**: focus order, ARIA, keyboard, screen reader.

## Notes

- Keep tables scannable; avoid walls of text.
- Include tokens only when the design has an explicit token system.
- If a design is missing information, flag it rather than guess.