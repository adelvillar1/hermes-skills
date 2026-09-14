---
name: design-resource-distillation
description: Distill external design sources into our skill library.
---

# Design Resource Distillation

Turn an external design resource the user points at (repo, site, skill collection) into durable, folded-in skill knowledge — the "anything useful for our design skills?" workflow. Proven across 5 sources in one session: top-welcome-screens, checklist.design, react-bits, motion.dev, emilkowalski/skills.

## When to Use

- User links a design repo/site and asks "is there anything useful for our design skills?" / "same pattern with this one".
- User notes we already have some skills from a source and wants the gap ("new ones have been added").
- Any external reference that might hold transferable design knowledge.

## Workflow

### 1. Research the source (read real content, not the landing page)

- Fetch README + repo tree / site nav first — establish what it actually is. **Star count ≠ quality**: an 8-hour-old 10-star repo held measured motion gold; a 45k-star repo was recipes; a docs site was tokens.
- List the FULL catalog (component names, checklist titles, skill names) — breadth matters for the coverage map.
- Sample 2–4 concrete artifacts: actual code, SKILL.md files, checklist pages. Judge craft from implementations, not marketing copy.
- Identify the DISTINCT value axis — each source usually teaches ONE thing (measured timings / surface completeness / recipes / tokens+rubric / principles). Name it before folding.

### 2. Coverage-map against our library

- Before creating anything: `skill listing` + `skill loader` the likely umbrellas (design-motion-principles, design-engineering, ui-implementation-review, animation-vocabulary, apple-design, tech-stack-evaluation, sketch…).
- Ask per source-skill: "do we already have this?" Output a source→existing mapping table. (emilkowalski/skills: 7 of 10 skills mapped to existing; only 2 were genuinely new.)
- Only genuinely new axes become new skills; overlaps get patched into existing umbrellas.

### 3. Fold in — prefer the earliest fit

1. **Patch the obvious umbrella** (design-motion-principles for motion; ui-implementation-review for QA/checklists) — a compact section in SKILL.md.
2. **Add `references/<topic>.md`** under the umbrella with the full distilled detail (exact values, code snippets, tables) + a one-line pointer in SKILL.md's References section.
3. **Create a new class-level skill ONLY for genuinely new axes** (e.g. animation-vocabulary: naming glossary; apple-design: fluid-interface playbook).

Extraction rules:
- Extract CONCRETE values (measured ms, cubic-beziers, spring constants, formulas, token tables) — never vibes. Quote verbatim where the source is authoritative.
- Description ≤60 chars, trigger first, ends with period (the validator rejects longer).
- Attribute the source in the skill body / file header.

### 4. Record the source durably

- `your memory store` (importance ~0.7): URL, what it's good for, which skill + section absorbed it, license.
- License discipline: GPL-3.0 (top-welcome-screens — branding-replacement required), MIT + Commons Clause (react-bits), MIT core (motion.dev), MIT (MengTo/skills, emilkowalski/skills). Always note before copying code.

### 5. Close the loop: platform doctrine (when the user runs an LLM-design product)

- If the user has a design-generating platform (DesignCanvas: `lib/llm.ts` `DESIGN_PRINCIPLES` doctrine injected into every generation/review/chat call + `lib/stylePresets.ts` from MengTo/skills), the endgame is injecting the distilled doctrine into that prompt and adding a review dimension (e.g. a `motion` score) — that's how skill knowledge reaches *generated* designs, not just our own UI work.
- Scope it as a plan (draft-feature-plan) → dispatch implementer (a subagent-driven development workflow) → 2-stage review → verify → commit on `develop` (DesignCanvas flow: develop → main, never commit on main).

## Verification pitfalls (learned the hard way)

- **Mangled grep ≠ absent code.** The terminal-output wrapper can reformat grep results (`37:0:number;` shape) and even report **"0 matches" for a marker that IS in the file** — happened with `cubic-bezier(0.23…` and `clampScore(obj.scores?.motion)` while `tsc --noEmit` passed and read_file showed both verbatim in place. **When grep output disagrees with a clean tsc or a subagent's claimed insertions, re-read the file with read_file before concluding work is missing** — a false "missing" burns a re-dispatch; the file is usually fine.
- **Prompt-doctrine changes must be verified in BUILT messages, not just source.** For a doctrine/doctrine-review change, write a throwaway inspection script that calls the message-builder (e.g. `buildGenerateMessages`) and asserts markers in the output. Run it with `npx --yes tsx .tmp/verify-*.mts` — Node 24's native type-stripping fails on extensionless relative imports (`./models`), so plain `node` won't work in Next.js repos.
- **Type-gate before saving the plan:** `pnpm exec tsc --noEmit` must pass on the whole project before the plan file lands.

## Related skills

- `expert-skill-builder` (third-party docs → knowledge-only skills), `learn-skill` (/learn), `web-technique-to-skill` (a technique you built → skill) — narrower cousins; this skill is the "evaluate an external design resource → coverage-map → fold into the existing library" workflow.
- `design-motion-principles`, `ui-implementation-review`, `animation-vocabulary`, `apple-design`, `design-spec-agent-prompts` — the umbrellas that receive the folds.
