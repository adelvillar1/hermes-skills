---
name: image-to-code
description: "Turn screenshots and mockups into production frontend code."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Frontend, Images, UI, Code]
    related_skills: [claude-design, sketch, popular-web-designs]
---

# Image-to-Code

Convert screenshots, mockups, and visual references into production-ready frontend code with a faithful layout, typography, and component structure.

## When to Use

- A visual reference exists (image, Figma export, screenshot, sketch) and the goal is to reproduce it in code.
- Building a landing page, section, or component from a generated or supplied design.

## Core Directive: Image-First Workflow

Generate design images first, analyze them deeply, then implement. Do not start with freeform coding.

## Image Rules

- Generate one image per section. Do not compress many sections into one unreadable board.
- Do not crop old images; generate fresh standalone images per section.
- Use `image_generate` to create the visual reference, then `vision_analyze` to inspect it.

## Clean Analysis Standard

Inspect every reference for:

- Text hierarchy and exact copy.
- Typography (sizes, weights, line-height, letter-spacing, font pairing).
- Spacing and rhythm.
- Buttons, colors, states.
- Layout structure and alignment.
- Section-to-section variation.

## Design Discipline

- **Hero minimalism:** 1-3 lines max, clean, spacious, readable on small laptops.
- **Anti-nested-box:** avoid cards-in-cards-in-cards and giant rounded wrappers.
- **Reduce micro-UI clutter:** no unnecessary pills, pseudo-system markers, or fake control labels.
- **Section rhythm:** vary density, image-to-text ratio, alignment, scale, and whitespace.
- **Typography-first:** clear size contrast, obvious reading order, strong display moments.
- **Spacing-first:** generous, even, breathable — not cramped or overfilled.
- **Anti-drift:** implemented code must match the generated reference; do not simplify into generic templates.

## Combinatorial Variation Engine

For each build, pick a coherent set of choices:

- Theme paradigm.
- Background character.
- Typography character.
- Hero architecture.
- Section system.
- 4 signature components.
- 2 motion-implied cues.

## Anti-AI-Slop Guardrails

- No default purple/blue gradients.
- No glowing edges or floating blobs.
- No stacked glassmorphism.
- No generic "unleash / elevate / revolutionize" copy.
- Theme and palette should not be guessable from the category alone.

## Workflow

1. Use `image_generate` to produce the design image(s).
2. Use `vision_analyze` to extract structure, typography, color, and spacing.
3. Build the HTML/CSS/JS component or page, matching the reference pixel-by-rhythm.
4. Use `browser_navigate` and `browser_vision` to verify the live output against the reference.
5. Iterate until the implementation matches the source image.

## Verification Checklist

- [ ] One image per section; no cropped composites.
- [ ] Text, typography, and spacing analyzed from the image.
- [ ] Hero is minimal and readable at small laptop sizes.
- [ ] No nested boxes or unnecessary micro-UI elements.
- [ ] Section rhythm varies across the page.
- [ ] Code matches the reference rather than a generic template.
- [ ] No AI-slop visuals or copy.
