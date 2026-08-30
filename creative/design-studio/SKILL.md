---
name: design-studio
description: "Orchestrated design workflow: discovery → brand assets → build → anti-slop gate → critique → iterate. Auto-chains: claude-design, brand-asset-protocol, anti-ai-slop, design-review. Use for any design task where quality matters — landing pages, prototypes, UI mockups, motion graphics, presentations."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [design, workflow, orchestration, quality, review]
    related_skills: [claude-design, brand-asset-protocol, anti-ai-slop, design-review, sketch, architecture-diagram, hyperframes]
    category: creative
    requires_toolsets: [terminal, browser, web, file, vision]
---

# Design Studio — Orchestrated Design Workflow

A structured 6-phase design workflow that chains discovery → brand research → build → quality gate → critique → iteration. This skill exists because the individual pieces (claude-design, brand-asset-protocol, design-review, anti-ai-slop) are powerful on their own, but each assumes you've already done the previous step. This skill closes the loop.

## When to Use

- User asks for any visual design: "design a landing page", "make a UI mockup", "create a prototype", "build a presentation"
- User wants professional-quality design output
- User asks for design direction or style recommendations
- Any design task where you'd want a second opinion before delivering

Do NOT use for:
- Simple HTML/CSS tweaks (use claude-design or sketch directly)
- Architecture diagrams (use architecture-diagram directly)
- Video-only work (use hyperframes directly)

## Phase Map

```
Phase 1 ── Discovery ──── Ask structured questions before ANY code
    │                        (audience, tone, brand, surface, constraints)
    ▼
Phase 2 ── Brand Assets ── If brand is involved, run brand-asset-protocol
    │                        (logo, colors, fonts, product images, UI refs)
    ▼
Phase 3 ── Build ───────── Create the design artifact
    │                        (choose the right tool: claude-design / sketch / hyperframes)
    ▼
Phase 4 ── Anti-Slop Gate ─ Run anti-ai-slop checklist before presenting
    │                        (purple gradients? emoji icons? data slop?)
    ▼
Phase 5 ── Critique ────── 5-dimension design review
    │                        (philosophy, hierarchy, craft, function, innovation)
    ▼
Phase 6 ── Iterate ─────── Present findings + offer fix options
                             (quick fixes now, structural changes next pass)
```

## Phase 1 — Discovery

**Rule: Do NOT write any code before completing this phase.** Ask all discovery questions in a single message. Maximum 6 questions.

Pick the right subset from:

| Question | When to ask |
|----------|------------|
| What are you designing? | Always (landing page, UI mockup, presentation, etc.) |
| Who's the audience? | Always — "travel advisors", "tech executives", "general consumers" |
| What's the brand/product? | Always — determines if we run Phase 2 |
| What's the desired tone? | If not obvious — professional, playful, luxurious, technical |
| What format/surface? | If not clear — desktop web, mobile app, presentation slide, social post |
| Any existing design system or brand guidelines? | If brand is named |
| What's the one thing this design must communicate? | Always — prevents scope creep |
| Any constraints? (content length, colors, etc.) | Optional |

**Format as a single message with inline questions**, not a multi-turn Q&A:

```
I'll start by asking a few questions to nail the brief:

1. What are you designing? (landing page, UI mockup, presentation, social carousel, etc.)
2. What's the brand or product? (so I can find real assets)
3. Who's the audience? (travel advisors, tech execs, general consumers, etc.)
4. What tone should it have? (professional, playful, luxurious, technical, warm)
5. What's the one thing it must communicate?
6. Any existing design system, brand guidelines, or reference materials?
```

Wait for the user's response before proceeding to Phase 2.

## Phase 2 — Brand Assets (conditional)

If the user named a specific brand or product, load `read the SKILL.md for '`brand-asset-protocol`' via your harness's skill loader` and follow its 5-step pipeline:

1. Ask for any existing brand assets (logo, colors, fonts, images)
2. Search official channels for what's missing
3. Download verified assets
4. Extract colors + fonts via grep
5. Write `brand-spec.md`

If the user has NO brand context and no style preference, skip directly to **design direction advisor** mode: recommend 3 differentiated design philosophies from `claude-design/references/design-philosophies.md` with small visual demos.

## Phase 3 — Build

### Phase 3a — Verify Data Claims (MANDATORY)

