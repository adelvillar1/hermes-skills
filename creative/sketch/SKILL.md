---
name: sketch
description: "Throwaway HTML mockups: 2-3 design variants to compare."
version: 1.0.0
author: Hermes Agent (adapted from gsd-build/get-shit-done)
license: MIT
metadata:
  hermes:
    tags: [sketch, mockup, design, ui, prototype, html, variants, exploration, wireframe, comparison]
    related_skills: [spike, claude-design, popular-web-designs, excalidraw]
---

# Sketch

Use this skill when the user wants to **see a design direction before committing** to one — exploring a UI/UX idea as disposable HTML mockups. The point is to generate 2-3 interactive variants so the user can compare visual directions side-by-side, not to produce shippable code.

Load this when the user says things like "sketch this screen", "show me what X could look like", "compare layout A vs B", "give me 2-3 takes on this UI", "let me see some variants", "mockup this before I build".

## When NOT to use this

- User wants a production component — use `claude-design` or build it properly
- User wants a polished one-off HTML artifact (landing page, deck) — `claude-design`
- User wants a diagram — `excalidraw`, `architecture-diagram`
- The design is already locked — just build it

## If the user has the full GSD system installed

If `gsd-sketch` shows up as a sibling skill (installed via `npx get-shit-done-cc --hermes`), prefer **`gsd-sketch`** for the full workflow: persistent `.planning/sketches/` with MANIFEST, frontier mode analysis, consistency audits across past sketches, and integration with the rest of GSD. This skill is the lightweight standalone version — one-off sketching without the state machinery.

  - `references/sharing-prototypes.md` — how to share sketches via public tunnel (cloudflared/ngrok) for stakeholder review on real devices.

## Core method

```
intake  →  variants  →  head-to-head  →  pick winner (or iterate)
```

### 1. Intake (skip if the user already gave you enough)

Before generating variants, get three things — one question at a time, not all at once:

1. **Feel.** "What should this feel like? Adjectives, emotions, a vibe." — *"calm, editorial, like Linear"* tells you more than *"minimal"*.
2. **References.** "What apps, sites, or products capture the feel you're imagining?" — actual references beat abstract descriptions.
3. **Core action.** "What's the single most important thing a user does on this screen?" — the variants should all serve this well; if they don't, they're just decoration.

Reflect each answer briefly before the next question. If the user already gave you all three upfront, skip straight to variants.

### 2. Variants (2-3, never 1, rarely 4+)

Produce **2-3 variants** in one go. Each variant is a complete, standalone HTML file. Don't describe variants — build them. The point is comparison.

Each variant should take a **different design stance**, not different pixel values. Three good variant axes:

- **Density:** compact / airy / ultra-dense (pick two contrasting poles)
- **Emphasis:** content-first / action-first / tool-first
- **Aesthetic:** editorial / utilitarian / playful
- **Layout:** single-column / sidebar / split-pane
- **Grounding:** card-based / bare-content / document-style

Pick one axis and pull apart from it. Two variants that differ only in accent color are wasted effort — the user can't distinguish them.

**Variant naming:** describe the stance, not the number.

```
sketches/
├── 001-calm-editorial/
│   ├── index.html
│   └── README.md
├── 001-utilitarian-dense/
│   ├── index.html
│   └── README.md
└── 001-playful-split/
    ├── index.html
    └── README.md
```

### 3. Make them real HTML

Each variant is a **single self-contained HTML file**:

- Inline `<style>` — no build step, no external CSS
- System fonts or one Google Font via `<link>`
- Tailwind via CDN (`<script src="https://cdn.tailwindcss.com"></script>`) is fine
- Realistic fake content — actual sentences, actual names, not "Lorem ipsum"
- **Interactive**: links clickable, hovers real, at least one state transition (open/close, filter, toggle). A frozen static image is a worse spike than a sloppy animated one.

Open it in a browser. If it looks broken, fix it before showing the user.

**Verify variants visually — use Hermes' browser tools.** Don't just write HTML and hope it renders; load each variant and look at it:

```
browser_navigate(url="file:///absolute/path/to/sketches/001-calm-editorial/index.html")
browser_vision(question="Does this layout look clean and readable? Any visible bugs (overlapping text, unstyled elements, broken images)?")
```

`browser_vision` returns an AI description of what's actually on the page plus a screenshot path — catches layout bugs that pure source inspection misses (e.g. a font import that silently failed, a flex container that collapsed). Fix and re-navigate until each variant looks right.

