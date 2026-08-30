---
name: brand-asset-protocol
description: "Find, extract, and use real brand assets (logos, colors, fonts, product images, UI screenshots) for design work. 5-step pipeline: ask → search official channels → download with fallbacks → verify → write brand-spec.md. Assets > specs: logo > product images > UI screenshots > colors > fonts."
version: 1.0.0
author: Derived from huashu-design (花叔Design) — alchaincyf
license: MIT
metadata:
  hermes:
    tags: [design, brand, assets, prototyping, visual-identity]
    related_skills: [claude-design, architecture-diagram, sketch]
    category: creative
    requires_toolsets: [terminal, browser, web]
---

# Brand Asset Protocol

When designing for a specific brand (product, company, or client), use this 5-step pipeline to ground your work in real brand identity. **Assets > specs** — a logo or product photo carries more brand recognition than any color palette.

## Core Philosophy

The essence of a brand is **being recognized**. Recognition comes from (in priority order):

| Asset Type | Recognition | When Required |
|-----------|-------------|---------------|
| **Logo** | Highest — instant brand ID | **Every brand, always** |
| **Product images / renders** | Very high — the "star" of physical products | **Hardware products required** |
| **UI screenshots** | Very high — the "star" of digital products | **Apps/SaaS required** |
| **Colors** | Medium — helps but often collides with other brands | Supplementary |
| **Fonts** | Low — needs the above to establish recognition | Supplementary |
| **Tone keywords** | Lowest — agent self-check only | Supplementary |

**Translation to execution rules:**
- Extracting only colors + fonts without finding logo/product images/UI → **violates this protocol**
- Using CSS silhouettes / SVG hand-drawn instead of real product images → **violates this protocol**
- If assets can't be found and you don't tell the user, or AI-generate without reference → **violates this protocol**
- Better to pause and ask the user for assets than to fill with generic placeholders

## 5-Step Pipeline

### Step 1 · Ask (one-shot asset inventory)

Don't just ask "do you have brand guidelines?" — be specific:

```
About <brand/product>, what do you have? In priority order:
1. Logo (SVG / high-res PNG) — every brand needs this
2. Product images / official renders — required for physical products
3. UI screenshots / interface assets — required for digital products
4. Color values (HEX / RGB / palette)
5. Font names (Display / Body)
6. Brand guidelines PDF / Figma design system / brand website link

Send what you have. I'll search for what's missing.
```

### Step 2 · Search Official Channels (by asset type)

| Asset | Search Path |
|-------|------------|
| **Logo** | `<brand>.com/brand` · `<brand>.com/press` · `<brand>.com/press-kit` · `brand.<brand>.com` · Homepage header inline SVG |
| **Product images/renders** | `<brand>.com/<product>` product page hero · Official YouTube launch film frames · Press release images |
| **UI screenshots** | App Store / Google Play product page · Website screenshots section · Product demo video frames |
| **Colors** | Website inline CSS / Tailwind config / brand guidelines PDF |
| **Fonts** | Website `<link rel="stylesheet">` references · Google Fonts tracking · brand guidelines |

WebSearch fallback keywords:
- Logo not found → `<brand> logo download SVG`, `<brand> press kit`
- Product images not found → `<brand> <product> official renders`, `<brand> <product> product photography`
- UI not found → `<brand> app screenshots`, `<brand> dashboard UI`

### Step 3 · Download Assets (3 fallback paths per type)

**3.1 Logo (required for every brand)**

Three paths, descending success rate:
1. Direct SVG/PNG file:
   ```bash
   curl -o assets/logo.svg https://<brand>.com/logo.svg
   curl -o assets/logo-white.svg https://<brand>.com/logo-white.svg
   ```
2. Extract inline SVG from homepage HTML:
   ```bash
   curl -A "Mozilla/5.0" -L https://<brand>.com -o homepage.html
   # Then grep <svg>...</svg> to extract the logo node
   ```
3. Official social media avatar (last resort): GitHub/Twitter/LinkedIn company avatars are often 400×400+ transparent PNGs

**3.2 Product images / renders (required for physical products)**

In priority order:
1. Official product page hero image (highest priority) — inspect element for image URL, resolution usually 2000px+
2. Official press kit — `<brand>.com/press` often has high-res downloads
3. Official launch video frames — use yt-dlp to download YouTube video, ffmpeg to extract frames
4. Wikimedia Commons — public domain often available
5. AI generation fallback — use real product image as reference to generate variants

