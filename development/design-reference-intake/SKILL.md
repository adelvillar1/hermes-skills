---
name: design-reference-intake
description: "Evaluate design sources; fold their knowledge into skills."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Design, Skills, Research, Library, Curation]
    related_skills: [skill-authoring, design-motion-principles, design-engineering, ui-implementation-review]
---

# Design Reference Intake

When the user points at an external design source (repo, site, checklist library, skills repo) and asks "is there anything here that could improve our design skills?" — research it properly, map it against what the library already holds, distill the genuinely new knowledge, fold it into the right skill(s), and record the source for future sessions. The deliverable is a skill-library change, not a report. Proven 5× in one session (2026-08-08) against top-welcome-screens, checklist.design, react-bits, motion.dev, and emilkowalski/skills.

## When to Use

- "is there anything from <repo/site> that could improve our design skills?"
- "let's do the same with this one" (the user is on an intake spree — expect a sequence)
- "should we review <project> against these skills?" (the apply-extension, below)
- Any request to evaluate an external resource for reusable design knowledge

## Workflow (in order)

1. **Research the source properly — sample the REAL content, not the README.**
   Fetch the README + the GitHub API tree (`api.github.com/repos/<owner>/<repo>/contents/...`), then fetch 2–3 actual implementations/docs pages (raw `.tsx`/`.md` files). The landing page tells you what the project *claims*; the raw files show the *actual craft* — curves, timings, constants, structure. Skimming only the README produces a vibes review.
   - top-welcome-screens: read `docs/MOTION_SPEC.md` + one full component (`yazio.tsx`) — the measured timings were the gold.
   - react-bits: read `BlurText.tsx`, `AnimatedContent.tsx`, `TiltedCard.tsx` — the spring constants and multi-step keyframes were the gold.
   - motion.dev: read `/docs/spring`, `/docs/easing-functions`, scroll-animations, MotionScore — the token values and the S–F rubric were the gold.

2. **Map coverage against the EXISTING library before deciding anything is new.**
   Build an explicit table: source item → our equivalent (covered / partial / NEW). This is what prevents duplicate skills and justifies each artifact. E.g. emilkowalski/skills: `emil-design-eng`→our `design-engineering` (covered), `review-animations`→`design-motion-principles` audit mode (partial — graft escalation triggers), `animation-vocabulary`→**NEW**, `apple-design`→**NEW**. Five sources produced exactly two new skills; the rest were umbrella patches.

3. **Distill VALUES not vibes.**
   Extract concrete, copyable knowledge: measured numbers, curves, formulas, tokens, named values, checklist items with their "why" rationale. Soft "good design matters" content is not worth a skill edit. If the extracted thing has a number/constant/curve, it ships; if it's a platitude, it doesn't.

4. **Fold into the right home (priority order).**
   1. Patch the existing umbrella that owns the territory: `design-motion-principles` for motion knowledge, `ui-implementation-review` for surface-completeness checks, `design-engineering` for component polish.
   2. Add a `references/<topic>.md` support file under that umbrella for the full distilled detail, with a one-line pointer in SKILL.md.
   3. Only create a NEW class-level skill when the source defines a genuinely new class (naming → `animation-vocabulary`; Apple fluid interfaces → `apple-design`). Never a source-named skill.

5. **Record the source in Mnemosyne (global, importance ~0.7).**
   Include: URL, license, what it's good for, and WHERE it was distilled ("distilled into <skill> section/ref"). Future sessions surface it automatically instead of re-discovering it.

6. **License triage before adopting values.**
   GPL-3.0 (top-welcome-screens: educational only, branding-replacement required) vs MIT (MengTo, emilkowalski) vs MIT+Commons Clause (react-bits: fine for app code, not for reselling a competing library). Values/rules are facts and adopting them is fine; copying code/assets needs the license check. Note it in the Mnemosyne record.

## The apply-extension: reviewing a product against the skills

When the user asks "should we review <product> against these skills?" (worked example: design-canvas, a Claude-Design clone that generates designs via LLM prompts):

1. **Find the generation pipeline** — the code that produces the designs. For a prompt-driven design app that's `lib/llm.ts` (doctrine constants + prompt builders) and the style-preset library.
2. **Audit the doctrine against the skills.** Grep for each skill's key rules. design-canvas's `DESIGN_PRINCIPLES` had strong static-visual coverage (anti-slop, typography, color, layout) but motion was ONE line — the whole motion-craft stack we'd just built was absent.
3. **The highest-leverage fix is prompt doctrine + the review feedback loop.** Upgrade the doctrine with the new rules AND add the missing review dimension (a `motion` score) so the reviewer can catch what generation now must follow. Doctrine without a reviewer can't close the loop; a reviewer without doctrine grades against nothing.
4. **Scope out what the artifact constraints forbid.** Self-contained HTML with no external libraries → spring physics (apple-design momentum/velocity handoff) is out of reach; CSS transitions/keyframes are the medium. Say this explicitly in the plan's Out of Scope.
5. **Backward-compat check before adding a review dimension.** Scores live in a JSON column → adding a key degrades with `?? 0`; no migration. Verify the read path (`reviews/route.ts`) before promising "no schema change".
6. **Verify like the presets plan did:** prompt-inspection script (assert doctrine text + new dimension appear in built messages) + local e2e generation + prod smoke.

## The apply-extension, implementation depth (worked: design-canvas 2026-08-08)

When the user says "do it" (not just "review it"), the doctrine upgrade + review dimension get built. Lessons from shipping it:

