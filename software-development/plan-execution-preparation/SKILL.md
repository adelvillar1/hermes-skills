---
name: plan-execution-preparation
description: When moving from a draft plan to active execution, scope it precisely and gather data-model answers before writing code. Prevents scope drift, ambiguous acceptance criteria, and mid-implementation blockers.
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [planning, scoping, execution, requirements, data-model, prisma]
    related_skills: [writing-plans, project-warmup, draft-feature-plan]
---

# Plan Execution Preparation

When a user says "let's scope out X" or "let's build this plan", they want the gap between the draft and active execution closed. This skill ensures the plan is crisp, bounded, and data-model questions are answered before code starts.

## Trigger

User says any of:
- "let's scope out the plan"
- "let's build this plan"
- "let's start on [plan-name]"
- "before we build this, I want clarity on..."
- "what's the concrete scope?"
- "update the plan with what's actually in scope"
- "what are we doing here exactly?"

## Workflow

### Step 1 — Read the plan file

Always start by reading the current plan `docs/plans/YYYY-MM-DD-<slug>.md`. Do NOT make assumptions about what the plan currently says — plans sit idle for days and their state may surprise you.

### Step 2 — Audit the plan against live code and docs

Before proposing any code, audit the plan against what already exists. Plans sit idle for days (or weeks) and parts may already be built, half-built, or conflict with shipped features.

Run checks for:

**Schema/model check:**
```bash
# Does the proposed table already exist?
grep -c 'model <name>' prisma/schema.prisma
# Does the migration already exist?
ls prisma/migrations/*<migration_name>*/migration.sql
```

**Existing code check:**
```bash
# Does the proposed endpoint already exist?
ls app/api/<path>/route.ts
# Does the proposed page already exist?
ls app/<path>/page.tsx
# Is the proposed component already extracted?
ls app/components/<name>.tsx
```

**Feature conflict check:**
```bash
# Does functional spec already claim this feature is done?
grep -i '<feature>' FUNCTIONAL-SPECIFICATIONS.md
# Does technical doc already document the proposed architecture?
grep -i '<concept>' TECHNICAL-DOCUMENTATION.md
```

For each check, report what's already done vs what's genuinely pending. A plan that says "create table X" when the table exists with the exact columns listed is step-complete, not half-done.

### Step 2b — Trace the dependency surface (blast-radius analysis)

The plan lists files it *intends* to touch. The actual blast radius is almost always larger. For any plan touching ≥5 files or spanning backend + frontend, trace the real dependency surface **before** scoping execution.

**Method:**

1. **Read every file the plan names.** Not just the plan's description of them — the actual code. Look at imports, function signatures, and return types.

2. **Follow the call graph outward.** For each file the plan names, trace who calls it and what it calls. An API route change means the frontend that calls it is also affected. A model change means every consumer of that model is affected.

3. **Identify shadow systems.** Large codebases often have multiple implementations of similar concepts (e.g., a CLI-only pipeline vs an API-level route). The plan may name one and be unaware of the other. Search for all references to the core concept.

4. **Build a blast-radius table:**

| # | Surface | File(s) | What changes | Blast radius |
|---|---------|---------|-------------|-------------|
| 1 | ... | ... | ... | Low/Medium/High |

5. **Flag conflation risk.** When the plan treats two separate systems as one, call it out explicitly. "The plan conflates X (CLI-only, used by `command`) and Y (API-level, used by dashboard). These share no code."

6. **Verify parameter assumptions.** If the plan proposes tuning parameters (K-factors, weights, thresholds), confirm those parameters actually exist in the codebase and match the plan's naming. Plans often reference parameters from documentation or analogy rather than from source.

7. **Propose phased scoping.** Group surfaces by dependency and risk. Isolate the low-risk backend-only work (new file, no existing deps) from the high-risk user-facing work (replacing existing behavior). Recommend independent phases.

**Key insight:** The plan's "Files to Be Touched" section is the *plan author's aspiration*. The dependency graph is *reality*. Always prefer reality.

See `references/surface-trace-technique.md` for a worked example.

