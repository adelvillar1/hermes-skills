---
name: external-spec-to-execution-plan
description: "Translate a complete external technical design document into a codebase-specific execution plan. Use when the user provides a finished spec/design doc and says 'create a plan to implement this', 'turn this into a plan', 'plan the build from this spec'. The spec IS the design — the plan is the execution contract that maps it to existing infrastructure, adds acceptance criteria, and defines delegation order. Distinct from draft-feature-plan (which designs from scratch); this skill governs the translation step."
tags: [project-management, planning, spec-translation]
related_skills: [draft-feature-plan, subagent-driven-development, pipeline-worker-pattern]
version: 1.0.0
---

# External Spec → Execution Plan

When a user provides a complete technical design document (attached file, pasted markdown, linked doc) and asks to "create a plan to implement this," the plan is an **execution contract**, not a redesign. The spec already made the design decisions; the plan's job is to map those decisions onto the existing codebase and make them buildable by subagents.

## When to use

- User attaches/pastes a complete technical spec and says "plan this", "create a plan to implement this", "turn this into tasks"
- The spec has its own data model, job definitions, infrastructure topology, and build sequence already decided
- Distinct from `draft-feature-plan` which designs from a verbal description — here the design is DONE, the plan is the bridge to implementation

## The translation mindset

The spec author (often the user, often with AI assistance) made design decisions in a vacuum — they describe what SHOULD exist. The plan author (you) knows what DOES exist. The plan's value is the delta:

| Spec says | Plan must answer |
|-----------|-----------------|
| "PostgreSQL tables in a `leads` schema" | Does Prisma support multiSchema? What version? What's the migration path for 114 existing models? |
| "Runs on pipeline-worker" | What's the JOB_REGISTRY pattern? What does workerType routing look like? What's the checkpoint protocol? |
| "Self-hosted Firecrawl" | Is it already deployed? What's the env var pattern? What's the concurrency constraint? |
| "Ollama classification" | Which client? `lib/ollama/client.ts`? What's the concurrency from prior campaigns? |
| "Playwright scraper" | Is Playwright already in scraper-worker's package.json? What version? |

## Workflow

### 1. Read the spec completely

Don't skim. The spec's "Build Sequence" section, "Cost Model", and "Guardrails" are as important as the data model. Note:
- What the spec explicitly excludes (these become "Out of Scope")
- What the spec marks as optional (surface as a decision point, don't unilaterally include or exclude)
- Legal/compliance constraints (these become hard rules in the plan)

### 2. Pre-flight: map spec components to existing infrastructure

For each component the spec names, verify against the real codebase:

```bash
# Does the infrastructure exist?
grep -rn "FIRECRAWL_URL" lib/ scripts/ --include="*.ts" | head -5
grep -n "playwright" scraper-worker/package.json

# What's the existing pattern?
head -80 lib/pipeline-jobs/registry.ts  # JOB_REGISTRY shape

# What Prisma version / features are available?
grep '"prisma"\|"@prisma/client"' package.json
grep "previewFeatures" prisma/schema.prisma

# What extensions are already installed?
grep -rn "CREATE EXTENSION" prisma/migrations/ --include="*.sql"
```

The plan's Context section must state what EXISTS vs what's NEW. This is the highest-value section — it prevents subagents from reinventing existing infrastructure.

### 3. Structure the plan as phases mapped to branches

For multi-worktree projects (develop / scraper / pipeline-worker), each phase MUST name its branch:

```markdown
### Phase 2 — FL SOT Scraper (scraper branch)
```

And the "Build Sequence & Delegation" section at the bottom must specify:
- Which phases are strictly sequential vs can overlap
- How many subagents per phase
- Which phases touch which worktrees (subagents can't touch two worktrees simultaneously)

### 4. Acceptance criteria: spec requirements → verifiable outcomes

Each spec requirement becomes one or more ACs. The AC format:
- Single observable outcome
- Verifiable by a concrete command (grep, psql, curl, tsc)
- Names the exact file path and expected content

**Anti-pattern:** "AC: Classification works" → **Correct:** "AC16: LLM call via Ollama client returns structured JSON `{ cruise_score, host_agency, signals, rationale }` — verified by running `npx tsx scripts/leads/classify.ts --limit=10 --dry-run` and inspecting output"

### 5. Risks: spec assumptions → tested claims

The spec makes assumptions ("Prisma supports multiSchema", "pg_trgm is available", "Firecrawl concurrency won't starve platform workloads"). The plan's Risks section must:
- Name each assumption
- State the impact if wrong
- Provide the mitigation (often: "test on staging before merging")

### 6. Out of Scope: respect the spec's exclusions + add engineering boundaries

The spec's "Explicitly excluded" section maps directly to Out of Scope. Additionally, add engineering boundaries the spec didn't consider:
- Downstream systems the spec mentions but doesn't design (outreach/sending layer)
- Optional components the spec marks as "skip if X suffices" (n8n)
- Business tasks that aren't engineering (partnership outreach)

## Pitfalls

### Pitfall 1: Redesigning instead of translating
The spec chose Reacher over email-verifier, gosom over Places API, Ollama over Anthropic-primary. Don't second-guess these in the plan. The plan's job is to make the spec's choices buildable, not to relitigate them. If a choice is genuinely infeasible (verified by pre-flight), surface it as a Risk with a question — don't silently substitute.

### Pitfall 2: Missing the existing-infrastructure mapping
A plan that says "deploy Firecrawl" when Firecrawl is already deployed (with an established `FIRECRAWL_URL` env var pattern in registry.ts) wastes a subagent's time and risks a parallel deployment. The Context section's "Existing infrastructure" vs "What does NOT exist yet" split is the most important part of the plan.

### Pitfall 3: Ignoring the spec's build sequence
The spec's "Build Sequence" section (Phase 1-5 with effort estimates) is a strong signal about dependency ordering. Respect it unless pre-flight reveals a different constraint (e.g., "Phase 2 needs a migration from Phase 1 that hasn't been deployed yet"). Don't reorder phases for aesthetic reasons.

### Pitfall 4: CLAUDE.local.md is NOT a shell-sourceable env file
In projects with a gitignored `CLAUDE.local.md` containing credentials in markdown table format: `source CLAUDE.local.md` does NOT export variables. You must grep values out:
```bash
STAGING_PG_PASSWORD="$(grep STAGING_DB_PW CLAUDE.local.md | grep -oP '(?<=\| `)[^`]+(?=`)' | head -1)"
```
The script may expect a different variable name than what's in the doc (e.g., `STAGING_PG_PASSWORD` vs `STAGING_DB_PW`).

### Pitfall 5: Multi-branch plans need explicit worktree attribution
Subagents run in the main working directory. If a phase touches `scraper-worker/` (which lives in `.worktrees/scraper`), the plan must say so explicitly, and the subagent context must include the worktree path. Otherwise the subagent edits files in the main dir that don't deploy to the scraper Railway service.

## Verification

After saving the plan:
- [ ] Every spec component has a corresponding phase + ACs
- [ ] Every "Existing infrastructure" claim was verified by grep/read (not assumed)
- [ ] Every phase names its branch
- [ ] The delegation section specifies sequential vs parallel phases
- [ ] Out of Scope includes the spec's explicit exclusions
- [ ] Risks section covers at least one "spec assumption that could be wrong"
- [ ] `npx tsc --noEmit` passes BEFORE saving (the plan references real file paths)
