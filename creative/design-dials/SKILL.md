---
name: design-dials
description: "Set design direction before UI: brief, dials, foundation."
version: 1.0.0
author: Derived from taste-skill (Leonxlnx, MIT)
license: MIT
metadata:
  hermes:
    tags: [design, workflow, frontend, dials, landing-page]
    related_skills: [anti-ai-slop, impeccable, popular-web-designs, design-review, design-motion-principles]
    category: creative
---

# Design Dials

Most LLM design output is bad because the model jumps to a default aesthetic instead of reading the room. This skill forces a read, a direction, and a foundation before any code. Run it before building a landing page, portfolio, marketing site, or redesign.

## When to Use

- Starting a landing page, portfolio, marketing site, or redesign.
- Any frontend build where the aesthetic direction is ambiguous.
- Before running `anti-ai-slop`, `impeccable`, or `design-review` audits.

## Step 1: Read the Brief

Before touching code, infer what the user actually wants.

### Signals to read
1. **Page kind**: landing (SaaS / consumer / agency / event), portfolio (dev / designer / creative studio), redesign (preserve vs overhaul), editorial / blog.
2. **Vibe words**: "minimalist", "calm", "Linear-style", "Awwwards", "brutalist", "premium consumer", "Apple-y", "playful", "serious B2B", "editorial", "agency-y", "glassy", "dark tech".
3. **Reference signals**: URLs linked, screenshots pasted, products named, brands being competed with.
4. **Audience**: B2B procurement panel vs design-conscious consumer vs recruiter scanning a portfolio. The audience picks the aesthetic, not your taste.
5. **Existing brand assets**: logo, color, type, photography. For redesigns these are starting material, not optional input.
6. **Quiet constraints**: accessibility-first audiences, public-sector, regulated industries, trust-first commerce, kids' products. These OVERRIDE aesthetic preference.

### Declare a one-line Design Read
State in one line: **"Reading this as: <page kind> for <audience>, with a <vibe> language, leaning toward <design system or aesthetic family>."**

Examples:
- "Reading this as: B2B SaaS landing for technical buyers, with a Linear-style minimalist language, leaning toward Tailwind utilities + Geist + restrained motion."
- "Reading this as: solo designer portfolio for hiring managers, with an editorial / kinetic-type language, leaning toward native CSS + scroll-driven animation + custom typography."
- "Reading this as: redesign of a public-sector service site, with a trust-first language, leaning toward GOV.UK Frontend or USWDS."

### Clarify once, then proceed
Ask exactly ONE clarifying question (never a multi-question dump) and only when the design read genuinely diverges: "Should this feel closer to Linear-clean or Awwwards-experimental?" If you can confidently infer, do not ask. Declare the design read and proceed.

### Anti-Default Discipline
Do not default to: AI-purple gradients, centered hero over dark mesh, three equal feature cards, generic glassmorphism on everything, infinite-loop micro-animations everywhere, Inter + slate-900. Reach past them deliberately based on the design read.

## Step 2: Set the Three Dials

After the design read, set three dials. Every layout, motion, and density decision is gated by these:

- **`DESIGN_VARIANCE: 8`** — 1 = Perfect Symmetry, 10 = Artsy Chaos
- **`MOTION_INTENSITY: 6`** — 1 = Static, 10 = Cinematic / Physics
- **`VISUAL_DENSITY: 4`** — 1 = Art Gallery / Airy, 10 = Cockpit / Packed Data

Baseline: `8 / 6 / 4`. Use these unless the design read overrides them. Overrides happen conversationally; never ask the user to edit a file.

### Dial Inference (design read → dial values)
| Signal | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| "minimalist / clean / calm / editorial / Linear-style" | 5-6 | 3-4 | 2-3 |
| "premium consumer / Apple-y / luxury / brand" | 7-8 | 5-7 | 3-4 |
| "playful / wild / Dribbble / Awwwards / experimental / agency" | 9-10 | 8-10 | 3-4 |
| "landing page / portfolio / marketing site (default)" | 7-9 | 6-8 | 3-5 |
| "trust-first / public-sector / regulated / accessibility-critical" | 3-4 | 2-3 | 4-5 |
| "redesign - preserve" | match existing | +1 | match existing |
| "redesign - overhaul" | +2 | +2 | match existing |