#### Preview delivery — prefer local opens over tunnels

If the user is on the **same machine where you created the files** (you have a local terminal session on their laptop), **do not bother with cloudflared/ngrok tunnels** by default. Quick tunnels expire quickly and produce 1033 errors, bot detection blocks, and background-process fragility. Instead just tell them to open the local file directly, e.g.:

```bash
open sketches/001-calm-editorial/index.html
```

Then they use Chrome DevTools mobile emulation (`Cmd+Shift+M`) to preview at phone dimensions.

Only use a tunnel if the user explicitly needs to view the sketch from a **different device** (their phone in another room, a stakeholder's device, cross-platform testing) AND local network file sharing (`python3 -m http.server`) is not viable.

**Default CSS reset + system font stack** for fast starts:

```html
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #1a1a1a;
    background: #fafafa;
    line-height: 1.5;
  }
</style>
```

### 4. Variant README

Each variant's `README.md` answers:

```markdown
## Variant: {stance name}

### Design stance
One sentence on the principle driving this variant.

### Key choices
- Layout: ...
- Typography: ...
- Color: ...
- Interaction: ...

### Trade-offs
- Strong at: ...
- Weak at: ...

### Best for
- The kind of user or use case this variant actually serves
```

### 5. Head-to-head

After all variants are built, present them as a comparison. Don't just list — **opinionate**:

```markdown
## Three takes on the home screen

| Dimension | Calm editorial | Utilitarian dense | Playful split |
|-----------|----------------|-------------------|---------------|
| Density   | Low            | High              | Medium        |
| Primary action visibility | Low | High | Medium |
| Scan-ability | High | Medium | Low |
| Feel | Calm, trusted | Sharp, tool-like | Inviting, energetic |

**My take:** Utilitarian dense for power users, calm editorial for content-forward audiences. Playful split is weakest — tries to do both and commits to neither.
```

Let the user pick a winner, or combine two into a hybrid, or ask for another round.

## Theming (when the project has a visual identity)

If the user has an existing theme (colors, fonts, tokens), put shared tokens in `sketches/themes/tokens.css` and `@import` them in each variant. Keep tokens minimal:

```css
/* sketches/themes/tokens.css */
:root {
  --color-bg: #fafafa;
  --color-fg: #1a1a1a;
  --color-accent: #0066ff;
  --color-muted: #666;
  --radius: 8px;
  --font-display: "Inter", sans-serif;
  --font-body: -apple-system, BlinkMacSystemFont, sans-serif;
}
```

Don't over-tokenize a throwaway sketch — three colors and one font is usually enough.

## Interactivity bar

A sketch is interactive enough when the user can:

1. **Click a primary action** and something visible happens (state change, modal, toast, navigation feint)
2. **See one meaningful state transition** (filter a list, toggle a mode, open/close a panel)
3. **Hover recognizable affordances** (buttons, rows, tabs)

More than that is over-engineering a throwaway. Less than that is a screenshot.

## Responsive & mobile-first sketching

> See also: `references/sharing-prototypes.md` — how to share sketches via public tunnel for stakeholder review on real devices.

When the user asks for mobile variants of an existing desktop screen, **always confirm scope first**:

> *"Got it — desktop stays exactly as-is. This is purely additive responsive behavior."*

**Critical pitfall:** If the user hasn't said this explicitly, ask. Desktop table layouts that get hidden with `hidden md:block` can break silently if the mobile layout depends on the desktop wrapper. Confirm the boundary, then build pure additive responsive classes (`md:hidden`, `hidden md:table-cell`) rather than global visibility toggles.

Mobile sketching carries different patterns than desktop. Use these consistently:

### Viewport & touch foundation

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
  * { -webkit-tap-highlight-color: transparent; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; -webkit-font-smoothing: antialiased; }
</style>
```

### Mobile interaction vocabulary

Always include **touch affordances**. A mobile sketch without active states feels dead:

```html
<!-- Press feedback -->
<button class="active:scale-[0.98] transition-transform">Label</button>

<!-- Swipe-friendly row -->
<div class="active:bg-neutral-50 cursor-pointer">...</div>

<!-- Sticky top nav with blur -->
<div class="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b">...</div>
```

### Mobile layout stances (add these to your variant axes)

When a desktop table needs a mobile view, explore these three approaches:

1. **Card list** — Each row becomes a card with compact label/value pairs. Good for browsing, visual hierarchy, new users.
2. **Condensed list** — Minimal rows, tap-to-expand bottom sheet. Good for power users, high volume, fast scanning.
3. **Dashboard-first** — KPI header → action items → calendar/upcoming. Good for reducing cognitive load, surfacing what needs attention.

Use **status dots** (not badges) for condensed lists. Use **rounded pills** for filters. Use **bottom sheets** for detail viewing — never push to a full new page simulation in a sketch.

### Bottom sheet pattern (verified)

```html
<style>
  .bottom-sheet { transform: translateY(100%); transition: transform 0.3s cubic-bezier(0.32,0.72,0,1); }
  .bottom-sheet.open { transform: translateY(0); }
  .backdrop { opacity: 0; transition: opacity 0.2s ease; pointer-events: none; }
  .backdrop.open { opacity: 1; pointer-events: auto; }
</style>
<div class="backdrop fixed inset-0 z-50 bg-black/40" onclick="closeSheet()"></div>
<div class="bottom-sheet fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-2xl shadow-2xl max-h-[80vh] overflow-y-auto">
  <!-- sheet content -->
</div>
```

### Mobile status taxonomy (keep it identical to desktop)

Map desktop status badges to mobile without changing the status semantics:

| Desktop Badge | Mobile Equivalent |
|---------------|-----------------|
| colored text badge | same-colored pill or dot |
| text-only status | status dot + text row |
| row background highlight | same, but consider opacity for cancelled/archived |

Never invent new status names or colors in the mobile sketch. Consistency with the live desktop UI is the whole point.

## Frontier mode (picking what to sketch next)

If sketches already exist and the user says "what should I sketch next?":

- **Consistency gaps** — two winning variants from different sketches made independent choices that haven't been composed together yet
- **Unsketched screens** — referenced but never explored
- **State coverage** — happy path sketched, but not empty / loading / error / 1000-items
- **Responsive gaps** — validated at one viewport; does it hold at mobile / ultrawide?
- **Interaction patterns** — static layouts exist; transitions, drag, scroll behavior don't

Propose 2-4 named candidates. Let the user pick.

## Output

- Create `sketches/` (or `.planning/sketches/` if the user is using GSD conventions) in the repo root
- One subdir per variant: `NNN-stance-name/index.html` + `README.md`

### Desktop review (single file)
- macOS: `open sketches/001-calm-editorial/index.html`
- Linux: `xdg-open sketches/001-calm-editorial/index.html`
- Windows: `start sketches/001-calm-editorial/index.html`

### Mobile / cross-device review (tunnels)
For stakeholders on phones or tablets, use `cloudflared` or an ngrok equivalent:

```bash
# 1. Serve the directory on a local port
cd sketches/001-calm-editorial && python3 -m http.server 8123 --bind 127.0.0.1

# 2. In another terminal, expose via cloudflared
cloudflared tunnel --url http://127.0.0.1:8123
# Copy the https://<subdomain>.trycloudflare.com URL from stdout
```

**If the tunnel returns 1033 / connection errors:**
- Kill stale processes: `killall -9 cloudflared; lsof -ti:8123 | xargs kill -9`
- Re-run — quick tunnels are ephemeral and expire when the process exits.

**Typical workflow with multiple variants:**
```bash
python3 -m http.server 8123 --bind 127.0.0.1 --directory sketches/NNN-stance/
cloudflared tunnel --url http://127.0.0.1:8123
# Stakeholder visits: https://<subdomain>.trycloudflare.com/index.html
```

- Keep variants disposable — a sketch that you felt the need to preserve should be promoted into real project code, not curated as an asset

**Typical tool sequence for one variant:**

```
terminal("mkdir -p sketches/001-calm-editorial")
write_file("sketches/001-calm-editorial/index.html", "<!doctype html>...")
write_file("sketches/001-calm-editorial/README.md", "## Variant: Calm editorial\n...")
browser_navigate(url="file://$(pwd)/sketches/001-calm-editorial/index.html")
browser_vision(question="How does this look? Any obvious layout issues?")
```

Repeat for each variant, then present the comparison table.

## Attribution

Adapted from the GSD (Get Shit Done) project's `/gsd-sketch` workflow — MIT © 2025 Lex Christopherson ([gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)). The full GSD system ships persistent sketch state, theme/variant pattern references, and consistency-audit workflows; install with `npx get-shit-done-cc --hermes --global`.
