---
name: anti-ai-slop
description: "Checklist of what NOT to do in AI-generated design. Covers visual traps (purple gradients, emoji icons, rounded-cards-with-border-left, SVG imagery, data slop) and content traps (fake stats, filler copy). Use as a gate before finalizing any visual design output."
version: 1.1.0
author: Derived from huashu-design (花叔Design) — alchaincyf
license: MIT
metadata:
  hermes:
    tags: [design, quality, review, anti-pattern]
    related_skills: [claude-design, design-review, sketch, architecture-diagram, brand-asset-protocol]
    category: creative
---

# Anti-AI-Slop Checklist

AI-generated design defaults to the "visual greatest common denominator" — purple gradients, rounded cards with left borders, emoji icons, SVG-drawn people. These are slop not because they're inherently ugly, but because they're the AI's default mode and carry zero brand identity.

**The logic chain:**
1. User hires you to design → needs their brand recognized
2. AI default output = average of training data = every brand mixed together = **no brand recognized**
3. So AI default output = diluting the user's brand into "another AI-made page"

## Visual Traps

### ❌ Aggressive gradient backgrounds
- Purple → pink → blue full-screen gradients (classic AI-generated web smell)
- Rainbow gradient in any direction
- Mesh gradient covering entire background
- ✅ If using gradients: subtle, monochromatic, purposeful (e.g., button hover only)

### ❌ Rounded cards with left border accent
```css
/* The signature AI-generated card smell */
.card {
  border-radius: 12px;
  border-left: 4px solid #3b82f6;
  padding: 16px;
}
```
- These cards are everywhere in AI-generated dashboards
- ✅ Better alternatives: background color contrast, font weight/size contrast, plain dividers, or skip the card entirely