- **Doctrine text must be handed to the implementer VERBATIM.** The doctrine line is the craft bar — give the subagent the exact never-list, curves, and budgets in the task context. Subagents invent plausible-but-weaker phrasing otherwise. (This is the "extract the pattern verbatim, don't re-derive" rule from draft-feature-plan applied to prompt text.)
- **When adding a review dimension, normalize at EVERY render site, not just the API read path.** The `reviews/route.ts` read-out got `?? 0`, but the ReviewPanel's *main score grid* read `frame.review!.scores[key]` raw — old reviews rendered "Motion undefined/10" in red. The spec reviewer caught it; the implementer and the plan both missed it because the plan only named the route. Audit every `scores[key]` access site (history strip, main grid, chat context, export) before declaring backward-compat.
- **The reviewer prompt must reconcile with the doctrine's own budgets.** We wrote "flag durations over 300ms" in the review system, but the doctrine allows modals/drawers 200–500ms — an internal contradiction the quality reviewer caught. When you write escalation triggers, re-check them against the doctrine's allowance table.
- **Reviewer rotation is a production decision, not just a taste decision.** The cross-model rotation defaulted Grok frames to the xAI reviewer, whose OAuth refresh 500s in prod ("xAI token refresh failed: HTTP 400") — a latent failure surfaced only by a live prod review. Fix: rotate to the model with best taste that's *reliable* (Kimi), keep no-self-grading (`kimi→deepseek`), and avoid the flaky provider entirely. Verify the rotation change with a live review on a frame generated by the previously-broken provider.
- **Prompt-inspection of review prompts requires exported consts.** `buildGenerateMessages` is exported, so generation-side doctrine assertions work out of the box. But `REVIEW_SYSTEM` / `REVIEW_SCHEMA_HINT` are module-private `const`s in `lib/llm.ts` — an import-based inspection script fails LSP with "declares 'REVIEW_SCHEMA_HINT' locally, but it is not exported" (hit 2026-08-08 writing `.tmp/verify-aiux-doctrine.mts`). Put the 2-token `export` change in the plan's Phase C, or assert the review schema by source grep instead.
- **Scope doctrine lines to their brief class.** A new bar that only applies to some briefs opens with a scope guard — "when the brief is an AI product (chat, assistant, agent, copilot, generation tool)…" — and the reviewer gets the matching guard ("Frames that aren't AI products are fine without agent-interface surfaces — do not penalize non-AI designs"). Without both, the model over-applies the new surfaces to every generation and the reviewer over-penalizes unrelated frames. Same pattern as the motion doctrine's "Frames with no motion are fine."
- **Wire-model changes need a live smoke, not just tsc.** Swapping `k3` → `k3-256k` compiled clean but only a live review (HTTP 200 + scores) proved the model name is valid on the provider's endpoint. A model-name typo compiles fine and 500s at runtime.
- **The prod deploy check is the served bundle, not the deploy log.** After `railway` reports Online, grep the *served* JS chunk for a new client-side marker (e.g. the new score label) — this is the silent-deploy-failure trap from subagent-driven-development applied to a prompt change. Server-side doctrine text isn't in the bundle, so verify a client-visible marker (SCORE_DIMS entry, panel copy) instead.

- **Pure-function e2e — no dev server needed for doctrine verification (AI/agent pass, 2026-08-08).** `generateFrame` and `reviewFrame` (lib/llm.ts) are pure LLM calls (no server/DB), so the AC e2e ran as a throwaway tsx script — `set -a; source .env.local; set +a; npx --yes tsx .tmp/e2e-aiux.mts` — generating an AI-brief frame with loading/streaming/chat surfaces and returning `aiUx: 8` without booting the app. Gotcha: `GenerateResponse.frames` is an ARRAY (variant fan-out), not `.frame`.
- **Parallel spec+quality review is safe for small parent-pre-verified changes.** When the parent has already read back the changed files verbatim (markers + text) and the inspection script passed, dispatch both read-only reviewers in ONE batch — saves a round-trip. Sequential spec→quality stays the default for larger or less-verified changes.

Full worked cases (files, doctrine text, verification commands): `references/product-doctrine-application-case.md` (application #1: motion; application #2: AI/agent-interface aiUx).

## Pitfalls

- **README-truth is not craft-truth.** Always fetch raw implementations. The catalog names matter (react-bits effect vocabulary), but the *values* come from the code.
- **Don't invent a new skill when an umbrella owns the territory.** Five sources → two new skills; the rest were patches. New skills only for genuinely new classes.
- **Description budget:** new skills must fit 60 chars (the tool rejects 60+). Hit this 3× this session at 64/65/66 chars. Write the description at ≤58 chars the first time — one sentence, trigger first, ends with a period.
- **Don't fold in everything from a source.** Each source has one distinct contribution (timings / recipes / tokens / checklists / vocabulary). Identify THE contribution and skip the rest — a 5-source stack stays lean because each source added only its class.
- **The library is cumulative.** Check Mnemosyne recall before re-deriving a source another session already distilled. The stack should grow by composition, not re-extraction.
- **Track the session's build state** — the design knowledge library is an ongoing project; end-of-session updates (skills created/patched this session) belong in the recap so the next session continues from the right state.

## Verification

- `your harness's skill loader` on the patched/created skill shows the distilled values inline (numbers, curves, tokens — not vibes).
- The coverage-mapping table exists in the plan or reply (what was covered vs what was new).
- Mnemosyne has a global record per source with a "distilled into" pointer.
- The user's follow-up "same pattern with this one" is the signal the workflow is legible and reusable.

## References

- `references/design-source-intake-cases.md` — the five worked cases (2026-08-08): exact URLs, what was sampled, what was distilled, where it landed, license notes. Reuse as a template for the next intake.
