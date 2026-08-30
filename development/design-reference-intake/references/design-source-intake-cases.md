# Design Source Intake Cases (2026-08-08)

Five worked cases of the design-reference-intake workflow. Use as a template for the next intake: same shape — URL, what was sampled, what was distilled, where it landed, license.

## 1. github.com/Appllama/top-welcome-screens

- **What it is:** 10 animated iOS splash/welcome/onboarding screens reverse-engineered from top-earning apps (Duolingo, Strava, MyFitnessPal, Perplexity, Yazio, onX Hunt, Speak & Learn, Hallow, SCRL, Speak). Expo/React Native + Reanimated, 6 commits, 10 stars.
- **Sampled:** README, GitHub API contents, `docs/MOTION_SPEC.md` (the gold — measured 30fps timings), one full component `src/welcome-screens/yazio.tsx`, shared infra (`timeline.ts`, `interaction-gate.ts`, `reference-canvas.tsx`), `docs/ASSET_PROVENANCE.md`.
- **Distilled:** measured motion timings (167ms mascot blink, ~66ms stagger with Easing.out(Easing.back(1.5)), hard cuts as legitimate premium motion, 234ms color shift), "never invent unsupported motion" rule, per-screen copy-paste agent prompts pattern.
- **Landed in:** `design-motion-principles` (Measured Motion Data section) + NEW skill `design-spec-agent-prompts` (the copy-paste prompt anatomy + 10 requirement clauses).
- **License:** GPL-3.0, educational only — branding-replacement required before any commercial use. Assets are IP-encumbered by design.

## 2. www.checklist.design

- **What it is:** 110 design checklists across mobile/web-app/website/design-system/flows, 5–8 items each with a "why it matters" tip. Figma AI-review plugin, export to Linear/GitHub/Notion.
- **Sampled:** homepage + 5 checklists (paywall, onboarding, empty-state, pricing, login) — the "why" rationales were the gold (zero vs no-results vs error state; neutral paywall dismiss copy; email-vs-password error distinction; Apple Sign In requirement).
- **Distilled:** the per-surface checklist pattern + the sharpest items, URL pattern `/{mobile|web-app|website|design-system|flows}/{surface}`.
- **Landed in:** `ui-implementation-review` — new workflow step 7h + `references/surface-checklist-library.md` (full item lists for 5 surfaces + all other surface names).
- **License:** consultational content; no code copied.

## 3. github.com/DavidHDev/react-bits

- **What it is:** 45k★, 165+ animated React components (TextAnimations/Animations/Components/Backgrounds), 4 variants each (JS/TS × CSS/Tailwind), reactbits.dev docs + tools.
- **Sampled:** README, API contents tree (full catalog), `BlurText.tsx`, `AnimatedContent.tsx`, `TiltedCard.tsx`, `hooks/` listing.
- **Distilled:** multi-step blur reveal (blur 10→5→0, opacity 0→0.5→1), trigger-once IntersectionObserver, GSAP scroll in-and-out with disappearAfter, tilt spring `{damping 30, stiffness 100, mass 2}`, velocity follow-through (`-velocityY * 0.6`), willChange hints, effect vocabulary for "make it memorable" requests.
- **Landed in:** `design-motion-principles` (Web Motion Recipes section) + `references/web-motion-recipes.md` (full distilled code + effect catalog + license note).
- **License:** MIT + Commons Clause — free for personal/commercial app code, cannot resell as a competing library.

## 4. motion.dev

- **What it is:** The Motion library (formerly Framer Motion), MIT core, React/JS/Vue. Plus Motion UI (production sections), MotionScore (performance audit), AI Kit (MCP for agents).
- **Sampled:** homepage, docs index, `/docs/spring`, `/docs/easing-functions`, react scroll-animations guide, `score.motion.dev/docs` (tier system), `/ui` (theme tokens).
- **Distilled:** production spring tokens from Motion UI theme (snap {1218,70}, ui {305,33}, gentle {110,20}, lively {622,17}, ambient {43,13}; stagger tight 0.04/base 0.08/relaxed 0.15s; travel hover 4/enter 24/section 48px; reducedMotion "calm"), MotionScore S–F tiers (S=compositor-only → F=thrashing), visualDuration vs duration, scroll-triggered vs scroll-linked model, smoothing config {stiffness 100, damping 30, restDelta 0.001}.
- **Landed in:** `design-motion-principles` (Motion Design Tokens + MotionScore tiers sections) + `references/motion-library-reference.md` (full spring/easing/scroll detail + MotionScore methodology + AI Kit pattern).
- **License:** MIT core; Motion+ premium is paid — only free/core knowledge distilled.