**If this design describes, demonstrates, or references product features** (demo videos, marketing pages, feature showcases, product mockups):

1. **Find the feature doc** — check the project's `docs/features/` directory for the relevant feature. Read it before writing any feature description.
2. **If no doc exists** — search the codebase for the actual implementation. Check Prisma schema for data models. Check API routes for endpoints.
3. **Never extrapolate features.** If the doc says "Port Intelligence shows weather, sea conditions, air quality" — do NOT add "water clarity" or "beach quality" or "tide schedules." Those don't exist.
4. **Never invent numbers.** If the doc says "67K+ sailings" — use that exact number. Do not round to 70K or 65K.
5. **If you can't find the data** — ask the user before describing it.

**Examples of hallucinated claims caught by this step:**
- ❌ "$2,400 for 10 nights" — product has no per-sailing pricing
- ❌ "Water clarity data" — product has air quality and sea conditions, not water clarity
- ❌ "Weather forecasts" — product has historical climate data, not forecasts

### Phase 3b — Choose and Build

Choose the right tool based on the deliverable:

| Deliverable | Tool |
|------------|------|
| Landing page / web prototype | `claude-design` or `sketch` (for quick mockups) |
| UI mockup / app screen | `claude-design` (if web) or `sketch` (throwaway) |
| Presentation / deck | `architecture-diagram` or a custom HTML deck |
| Presentation / deck | `slide-deck` (purpose-built) or `architecture-diagram` |
| Device-framed preview | `device-frames` — wrap in iPhone/MacBook/browser chrome |
| Motion video / social short | `hyperframes` |
| Architecture diagram | `architecture-diagram` |
| Throwaway mockup / 2-3 variants | `sketch` |

### Phase 3c — Automated Preview

After building the artifact, preview it automatically before presenting:

1. **If the artifact is an HTML file**, open it in the embedded browser:
   ```
   browser_navigate('file:///path/to/artifact.html')
   ```

2. **Check for JavaScript errors:**
   ```
   browser_console()
3. **Take a screenshot** at the primary viewport. The `browser_vision` tool may not reliably process screenshots in all environments. If it fails, save the screenshot to disk and use `vision_analyze` with the file path, or simply note that visual verification was attempted but the tool was unavailable.

4. **If device context matters** (mobile app, desktop app, browser), wrap the artifact in a device frame from `device-frames` skill first:
   - iPhone 15 Pro for mobile mockups
   - MacBook Pro for desktop designs
   - Browser Chrome for web page previews

5. **Report:**
   - Console errors: none / fixed
   - Visual issues found: none / list
   - Screenshot available: yes
   - Device frame used: if applicable

Skip the browser preview if the artifact isn't HTML (e.g., raw CSS, SVG, markdown).

Build the artifact. Apply the brand spec (colors, fonts) from Phase 2 if available.

## Phase 4 — Anti-Slop Gate

Before presenting the output, load `read the SKILL.md for '`anti-ai-slop`' via your harness's skill loader` and run through its checklist. Fix any issues found:

- ❌ Purple gradient backgrounds? → Replace with brand-appropriate solid or subtle radial
- ❌ Emoji as UI icons? → Replace with proper icons or remove
- ❌ Rounded cards with left border accent? → Redesign without the AI-signature pattern
- ❌ SVG-drawn imagery (people, scenes)? → Replace with real images or honest placeholders
- ❌ Data slop (fake stats)? → Remove if no real data available
- ❌ Inter/Roboto/Arial as display without brand spec? → Use brand-spec fonts

After fixes, re-evaluate. Only proceed to Phase 5 when anti-slop passes.

## Phase 5 — Critique

Run the 5-dimension design review. Load `read the SKILL.md for '`design-review`' via your harness's skill loader` and produce a scored critique:

| Dimension | Score | Why |
|-----------|-------|-----|
| Philosophy Alignment | X/10 | Brief justification |
| Visual Hierarchy | X/10 | Brief justification |
| Craft Quality | X/10 | Brief justification |
| Functionality | X/10 | Brief justification |
| Innovation | X/10 | Brief justification |
| **Overall** | **X/10** | |

Separate findings into:
- **Quick fixes** (can do now, <5 min) — spacing, alignment, color consistency
- **Structural issues** (next iteration) — layout rethink, content changes

## Phase 6 — Iterate

Present the results to the user:

