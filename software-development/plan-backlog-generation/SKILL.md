---
name: plan-backlog-generation
description: Generate a complete, dependency-ordered plan backlog for.
triggers:
- backlog.*feature
- plan.*roadmap
- plan.*everything.*not implemented
- compare.*roadmap.*code
- what.*left to build
- feature plan for everything
---

# Plan Backlog Generation

Generate a complete, dependency-ordered plan backlog in a single session by
mapping a project's roadmap/spec docs against the current codebase. Each
unimplemented feature becomes one plan file; inter-plan dependencies live in a
separate `PLAN-INDEX.md` plus a wave-ordered dependency graph.

## When to use

- User asks "plan all the unimplemented features" or "backlog everything."
- A project has roadmap/spec docs and a working codebase, but no plan set exists yet.
- The user wants a sequenced plan set covering MVP/v1/v2/v3 phases.
- You need to make an explicit "do auth first vs later" or similar bottleneck call
  that ripples through 10+ plans.

## When NOT to use

- A single feature is being planned → use `draft-feature-plan` instead.
- No codebase exists yet (greenfield) → use `init-project-structure`.
- User wants to execute one specific plan → that's the build phase of `project-methodology`.

## The 4-phase workflow

### Phase 1 — Codebase scan (sequential, single agent)

Before any planning, build a complete map of:
- What's implemented (REST routes, op types, schema tables, UI components).
- What's referenced in docs but missing in code.
- Which docs mention each missing item (PRD, architecture proposal, roadmap phases).
- The cross-cutting infra gaps (auth, deploys, tests).

Use `search_files`, `read_file`, `terminal grep`/`rg`. This phase is single-agent
because information flows in many directions and a subagent in fresh context
would need to re-derive most of it.

### Phase 2 — Inventory + dependency graph

Build a structured table:

| Plan | Depends on | Unblocks | Roadmap phase |
|------|-----------|----------|---------------|

CRITICAL: identify the bottleneck — the dependency that, when done, unblocks
the most other plans. Common bottlenecks:

- **Real auth** — every plan touching permissions/visibility depends on it.
- **Schema decision** — picking R2/S3/local for assets unblocks map upload, handouts,
  journal images, character avatars in one move.
- **Shared UI primitives** — character sheet UI patterns feed multiple feature panels.

Surface the bottleneck to the user as a sequencing decision BEFORE drafting plans.
The user's answer ("auth first" vs "re-do the auth later") shapes every plan's
Out-of-scope section and determines whether plan 00 (a meta-retrofit plan) exists.

### Phase 3 — Plan drafting (parallel subagents, batched)

Dispatch one subagent per plan via `subagent dispatch`. Each subagent gets:
- A pointer to `PLAN-INDEX.md` (so it knows the overall structure).
- A pointer to the relevant docs (PRD, architecture, roadmap) the plan satisfies.
- The plan's wave + sequence number + dependency list.
- The standard plan template (frontmatter + Context + Approach + ACs + Files +
  Out-of-Scope + Verification + Linked Artifacts + Risks + Dependencies + Notes).
- Specific instructions: which schema migration number, which op kinds to add,
  which routes, which UI components — the more concrete the prompt, the less
  divergent the output.

Batching constraint: 3 subagents concurrent (`max_concurrent_children` = 3).
For 25 plans, that's 8-9 batches. Plan duration per subagent is 2-4 minutes.

