---
name: codebase-survey
description: Survey an existing codebase to understand its structure,.
---

# Codebase Survey

Systematically discover what an existing codebase contains, how it's organized, and where the complexity lives. Produces a synthesized report rather than a raw file dump.

## When to Use

- User says: "do a deep dive of this project", "explore this codebase", "survey the project", "understand the architecture", "onboard me to this project", "walk me through this repo", "what are we working with here"
- Picking up a project you haven't worked on in a long time and need a refresh before starting work
- Pre-planning reconnaissance: need to know the schema, API surface, and dependency graph before estimating a feature
- Handoff context: explaining to the user (or a future reader) what the codebase currently contains

## Step 0: Define the question BEFORE reading or querying

A "deep dive" is not license to explore freely. Before reading CLAUDE.md, before running a single query, answer three questions:

1. **Is there a specific question?** "Deep dive on X" without a stated question is a request to manufacture findings. Don't manufacture. Ask: "What specifically do you want to know — counts, a recent change, a specific gap, an audit, a decision that needs data?" If the user can't articulate one, the right move is to ask, not to invent.
2. **Is the topic actually a feature in this project?** Search the contract docs (see Step 0.5) for the topic by name. If `TECHNICAL-DOCUMENTATION.md` and `FUNCTIONAL-SPECIFICATIONS.md` never describe it as a user-facing feature or a documented subsystem, the topic may be internal plumbing — a deep dive into it can produce findings the user doesn't care about.
3. **What does "done" look like?** State the deliverable in one sentence. Examples: "A count of active itins missing routeSignature grouped by cause." "A list of port-visit match-rate discrepancies by year with root cause for each." "A summary of how the port_visit_itineraries junction table is populated and consumed." Without this, you will over-explore.

If any of these are unclear, ask before proceeding. The cost of a clarifying question is one turn; the cost of a misaligned 20-query investigation is the user's trust.

## Important: CLAUDE.md overrides generic survey