```
✅ Done with the first pass.

[Screenshot or description of output]

**Quality check:**
- Anti-slop gate: passed (fixed X issues)
- Design review: X/10 — [verdict]

**Quick fixes I can apply now:**
1. [fix]
2. [fix]

**Structural feedback for next pass:**
1. [feedback]
2. [feedback]

Want me to apply the quick fixes, start over with a different direction, or ship it?
```

## Quick-Reference Flow (for simple tasks)

For quick tasks where the full 6-phase flow is overkill, compress to:

1. **3 discovery questions** (what, brand, tone) → proceed
2. **Quick brand check** — if brand is named, spend 2 minutes finding colors + logo
3. **Build** directly
4. **Anti-slop quick check** — 30 second scan
5. **Deliver**

## Companion Skills

The design skill library extends well beyond the core chain. Load these when the task calls for them:

| Need | Skill | When to load |
|------|-------|-------------|
| Look up exact UI component names | `namethatui` | When writing prompts that reference specific UI elements by framework name |
| Searchable design intelligence (styles, colors, fonts, UX rules) | `ui-ux-pro-max` | When you need style/color/font recommendations by product type, or a pre-delivery UX checklist |
| WCAG 2.2 accessibility audit | `wcag-accessibility` | When accessibility compliance is the task, not just a gate |
| Code-level compliance audit (Vercel guidelines) | `web-design-guidelines` | When asked to audit UI code against best practices with file:line findings |
| Reverse-engineer tokens from a live site | `extract-design-system` | When building a design system from an existing website |
| Developer handoff specs from a design | `design-handoff` | When a design is ready for engineering and needs a spec sheet |
| Microcopy for interfaces | `ux-writing` | When writing button labels, error messages, empty states, tooltips |
| Animation decision framework (Emil Kowalski) | `design-engineering` | When making animation timing/easing/component-polish decisions |
| Motion design with AI-slop audit | `design-motion-principles` | When building or auditing UI motion, especially for AI-slop motion patterns |
| Screenshot/mockup to code | `image-to-code` | When converting visual references into production frontend code |
| Full UI critique + polish loop | `impeccable` | When the user wants iterative design-audit-polish on live browser UI |
| Tailwind v4 design systems | `tailwind-design-system` | When building scalable design systems with Tailwind CSS v4 |
| shadcn/ui component composition | `shadcn-ui` | When adding, searching, fixing, or composing shadcn/ui components |
| Data visualization (charts, dashboards) | `data-visualization` | When designing charts, graphs, dashboards, or infographics |
| Lottie JSON animation generation | `text-to-lottie` | When generating production-ready Lottie animations with live preview |
| Parallel interface design exploration | `design-an-interface` | When you need to explore multiple radically different interface designs |
| Low-fidelity wireframes | `wireframe-prototyping` | When you need fast UX validation before visual polish |

## Pitfalls

1. **Do NOT skip Phase 1.** Writing code before understanding the brief is the #1 source of rework. The user would rather answer 5 questions than redirect 3 iterations.
2. **Do NOT combine Phases 1 and 2** — ask the discovery questions separately so the user doesn't feel bombarded.
3. **Phase 4 is mandatory, not optional** — the anti-slop checklist catches the most common AI-error class. Skipping it means the user will catch the issues instead. For motion-specific anti-slop patterns (pulsing indicators, blur-everywhere, hover-scale-on-everything, stagger-spam), load `design-motion-principles` which has a dedicated anti-checklist.
4. **Phase 5 scores should be justified.** "Visual hierarchy: 6/10 because headlines and body text are only 1.5x apart" is useful. "6/10" alone is not.
5. **Do not spend more than 5 minutes on Phase 4 fixes** — the goal is to catch obvious problems, not to perfect. Over-polishing pre-delivery is premature.
6. **If the user says "just make it", compress to quick-reference mode** — don't force 6 phases on someone who wants speed.
7. **Browser vision tools may fail silently.** If `browser_vision` or `vision_analyze` cannot process the screenshot, note the limitation in your report and proceed. Do not get stuck in a loop trying to verify visually. Console error checks and manual code review are sufficient substitutes.
8. **For design intelligence queries, prefer `ui-ux-pro-max` over guessing.** The searchable CSV database has 161 color palettes, 57 font pairings, and 99 UX guidelines. Running `search.py --design-system` before building saves time and produces better results than improvising.
