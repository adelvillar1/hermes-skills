---
name: ui-ux-pro-max
version: 0.1.0
author: Hermes
description: "Searchable UI/UX design intelligence: styles, colors, fonts, UX rules."
metadata:
  hermes.tags:
    - UI
    - UX
    - Design
    - Accessibility
    - Design-System
---

# UI/UX Pro Max — Design Intelligence Engine

A searchable local database with 50+ styles, 161 color palettes, 57 font pairings, 161 product types, 99 UX guidelines, 25 chart types, and 13 stack-specific guides. Python stdlib only — no dependencies, no network. The data lives in a cloned repo at `~/.hermes/skills/creative/ui-ux-pro-max-repo/` and is queried via `search.py`.

## When to Use

- Designing new pages or components and need style/color/font recommendations
- Reviewing UI for UX issues, accessibility, or visual consistency
- Choosing a color palette or typography system for a product type
- Getting stack-specific best practices (React, Next.js, Vue, Svelte, SwiftUI, Flutter, etc.)
- Pre-delivery QA gate: run the 10-category UX checklist before shipping UI
- Building dashboards and need chart type recommendations
- "UI looks not professional enough" but the reason is unclear — search `--domain ux`

## Prerequisites

Python 3 (stdlib only — no pip installs, no network). Verify:

Invoke through the `terminal` tool:
```bash
python3 --version
```

The search engine lives at:
```
~/.hermes/skills/creative/ui-ux-pro-max-repo/.claude/skills/ui-ux-pro-max/scripts/search.py
```

The CSV data lives at:
```
~/.hermes/skills/creative/ui-ux-pro-max-repo/.claude/skills/ui-ux-pro-max/data/
```

## How to Run

All commands invoke through the `terminal` tool. Set the base path:

```bash
SEARCH=~/.hermes/skills/creative/ui-ux-pro-max-repo/.claude/skills/ui-ux-pro-max/scripts/search.py
```

### Generate a complete design system (REQUIRED first step)

```bash
python3 $SEARCH "<product_type> <industry> <keywords>" --design-system [-p "Project Name"]
```

This searches all domains in parallel, applies reasoning rules, and returns: pattern, style, colors, typography, effects, anti-patterns, and a pre-delivery checklist.

### Add design dials (optional)

Three 1-10 sliders that tune the output:

```bash
python3 $SEARCH "<query>" --design-system --variance <1-10> --motion <1-10> --density <1-10> [-p "Project"]
```

| Dial | Low (1-3) | Mid (4-7) | High (8-10) |
|------|-----------|-----------|-------------|
| `--variance` | Minimal/balanced | Modern | Bold/brutalist/bento |
| `--motion` | Subtle micro-interactions | Standard scroll/stagger | Complex choreography |
| `--density` | Spacious (24-96px) | Standard (16-64px) | Dense/dashboard (8-32px) |

### Domain-specific search

```bash
python3 $SEARCH "<keyword>" --domain <domain> [-n <max_results>]
```

### Stack-specific best practices

```bash
python3 $SEARCH "<keyword>" --stack <stack>
```

### Persist design system (Master + page overrides)

```bash
python3 $SEARCH "<query>" --design-system --persist -p "Project Name" [--page "dashboard"]
```

Creates `design-system/MASTER.md` (global) and optionally `design-system/pages/<page>.md` (page-specific overrides).

## Quick Reference

### Available Domains

| Domain | Use For | Example Keywords |
|--------|---------|------------------|
| `product` | Product type recommendations | SaaS, e-commerce, healthcare, beauty |
| `style` | UI styles + effects | glassmorphism, minimalism, dark mode |
| `typography` | Font pairings + Google Fonts | elegant, playful, professional |
| `color` | Color palettes by product type | saas, ecommerce, fintech, beauty |
| `landing` | Page structure + CTA strategies | hero, testimonial, pricing, social-proof |
| `chart` | Chart types + library recs | trend, comparison, timeline, funnel |
| `ux` | Best practices + anti-patterns | animation, accessibility, z-index |
| `gsap` | GSAP animation skeletons | scroll reveal, stagger, magnetic cursor |
| `google-fonts` | Individual Google Fonts | sans serif, monospace, variable |
| `react` | React/Next.js performance | waterfall, bundle, suspense, memo |
| `web` | App interface (iOS/Android/RN) | accessibilityLabel, touch, safe-areas |
| `prompt` | AI prompts + CSS keywords | (style name) |

### Available Stacks

`react` · `nextjs` · `vue` · `nuxtjs` · `nuxt-ui` · `svelte` · `astro` · `shadcn` · `html-tailwind` · `angular` · `laravel` · `swiftui` · `flutter` · `react-native` · `jetpack-compose` · `threejs`