**Draft plan 00 (the bottleneck/retrofit meta-plan) LAST and BY HAND.** It
references the others (e.g., "enumerates 14 retrofit touchpoints across
plans 04, 09, 10, 11, 12, 13, 14, 16, 23, 24, 25"). Subagents in fresh context
don't have visibility into the others' contents.

**Why hand-written:** plan 00's quality depends on knowing every other plan's
exact `Out-of-scope` wording (so the retrofit checklist matches). A subagent
in fresh context only has its own plan's contents to reference — it cannot
verify cross-plan consistency. The 5-10 minutes of hand-writing pays for
itself by eliminating false-completion risk when retrofit work eventually runs.

### Phase 4 — Verification + commit

After all plans land, run:
1. **Frontmatter check**: every plan has `status`, `created`, `updated`, `slug`.
2. **Cross-reference check**: every plan that mentions a dependency actually
   names the right plan file. Use `grep` for `plan-0X-name` patterns.
3. **Retrofit coverage**: if plan 00 enumerates N touchpoints, verify N plans
   each have a corresponding reference in their Out-of-scope section.
4. **Numbering consistency**: PLAN-INDEX's numbering matches the actual file slugs.
5. **Drift checks**: CLAUDE.md line count, gitignore, branch state.

Commit all 25+ plan files in ONE batch (per `project-methodology` "batch all
changes before pushing"). Then append a Post-recap section to today's session
recap — DO NOT create `SESSION-RECAP-YYYY-MM-DD-followup.md` per the methodology
pitfall.

## Output structure

```
docs/
├── plans/
│   ├── README.md              # already exists per project-methodology
│   ├── PLAN-INDEX.md          # NEW — dependency map + wave structure
│   └── 2026-MM-DD-<slug>.md   # 25 plan files
├── STATE-SNAPSHOT.md           # refresh with new plan count
├── recaps/
│   └── SESSION-RECAP-YYYY-MM-DD.md  # append Post-recap section
```

## Common pitfalls

### Subagents diverge without shared context
Without the PLAN-INDEX as context, each subagent independently invents
its own dependency graph and the plans don't link up. **Always** pass
PLAN-INDEX to each subagent's context prompt.

### Plan 00 from a subagent is always worse than by hand
A subagent writing the meta-retrofit plan lacks visibility into the
specific OOS language each other plan used. Hand-write plan 00 last.

### Conflict-resolution / per-recipient filtering has hidden complexity
DM priority for same-token races, dice-rolls exempt from version checks,
SPECTATOR role rejection — these are easy to miss when briefing
subagents. Spell out the rules in the prompt.

### Migration numbering collides
Handwritten migrations (`packages/db/drizzle/000N_*.sql`) need unique
sequential numbers. Pre-assign in PLAN-INDEX to avoid subagents picking
the same number.

### Op kind enumeration
Each plan that adds ops should specify the EXACT op type strings (e.g.,
`HP_UPDATE`, `CONDITION_UPDATE`, `DEATH_SAVE_ROLLED`) so the union doesn't
collide. Include in subagent prompts.

### AC style drift
Some subagents will use numbered ACs (`1.` `2.`) instead of checkboxes
(`- [ ]`). Both are verifiable — number-style is non-standard but
acceptable per the methodology ("free-form prose is not allowed"; numbered
is structured).

### Don't recreate `SESSION-RECAP-*`
Per `project-methodology` pitfall: if a recap exists for today, APPEND a
"## Post-recap — <topic>" section rather than creating a new file.

## Sequencing decision template

When asking the user about bottleneck sequencing, present the trade-off in
this shape:

> Architecture doc says X is the bottleneck for ~70% of the roadmap. Doing it
> first unblocks A, B, C, D... Doing it later forces those features to either
> (a) accept the X risk or (b) re-do the X work later.
>
> Options:
> - X-first (recommended): the bottleneck plan. N+ downstream plans unblock
>   when X lands. Slower first-week velocity, faster end-to-end.
> - alternative-first: ship visible wins per week, defer X. Faster first-week
>   velocity, retrofit cost later.
> - parallel-safe first: ship features with no X dependencies in parallel.

User answer is binding. Encode the answer in `PLAN-INDEX.md` "Sequencing
rationale (user directive, YYYY-MM-DD)".

## Reference implementation

This skill is born from a 2026-07-17 session: the D&D VTT project project, 25 plans
produced, auth chosen as deferred. See `docs/plans/PLAN-INDEX.md` of that
project for the structure.