## 5. github.com/emilkowalski/skills

- **What it is:** 10 skills by Emil Kowalski (Vercel/Linear) — design/engineering craft as skill files. Installable `npx skills@latest add emilkowalski/skills`.
- **Sampled:** README (skill list), `emil-design-eng/SKILL.md`, `animation-vocabulary/SKILL.md`, `apple-design/SKILL.md`, `review-animations/SKILL.md`, `find-animation-opportunities/SKILL.md`, `improve-animations/SKILL.md`. Also compared against our existing `design-engineering` skill.
- **Distilled:** coverage mapping (emil-design-eng→design-engineering covered; review-animations→graft escalation triggers; find-animation-opportunities→graft Gate; improve-animations→covered by ui-implementation-review + design-spec-agent-prompts; animation-vocabulary→NEW; apple-design→NEW). Escalation triggers (14 flag-on-sight conditions) + remedial hierarchy + verdict discipline; the 4-question find-gate (frequency/purpose/speed/function) + rejected-candidates report format.
- **Landed in:** NEW skills `animation-vocabulary` (reverse-lookup glossary) and `apple-design` (WWDC fluid-interface principles: damping/response springs, velocity handoff, momentum projection, rubber-banding, gesture feel); `design-motion-principles` audit mode extended with escalation triggers + find-gate; coverage mapping table added to its References section.
- **License:** MIT.

## 6. github.com/starc007/ui-components (beUI)

- **What it is:** 923★, 123 motion components + ~20 Agent Interface components + blocks, shadcn-registry format (install `npx shadcn@latest add @beui/{slug}`), with agent-readable endpoints (llms.txt, /r/{slug}.json, /r/{slug}/raw, /r/{slug}.md). React 19 / Motion / Tailwind v4 / Next.js.
- **Sampled:** README, GitHub API tree (full 123-component catalog), beui.dev llms.txt + JSON registry, `lib/ease.ts` (the gold — purpose-named token system verbatim), raw `tabs.tsx` / `action-swap.tsx` / `bottom-sheet.tsx` (component-typed values), button.md + loading-states.md + message-scroller.md + streaming-response.md (LLM-facing specs), agent-interface catalog.
- **Distilled:** purpose-named springs (SPRING_PRESS {500,30,0.6}, SPRING_SWAP {460,30,0.55}, SPRING_PANEL {420,40,0.5}, SPRING_LAYOUT {360,32,0.6}, SPRING_MOUSE {200,15,0.3}, SPRING_GLIDE {700,50,0.5}) + EASE_DRAWER [0.32,0.72,0,1]; weighty layout-indicator spring {170,24,1.2}; blur-swap slots (blur 8px/0.2s; roll 3px/0.14s; width 220ms); drawer-as-tween (0.5s, dragElastic {top 0.02, bottom 0.4}, fling −80px); agent-interface surface catalog (12 surfaces) + stable-streaming craft rules.
- **Landed in:** `design-motion-principles` (beUI Motion Tokens section + `references/beui-motion-recipes.md` full values + agent-readable endpoints) and NEW skill `ai-interface-design` (the agent-interface class — catalog + behavioral principles + DesignCanvas doctrine application).
- **License:** MIT — free to copy/adapt; attribution per MIT terms.

## Intake hygiene notes

- Batch the web_extract calls (README + API tree + raw files in 2–3 calls) — independent fetches run concurrently.
- The description-budget error (60 chars) fired 3× this session at 64/65/66 chars; write ≤58 first time.
- Each source landed in EXACTLY one class of home: motion knowledge → `design-motion-principles`; surface checks → `ui-implementation-review`; naming/glossary → new skill; platform-specific design philosophy → new skill.