### UX Rule Priority (1 = check first)

| Priority | Category | Impact | Key Checks |
|----------|----------|--------|------------|
| 1 | Accessibility | CRITICAL | Contrast 4.5:1, alt text, keyboard nav, aria-labels |
| 2 | Touch and Interaction | CRITICAL | Min 44x44px, 8px spacing, loading feedback |
| 3 | Performance | HIGH | WebP/AVIF, lazy load, CLS < 0.1 |
| 4 | Style Selection | HIGH | Match product type, SVG icons (no emoji) |
| 5 | Layout and Responsive | HIGH | Mobile-first breakpoints, no horizontal scroll |
| 6 | Typography and Color | MEDIUM | Base 16px, line-height 1.5, semantic color tokens |
| 7 | Animation | MEDIUM | 150-300ms, motion conveys meaning, reduced-motion |
| 8 | Forms and Feedback | MEDIUM | Visible labels, error near field, helper text |
| 9 | Navigation | HIGH | Predictable back, bottom nav <=5, deep linking |
| 10 | Charts and Data | LOW | Legends, tooltips, accessible colors |

### Output Formats

```bash
# ASCII box (default) — terminal display
python3 $SEARCH "<query>" --design-system

# Markdown — documentation
python3 $SEARCH "<query>" --design-system -f markdown
```

## Procedure

### 1. New project / page design

```bash
# Step 1: Generate design system
python3 $SEARCH "beauty spa wellness service" --design-system -p "Serenity Spa"

# Step 2: Deep-dive specific domains
python3 $SEARCH "glassmorphism dark" --domain style
python3 $SEARCH "playful modern" --domain typography
python3 $SEARCH "animation accessibility" --domain ux

# Step 3: Stack-specific guidance
python3 $SEARCH "list performance navigation" --stack nextjs
```

### 2. Review existing UI

```bash
# UX validation pass before implementation
python3 $SEARCH "animation accessibility z-index loading" --domain ux

# Check chart best practices
python3 $SEARCH "real-time dashboard" --domain chart
```

### 3. Pre-delivery checklist

Before delivering UI code, verify through `search.py`:

```bash
python3 $SEARCH "accessibility contrast touch" --domain ux -n 10
python3 $SEARCH "animation loading states" --domain ux -n 5
```

Then manually verify:
- [ ] No emojis as icons (use SVG: Heroicons, Lucide)
- [ ] All icons from consistent icon family and style
- [ ] Touch targets >=44x44pt (iOS) / >=48x48dp (Android)
- [ ] Micro-interaction timing 150-300ms
- [ ] Primary text contrast >=4.5:1 in both light and dark mode
- [ ] Dividers/borders distinguishable in both themes
- [ ] Modal scrim 40-60% black opacity
- [ ] Safe areas respected for headers, tab bars, CTA bars
- [ ] Scroll content not hidden behind fixed/sticky bars
- [ ] Tested on 375px (small phone) and landscape
- [ ] Verified with reduced-motion enabled and Dynamic Type at largest size
- [ ] All meaningful images have accessibility labels
- [ ] Color is not the only indicator (add icon/text)

### 4. Dashboard / data viz

```bash
python3 $SEARCH "analytics dashboard" --design-system --density 8 -p "Analytics"
python3 $SEARCH "trend comparison" --domain chart
```

## Pitfalls

- **The search is keyword-based, not semantic** — use multi-dimensional keywords like `"entertainment social vibrant content-dense"` not just `"app"`.
- **`--design-system` is the starting point** — always run it first, then supplement with `--domain` searches. Don't jump straight to domain search.
- **Data density** — the CSVs have 161 product types, 99 UX rules, 57 font pairings. The BM25 search returns ranked results; use `-n` to control how many.
- **The repo also contains 6 other skills** (design-system, design, ui-styling, brand, banner-design, slides) at `~/.hermes/skills/creative/ui-ux-pro-max-repo/.claude/skills/`. They have their own scripts for logo generation, CIP mockups, token generation, and slide creation — but those require Gemini API keys and npm dependencies. The core `search.py` engine is pure stdlib.
- **Windows**: use `python` instead of `python3`.

## Verification

```bash
python3 ~/.hermes/skills/creative/ui-ux-pro-max-repo/.claude/skills/ui-ux-pro-max/scripts/search.py "SaaS dashboard" --design-system -p "Test Project"
```

Should output an ASCII-formatted design system with pattern, style, colors, typography, effects, anti-patterns, and a pre-delivery checklist.