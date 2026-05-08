---
name: draft-feature-plan
description: "Use when starting non-trivial work, or when the user says 'plan this feature', 'draft a plan for X', or 'before we build this'. Skips for typo fixes, single-line bug fixes, dependency bumps, and trivial changes. Creates an ISO-date-prefixed plan file at docs/plans/YYYY-MM-DD-<slug>.md with status, context, approach, acceptance criteria as a checkbox list, files to be touched, out of scope, verification, and linked artifacts."
version: 2.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [project-management, planning, feature-spec, claude-md]
    related_skills: [session-warmup, write-session-recap, init-project-structure]
---

# Draft Feature Plan

Draft a structured plan-as-contract for a feature before implementation. The plan is the contract: it describes what's being built, how we'll know it's done (acceptance criteria), and which contract docs will need updating when the work is finished.

## When to Use

- User says "plan this feature", "draft a plan for X", "before we build this"
- Session opens with significant new work that needs a contract
- Non-trivial work starting that adds capability, changes user-visible behavior, adds tables/columns, touches auth, modifies billing, or changes API contracts

## When to Skip

**Tell the user "this looks too small for a plan, just go straight to implementation and write a recap when done" if the feature is:**
- A typo fix
- A single-line bug fix with no behavior contract change
- A dependency bump with no behavior change
- A pure refactor with no observable change
- Renaming a variable
- Updating a comment
- Cleaning up dead code

## Workflow

### 1. Pre-flight checks

```bash
[ -d docs/plans ] || echo "WARNING: docs/plans/ does not exist — run init-project-structure or mkdir docs/plans"
[ -f CLAUDE.md ] && echo "OK: CLAUDE.md present"
ls docs/plans/*.md 2>/dev/null | tail -5    # see recent plans for naming consistency
```

If `docs/plans/` doesn't exist, ask whether to create it or abort. Don't silently create project structure.

### 2. Gather context

Before drafting, read:

- `CLAUDE.md` to understand the project's hard rules and branch topology
- `docs/plans/README.md` if it exists
- The relevant `docs/features/*.md` if the feature touches an existing area
- `TECHNICAL-DOCUMENTATION.md` table of contents to know what sections might need updating
- `FUNCTIONAL-SPECIFICATIONS.md` table of contents same

**If the user provides a concrete output example** (sample DOCX, screenshot, mockup, existing report, competitor output), **analyze it before drafting criteria.** The example is ground truth — it reveals section structure, field-level detail, ordering, and edge cases the spec might not mention. Extract a specific section-by-section inventory from the example and reference it explicitly in the plan's approach and acceptance criteria. A plan whose criteria reference the example's structure ("all 23 indicators individually rated with 3-element justifications") is more accurate than one based on the spec alone ("domain-level summary ratings").

### 3. Ask the user for the feature description

If the user hasn't already described the feature, ask:

1. **What are we building?** (1-2 sentences)
2. **Why?** (the problem it solves or the value it adds)
3. **Any non-obvious constraints?** (e.g. "must work without breaking existing import script")
4. **Any approach preferences?** (default: you pick one)

### 4. Compute the slug and filename

Slug rules:
- Kebab-case
- Describes the *thing being built*, not the action: `cabin-scoring` not `add-cabin-scoring`
- Short (3-5 words max): `stripe-metered-billing`, `port-weather-cleanup`
- Lowercase, ASCII only

Filename: `docs/plans/$(date +%Y-%m-%d)-<slug>.md`

Verify the file doesn't already exist. If it does, append `-2`, `-3`, etc. to the slug.

### 5. Draft the plan

Fill in:

- **Frontmatter**: `status: draft`, `created: YYYY-MM-DD`, `updated: YYYY-MM-DD`, `slug: <slug>`
- **Title**: `Plan: <Human Readable Feature Name>`
- **Context**: 2-4 sentences. The problem, the user need, what triggered this work.
- **Approach**: ONE recommended path. Not a menu of options. Brief — 1-2 paragraphs, plus a numbered list of high-level steps. Reference existing utilities/functions that will be reused.
- **UI constraints** (only if the plan touches UI): Explicitly call out what's NOT changing. "The heatmap grid layout stays intact. All additions are chips in the existing expanded detail — no new tabs, no split views." This prevents the approach from implying unnecessary restructuring. If the plan has no UI surface changes, omit this section.

  **Also document visual design consistency.** List the design tokens (`--surface`, `--border`, `--gold`, `--bg`, `--text-primary`), component patterns (AppShell, `.btn-gold`, `.btn-action`, `.btn-outline`, `rounded-xl` card surfaces), and layout conventions (same table patterns, same spacing) that the implementation MUST reuse. A plan with this section signals that every new component should feel like it was already part of the existing app — not a separate design system or visual language.
- **Acceptance criteria**: 3-10 markdown checkboxes. Each is a verifiable assertion.

  Bad: `- [ ] Performance is good`
  Good: `- [ ] Initial page load completes in under 2 seconds on 4G simulation`

  If you can't write a criterion as a verifiable assertion, refine it before writing the plan.

- **Files to be touched**: explicit paths grouped by area (frontend, backend, db, scripts, tests, docs). Don't include speculative paths.
- **Out of scope**: 2-5 bullets of things people might assume are part of this work but aren't.
- **Verification**: how to confirm each criterion. Commands to run, manual steps, screens to check, DB queries.
- **Linked artifacts**: which docs need updating when this ships.

  ```
  - `docs/features/<name>.md` — <what needs to be added>
  - `TECHNICAL-DOCUMENTATION.md` section <n> "<name>" — <what needs to be added>
  - `FUNCTIONAL-SPECIFICATIONS.md` section <n> "<name>" — <what needs to be added>
  ```
  If the feature is small enough to not require contract-doc updates, write  `- None — change is too small to require contract doc updates`.