### ❌ Emoji as UI icons
Unless the brand uses emoji (Notion, Slack), never put emoji in UI. **Especially not:**
- 🚀 ⚡️ ✨ 🎯 💡 before headings
- ✅ in feature lists
- → in CTA buttons (arrow alone is OK, emoji arrow isn't)

✅ Use real icon libraries (Lucide, Heroicons, Phosphor) or honest placeholders.

### ❌ SVG-drawn imagery
Never use SVG to draw: people, scenes, devices, objects, abstract art. AI-drawn SVG imagery looks cheap and childish. **A gray rectangle with "Illustration slot 1200×800" text is 100x better than a bad SVG hero illustration.**

✅ SVG is OK for:
- Real icons (16×16 to 32×32)
- Geometric decorative elements
- Data visualization charts

### ❌ Excessive iconography
Not every heading / feature / section needs an icon. Overusing icons makes the interface look like a toy. Less is more.

### ❌ "Data slop"
Fabricated stats used as decoration:
- "10,000+ happy customers" (you don't know if this is true)
- "99.9% uptime" (don't write it without real data)
- Icon + number + word "metric cards" as decorative elements
- Mock tables with elaborately decorated fake data

✅ Real data or nothing. Honest gap beats fake fill.

### ❌ Inter/Roboto/Arial/system fonts as display
Too common — viewers can't tell if this is "a designed product" or "a demo page."

✅ Only acceptable if the brand spec explicitly uses these (Stripe uses system fonts but with custom modifications)

### ❌ Cyber neon / dark blue #0D1117
Overused GitHub dark mode aesthetic repurposed everywhere.

✅ Acceptable if it's a developer tool product and the brand actually goes in this direction.

## Content Traps

### ❌ Filler copy
- "Revolutionizing the way you..."  
- "Unlock your potential with..."  
- "Next-generation platform for..."  

✅ Write specific, honest copy. If you don't have real copy, use "[Brief description of feature]" as placeholder.

### ❌ Generic feature names
- "Smart Dashboard" / "Intelligent Analytics" / "AI-Powered Insights"

✅ Use features' actual names from the product's own UI.

### ❌ Testimonials without real sources
- "This product changed my life" — Sarah J.

✅ Skip testimonials entirely if you don't have real ones. Or use honest placeholder: "[Real customer testimonial TBD]"

## Judgment Boundaries

> **"The brand itself uses it"** is the only legitimate reason to break these rules. If the brand spec explicitly uses purple gradients, use purple gradients — it's no longer slop, it's brand signature.

For example:
- Notion uses emoji? ✅ OK for Notion work
- Linear uses purple-blue gradients in some contexts? ✅ OK for Linear work
- Stripe uses Inter as display? ✅ OK with Stripe's custom font modifications

## Motion Anti-Slop (load `design-motion-principles` for the full checklist)

The following AI-slop motion patterns are not covered by the visual traps above but are equally recognizable:

- **Pulsing indicators**: glowing dots, breathing CTAs, throbbing rings — almost always slop
- **Blur-everywhere entrances**: `filter: blur(4px)` on every entering element — slop when 3+ components share the same blur
- **Hover-scale-on-everything**: `transform: scale(1.05)` on every card/button/image — slop when 3+ components share the same scale with no discriminating context
- **Stagger-spam-on-every-list**: staggered entrance on every list/grid — slop when 2+ lists in the same view use stagger
- **Bouncy-springs-on-utility-actions**: `bounce > 0` on dropdowns, menus, toggles, modals — always slop on utility actions
- **Uniform-fade-in**: identical opacity+translateY on every section/card/paragraph — slop when 4+ components share identical enter animations
- **Motion-on-mount-for-static-content**: entrance animations on headings, paragraphs, nav — slop when the only purpose is the entrance itself

For the full audit checklist, motion cookbook, and per-designer perspective weighting, load `read the SKILL.md for '`design-motion-principles`' via your harness's skill loader`.

## Production-Tell Bans (Landing Pages & Marketing Sites)

These signatures come out of real LLM-generated landing-page tests. They are what the model defaults to when it tries to "look designed." Hard bans unless the brief explicitly calls for one. (Derived from taste-skill by Leonxlnx, MIT.)

### ❌ Em-dash as a design element
The single most-violated tell. Banned in headlines, eyebrows, pills, buttons, captions, nav, and body copy. Replace with a period, comma, parentheses, colon, or a hyphen with spaces. Binary rule: zero em-dashes on the page. En-dash as a separator is banned too; ranges use a hyphen (`2018-2026`). The model ignores "use sparingly" phrasing; only a hard zero works.

### ❌ Section-number eyebrows
`00 / INDEX`, `001 · Capabilities`, `06 · how it works`, `05 · The honest table`. Eyebrows name the topic in plain language; they do not enumerate.

### ❌ Numbered pagination on media
`01 / 4` on images or bento tiles. If the user can count, they do not need the label.

### ❌ Scroll cues
`Scroll`, `↓ scroll`, `Scroll to explore`, animated mouse-wheel icons. Users know what scroll is; the viewport bottom needs no label.

### ❌ Locale / city / time / weather strips
`LIS 14:23 · 18°C` in the header, `1200-690 Lisbon, Portugal` in the footer, "Lisbon, working with founders" in the hero. Allowed only for genuinely distributed studios, travel brands, or physical venues. A single contact address in the footer is fine; an atmospheric locale strip is not.

### ❌ Div-based fake product previews
Fake task lists, fake terminals, fake dashboards built from styled `<div>`s in the hero. The #1 LLM-design tell. Use a real screenshot, a generated image, a real component preview, or none at all.

### ❌ Fake version / status footers
`v0.6.2-rc.1`, `Build 0048`, `last sync 4s ago · main` on marketing pages or inside fake screenshots. CLI/devtool fixtures, not landing-page content.

### ❌ Version labels in the hero
`V0.6`, `v2.0`, `BETA`, `INVITE-ONLY PREVIEW`, `EARLY ACCESS` as default eyebrows. Acceptable only when the brief is explicitly about a launch or preview status.

### ❌ Middle-dot chains
The `·` is rationed: max 1 per line in metadata strips. `foo · bar · baz · qux` is the default AI separator. Prefer line breaks, hairlines, or columns.

### ❌ Decorative colored status dots
A colored dot before every nav link, list row, or badge. Acceptable only when it conveys real semantic state (live server status, availability flag) and at most one per section.

### ❌ Decoration text strips
`BRAND. MOTION. SPATIAL.`, `TYPE / FORM / MOTION`, `ESTD. 2018 · LISBON` as a mono-caps strip across the hero bottom. Acceptable only when the strip carries real navigable links or real status info.

### ❌ Floating top-right sub-text in section headings
A giant left-aligned headline with a tiny explainer paragraph floating unaligned in the top-right corner of the section header. Put the sub-text under the headline, or build a clean 2-column header (left: headline, right: aligned body).

### ❌ Label / pill overlays on images
`<span>` overlays on photos like `Brand · 02`, `PLATE · BRAND`, `Field notes - journal`. Let the image speak alone, or add a caption directly below the image.

### ❌ Pretentious photo-credit captions
`Field study no. 12 · Ines Caetano`, `Frame XII · 35mm` under stock or picsum images. Credit is allowed only when a real photographer is credited for a real photo (with permission). Otherwise skip the caption or use a one-line functional caption ("The 6-quart, in Sage.").

### ❌ Hairline-per-row tables
`border-t` + `border-b` on every row of a long list or spec table. Pick one border and use it sparsely. A 10-row spec table with hairlines under each row is the laziest layout.

### ❌ Filled-track progress bars as comparison visuals
Big `bg-zinc-200` tracks with a partial fill for "X out of Y" comparisons. Prefer a number + small icon, or a tiny inline bar without a background track.

### ❌ Generic step labels
`Stage 1 / Stage 2 / Stage 3`, `Step 1 / Step 2 / Step 3`, `Phase 01 / Phase 02 / Phase 03`. The actual step content is the label ("Install", "Configure", "Ship"), not "Stage 1: Install".

### ❌ Poetic section labels
`From the field`, `Field notes`, `Currently on the bench`, `Loose plates` on quote, blog, or sidebar sections. Use plain functional labels ("Testimonials", "Latest writing", "Now working on") or skip the label.

### ❌ Mock-humble industry references
"We respect the French ones"-style body copy. Cute and AI-y.

### ❌ "Quietly in use at" social proof
Use natural language: "Trusted by", "Used at", "Customers include", or skip the heading if the logos speak.

### ❌ Live-stock counters as decoration
`Reservation 412 of 800` unless the brief is explicitly a limited-run waitlist with real data.

### ❌ Micro-meta-sentences under eyebrows
"Each of these is a feature we ship today, not a roadmap promise. The list will stay short on purpose." sitting under a section heading is clutter. Eyebrow + Headline + Body is enough.

### ❌ Vertical rotated text
`INDEX OF WORK, 2018 - 2026` rotated 90°. Agency-portfolio cliché. Only for explicitly agency/experimental briefs where it serves a real composition purpose.

### ❌ Crosshair / hairline grid decoration
Vertical and horizontal lines drawn just to make the page "feel designed." Use them only when they organize real content.

### ❌ `<br>`-broken italicized headlines
`for thirty<br>*years.*` splits as a default design move. Headlines read naturally first, get clever only when the brief demands it.

### ✅ Escape hatch
The brief explicitly calls for the pattern, or the brand itself uses it (see Judgment Boundaries above). The pattern is then brand signature, not slop.

## Executable companions (scripts/)

The checklist above is the judgment half; these vendored gates (plugin87/ux-ui-agent-skills, MIT) are the measurement half — they render the page in headless Chrome and flag tells from computed styles and geometry, catching what static review misses. Usage: `node scripts/<gate>.mjs <file.html...>` from any directory; playwright is installed inside `scripts/`. `lint_hardcodes.py` is stdlib-only.

| Gate | Measures |
|------|----------|
| `slop_tells.mjs <files> [--dark] [--strict]` | Single-radius monotony, flat elevation (one shadow everywhere / the `0 1px 3px rgba(0,0,0,.1)` default), the indigo→violet→blue "default AI gradient", pure `#000` text, opaque black shadows, lorem ipsum left in, flat padding hierarchy, near-duplicate neutrals |
| `taste_audit.mjs <file> [--dark] [--strict]` | Type-scale collapse, uniform blocks, measure (line-length) violations, palette sprawl |
| `lint_hardcodes.py <path>` | Hardcoded hex/px values in source that bypass the token system |

Heuristic, not proof: a LOW finding is a strong signal to look, not an automatic fail — pair with human visual review (the brand-signature escape hatch above still applies).

## When to Apply This Checklist

1. **Self-review gate** — before presenting any visual design output, run through this checklist
2. **Peer review** — when reviewing another agent's visual design output
3. **Design review** — as part of the Philosophy Alignment and Craft Quality dimensions

See also: `design-review` skill for the full 5-dimension critique framework.
See also: `design-motion-principles` skill for motion-specific anti-slop patterns and audit workflow.