```bash
# Example: download product hero image
curl -A "Mozilla/5.0" -L "<hero-image-url>" -o assets/product-hero.png
```

**3.3 UI screenshots (required for digital products)**

- App Store / Google Play product screenshots (verify they're real UI, not mockups)
- Website screenshots section
- Product demo video frames
- Official product Twitter/X posts (often latest version)
- User's own account screenshots when they have access

### Step 4 · Verify + Extract

| Asset | Verification |
|-------|-------------|
| **Logo** | File exists + SVG/PNG opens + has transparent background + at least light/dark variants |
| **Product image** | At least one 2000px+ resolution + clean background + multiple angles (hero, detail, scene) |
| **UI screenshot** | Real resolution (1x/2x) + latest version + no user data contamination |
| **Colors** | `grep -hoE '#[0-9A-Fa-f]{6}' assets/*.{svg,html,css} | sort | uniq -c | sort -rn | head -20`, filter grayscale |

**⚠️ Demo brand contamination**: Product screenshots often contain a demo brand's colors (e.g., a tool screenshot showing red from a demo brand). When two strong colors appear simultaneously, distinguish them.

**⚠️ Brand multi-facet**: A brand's marketing site colors often differ from its product UI colors (e.g., website uses warm tones but product uses cool tones). Both are real — pick the right facet for your deliverable.

### Step 5 · Write `brand-spec.md`

```markdown
# <Brand> · Brand Spec
> Collected: YYYY-MM-DD
> Sources: <list download sources>
> Completeness: <complete / partial / inferred>

## Primary Assets

### Logo
- Primary: `assets/<brand>/logo.svg`
- Light-background version: `assets/<brand>/logo-solid.svg`
- Usage: <opening/closing/corner watermark/global>
- No: <stretching/recoloring/outlining>

### Product Images (physical products)
- Hero: `assets/<brand>/product-hero.png`
- Detail: `assets/<brand>/product-detail.png`
- Scene: `assets/<brand>/product-scene.png`
- Usage: <close-up/rotation/comparison>

### UI Screenshots (digital products)
- Home: `assets/<brand>/ui-home.png`
- Feature: `assets/<brand>/ui-feature-*.png`
- Usage: <product showcase/onboarding/demo>

## Supplementary

### Colors
- Primary: #XXXXXX  <source>
- Background: #XXXXXX
- Text: #XXXXXX
- Accent: #XXXXXX
- Forbidden: <colors the brand explicitly doesn't use>

### Typography
- Display: <font stack>
- Body: <font stack>
- Mono (data/HUD): <font stack>

### Signature Details
- <which details are "120% executed">

### Prohibited
- <explicitly disallowed patterns>

### Tone Keywords
- <3-5 adjectives>
```

## Execution Discipline

1. All HTML must **reference** brand-spec.md asset paths — no CSS silhouettes or SVG hand-drawn replacements
2. Logo as `<img src="...">` referencing real file — never redrawn
3. Product images as `<img src="...">` referencing real file — never replaced with CSS silhouettes
4. CSS variables from spec: `:root { --brand-primary: ...; }`, HTML uses `var(--brand-*)`
5. This makes brand consistency structural — adding a temporary color requires changing the spec first

## Full Failure Fallbacks

| Missing Asset | Handle |
|--------------|--------|
| **Logo completely unfindable** | **Stop and ask the user** — never hard-code (logo is the root of brand recognition) |
| **Product images (physical) unfindable** | AI generate with official reference → ask user → honest placeholder ("product image TBD") |
| **UI screenshots unfindable** | Ask user for account screenshots → official demo video frames. Don't use mockup generators |
| **Colors completely unfindable** | Use Design Direction Advisor mode, recommend 3 directions with explicit assumptions |

## Pitfalls

1. **Never silently substitute missing assets with CSS silhouettes / generic gradients** — this is the protocol's biggest anti-pattern. Better to pause and ask than to fill.
2. **The brand-spec.md is the contract** — every element in the final output must trace back to it. If you can't, the spec is incomplete.
3. **Logo is NOT subject to "5-10-2-8" filtering** — unlike other assets, even a 6/10 logo is massively better than no logo.
4. **App Store screenshots may be mockups, not real UI** — cross-reference with official demo videos or user accounts.