- **Risks**: things that could go wrong. Empty list if nothing concerning.
- **Dependencies**: other plans/features this depends on, with links to their plan files.

### 6. Present for review

Show the user the drafted plan in the response. Ask: "Does this match what you want to build? Edit the criteria, approach, or scope if anything's off."

Do NOT mark the plan as `active` yet. It stays `draft` until the user signals "looks good, let's build it."

### 7. After approval

Once the user approves:
- Update the plan's `status` from `draft` to `active`
- Update the `updated` field to today
- Tell the user: "Plan is active at `docs/plans/<filename>`. When you're done, run `/recap` to draft a session recap that ticks off the criteria and updates the contract docs."

Do NOT start implementation. The plan is the contract; implementation is the next session's work (or the next step the user takes).

## Things to Avoid

1. **Do not draft a plan for trivial work.** It wastes time and trains the user that the methodology is overhead.
2. **Do not present multiple approach options.** Pick one and recommend it. Plans are decisions, not menus.
3. **Do not invent acceptance criteria.** If the user hasn't told you what "done" means and the description is vague, ASK. Don't fabricate criteria.
4. **Do not mark the plan `active` without user approval.** Status changes are user-driven decisions.
5. **Do not invent a new approach when an existing one will do.** The user has deep expertise with FalkorDB, Ollama, Prisma, Railway, etc. If the approach can use an existing tool or pattern from the project's stack, prefer it over a clean-slate alternative — even if the new approach is technically simpler. The infra overhead of running a Docker container is a one-time setup; the cognitive overhead of learning a new pattern recurs every session. When in doubt, ask: "We have X from project Y. Should I use that, or build something new?"
6. **Do not commit the plan automatically.** The user owns commits.
7. **Do not write fake "verification" steps.** If you don't know how to verify a criterion, ask the user.
9. **Do not skip the "what stays the same" section when planning UI changes.** If the plan touches user-facing surfaces, explicitly document UI preservation constraints alongside the approach. Without this, the approach reads as "everything is changing" and the user has to correct you. A simple bullet like "The heatmap grid layout is untouched — all additions go in the existing expanded detail" prevents rework.

9a. **When the user approves with "maintain cohesive approach/UI design": encode the preservation rules in the plan's UI constraints section.** List the specific design tokens (`--surface`, `--border`, `--gold`), component patterns (`AppShell`, `.btn-gold`, `.btn-action`, `rounded-xl` card surfaces), and page layouts that must remain intact. A plan with this section signals to the implementer that every new component should feel like it was already part of the existing app, not a separate design.

10. **For pricing or tier changes: enumerate every UI surface that references prices, query counts, or feature lists in "Files to be touched".** Missing one causes the user to catch stale references post-deploy. Do a grep for `\$XX`, `XXX AI queries`, and `XXX queries` across the entire `app/` tree before finalizing the plan. Common surfaces: `app/HarborLanding.tsx`, `app/(marketing)/pricing/page.tsx`, `app/components/ai-chat/AIChatUpgradeModal.tsx`, `app/how-to/HarborHowToGuideContent.tsx`, `app/how-to/HowToGuideContent.tsx`, `lib/ai-chat/feature-flags.ts`, `lib/stripe/client.ts`, `lib/email/subscription-emails.ts`, `docs/features/billing.md`. Grep first, then build the file list from actual hits — don't guess.

10. **For multi-tool plans: each tool needs its own concrete criterion with specific columns, metrics, and behavior.** A criterion like "Shows corridors ranked by crowding" is too vague to verify. Instead: "Region picker → table sorted by monthlyShips descending. Columns: corridor name, ships/month, lines/month, dominant operator, exclusive ports count." If you can't picture walking up to the rendered page and checking the criterion off, it's not ready. The user will reject vague criteria — specificity is the difference between a plan they approve and one they send back.

11. **Shipping to production is a stronger completion signal than criteria wording.** When the user pushes work to production, the acceptance criteria are effectively met — they wouldn't ship broken or partial work. Don't mark a plan as "partial" because the criteria text was conservative and the implementation exceeded it. If the user ships it, update the criteria to reflect reality and mark the plan complete. If you're unsure ("the criteria say X but the user shipped Y"), ask "Does this mean the plan is complete?" rather than assuming criteria gaps remain.

12. **Do NOT mark a plan completed when the core behavior doesn't work yet.** Scaffolding (DB schema, API routes, UI skeleton, tests) is not the same as working functionality. Criteria like "Run Phase button executes all steps sequentially" is not satisfied by a fragile polling loop that times out. Be ruthlessly honest about what's actually wired versus what's just present. The user will call out premature completion every time — it damages trust. When in doubt, ask: "Is this actually working end-to-end, or is it just the structure for it?" before updating status.

## Verification Checklist

- [ ] Filename follows `YYYY-MM-DD-<slug>.md` format
- [ ] Frontmatter present with `status: draft`, `created`, `updated`, `slug`
- [ ] Context is 2-4 sentences describing the problem
- [ ] Approach recommends exactly one path (not a menu)
- [ ] If UI changes are involved: "UI constraints" section documents what's NOT changing
- [ ] Acceptance criteria are verifiable assertions (not subjective)
- [ ] Files to be touched are explicit, not speculative
- [ ] Out of scope lists 2-5 common assumptions
- [ ] Verification steps are concrete (commands, screens, queries)
- [ ] Linked artifacts reference real docs, or explicitly state "None"
- [ ] Status is `draft` until user explicitly approves
- [ ] User told NOT to commit yet
- [ ] User pointed to `/recap` skill for closure