### Use-Case Presets
| Use case | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| Landing (SaaS, mainstream) | 7 | 6 | 4 |
| Landing (Agency / creative) | 9 | 8 | 3 |
| Landing (Premium consumer) | 7 | 6 | 3 |
| Portfolio (Designer / studio) | 8 | 7 | 3 |
| Portfolio (Developer) | 6 | 5 | 4 |
| Editorial / Blog | 6 | 4 | 3 |
| Public-sector service | 3 | 2 | 5 |
| Redesign - preserve | match | match+1 | match |
| Redesign - overhaul | +2 | +2 | match |

Treat the dial values as global variables for the whole build. Keep the exact names `DESIGN_VARIANCE` / `MOTION_INTENSITY` / `VISUAL_DENSITY`; never invent aliases.

## Step 3: Pick the Foundation

### When the brief maps to a real design system (use official packages)
| Brief reads as... | Reach for | Why |
|---|---|---|
| Microsoft / enterprise SaaS / dashboards | `@fluentui/react-components` or `@fluentui/web-components` | Official Fluent UI, Microsoft tokens, accessibility done |
| Google-ish UI, Material-flavored product | `@material/web` + Material 3 tokens | Official, theme-able via Material Theming |
| IBM-style B2B / enterprise analytics | `@carbon/react` + `@carbon/styles` | Official Carbon, mature data-density patterns |
| Shopify app surfaces | Polaris React / polaris.js web components | Required for Shopify admin UI |
| Atlassian / Jira-style product | `@atlaskit/*` + `@atlaskit/tokens` | Official Atlassian DS |
| GitHub-style devtool / community page | `@primer/css` or `@primer/react-brand` | Official Primer; Brand variant for marketing |
| Public-sector UK service | `govuk-frontend` | Legally / regulatorily expected |
| US public-sector / trust-first | `uswds` | Same |
| Fast local-business / agency MVP | Bootstrap 5.3 | Boring, fast, works |
| Modern accessible React foundation | `@radix-ui/themes` | Primitives + polished theme |
| Modern SaaS where you own the components | shadcn/ui (`npx shadcn@latest add ...`) | You own the code, easy to customise; never ship default state |
| Tailwind-based modern SaaS / AI marketing | Tailwind v4 utilities + `dark:` variant | Default for indie + small team builds |

**Honesty rule:** if the brief reads as one of these systems, install and use the official package. Do not recreate its CSS by hand. Do not import a system's tokens then override 90% of them. **One system per project**; do not mix Fluent React with Carbon in the same tree.

### When the brief is an aesthetic, not a system
No single official package exists. Build with native CSS + Tailwind + a maintained component library. Be honest in comments about borrowed inspiration vs official material.

| Aesthetic | Honest implementation |
|---|---|
| Glassmorphism / "frosted glass" | `backdrop-filter`, layered borders, highlight overlays. Solid-fill fallback for `prefers-reduced-transparency`. |
| Bento (Apple-style tile grids) | CSS Grid with mixed cell sizes. No library owns this. |
| Brutalism | Native CSS, monospace, raw borders. No library. |
| Editorial / magazine | Serif type, asymmetric grid, generous whitespace. No library. |
| Dark tech / hacker | Mono + accent neon, terminal motifs. No library. |
| Aurora / mesh gradients | SVG or layered radial gradients. No library. |
| Kinetic typography | Native CSS animations, scroll-driven animations, GSAP for hijacks. No library. |
| Apple Liquid Glass | Apple documents this for Apple platforms only. There is no official `liquid-glass.css`. Web implementations are approximations using `backdrop-filter` + layered borders + highlights. Label clearly as approximation. |

## Sequence

1. Read the brief and list the six signal groups.
2. Declare the Design Read in one line.
3. Set `DESIGN_VARIANCE` / `MOTION_INTENSITY` / `VISUAL_DENSITY`.
4. Pick the foundation from the map.
5. Build. Then run `anti-ai-slop` and `impeccable` as gates before presenting.

## Verification

- [ ] A one-line Design Read was declared before code.
- [ ] Dial values are explicit and consistent with the brief language.
- [ ] One foundation chosen; official package used when one exists.
- [ ] No LLM-default aesthetic (purple gradient, centered hero, 3 equal cards) shipped.