Many projects (especially this user's) maintain a CLAUDE.md file with a "Where to find things" map. **If the project has a well-structured CLAUDE.md, read it FIRST — before any of the steps below.** Use the "Where to find things" map as your primary survey guide. Steps below become fallbacks for areas the CLAUDE.md doesn't cover.

A rich CLAUDE.md will tell you:
- The project's doc tree structure (which files to read for architecture, schema, features, pipeline)
- The branch → environment topology
- Current state / what's shipped
- Hard rules and conventions
- Contracts (what artifacts matter)

This is more efficient than running a generic breadth-first scan. Only fall back to the generic workflow if the CLAUDE.md is absent, sparse, or stale.

### Targeted Deep Dive Pattern

After warmup (CLAUDE.md, CLAUDE.local.md, recaps, active plans loaded):

1. **Read the relevant feature doc(s)** — the `docs/feature-<slug>.md` or `docs/technical-documentation.md` section for that domain. This gives you the contract: what it's supposed to do, API schemas, prompt strategy, business rules, acceptance criteria.

2. **Read the Prisma schema model(s)** — the `model Booking { ... }` block. Note every field, relation, index, and `@map` column name. Cross-reference against the feature doc's field descriptions.

3. **Read ALL API routes under the domain** — every file in `src/app/api/<domain>/route.ts` and any sub-routes. In a booking import system, that's extract, reprocess, and import — three routes that chain together. Note validation patterns, auth guards, feature-flag guards, and transaction patterns.

4. **Read the pipeline/infrastructure files** — the shared library files that the routes depend on: AI clients, extractors, prompt parsers, matchers, loggers, cost calculators. These will contain the actual implementation depth (vision vs. text extraction, spatial ordering, fuzzy matching algorithms).

5. **Read the UI components** — the page and review component. Note the data flow: how extracted data travels from API → UI state → submit. Pay special attention to validation UX, error states, partial submission, and dormant features (like hidden reprocess buttons).

6. **Synthesize into a structured report:**
   - **Architecture overview** — ASCII/flow diagram showing the phases and data movement
   - **Data model** — the Booking model with field-by-field mapping from extraction → import
   - **Detailed flow** — each phase (extract → review → import) with endpoint, auth, processing logic
   - **Edge cases & business rules** — table of rules and where they're enforced (frontend vs backend vs both)
   - **Shared infrastructure** — the `src/lib/ai/` pipeline and how it's structured for reuse
   - **Dormant / hidden paths** — features that exist in code but are inaccessible from UI (like the Sonnet reprocess endpoint)
   - **Field-level mapping** — which extraction fields map to which import fields, with transformations (backfills, defaults, type coercions)

   Format: plain text or markdown. Do NOT paste raw file contents — synthesize. The report should convey the full data flow from input to persistence.

### Variant: Full App Deep Dive (Comprehensive Domain Survey)

**When:** The user asks for a "deep dive of the app" without naming a specific domain — they want the full picture of what the application does, its major features, data flows, and architecture. This is broader than a single-domain targeted dive but more focused than a generic codebase survey.

**Precondition:** Project context already loaded (CLAUDE.md, schema, recaps, etc.)

**Steps:**

1. **Schema audit** — Read the full Prisma schema. For each model, note: purpose, key fields, relations, indexes, soft-delete status. Group models by domain (auth, bookings, payments, CRM, AI pipeline, admin). Identify the central entity (usually `Booking`) and how everything orbits it.

2. **Route inventory** — List all API routes (`find src/app/api -type f`). Group by domain. For each domain, read the main CRUD route and any special routes (extract, import, upload, reports). Note auth guards, role restrictions, and feature-flag gates.

3. **Page inventory** — List all dashboard pages (`find src/app/(dashboard) -type f`). Group by domain. For each major domain, read the list page to understand the UX: filters, bulk actions, mobile/desktop split, CSV export.

4. **Key feature deep dives** — For each major feature area (AI extraction, commission checks, agent payroll, customer management, reports), do a lightweight version of the targeted deep dive:
   - Read the feature doc if it exists
   - Read the main API route(s)
   - Read the page component
   - Note the data flow and any special patterns

5. **Shared infrastructure** — Read the key library files: auth, Prisma client + soft-delete middleware, agency scope, cache layer, AI pipeline (`src/lib/ai/`). Note reusable patterns and cross-cutting concerns.

6. **Testing & deployment** — Note test count, frameworks, E2E coverage. Read Dockerfile and deployment config.

7. **Synthesize into a structured report:**
   - **Overview** — what the app does, who uses it, production URL
   - **Tech stack** — concise bullet list
   - **Architecture** — multi-tenancy, auth, soft deletes, role hierarchy
   - **Database** — model count, central entities, notable patterns
   - **API surface** — route count, grouped by domain
   - **Key features** — for each major feature: what it does, how it works, special patterns
   - **Frontend** — route groups, shared components, responsive patterns
   - **Shared infrastructure** — AI pipeline, extraction patterns, matching algorithms
   - **Testing** — unit + E2E coverage
   - **Deployment** — environments, branch flow
   - **Current state** — what's shipped, what's deferred, recent activity
   - **Notable patterns** — idioms that show up repeatedly

**Key difference from targeted deep dive:** Covers ALL domains at moderate depth rather than ONE domain at full depth. The user gets a complete picture of the application's capabilities and architecture.

### Variant: Data Architecture Deep Dive

**When:** The user asks for a deep dive into the data layer, database architecture, caching strategy, or storage systems — not a specific feature but the foundational data infrastructure.

**Precondition:** Project context already loaded (CLAUDE.md, schema, etc.)

**Steps:**

1. **Schema breadth audit** — Count models, lines, relationships. Identify: structural tables, derived tables, insight/precompute tables, content tables, operational tables. Note which tables are time-series (grow indefinitely) vs static.

2. **Embedding strategy analysis** — Identify ALL embedding systems:
   - Float[] arrays with in-memory index (high-volume, chat cache)
   - pgvector with HNSW (semantic search, discovery)
   - Any other vector storage (Redis, external services)
   Document dimensions, models, indexing strategy, lookup patterns

3. **Knowledge graph inspection** — If FalkorDB/Neo4j exists:
   - Node labels and counts
   - Edge type and their semantics
   - Projection patterns (how PG data becomes graph nodes)
   - Replication/sync strategy

4. **Caching hierarchy** — Document the full cache stack:
   - L1: In-memory (embedding index, hot data)
   - L2: Redis (speed cache, ephemeral)
   - L3: PostgreSQL (source of truth, persistent)
   - For each: invalidation strategy, TTL, what happens on miss

5. **Cost engineering analysis** — If AI/LLM costs matter:
   - Tiered cache hit rates and costs
   - Blended per-query cost
   - Savings from each optimization tier

6. **Synthesize into a structured report:**
   - **Storage topology** — what lives where and why
   - **Scaling characteristics** — memory bounds, query complexity, growth trajectories
   - **Cost model** — per-query economics, infrastructure costs
   - **Risk assessment** — single points of failure, complexity thresholds, maintenance burden
   - **Architectural tradeoffs** — why each choice was made, what alternatives exist

### Variant: Dashboard KPI Deep Dive

**When:** The user asks for a deep dive on dashboard analytics, KPI cards, or monthly metrics — "deep dive on the dashboard, particularly X and Y for the month." This is a specialized targeted deep dive that traces each KPI from the UI card back to the database query.

**Precondition:** Project context loaded (CLAUDE.md, schema). The dashboard page component and API route exist.

**Steps:**

1. **Read the dashboard page component** — Identify what KPI cards are rendered, what data each card displays (MTD headline, YTD subtitle, or single number), and any role-based visibility logic (owner-only cards, view-as-agent filtering).

2. **Read the dashboard API route** — For each KPI, trace the exact Prisma `aggregate()` or `findMany()` query. Note:
   - What `where` clause filters are applied (date ranges, soft-delete, agency scope, agent scope)
   - Which field is being summed (`_sum: { packagePrice }`, `_sum: { commissionReceived }`, etc.)
   - Whether the query uses the `agencyScope()` helper or hardcodes `session.user.agencyId`
   - Whether the query filters on a date field (`bookingDate`, `supplierPaidDate`, `paymentDate`) or has no date filter at all

3. **Read the stats/KPI card component** — Check how each KPI is displayed:
   - Does the card label imply a time period (e.g., "Anticipated (Jun)") but the query has no date filter? This is a **stock-vs-flow mismatch** — the label implies a monthly flow but the query computes an all-time stock.
   - Is MTD shown as headline with YTD as subtitle, or is only one number shown?
   - Are null `mtd` values handled differently in the UI?

4. **Read the Prisma schema for each aggregated model** — Cross-reference the fields being summed against the schema. Note which fields are `Decimal(10,2)` vs `Decimal(5,4)` (commission rates). Check for nullable fields that could produce null sums.

5. **Trace role-based and view-as-agent filter propagation** — For each KPI query, verify:
   - Agency owner sees all bookings in their agency
   - Travel agent sees only their own bookings
   - View-as-agent filter (`viewAsAgentId`) correctly overrides the agent filter
   - Agent payment KPIs are owner-only (agents don't see agency-wide payment totals)

6. **Synthesize into a structured report:**
   - **KPI inventory** — table of each card: label, MTD query, YTD query, display format, role visibility
   - **Data flow diagram** — how each number travels from DB aggregate → API response → UI card
   - **Findings** — stock-vs-flow mismatches, missing filters, misleading labels, role visibility gaps, view-as-agent propagation issues
   - **Lifecycle map** — for related domains (e.g., commission lifecycle: anticipated → received → agent-paid), show how bookings move through states and which KPIs capture each state

**Key audit checks per KPI:**

| Check | What to look for |
|-------|-----------------|
| Stock vs flow | Label says "(Jun)" but query has no date filter — it's an all-time sum, not monthly |
| Soft-delete filter | Middleware is *supposed* to auto-inject `deletedAt: null` on `aggregate`/`findMany`, but do NOT assume it did — verify each query's `where` clause explicitly. See `prisma-soft-delete` Pitfall #6. Models in `NO_SOFT_DELETE` are exempt by design. |
| Agency scope | Query uses `agencyScope(session.user)` helper or hardcodes `agencyId` — both work, but inconsistency signals code smell |
| View-as-agent propagation | `viewAsAgentId` from query param correctly overrides `agentScope()` filter in aggregate queries |
| Role-based visibility | Owner-only KPIs (agent payments) are conditionally rendered and conditionally queried |
| Nullable sum fields | `_sum: { commissionReceived }` on a nullable `Decimal?` field returns null, not 0 — code should use `?? 0` |
| Relation filter soft-delete | When filtering through a relation (`batch: { agencyId }`), the related model's `deletedAt` is NOT auto-filtered by the middleware — add explicit `deletedAt: null` in the relation filter if needed |

### Comparison to Full Survey

| Aspect | Full codebase survey | Targeted domain deep dive | Dashboard KPI deep dive |
|--------|---------------------|--------------------------|-------------------------|
| Scope | Entire project | One domain/feature | Dashboard metrics + data flow |
| Approach | Breadth-first (14 steps) | Depth-first (6 steps) | KPI-trace (6 steps) |
| Reading pattern | Representative samples | Every file in the domain | UI card → API query → schema field |
| Output | Project-level state summary | Domain-level architecture + data flow | KPI inventory + findings + lifecycle map |
| Precondition | Project unfamiliar | Already worked on this project | Dashboard exists, KPI cards rendered |

## When NOT to Use (Full Survey)

- The project is trivial (< 20 files) — skip straight to reading the files
- You're already mid-session and the user names a specific file to edit — just read that file
- The user wants a narrow answer like "where is X defined" — use grep or the knowledge graph instead
- **Python projects with good documentation**: If the project has a well-structured `SPEC.md` or `ARCHITECTURE.md` and clear module boundaries, you may be able to do a lighter survey. Still run the test suite and file-size audit.

## Workflow

Run these steps in order. At each step, **synthesize** what you found before moving on. The final output is a cohesive report, not a concatenation of individual file reads.

### 1. Establish repository state

```bash
git branch -a
git log --oneline -20
```

Look for:
- Active branch (likely where work happens)
- Branch topology (feature branches, main/staging/development flow)
- Recent commit activity and commit message patterns
- Whether the working tree is clean or has uncommitted changes

**Goal:** Understand the project's cadence and current position in the commit graph.

### 2. Top-level structure and scale

```bash
ls -la
find src -type f | head -60
echo "---TOTAL---" && find src -type f | wc -l
```

Break down by major directory:
- App routes/pages
- Components
- Library/utils
- Tests
- Config files
- Documentation

**Goal:** Know how big the codebase is and where the files live.

### 3. Package manifest and README

Read `package.json` (or equivalent: `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`) and `README.md`.

Capture:
- Framework and major dependencies
- Build/dev/test commands (e.g., `npm run dev`, `pytest`, `cargo test`, `go test`)
- Project purpose and live URL (if any)
- Environment setup instructions

**Goal:** Confirm tech stack and entry points.

### 4. Database schema (if ORM/schema file exists)

Read the schema definition (e.g., `prisma/schema.prisma`, `schema.sql`, `models.py`).

Produce a table summary:

| Table | Purpose | Key relationships |

Note soft-delete conventions, multi-tenancy fields, and any unusual patterns.

**Goal:** Understand the data model and how entities relate.

### 5. Core documentation files

**Hard gate — read these BEFORE running any DB query or codebase scan when the user asks a question about a specific topic.** The contract docs tell you whether the topic is even a thing in the project. Reading them is cheap; running 20 ad-hoc queries without reading them is expensive.

Read the project's contract docs — typically `TECHNICAL-DOCUMENTATION.md` and `FUNCTIONAL-SPECIFICATIONS.md` at the repo root, plus any `CLAUDE.md`, `docs/architecture/`, `docs/features/` topical files. Read only if they exist and are reasonably sized (< ~600 lines each). For very large docs, read the table of contents and the "Today's state" or "Status" sections.

**Search order for a topic-specific question:**
1. `CLAUDE.md` — "Where to find things" map, hard rules, today's state
2. `TECHNICAL-DOCUMENTATION.md` — does the topic appear as a documented subsystem, table, phase, or service?
3. `FUNCTIONAL-SPECIFICATIONS.md` — does the topic appear as a user-facing feature? (If no in both, it's internal plumbing — adjust the question framing accordingly.)
4. `docs/features/<topic>.md` or `docs/architecture/<topic>.md` — deeper contract for the topic
5. `docs/plans/` — active or historical plans touching the topic
6. Only then: source files, schema, queries

Capture:
- Architecture decisions
- Role/permission model
- Feature completion status
- Known debt or deferred work
- Whether the topic is a feature or internal plumbing

**Goal:** Understand what the system is supposed to do and what's already built, AND verify the topic exists as documented before treating it as a deep-dive target.

### 6. Access control model

Review the project's access control architecture — focusing on *what* is protected, not the specific secret values.

Capture:
- Auth strategy (JWT, session, OAuth) — from import/type files, not credential files
- Role model and how roles are enforced (middleware, decorators, guards on routes)
- Protected vs public route patterns
- Middleware redirects and guards

**Do NOT read files containing actual secrets** (credential files, `.env`, `CLAUDE.local.md`, API key configs, JWT secret values, OAuth client secrets, etc.). Read only:
- Route middleware files (which check auth, not the auth config itself)
- Type/interface files for auth models
- The Prisma schema's User/Account/Session models
- Route handler files to see guard patterns

The goal is understanding *who can access what*, not finding credential values.

### 7. Key library files

Read 3–5 of the most consequential utility files:
- Database client singleton + soft-delete middleware
- Auth middleware (route guards, not credential config)
- Cache layer
- Feature flags / agency scope

**Do NOT read:** files containing actual credential values, API keys, encryption secrets, or password hashes. Read the interface types and middleware patterns only.

**Goal:** Understand the platform's shared infrastructure and guardrails.

### 8. Directory tree depth check

```bash
find src/app -type d | sort       # or pages/, routes/, controllers/
```

Map the routing structure. Note nested routes, parallel routes, route groups.

**Goal:** Visualize the URL surface and page hierarchy.

### 9. Component and API inventory

Count files per category:

```bash
find src/components -type f | wc -l
find src/app/api -type f | wc -l
find src/lib -type f | wc -l
```

Read a representative sample (1–2 files) from each major component area if the user hasn't specified a focus area.

**Goal:** Know where UI components and API routes live.

### 10. Tests and scripts

List test files and utility scripts.

```bash
find tests -type f | sort
find scripts -type f | sort
```

For Python projects, also capture:
- pytest configuration (from `pyproject.toml` or `pytest.ini`)
- Test count: `pytest --co -q | tail -1`
- Fixture files: `find tests -name "conftest.py"`

Note test quantity, framework, and coverage. Note any data migration/import scripts.

**Goal:** Understand test infrastructure and one-off tooling.

### 11. Deployment and environment

Read deployment docs or CI config. Note:
- Hosting platform
- Branch → environment mapping
- How environment variables are managed
- Database migration strategy

**Goal:** Know how the project ships.

### 12. Synthesize the report

Produce a structured summary covering:

1. **Project identity** — name, purpose, live URL, repo
2. **Tech stack** — concise bullet list
3. **Scale** — total file count, test count, schema line count
4. **Data model** — table count + notable relationships
5. **Key engineering decisions** — architecture patterns worth highlighting
6. **Features implemented** — what's complete
7. **Testing & quality** — test count, frameworks, coverage posture
8. **Deployment** — environments, branch flow
9. **Current state** — recent activity, active plans, known debt
10. **Notable code patterns** — idioms that show up repeatedly
11. **Maintainability assessment** — file size distribution, separation of concerns, coupling analysis (see below)

Use plain text or markdown. Do NOT paste raw file contents unless quoting a specific pattern. The report should be readable by a human in 2–3 minutes.

#### Maintainability assessment (new)

After the standard synthesis, add a **maintainability section** that surfaces structural risks before they become blockers:

**File size audit:**
```bash
# Find the largest files (potential monoliths)
find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.tsx" -o -name "*.rs" -o -name "*.go" \) -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/venv/*" -not -path "*/__pycache__/*" | xargs wc -l | sort -rn | head -20
```

Flag any file > 400 lines as a potential monolith. Flag any file > 800 lines as a definite refactor target.

**Method/class count audit:**
```bash
# Python: count methods per class
grep -c "def " src/core/engine.py

# Python: count classes per module
grep -c "^class " src/core/engine.py

# JS: count functions per file
grep -c "function " app/static/js/charts.js
```

Flag any class with > 15 methods or any file with > 30 functions as violating single-responsibility.

**Coupling signals to check:**
- Does one class handle > 3 unrelated feature domains? (e.g., portfolio views + risk analysis + workforce + trends all in one processor)
- Does the frontend have one function per API endpoint, or is there a registry/dispatch pattern?
- Are chart rendering concerns duplicated between live dashboard and export formats?
- Is there a shared type/schema between backend and frontend, or do they maintain separate contracts?
## Maintainability Assessment (Python)

| Grade | Criteria |
|-------|----------|
| A | Files < 300 lines, clear module boundaries, type hints everywhere, pytest fixtures, shared types in `models.py` or `schemas.py` |
| B | Some files 300-500 lines, minor duplication, mostly clean boundaries, some type hints |
| C | Several files 500-800 lines, noticeable duplication, fuzzy boundaries, inconsistent type hints |
| D | Multiple files > 800 lines, heavy duplication, no clear separation, untyped |
| F | Monolithic files > 1200 lines, everything coupled, changes require touching 4+ files, no tests |

## Git Repository State

For projects without an existing `.git` directory:
- Note "not a git repository" in the survey report
- Do NOT attempt to initialize git unless the user explicitly requests it
- The absence of version control is itself a signal (no commit history, no branch tracking, no rollback capability)
- If the user later provides a remote URL, use `git init` + `git remote add origin` + `git fetch` to establish the connection, then proceed with the survey

Include specific refactor recommendations: "Split AllocationProcessor into Portfolio/Risk/Workforce/Project/People/Trend processors" or "Consolidate 45 loadChart() functions into a chart registry."

**Why this matters:** The user often asks "what can you tell me about the app?" or "is there a better tech stack?" after a survey. The maintainability assessment gives them the vocabulary and evidence to make that decision, rather than leaving it as an open-ended question.

### 13. Assess project maturity and velocity

After reading the codebase, produce a **complexity assessment** — not just file counts. Answer:

- **How long did this take to build?** Compare scope against the user's known velocity. If they've built similar things before, use that as a baseline for scope estimates rather than generic industry averages.
- **What does the architecture reveal about domain expertise?** Edge types that serve specific advisor query patterns, pipeline optimizations that reflect years of domain knowledge (port tiering by traffic with 85% page-load reduction, dual-emit structured extraction, season-mode distinction in T7 prompts) — these are not accidental. Note them as domain-compression signals.
- **What's the actual complexity driver?** A project with 50 tables but straightforward CRUD is less complex than a project with 16 tables but multi-environment replication, knowledge graph sync, and distributed pipeline orchestration. Complexity is in the *interactions*, not the entity count.
- **Could a team replicate this timeline?** Be honest. If the architecture embeds years of domain knowledge that a team would need to learn, say so. The user's output is not a benchmark for standard team velocity — it's a different throughput model entirely (zero handoffs, zero meetings, domain-compressed decision-making).

**Goal:** The survey should convey *what kind of project this is*, not just what it contains.

### 14. Synthesize user context for future readers

After the report, add a brief operating-context note that any future session will benefit from:

- Everything in this project's methodology is a compression mechanism: plans, recaps, contract docs, skills, local env files — all designed to eliminate context re-discovery.
- Communication should be action-first. Read everything before suggesting anything. Own errors immediately.
- This is a live production product with real customers. Uptime is non-negotiable.

**Goal:** Any future agent that reads this survey report understands who the user is and how they operate, not just what the code contains.

## Granularity Rules

- **Stop at the right level of detail.** For a 50-file project, read most files. For a 500-file project, read representative samples and summarize the rest by category.
- **Don't read every file.** The goal is understanding, not comprehensive indexing. Use the knowledge graph or grep for drill-downs on specific areas.
- **Synthesize as you go.** Don't accumulate 20 file reads and dump them all at the end. Each section should feed the synthesis.
- **Surface the project's own docs, don't replace them.** The survey points TO the feature docs; it doesn't absorb them.

## Common Pitfalls

1. **Raw catalogue dump.** Listing every file in `src/components/` is not a survey — it's a directory listing. Group by function and summarize.
2. **Reading files the project doesn't have.** If there's no `README.md`, note it and move on. Don't fabricate.
3. **Getting lost in one file.** If a file is huge (> 400 lines), read the first 100 and the last 50, or scan for exported functions. The survey is breadth-first, not depth-first.
4. **Ignoring git history.** The commit log tells you what the team actually values (feature commits vs. fix commits vs. doc commits). Use it.
5. **Forgetting environment discipline.** If the project has staging/production credentials in a gitignored file, reference the env var names only — never read or include actual secret values in the synthesized report.
6. **Stopping at "what" instead of "how maintainable."** A survey that only lists files and endpoints misses the user's real question: "can I work with this?" Always include the maintainability assessment (file size audit, coupling analysis, grade) so the user has actionable intelligence, not just a catalogue.
7. **Confusing targeted deep dive with full survey.** When the user asks for a "deep dive of X" in an already-familiar project, do NOT run the full 14-step codebase survey. That wastes time reading areas they already know. Use the targeted domain deep dive pattern instead (6 steps, depth-first into one area).
8. **Confusing targeted deep dive with lightweight warmup.** The `project-warmup` skill's lightweight mode handles "answer a question by reading one doc." A deep dive requires reading ALL source files (routes, pipeline, schema, UI) under the domain. The separation line: if you can answer from one doc file, it's lightweight warmup. If you need to read multiple implementation files + the feature doc, it's a targeted deep dive. When in doubt, lean toward deep dive — reading extra files costs minutes, piecing together incomplete context costs the user's time.
9. **Tool-call loop exhaustion.** If you find yourself calling the same tool repeatedly with diminishing returns (e.g., running `grep -r "^def "` 10+ times to get a method count), STOP. Summarize what you have and move on. The user will tell you if they need more detail. Burning tool iterations on marginal data points wastes the user's time and hits iteration limits.
10. **Missing the "initialize properly" signal.** When a user says "let's initialize this project properly" after a codebase survey, they want the `init-project-structure` skill applied to an existing codebase. The project has code but lacks methodology (CLAUDE.md, docs/, contracts). Detect this with the pre-flight checks from `init-project-structure` and scaffold around the existing code rather than treating it as greenfield.

11. **🚨 API response key mismatch — the silent feature killer.** During targeted deep dives, always trace the API response shape from backend route → API client → frontend consumer. A mismatch (backend returns `{ recommendations: [...] }` but frontend destructures `.itineraries`) produces a feature that renders empty data with zero errors. This is the #1 silent bug in Express+React apps. **Detection pattern:** grep the route file for `res.json({` to find the response key, then grep the frontend for the corresponding `.property` access. If they don't match, the feature is broken. **Common victims:** recommendation/related-item endpoints (often added later with different naming conventions), nested data endpoints (route returns `{ itinerary: { ports: [...] } }` but consumer accesses `data.ports`), and catch-fallback defaults (`catch(() => ({ itineraries: [] }))` when the actual key is `recommendations`).
12. **🚨 Delegated deep-dive false positives.** When delegating a full-app deep dive to a subagent via `subagent dispatch`, the subagent reads many files and synthesizes a report — but can produce false positives. Example: reporting "CORS not configured" when it is, or "no pagination" when it exists. **Before converting deep-dive findings into a remediation plan, spot-check at least the high-priority items against actual code.** One `grep` per finding catches most false positives. A plan built on unverified findings includes unnecessary work items and erodes trust.
13. **Delegating full-app deep dives to subagents.** The full-app deep dive variant requires reading dozens of source files, which floods the controller's context. Delegating to a subagent via `subagent dispatch` with a structured 10–14 area audit prompt is an effective alternative: the controller stays clean, the subagent reads files and synthesizes, the controller reviews the summary and plans next steps. This is especially valuable for Python projects where the file count is manageable for a single subagent.
14. **API response shape not verified against frontend consumption.** When doing a mobile/frontend deep dive, the most common silent bug is: the API route returns `res.json({ recommendations: [...] })` but the frontend destructures `data.itineraries`. All data silently becomes empty arrays. For every API function consumed by the frontend, cross-reference the route handler's `res.json()` shape against the consumer's destructuring pattern. Also check `.catch()` fallback shapes. See `references/mobile-ui-review-patterns.md` §1 for the full audit pattern.
15. **`search_files` with `target='files'` uses glob patterns, not regex.** A pattern like `deckgl|deck.gl|maplibre` will be treated as a literal filename containing pipes, not as a regex OR. Use `terminal` with `find` instead, or use `search_files` with `target='content'` (which uses ripgrep regex) and then deduplicate filenames. **Detection:** `search_files` returns 0 results for a pattern you know exists → check whether `target='files'` vs `target='content'` is the issue.

16. **🚨 Conflating separate systems during deep dives.** When a codebase has multiple systems with similar names or overlapping concerns, it's easy to merge them mentally. Example: "port maps" could mean (a) SVG location map in hero, (b) 3D Deck.gl map with buildings, (c) 2D JPEG static images for mobile. Each has different data sources, coordinate policies, consumers, and lifecycles. **When the user corrects your framing, accept the correction immediately and re-segment your mental model.** Don't defend the conflation with "but the docs say..." — docs can be misleading or stale. The user's correction is ground truth. Re-trace each system independently after correction.

21. **🚨 Refusing to re-frame when the user provides new context mid-dive.** Symptom: the agent committed to an interpretation early in a deep-dive ("this is a stale-SVG problem caused by the matcher"), then the user provides a mid-dive correction ("this is a B2B cruise, so the mid-cruise Miami stop is correct"), and the agent defends the original framing instead of accepting the new framing immediately. The damage is multiplicative: the user loses trust in the entire investigation, future findings are filtered through skepticism, and the session ends with a fractured picture. **Rule:** when the user provides a correction or new framing during a deep-dive, accept it on the spot and re-segment the mental model. Don't defend. Don't append a footnote "although your correction would mean…". The user's domain knowledge is ground truth; the agent's prior inference is not. **Real pattern (2026-06-26, this project):** deep-dive into "missing last leg on route map SVGs" started with an interpretation that a junction-row was missing → user interrupted to say "this is a back-to-back cruise, the arrival in the middle is correct" → the agent immediately re-segmented into (a) stale-SVG (separate from junction), (b) cursor-target ordering for B2B combos, (c) latent cross-coder divergence. The user's correction didn't reduce work — it increased the surface area the agent eventually uncovered (3 bug classes instead of 1). Trust is preserved by accepting fast and re-segmenting fast.

22. **🚨 Manufacturing findings when the question isn't defined.** A user request like "do a deep dive on X" without a stated question is NOT license to explore freely. The temptation is to run ~10-20 ad-hoc queries, find whatever looks anomalous, and present those as findings. This produces: (a) noise the user has to filter, (b) findings about areas they don't care about, (c) speculative claims based by data patterns whose actual meaning the agent didn't verify. **The fix:** Before any query or read, answer: is there a specific question? Is this topic even a feature in the project (check `TECHNICAL-DOCUMENTATION.md` and `FUNCTIONAL-SPECIFICATIONS.md`)? What does "done" look like in one sentence? If any of these are unclear, ASK. One clarifying question costs one turn; a misaligned investigation costs the user's trust. **Detection:** you find yourself about to run query #5, #10, or #20 with no stated hypothesis — stop and either ask or present what you have so far.

23. **🚨 Over-applying "ask first" to read-only deep dives.** Pitfall 22 is about *not* asking when a question is undefined and the work has side effects (DB writes, deploys, config edits, metered API calls, data-mutating queries). The discriminator is **side effects**, not the request phrasing. A user saying "do a deep dive on the pathfinding algorithm and the MapLibre 3D maps" is **not** the same risk profile as "do a deep dive on port visit match rates" — the first is reading code (no blast radius, scope emerges from the code itself), the second is running queries against staging data. **Symptom:** the agent fires two `an ask-the-user prompt` calls before reading a single file, with safety-flavored language ("defaults are dangerous", "scope this before any query"). The user pushes back: *"why are you asking, you're just reading files?"* **The fix:** when the deliverable is reading code, dive in. The question of scope resolves itself as the file tree reveals its shape. If after reading you find three plausible interpretations, present them in one sentence in the report and let the user pick — don't gate the entire read on a pre-flight question. **Where the rule still applies:** live DB queries (especially on production), deploys, data deletions, feature flag flips, any action with a blast radius larger than the current session. The skill's pre-flight questions (Step 0) are calibrated for query-driven dives; for code-reading dives, skip them. **Detection:** you are about to call `an ask-the-user prompt` about scope before reading any source files. Stop. Read first, surface scope questions in the report if needed.

24. **🚨 The "deep dive" deliverable shape that actually works.** Pitfall 23 covers *whether to ask first*. Once you're reading, the next failure mode is delivering the wrong shape: dumping a flat file-by-file summary, wall-of-text prose, or a vague "here's what I found" without structure. The shape that works for code-reading deep dives (validated 2026-06-27 in this project: A* pathfinder + MapLibre 3D maps) has these sections, in this order: (1) **Algorithm/code walkthrough** — what does the code actually do, in human prose, with the key data structures called out. (2) **Architecture seams** — where the data comes from, where it goes, what touches what. (3) **Edge cases — what is and isn't handled**, with specific line numbers when possible. (4) **Findings** — dead code, bugs, sharp edges, things the user should know. (5) **Suggested follow-ups** — non-actionable, just named, so the user can pick. Do NOT: open with a 5-paragraph preamble, recap the file tree, narrate your reading process, paste large code blocks without commentary, or end with "let me know if you want me to dig deeper." Do: name the actual file paths and line numbers when you find bugs, contrast the code's stated behavior with its actual behavior, and surface the discrepancies (the dead env var, the version drift, the missing import) — those are what the user actually wanted from "deep dive." **Detection:** the writeup is over 2000 words and the user hasn't engaged yet — you're being too verbose. Trim. **Symptom of success:** the user replies "it looks great" or starts asking about a specific finding within their first reply.

25. **🚨 Treating legacy code as active during analysis.** Symptom: during a deep dive, the agent reads and analyzes legacy/deprecated components alongside active ones, presenting findings about both as if they're equally relevant. The user then has to interrupt with "that modal is legacy code" or "we don't use that path anymore." This wastes the user's time and signals the agent didn't do basic reconnaissance on which code paths are actually live. **The fix:** before analyzing any feature area, check for dual-path or legacy-path indicators: (a) search for feature-flag toggles (`isHarborEnabled`, `isNewUI`, `useFeatureFlag`), (b) check for files with "legacy", "old", "deprecated" in their names or comments, (c) look at the page router — does it conditionally render one of two components? (d) check git history — is one path actively committed to while the other is stale? (e) check if the user has previously stated a preference for one UI path. If you find a legacy path, **exclude it from analysis unless the user explicitly asks for it.** State in your report: "Legacy path X exists but is deprecated; analysis focuses on active path Y." **Real example (2026-06-28, this project):** deep dive on itinerary export functionality included `ItineraryDetailModal.tsx` (glassmorphism, 1954 lines) in the analysis alongside the active Harbor export page. The user had to explicitly state "the itinerary modal is legacy code" — the agent should have detected this from the `isHarborEnabled()` toggle in the page router, the file's glassmorphism tokens, and the fact that Harbor was confirmed as the active UI in prior sessions. **Detection:** you're about to present findings that include both `HarborXxx.tsx` and `Xxx.tsx` (legacy) components as equally relevant — stop, re-segment, and focus on the active path.

18. **🚨 Confusing "data exists in PG" with "this is a feature surface."** Internal tables (junction tables, audit tables, materialized views, precompute caches) exist because the pipeline needs them. That does NOT mean they describe a user-facing feature. Before treating a topic as a deep-dive target, search the functional spec for the topic by name. If `FUNCTIONAL-SPECIFICATIONS.md` never describes it as a user-facing capability, the data exists to support a downstream consumer (corridor intelligence, weather joins, search ranking) — not to be a survey target in itself. **Real example:** `port_visit_itineraries` is in the schema and the pipeline (Phase 6 of the 11-phase pipeline). The functional spec never mentions it. A "deep dive on port visits to itineraries matching" sounds like a feature audit but is actually a data-pipeline audit. The right framing matters — pipelines have different evaluation criteria than features.

19. **🚨 Asserting infrastructure facts (deployment tier, framework version, region) without checking.** Symptom: confidently stating "you're on the Hobby tier" or "this is Node 18" or "production runs in us-east-1" based on a single error message or inference. The 53100 (shared memory) error has multiple possible causes; the absence of a feature-flag env var doesn't mean the feature is disabled; a slow query doesn't prove the underlying hardware. **Rule:** before stating any non-obvious infrastructure fact, verify it — `railway status`, `psql \dt+`, a direct curl to the service's metadata endpoint, or reading `railway.toml` / `Dockerfile`. If you can't verify, qualify the claim ("this could indicate..." instead of "you are on..."). The user WILL catch unverified assertions and the correction burns trust on every subsequent finding.

20. **🚨 Treating a within-domain normal pattern as a data-quality bug.** Symptom: a query shows N rows where field A is within ±X hours/units/days of field B, and the model flags this as "out of range" or "timezone bug." But field A and field B describe a normal relationship in the domain — e.g., `port_ship_visits.visitDate` is the day the ship calls the port, and `ship_itineraries.departureDate` is when the cruise departs from the embarkation port. The two are NOT the same event: a ship can call the same port the day before a new sailing departs (turnaround), and a cruise routinely visits ports within ±24h of embarkation. **The fix:** before declaring any "out of range" finding, ask: what does this domain object represent? What is the normal relationship between these two fields in real-world data? When the user explains the domain ("visit date is arrival time, departure time is 6-8 hours after arrival"), drop the finding immediately and don't defend it. The user's domain knowledge is ground truth.

## References

- `references/codebase-survey-checklist.md` — ordered checklist for running a full codebase survey (breadth-first, 12 phases)
- `references/targeted-deep-dive-checklist.md` — checklist for doing a targeted deep dive into one domain/feature (depth-first, 6 steps). Use when the user asks for a "deep dive of X" in an already-familiar project.
- `references/full-app-deep-dive-checklist.md` — checklist for comprehensive app-wide survey covering all domains at moderate depth. Use when the user asks for a "deep dive of the app" without naming a specific domain.
- `references/pipeline-registry-audit.md` — audit a pipeline/job registry against actual app usage: find stale jobs, missing steps, sync gaps, and dependency order issues. Use when the user says "audit the pipeline" or "what jobs are needed vs dead" or before pipeline hardening.
- `references/search-filter-deep-dive-checklist.md` — Systematic investigation of search/filter features: tracing frontend state → API calls → backend where-clause construction → data layer (MVs, graph DB, indexes). Includes comparison tables for multiple implementations and common pitfall patterns.
- `references/python-survey-patterns.md` — Python-specific commands, heuristics, and maintainability criteria for surveying Python (not JS/TS) projects.
- `references/python-data-pipeline-survey.md` — Python data pipeline patterns: extractor coverage, API endpoint verification per sport, double-serialization bugs, injury field mapping, offseason handling, corpus schema checks, advanced player stats (WAR proxy) integration.
- `references/mobile-ui-review-patterns.md` — React Native / mobile consumer app audit checklist: API response shape verification, nested ScrollView detection, silent error swallowing, jargon consistency, dead UI elements, favorites state sync, and tab icon quality.