### Step 3 — Read the data layer

Before proposing any code, query the database to confirm the data the plan depends on. Use `psql` or `npx prisma db execute` if Prisma is reliable, `psql "$STAGING_DB"` if not. The user will call out stale assumptions — don't rely on `docs/STATE-SNAPSHOT.md` or recaps for data-state.

Run checks for:
- Row counts on tables the plan reads
- Coverage counts (rows with narration vs rows without)
- Prisma schema validity (does the column exist in the generated client?)
- Whether structured columns are accessible or only present in raw SQL

### Step 3 — Eliminate speculative sections

Strip from the plan before active execution:
- "Future" / "when X completes" / "Phase N (optional)" sections
- FalkorDB / graph-native query paths when the PG path is the actual implementation
- Feature flags that are not needed for this scope
- Backend sort expansion or schema changes that are prerequisites, not part of the current work
- Season toggle widgets, mobile layout optimization, or other UI embellishments

If the user wants a future section, they will say so. Default to removing speculation.

### Step 4 — Add what's-in / what's-out

Insert an explicit "What we are doing" section followed by "What we are NOT doing". The user has already made these decisions; the plan should reflect them.

- What's in: shared component extraction, resolver wiring, tRPC endpoints, UI integration
- What's out: data pipeline, schema migration, new tables, feature flags, export integration, mobile optimization

### Step 5 — Define the concrete acceptance criteria

Replace vague criteria with specific ones. Instead of:

> "Insight panel shows on the detail page"

Use:

> "HarborShipDetailContent.tsx renders persona badge bar between hero/fact strip and tab bar. Badge click calls `ships.getInsights` and reveals insight panel below. Panel shows 'Ship & Route Fit' (T6) and 'Line Character' (T7) sections."

Each criterion names:
- File touched
- Location in the component (not just "on the page")
- Data source (tRPC endpoint name, table name)
- Label copy for the section

### Step 6 — Add a rollout order

Numbered steps that define a safe order of operations:

1. Extract shared components (no behavioral change)
2. Build resolver for one surface (ship = simplest)
3. Wire to one detail page (ship = proves the abstraction)
4. Replicate to second surface (cruise line)
5. Replicate to third surface (region)
6. Backfill: swap existing page to use shared components (itinerary = validation)
7. `tsc --noEmit` pass

### Step 7 — Surface open questions

If the plan references columns, tables, or row shapes that might not match reality, list them as explicit open questions rather than assuming the data model.

Example:

> **Open question:** Does `corridor_family_insights` store per-persona rows for region aggregations, or do we need to parse a JSON array in a single row per region×season?

### Step 8 — Wait for user approval before starting

Do NOT begin implementation until the user says "go" or "approved" or "let's start". The scoped plan is a contract — they need to sign it.

## Anti-patterns

1. **Starting implementation while scoping.** If the user says "let's scope out X" and you open a file to edit, you've skipped the contract step.
2. **Trusting STATE-SNAPSHOT.md or recaps for data state.** These files go stale. Query the DB every time.
3. **Leaving "Future: FalkorDB migration" in the active plan.** The user sees it as scope creep. Remove it.
4. **Rolling out itinerary first because it already works.** Extract shared components on a NEW surface first (ship), then backfill to the existing one (itinerary). This proves the abstraction doesn't break the known-good path.
5. **Trusting the plan's file list as complete.** The plan lists files the author *intends* to touch. The dependency graph almost always reveals additional surfaces (callers, consumers, shared models, frontend renderers). Always trace the graph for plans touching ≥5 files.

## Verification

After the scoped plan is written, run these checks before code starts:
- [ ] Plan reads the plan file and knows current status
- [ ] Data counts confirmed by live query (not recap or snapshot file)
- [ ] No speculative sections remain
- [ ] What's in / what's out is explicit
- [ ] Each acceptance criterion names a file, location, data source, and label
- [ ] Rollout order specifies safe sequence
- [ ] Open questions are listed and not hidden in prose
- [ ] User explicitly approves before implementation begins
