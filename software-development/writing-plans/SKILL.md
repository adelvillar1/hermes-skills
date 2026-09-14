---
name: writing-plans
description: 'Write implementation plans: bite-sized tasks, paths, code.'
---

# Writing Implementation Plans

## Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, complete code, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

**Core principle:** A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

## When to Use

**Always use before:**
- Implementing multi-step features
- Breaking down complex requirements
- Delegating to subagents via a subagent-driven development workflow

**Don't skip when:**
- Feature seems simple (assumptions cause bugs)
- You plan to implement it yourself (future you needs guidance)
- Working alone (documentation matters)

## Bite-Sized Task Granularity

**Each task = 2-5 minutes of focused work.**

Every step is one action:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

**Too big:**
```markdown
### Task 1: Build authentication system
[50 lines of code across 5 files]
```

**Right size:**
```markdown
### Task 1: Create User model with email field
[10 lines, 1 file]

### Task 2: Add password hash field to User
[8 lines, 1 file]

### Task 3: Create password hashing utility
[15 lines, 1 file]
```

## Plan Document Structure

### Header (Required)

Every plan MUST start with:

```markdown
# [Feature Name] Implementation Plan

> **For the harness:** Use a subagent-driven development workflow to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### Task Structure

Each task follows this format:

````markdown
### Task N: [Descriptive Name]

**Objective:** What this task accomplishes (one sentence)

**Files:**
- Create: `exact/path/to/new_file.py`
- Modify: `exact/path/to/existing.py:45-67` (line numbers if known)
- Test: `tests/path/to/test_file.py`

**Step 1: Write failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify failure**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: FAIL — "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify pass**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Writing Process

### Step 1: Understand Requirements

Read and understand:
- Feature requirements
- Design documents or user description
- Acceptance criteria
- Constraints

### Step 2: Explore the Codebase

Use the harness tools to understand the project:

```python
# Understand project structure
search_files("*.py", target="files", path="src/")

# Look at similar features
search_files("similar_pattern", path="src/", file_glob="*.py")

# Check existing tests
search_files("*.py", target="files", path="tests/")

# Read key files
read_file("src/app.py")
```

### Step 3: Design Approach

**Before designing new endpoints or data flows, audit what the API already returns.** This session (2026-05-30) revealed that the schedule endpoint already returned rich `NextGameProbability` objects with factors, scenarios, pitcher matchups, injury data, and WAR breakdowns — but the frontend only showed team names and a percentage. The entire "informative surfaces" feature was a presentation problem, not a data problem. Always `read_file` the existing API models and route handlers before designing new ones.

Decide:
- Architecture pattern
- File organization
- Dependencies needed
- Testing strategy

### Step 4: Write Tasks

Create tasks in order:
1. Setup/infrastructure
2. Core functionality (TDD for each)
3. Edge cases
4. Integration
5. Cleanup/documentation

### Step 5: Add Complete Details

For each task, include:
- **Exact file paths** (not "the config file" but `src/config/settings.py`)
- **Complete code examples** (not "add validation" but the actual code)
- **Exact commands** with expected output
- **Verification steps** that prove the task works

### Step 6: Review the Plan

Check:
- [ ] Tasks are sequential and logical
- [ ] Each task is bite-sized (2-5 min)
- [ ] File paths are exact
- [ ] Code examples are complete (copy-pasteable)
- [ ] Commands are exact with expected output
- [ ] No missing context
- [ ] DRY, YAGNI, TDD principles applied
- [ ] **Compilation/verification step included** — every plan that modifies typed/compiled code MUST include a `tsc --noEmit` (or equivalent) step after the last implementation task, before closing. This catches type errors, missing imports, and property mismatches before the plan is marked complete.

### Step 7: Pre-flight Verification (MANDATORY before saving)

**Three layers of pre-flight checks.** Plans that skip any layer ship with bugs the user catches in review.

#### Layer 1 — Verify every file path and line number in the plan actually exists

For every path the plan names (`path/to/file.ts:45-67`), the line numbers and the file must exist in the working tree. Run from the project root:

```bash
# Confirm every named path exists
for f in $(grep -oE '[a-zA-Z][a-zA-Z0-9_/\.\[\]-]+\.(ts|tsx|js|jsx|py|go|rs|swift|kt|java|c|cpp|h|m)' docs/plans/<plan>.md | sort -u); do
  test -f "$f" || echo "MISSING: $f"
done

# Spot-check line numbers
grep -n "Page X of" <file>    # does line 183 still say what the plan claims?
sed -n '52p;183p;300p;413p' <file>
```

Why this matters: plans drift because subagents or new commits shift line numbers between plan-authoring and plan-execution. A plan that says "modify line 332-344" when line 332 is now blank text costs a 30-minute debug cycle.

#### Layer 2 — tsc/compile dry-check on stand-in code snippets

For plans with code snippets that define new exports, types, or interfaces:

```bash
# Example: writing-plans phase 1 helper extraction
cat > /tmp/dry-check.ts <<'EOF'
import { typeThatShouldExist } from './existing-module';
// ... rest of the planned code, with stubs for anything external
EOF
npx tsc --noEmit --strict /tmp/dry-check.ts
```

Or for React/Next.js: write the planned code into a temporary `.check.ts` file alongside the real source, run `npx tsc --noEmit` against the project, delete the temp file. If it doesn't compile, the plan's type assumptions are wrong — fix the plan, don't save it.

#### Layer 3 — Production-behavior audit

For every AC that names a production function, table, or rule: **grep the production code for the rule, compare word-by-word.** Common failures:

| AC says | Production actually does | Plan fix |
|---------|--------------------------|----------|
| "Last port is `arrival`" | "Last port matching departure within 0.5° is demoted to `port_of_call`" | Add the exception clause |
| "Returns `{name, lat, lng}`" | Returns `{portName, lat, lng}` | Field-name mismatch — fix the plan |
| "Writes to `route_corridors`" | Writes to `route_corridors` but a different column | Column-name mismatch |

Production code is the deployed contract. The plan is an internal spec. When they disagree, **production wins**. Update the plan.

#### Layer 4 — Schema/data-shape verification for DB-touching plans

For any plan referencing database columns, tRPC procedure returns, or MV fields:

```bash
# Verify the columns actually exist
psql "$STAGING_DB" -c "\d itinerary_port_conditions" | grep packing_category

# Verify the tRPC procedure returns the shape the plan assumes
grep -n "packing_category\|avgHighTempF\|precipitationMm" server/routers/itineraries.ts | head -10
```

A plan that says "the MV returns `packing_category`" when the MV doesn't have that column forces the implementer to invent a workaround.

If any layer fails, fix the plan before saving. Don't ship a plan with stale line numbers, untested type signatures, or production-mismatched ACs.

**For snippets that reference not-yet-existing types** (e.g. a helper extraction plan that shows the new signature but the helper file doesn't exist yet), the project-wide `tsc --noEmit` won't catch mismatches. Write a stand-in file with the exact plan snippet, then compile it standalone:

```bash
# Stand-in: write the planned signature at lib/<name>.check.ts
cat > lib/<name>.check.ts <<'EOF'
import { ExistingType } from './index';  // exact import the plan shows
export function newHelper(x: ExistingType): ExistingType { return x; }
EOF

# Compile standalone with the project resolution
npx tsc --noEmit --strict --target ES2022 --moduleResolution bundler \
  --module ESNext --esModuleInterop lib/<name>.check.ts

# Clean up
rm lib/<name>.check.ts
```

This catches type-import mismatches, wrong module-resolution behavior, and `T | null` vs `T | undefined` differences that a project-wide check would miss (because the new helper file doesn't exist in the project yet).

### Step 8: Save the Plan

```bash
mkdir -p docs/plans
# Save plan to docs/plans/YYYY-MM-DD-feature-name.md
git add docs/plans/
git commit -m "docs: add implementation plan for [feature]"
```

## Principles

### DRY (Don't Repeat Yourself)

**Bad:** Copy-paste validation in 3 places
**Good:** Extract validation function, use everywhere

### YAGNI (You Aren't Gonna Need It)

**Bad:** Add "flexibility" for future requirements
**Good:** Implement only what's needed now

```python
# Bad — YAGNI violation
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.preferences = {}  # Not needed yet!
        self.metadata = {}     # Not needed yet!

# Good — YAGNI
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
```

### TDD (Test-Driven Development)

Every task that produces code should include the full TDD cycle:
1. Write failing test
2. Run to verify failure
3. Write minimal code
4. Run to verify pass

See `test-driven-development` skill for details.

### Frequent Commits

Commit after every task:
```bash
git add [files]
git commit -m "type: description"
```

## Common Mistakes

### Frontend + backend coupling

When a feature requires matching changes on both sides (new API endpoint + new UI component), **one task per side is fine if the backend ships first.** But when CSS, JS, and endpoint changes are tightly coupled (e.g., a modal that depends on a new endpoint's response shape), combine them into a single task. Splitting CSS into its own task creates a broken intermediate state where the JS references classes that don't exist yet. In a recent session (2026-05-30), combining the match detail modal CSS + JS into one task was cleaner than the original 2-task split.

### Vague Tasks

**Bad:** "Add authentication"
**Good:** "Create User model with email and password_hash fields"

### Incomplete Code

**Bad:** "Step 1: Add validation function"
**Good:** "Step 1: Add validation function" followed by the complete function code

### Missing Verification

**Bad:** "Step 3: Test it works"
**Good:** "Step 3: Run `pytest tests/test_auth.py -v`, expected: 3 passed"

### Missing File Paths

**Bad:** "Create the model file"
**Good:** "Create: `src/models/user.py`"

## Execution Handoff

After saving the plan, **dispatch the first subagent immediately**. Do NOT ask "shall I proceed?" — if the user said "plan and implement it" or "and then build it," that's an unambiguous chain. Project memory captures this user-style rule explicitly: when the instruction is unambiguous, the next response is tool calls, not questions.

When executing, use the `a subagent-driven development workflow` skill:
- Fresh `subagent dispatch` per task with full context
- Spec compliance review after each task
- Code quality review after spec passes
- Proceed only when both reviews approve
- **Dispatch foundational phases first** (Phase 1 helpers, shared types, refactors that unlock later phases). Don't try to parallelize phases with data dependencies.
- **Phase ordering matters:** extract shared helpers before adding consumers; refactor the server before touching the UI; UI polish last.

**Pitfall (observed 2026-07-02, plan-and-implement pair):** agents finish a plan and stop to ask "shall I proceed?" even when the user explicitly said "plan and implement." This produces a frustrating back-and-forth loop where the user re-authorizes work they already asked for. The fix is structural: this section reads as an instruction, not an offer.

## Dead-Code Removal: Safe Workflow (comment → build → verify → delete)

When a plan includes deleting files or collapsing branches, **never delete first and build second.** The correct sequence:

1. **Comment out** the dead code or wrap the legacy branch in `/* ... */`
2. **Run `pnpm run build`** to confirm zero compile errors
3. **Grep for consumers** of the deleted identifiers
4. **Delete the code** only after both gates pass
5. **Build again** to confirm deletion doesn't break anything

This was a direct user correction (2026-06-30, glassmorphism removal): "let's comment out code to see what breaks instead of full deletion." Commentary approach proves safety before irreversibly removing code.

## Bulk sed Substitutions: Pitfalls & Cleanup

When rewriting tokens across dozens of files with `sed`, these specific artifacts occur predictably:

### `hover:hover:bg-bg` / `hover:hover:` prefix doubling
**Cause:** `sed -i '' 's/bg-\[var(--bg-glass-hover)\]/hover:bg-bg/g'` replaces the value portion, but the original className already had `hover:`. The result is `hover:hover:bg-bg`.
**Fix:** After all substitutions, run: `find app lib -name '*.tsx' | xargs sed -i '' 's/hover:hover:bg-bg/hover:bg-bg/g'`

### `bg-gold /bg-accent` vs `bg-gold/` ordering
**Cause:** Running `s/bg-gold/bg-accent/g` before `s/bg-gold\//bg-accent\//g` would double-substitute `bg-gold/10` → `bg-gold/10` (still gold) because `bg-gold` with space didn't match. But running the reverse order avoids this entirely.
**Fix:** Always substitute `bg-gold/` → `bg-accent/` before `bg-gold ` → `bg-accent `.

### Template literal tokens missed by regex
**Cause:** JavaScript template literals (backtick strings in JSX) like `` `${'bg-gold/20 text-gold'}` `` aren't caught by basic `sed` because the pattern appears inside a string literal in source.
**Fix:** After bulk sed, run exact-string `grep` for `bg-gold` / `text-gold` / `border-gold` residue. Patch individually with `patch(old_string='bg-gold/20 text-gold', new_string='bg-accent/20 text-accent')` because these need exact matching through patching.

### CSS custom properties survive sed
**Cause:** Sed replaces `--bg-glass` but doesn't catch `var(--glacier)`, `var(--gold)`, `var(--aurora)` in component code.
**Fix:** Final pass: `for f in $(grep -rnl "var(--gold)\|var(--glacier)\|var(--aurora)" app/ lib/); do sed -i '' 's/var(--gold)/var(--harbor-accent)/g; s/var(--glacier)/var(--harbor-sage)/g; s/var(--aurora)/var(--harbor-sage)/g' "$f"; done`

### `colors:` block deletion removes matching brace
**Cause:** `patch` with multi-line `old_string` that spans the opening `colors: {` line can leave the object missing its `colors:` wrapper entirely.
**Fix:** Verify the file with `read_file` after patching. If `bg: '#eef2f0'` appears directly under `extend: {` without `colors: {`, insert it.

### Pattern-driven renames beat hand-listed file sets
**Cause (observed 2026-07-08):** A plan listed 17 tsx files to rename a broken Tailwind token (`text-ink2` → `text-ink-2`). The delegated subagent ran a `grep` sweep first and found **7 additional files** in `app/tools/*` with the same typo that the plan's explicit list missed. A hand-curated file list is fragile exactly where it matters — the typo pattern is more reliable than the enumerator's memory.
**Rule for bulk mechanical renames (token typos, import path changes, class renames across many files):**
- In the plan, give the **pattern + a grep command** as the authoritative file set, not just a static list. Example: `for f in $(grep -rl 'ink2' app --include='*.tsx'); do sed -i '' 's/ink2/ink-2/g' "$f"; done` then verify with `grep -rn 'ink2' app --include='*.tsx'` → 0 matches.
- Still list the files you *know* about (it helps the reviewer), but state the grep is the source of truth and the subagent should sweep first.
- **Safeguard the anti-pattern:** name any file/identifier that must NOT be touched (e.g. `lib/harbor/tokens.ts` has a legitimate `ink2` JS object key, not a class — explicitly exclude it). The subagent must `grep` and confirm the excluded file is unchanged.
- Verify with a negation grep (zero matches) plus a type-check, not by counting edited files.

This also generalizes: when a fix is "the same wrong pattern in N places," describe the *pattern* and the *detection grep*, and let the implementer enumerate occurrences — don't try to enumerate them yourself in the plan.

## Plan Lifecycle: Reviewing & Closing Plans

Plans that stay `status: active` after all work is done create false positives during warmup and waste future sessions re-investigating completed work.

### When to audit plan status

- **During warmup** — check `the harness plans dir/` or `docs/plans/` for any `status: active` plans and verify they're still in progress.
- **When the user says "I thought we finished X"** — audit the plan's ACs against current code.
- **Before session wrapup** — if any plan's work was confirmed complete this session, close it now.

### How to audit a plan for completion

1. **Read the plan** and extract every acceptance criterion (AC).
2. **For each AC, verify against evidence** — Prisma schema, existing files, DB data, build logs. Don't trust comments or labels; trust code and data.
3. **Classify each AC**: ✅ Done, ⚠️ Partial, ❌ Not done.
4. **Summarize gaps** — if any AC is partial, document exactly what's missing (e.g., "fire-and-forget runs on every upsert but doesn't check `hasEmbedding` before calling OpenAI").
5. **Be honest about functional completeness** — a plan can be `completed` even with minor optimization gaps, as long as all ACs are functionally met.

### Closing a completed plan

1. Set `status: completed` in the plan's YAML frontmatter.
2. Update the `updated` date to today.
3. That's it — don't rewrite the plan body or strip ACs.

### Pitfall: stale active plans

If warmup shows a plan you don't recognize as active, investigate before assuming it's stale. The user may have asked for it last session. But if the codebase already implements everything the plan describes, mark it completed — don't leave it active just because you're unsure.

**Reference:** `references/plan-audit-checklist.md` — detailed checklist for auditing plan completion status.

### Pitfall: deferred UI work ships invisibly in the merge

When a plan is large enough that some user-visible surface (a page, a card, a button, a calibration report admin page) is parked as "follow-up" instead of in-scope, the plan technically completes but the **user can't see** any of the new data or behavior. The next session's user looks at the dashboard and asks "where's the X report?" — the API has it, the corpus has it, but the UI doesn't surface it.

**Concrete failure mode observed (2026-06-01, market-odds integration):** The plan shipped a `/api/calibration/market-odds` endpoint that returned a striking Brier-score finding ("our model is worse than a coin-flip; the market beats it by 0.030"). The endpoint was technically complete. The plan was marked `status: completed`. The merge shipped. But **the only way to see the finding was `curl`** — there was no admin dashboard page. The user came back, said "do 2 and then 1" (build the Calibration admin page, then merge). A second round of work that the original plan should have included.

**How to prevent this in future plans:**

1. **List the user-visible surfaces explicitly in the plan's acceptance criteria.** Not "expose calibration data via API" — also "and surface it in the admin dashboard with a single-glance headline card." A plan's ACs should describe what the **user sees**, not just what the code does.

2. **If a surface genuinely must be deferred, mark it explicitly with the reason** ("deferred because X dependency, tracked in Y issue, ETA Z"). Unmarked "out of scope" silently disappears.

3. **Audit deferred work before marking the plan `completed`.** When you're about to flip the status, scan the plan for any "out of scope" / "follow-up" / "future" / "deferred" mentions. Each one is a candidate for: (a) do it now, (b) explicitly track it elsewhere, or (c) flag it to the user before flipping.

4. **The user's question before merging is a forcing function.** A natural pre-merge question to ask: "Before I merge this, anything in the plan that I marked 'out of scope' or 'follow-up' that you'd like to ship in this PR?" This catches the deferred-UI work before the next session.

**Reference:** `references/plan-audit-checklist.md` — detailed checklist for auditing plan completion status.

## Precompute Architecture (for computationally expensive features)

When a plan involves expensive computation (Monte Carlo simulation, ML inference, large aggregation, batch enrichment), **the plan must specify a precompute architecture** — never design the feature to run computation at request time.

### When this applies

- Feature involves simulation, sampling, or probabilistic computation
- Feature requires running ML inference or LLM calls per entity
- Feature aggregates data across large tables and the result changes slowly
- User says "precompute as much as possible" or "cache everything"

### Three-tier read path

Every plan for an expensive feature should specify this read path:

```
API request → Redis (hot, <1ms) → Postgres (warm, ~5ms) → deterministic fallback
```

**Plan must specify:**

1. **Compute trigger** — CLI command, cron schedule, or pipeline post-step. Never request-time.
2. **Write-through** — compute writes Postgres (durable source of truth) then Redis (hot cache) in the same run.
3. **Redis key schema** — `prefix:{entity_type}:{identifier}` with TTLs (24h for frequent data, 72h for slow-changing).
4. **Graceful fallback** — if Redis miss → Postgres → if Postgres miss → deterministic/current behavior. No 500s, no empty responses.
5. **Staleness handling** — TTL auto-expires stale data. API response includes `last_computed_at` timestamp. Dashboard shows "Last updated X ago."
6. **Cache invalidation** — full replace (DELETE + INSERT on Postgres, SET on Redis) per compute run. No incremental invalidation.

### Anti-patterns to call out in plans

- **MC/inference at request time** — even "fast" computation (~50ms) adds up under load
- **Redis-only without Postgres** — Redis flush loses all data, no recovery
- **Incremental cache invalidation** — full replace is simpler and more reliable
- **Missing fallback** — fresh deploy or Redis outage must still serve data

**Reference:** `references/precompute-architecture-pattern.md` — detailed pattern with DB table schemas, Redis key conventions, and worked example from Monte Carlo simulation plan.

**Reference:** `references/precompute-architecture-pattern.md` — three-tier precompute pattern (Redis → Postgres → fallback) with cache service implementation, key schema, and CLI trigger design. Use when planning features with expensive computation.

### Dependency-Chain Tracing (for pipeline/data-flow plans)

When a plan involves a sequence of computational steps — pipeline jobs, data transforms, enrichment scripts — **the plan's task order MUST be derived from the actual data dependency chain, not from "is it used?" audits.** Usage audits tell you *whether* a step matters; dependency tracing tells you *where* it must run and *what it needs as input*.

### The tracing technique

For each script/job in the pipeline, trace its actual PG table reads and writes:

1. **Prisma API calls:** `grep -n 'prisma\.\$\|\.findMany\|\.findUnique\|\.create\|\.update\|\.upsert\|\.delete' scripts/<job>.ts`
2. **Raw SQL ($queryRaw):** `grep -n '\$queryRaw\|\$executeRaw\|FROM\|JOIN\|INSERT\|UPDATE\|DELETE' scripts/<job>.ts` — these often reveal the real dependencies that Prisma calls miss
3. **FalkorDB reads/writes:** `grep -n 'falkorQuery\|MERGE\|CREATE\|MATCH.*DELETE' scripts/<job>.ts`
4. **Cross-script data flow:** Build a DAG where each node is a job and edges are "writes table X → reads table X"

### Common pitfall: "Is it used?" ≠ "Where does it go?"

A job may be actively used by the app but missing from the pipeline, or it may be in the pipeline but in the wrong order. The audit must answer:
- **What tables does this job READ?** (inputs — must exist before this step runs)
- **What tables does this job WRITE?** (outputs — must exist before downstream steps run)
- **What columns specifically?** (e.g., `route_corridors.familyPct` — written by persona_fit, read by clan_aggregates)
- **What FalkorDB edges/nodes?** (e.g., `SAILS_TO` edges — created by scraper, go stale after region reclassification)

### Stale edge detection

After pipeline steps that *reclassify or re-derive* data (e.g., region reassignment), check whether any FalkorDB graph edges that were created earlier (by the scraper or a prior pipeline step) now reference stale relationships. Example: `SAILS_TO` (Ship→Region) edges created during P0 scraping go stale after P2 reclassify_regions — the ship's region assignment changes but the edge doesn't. AI Chat tools that traverse these edges return wrong results.

**Checklist for stale edges:**
1. List all edge types created by the scraper or early pipeline steps
2. For each edge, check if any later pipeline step could change the underlying data (region assignment, deployment changes, corridor membership)
3. If yes, add a refresh step after the data-changing step

## Pitfalls

### requirements.txt vs pyproject.toml divergence

When a Python project has BOTH `requirements.txt` and `pyproject.toml`, they can silently diverge. The Dockerfile may use one while developers use the other. This causes "works locally, crashes in production" bugs.

**Rule:** When adding a new dependency, add it to BOTH files. Better yet, use only `pyproject.toml` and delete `requirements.txt`.

**Detection:** `grep "pip install" Dockerfile` — if it uses `pyproject.toml`, then `requirements.txt` is dead weight that creates false confidence.

### Classifying data-truncation as "feature work"

When a review or audit finds that a list/screen only loads page 1 of N and never fetches more, this is a **functional bug** (users cannot access the data), not a "pagination feature enhancement." The same applies to any finding where existing functionality silently drops or hides data from the user.

**Wrong:**
> "ItineraryBrowser fetches only page 1 — Low, Deferred (feature enhancement)"

**Right:**
> "ItineraryBrowser fetches only page 1 — Low-Med, Task 12 (users can't see beyond 50 results)"

The heuristic: if the user expectation is "I see all the items" and the reality is "I see a truncated subset with no way to get more", that's a bug in the plan — promote it to a real task.

### Proposing UI density plans without verifying backend data or existing patterns

When a user requests a UI refactoring for higher information density, there is a strong temptation to design dense card layouts (inline badges, micro-sparklines, merged tables) and assume the API payload already provides the necessary granular data. 

**Always do these two things before finalizing a UI density plan:**
1. **Audit the Backend API Payload:** Inspect the relevant API route handler or payload to verify the exact data is present or can be efficiently added. (e.g., Does the team history endpoint return a `last_5_results` array of W/L booleans for a pill row? Does the schedule endpoint include the specific divergence percentage needed for an inline badge?)
2. **Cross-reference Existing Dense Components:** Read the code for existing high-density UI components (e.g., `renderMatchCard`, `.player-card-grid`) to reuse established CSS classes and micro-visualization patterns rather than inventing new ones. This ensures visual consistency and reduces CSS bloat.

**Wrong:** Plan proposes replacing a bulky table with a "compact player card grid" without checking if the API returns the required top-3 hitter stats or if the `.player-card-grid` CSS class exists.
**Right:** Plan explicitly states: "Verify `/api/teams/{id}/history` returns `last_5_results`. Reuse `.player-card-grid` and existing color-coded badge patterns from `ui/js/views/today.js` `renderMatchCard`."

### Proposing blanket data operations when surgical targeting is possible

When a plan involves filling a data gap (missing signatures, missing enrichment, missing scraped data), **categorize the gap before proposing any action.** The default plan impulse is "re-scrape everything" or "force recompute all" — this is almost always wasteful and sometimes destructive.

**Diagnostic breakdown pattern:**

1. **Computation gap** — data exists but wasn't processed (e.g. itineraries in MV but signatures not computed). Fix: run the computation script. Zero scraping, zero re-processing.
2. **Stale cache/MV** — derived data is outdated (e.g. MV not refreshed after new data). Fix: refresh the MV. Zero scraping.
3. **Matching/linking gap** — source data exists but linking rows are missing. Fix: run additive matching. Zero scraping.
4. **Genuinely missing source data** — the only case that requires actual data collection.

In practice (CruiseMapper June 2026), 52% of a 1,864-row gap was categories 1-2 (just refresh + compute), and only 40% needed actual scraping — and that was 15 specific ships × their specific departure months, not a blanket force-scrape of 2,377 ports.

**Domain-aware planning:** Before proposing any data operation, consider:
- **Does the data settle?** (Cruise itineraries lock 12-18 months out; re-scraping settled periods yields nothing.)
- **Is past data valuable to the product?** (For forward-looking products like travel agent tools, historical data has zero user value.)
- **What's the minimum intervention?** (Derive the exact set of `(entity, period)` tuples from orphan records, and target only those.)

### Assuming the engine without verification (the plan is wrong about what DB is in use)

**The pitfall:** the plan shows a code snippet using PostgreSQL-specific syntax (`pg_insert`, `JSONB`, `RETURNING *`, partial unique indexes, etc.) or SQLite-specific syntax (`batch_alter_table` workaround for `ALTER TABLE`, `WITHOUT ROWID` tables) — but the author never verified which database the project *actually* uses. The implementer copies the snippet verbatim, the snippet crashes at first execution, and the user catches a Tier 1 bug that should have been a pre-flight check.

**The pattern:** before writing *any* DB-touching code in a plan, **always run the engine-detection grep as a pre-flight step.** The grep is dialect-portable:

```bash
# For Python projects using SQLAlchemy
grep -E "sqlite|aiosqlite|postgresql|psycopg" apps/api/pyproject.toml apps/api/src/config.py apps/api/src/db/engine.py 2>/dev/null

# For TypeScript projects using Prisma
grep -E "provider\s*=" apps/api/prisma/schema.prisma 2>/dev/null

# For TypeScript projects using Drizzle
grep -E "dialect:" apps/api/drizzle.config.ts 2>/dev/null
```

If the answer is ambiguous (e.g. "the dev default is SQLite but the prod env var is `DATABASE_URL`"), the plan must say **which code paths run on which engine** and write code that works on BOTH. Concretely:

- **SQLAlchemy:** use dialect-agnostic primitives (`UniqueConstraint`, `Index`, `CheckConstraint`, generic `insert().on_conflict_do_update()`). When dialect-specific behavior is required (e.g. `where=` clause on the upsert, which PostgreSQL supports but SQLite does not), branch on `db.bind.dialect.name` and provide per-engine implementations.
- **Prisma:** use `@@unique` and `@@index` instead of raw SQL migrations where possible; verify each generated migration runs on the prod engine.
- **Drizzle:** avoid the `drizzle-orm/{postgres,sqlite}-specific` imports; use `drizzle-orm` core.

**Real example (2026-06-13, stock-predictor followups-batch plan):** The plan's B2.4 ingest service used `from sqlalchemy.dialects.postgresql import insert as pg_insert` for the upsert. The project *defaults* to `aiosqlite` in dev but accepts a `DATABASE_URL` env var for production. The original code was *fine* on prod (PostgreSQL) but *would have failed in local dev* (SQLite). The fix: detect `db.bind.dialect.name` at call time and import from the correct dialect.

**The rule of thumb:** if the plan's code snippet imports from `sqlalchemy.dialects.postgresql` or `sqlalchemy.dialects.sqlite` without branching, the plan is either wrong or the project has only one engine. Verify which. The grep takes 10 seconds; the bug catch takes an hour.

### Prisma-`any`-typed helper extraction breaks consumer types silently

**The pitfall:** when extracting a helper function out of a tRPC procedure to share it with another procedure, the plan templates the helper's parameter as `itinerary: any` for "flexibility". The original `getById` worked because `ctx.prisma.ship_itineraries.findUnique(...)` returned a fully-typed object whose type flowed through every downstream `ctx.prisma.port_ship_visits.findMany({ where: { matchedShipId: itinerary.shipId, ... } })` — Prisma's where-clause inference and the result-row types both depended on the upstream object's type. Once `itinerary: any` is the parameter, every nested access (`itinerary.shipId`, `itinerary.ship.passengerCapacity`) widens to `any`, the where-clause inference returns `never[]` (typed as `{}[]` for the consumer), and you get 60+ "Property X does not exist on type '{}'" errors across the helper.

**The pattern:** when extracting a helper that consumes Prisma results, **type the parameter with the actual Prisma payload type, not `any`.** Two options, in order of preference:

1. **`Prisma.ShipItinerariesGetPayload<{ include: { ship: ..., region: ..., routeMapSvg: ... } }>`** — gives you the exact shape `getById`'s Prisma query returns, and types flow through every nested `ctx.prisma.*` call.
2. **If the helper is genuinely generic over many entity types**, parameterize it with a type variable and require the caller to pass the typed object. Don't default to `any` "for simplicity" — `any` is never the right type for code that calls Prisma.

If you genuinely don't know the type yet, write `itinerary: { id: string; shipId: string; departureDate: Date; ... }` with an inline type literal — narrower than `any` and unblocks Prisma inference for the specific fields the helper touches.

**Real example (2026-07-02, itinerary-data-parity plan Phase 4A):** The plan's `buildEnrichedPorts(ctx: any, itinerary: any, options: ...)` helper extracted from `getById` introduced 63 type errors across the helper body. The fix would have been `itinerary: Prisma.ShipItinerariesGetPayload<{ include: { ship: { select: { id, name, slug, heroImage, ... } } } }>`. The plan author chose `any` for "easier contract"; the result was a refactor that compiled nowhere, two subagent timeouts, and a reverted commit. The helper is still valuable code; the *next* attempt needs to type the parameter correctly.

**The rule:** when extracting a helper that calls Prisma, the parameter type is *load-bearing*. A 5-second decision (use `Prisma.ShipItinerariesGetPayload<...>`) saves a 30-minute debug cycle.

### Cursor encoding for non-unique sort keys (the plan picks the wrong sort column)

**The pitfall:** cursor pagination requires a *unique* sort key. Plans written from a template often show a single-column cursor on the "obvious" sort column (`made_at`, `timestamp`, `name`) — but that column may have duplicates. The implementer copies the cursor code; pagination skips or duplicates rows on ties.

**The pattern:** when designing cursor pagination, **verify the sort column is unique, or use a composite cursor.** Concretely:

1. **Identify the sort column** for each list endpoint. The "obvious" choice (newest-first for predictions) is rarely unique. Batch runs produce ties on `made_at`; cached price snapshots produce ties on `timestamp`; alphabetical `name` is unique but `name` doesn't match the user's "newest first" expectation.
2. **If the sort column is non-unique, define a tiebreaker.** The natural tiebreaker is the primary key (`id`, `prediction_id`, `price_id`). Sort by `(sort_col DESC, id DESC)`, encode both in the cursor, and use SQLAlchemy's `or_` + `and_` for the row-tuple comparison:

```python
stmt = stmt.where(
    or_(
        Prediction.made_at < last_made_at_dt,
        and_(Prediction.made_at == last_made_at_dt, Prediction.prediction_id < last_pred_id),
    )
)
stmt = stmt.order_by(Prediction.made_at.desc(), Prediction.prediction_id.desc())
```

3. **The cursor utility must accept a dict** (not a single string) and round-trip the entire composite payload. Plans that show `encode_cursor(instrument_id: str)` are a single-ID cursor template — fine for unique sort keys, broken for composite ones.
4. **Add a test that seeds two rows with the same `made_at`** (or whatever the sort column is) and asserts no overlap between consecutive pages. Without this test, the bug is invisible until production data has ties.

**The same pattern applies to idempotency keys for upserts.** `EntityMatch (raw_name, cik, matched_instrument_id, algorithm_version)` is the business key. Using the UUID PK as the `ON CONFLICT` target is a no-op (UUIDs never collide) and silently inserts duplicates on every re-run. Use a unique constraint on the business-key columns + `ON CONFLICT (...) DO UPDATE` (or `DO NOTHING`).

**Real example (2026-06-13, followups-batch plan):** Pass 1 review caught the `ON CONFLICT` UUID bug; Pass 2 review (buildability) caught the missing composite-cursor pattern for predictions/prices. Both bugs were Tier 1; both had the same root cause: the plan's template used a single-ID cursor and a UUID-based conflict target as if they were the default, when in practice they're wrong for any non-unique sort key or any real-world entity.

### Path-resolution bugs from `Path(__file__).parent` arithmetic

**The pitfall:** the plan shows `Path(__file__).parent.parent / "fixtures"` to compute a path relative to a source file. The author counts "2 directories up" based on a directory tree that doesn't match the actual file location. The implementer copies the arithmetic verbatim and the path resolves wrong (file not found at runtime).

**The pattern:** when showing a `Path(__file__).parent[...]` expression in a plan, **verify the file's actual location with `ls` or `find`** before writing the expression. Concretely:

```bash
# Always verify before writing
ls -la apps/api/src/cli/seed.py
# → apps/api/src/cli/seed.py (confirmed)
# Path: parent = apps/api/src/cli/, parent.parent = apps/api/src/, parent.parent.parent = apps/api/
# So: FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures"
```

The safe form is `Path(__file__).resolve().parent.parent.parent / "fixtures"` with `.resolve()` to handle symlinks and enough `.parent` levels to be unambiguous. Add a `FileNotFoundError` guard with a clear error message so the failure mode is diagnostic, not silent:

```python
fixture_path = FIXTURES / name
if not fixture_path.exists():
    raise FileNotFoundError(
        f"Fixture {name} not found at {fixture_path}. "
        f"Hand-curated fixtures must be created (see plan §Open questions Q5)."
    )
```

**The same pattern applies to** `os.path.join(os.path.dirname(__file__), '..', '..', 'fixtures')` and any other path-arithmetic idiom. The plan should always show the verified `ls` output, not just the resulting expression.

**Real example (2026-06-13, followups-batch plan, Pass 2):** The plan said `FIXTURES = Path(__file__).parent.parent / "fixtures"` for `apps/api/src/cli/seed.py` to resolve `apps/api/fixtures/cusips.json`. But `parent` is `apps/api/src/cli/`, and `parent.parent` is `apps/api/src/` — not `apps/api/`. The seed crashes with `FileNotFoundError` at runtime. The fix: `parent.parent.parent` plus a `FileNotFoundError` guard. The reviewer caught this because the grep output for `apps/api/src/cli/seed.py` was visible in the plan's pre-flight check; the author just didn't apply the same discipline to the path expression.

### Plan AC vs production code: which is the source of truth?

**The pitfall:** the plan is reviewed for spec consistency, internal coherence, and AC quality — but never against the production code it will run alongside. So when the plan says "the spec says X" and production actually does Y, the plan's AC wins in the plan but Y wins in production. The implementer hits the production behavior, the test fails, and the user has to debug which side was wrong.

**The pattern:** for every AC that names a production function, table, or rule, **verify the AC against the actual production code before saving the plan.** Concretely:

1. **Production rule ACs** ("First port → departure, last port → arrival, intermediate → port_of_call") — `grep` the production function for the rule. Compare word-by-word. If the production code adds an exception clause ("last port matching departure within 0.5° → port_of_call"), the AC must encode that clause too, not the simplified version.
2. **Production shape ACs** ("returns `{name, lat, lng}`") — read the production type definition. If production returns `{portName, lat, lng}`, the plan must say `portName`, not `name`. Field-name mismatches between plan and production are the most common silent AC error.
3. **Production side-effect ACs** ("writes to route_map_svgs") — `grep` for the actual write call. Confirm the column name, the upsert key, and the relationship to the rest of the write path.

**Real example (2026-06-27, itinerary-3d-map-toggle plan):** The plan's N=2 test case stated types = `[departure, arrival]`. Production `get-detail-coordinates.ts:99` demotes the last port to `port_of_call` whenever its coords match departure within 0.5°. The unit test caught the inconsistency on first run. The fix: update the plan AC to `[departure, port_of_call]` to match production, and add a one-line note in the plan documenting what changed and why. **Always follow production behavior when the two diverge** — production is the deployed contract; the plan is an internal spec.

### Plan layer split: parent plan (AC-level) + execution plan (task-level)

Large multi-phase plans (e.g., a 7-phase T6 staleness cleanup) benefit from **two plan files** rather than one:

1. **Parent plan** at `docs/plans/YYYY-MM-DD-<slug>.md` — describes the overall approach, phases, ACs at the *outcome* level, risks, links to references. Read by humans reviewing the strategy. Stays stable across execution revisions.
2. **Execution plan** at `docs/plans/YYYY-MM-DD-<slug>-execution.md` (or similar suffix) — bite-sized tasks with file paths, complete code, exact verification commands. Read by subagents. Gets updated as tasks complete.

**Why split:** the parent plan's "Phase 2: cross-persona backfill of 1,740 truly-missing pairs" reads cleanly to a stakeholder. The execution plan's "Task 2: create `scripts/insights/deprecate-stale-t6.ts` with this exact Prisma SQL..." reads cleanly to a subagent. Combining them produces a 270-line doc that serves neither audience well, and revisions (e.g., changing the LLM provider from DeepSeek to the LLM provider) require touching both strategy and code sections.

**Cross-references:** the parent plan links to the execution plan in its "Files to be Touched" or "Implementation" section. The execution plan's frontmatter cites the parent (`parent_plan: docs/plans/...`).

**When NOT to split:** if the plan has ≤3 tasks or fits in <150 lines, one document is fine. The split earns its keep when the plan needs to be revised (provider change, scope trim) without re-issuing the whole doc.

### Subagent dispatch order: foundation → parallel batch → verification gate → dependent batch

The execution plan's "Subagent Dispatch Order" section should be explicit, not implied. Recommended pattern:

1. **Task 1** (foundation: creates a shared module) — dispatch sequentially first. Wait for completion.
2. **Tasks 2, 3** (disjoint NEW files, both import from Task 1's module) — parallel batch. They cannot collide because they write different files.
3. **Verification gate** — read both files yourself. Confirm exported symbols match what dependents will import. THEN dispatch dependents.
4. **Tasks 4, 5** (depend on 2 and 3) — sequential or parallel depending on dependencies.

This is the "two parallel waves with a verification gate between them" pattern. Skipping the gate produces import rot: dependents guess at exported names that don't exist or have different signatures.

**Risk-based review rigor table** in the execution plan makes the dispatch repeatable:

| Task | Risk | Reviewer dispatches |
|---|---|---|
| 1 (foundation) | Low | Single combined reviewer |
| 2 (destructive UPDATE) | High | Spec + quality + cross-LLM |
| 3 (read-only audit) | Medium | Spec + quality |
| ... | ... | ... |

See `a subagent-driven development workflow/references/risk-based-review-rigor.md` for the full classification rubric.

### Production code is the deployed contract. The plan is an internal spec. When they disagree, production wins. Update the plan to match production, and add a note in the plan's "Lessons learned" or similar section so future sessions see what was corrected.

### Missing-feature bug reports usually mean N-of-M surfaces are missing it

**The pitfall:** the user reports "X is missing" or "X is not in there" after looking at one surface (a share link, a PDF, a print page). The implementer goes and adds X to that one surface. Two weeks later, the same user reports "X is still missing" — looking at a different surface this time. The same AC repeats.

**The pattern:** before drafting a fix, **enumerate every surface where the feature could exist**, and check each one. Common surface inventory for a B2B SaaS:

- Detail page (authenticated user view)
- Magic-link share page (public, recipient view)
- HTML export / printable view (advisor's browser-print-to-PDF)
- Server-side PDF download (advisor's email-attachment)
- API endpoint (does it return the data at all?)
- Mobile / responsive variant

For each surface: present? partial? silently broken (e.g. `null` returns when input data missing)? The plan's ACs must cover all surfaces, not just the one the user named in their bug report.

**Real example (2026-07-01, packing-guide-export plan):** The user said "the packing guide is not in there" while looking at the itinerary share page. There are 4 surfaces where the packing guide could appear: detail page (present), magic-link share (present but silently returns `null` on missing weather), HTML export (missing entirely), PDF download (missing entirely). A "fix the share page" plan would have left 2 surfaces broken. The full-surface audit turned a one-page fix into a 4-phase plan covering all surfaces — including a follow-up helper-extraction to stop the same drift from happening on the next weather-data schema change.

**The shortcut:** when the user reports a feature is missing, do not draft a fix for the surface they named. First, list every surface where it could live, then ask: "is the feature missing from N of those surfaces?" If yes, the plan must enumerate them.

### Method-name mismatches between the plan and the existing codebase

**The pitfall:** the plan shows one method signature; the existing codebase uses a different one. The implementer follows the plan literally, and the type checker catches the bug — but only after they've written 50+ lines around the wrong call.

**The pattern:** when a plan shows a function call from a file that *already exists*, **read the existing function signature with `read_file` or `grep`** before writing the plan. Include the actual signature in the plan as a code block, not just a usage:

```typescript
// apps/web/src/api/client.ts:38-44 (verified)
export async function getInstruments(
  params?: { sector?: string; kind?: string },
  signal?: AbortSignal,
): Promise<Instrument[]> { ... }
```

The subagent implementing the plan should not have to re-derive the API surface. If the plan's code calls a method with a signature the codebase doesn't have, the bug is silent (TypeScript's excess-property-check is lenient on object types) and only surfaces at runtime.

**Real example (2026-06-13, followups-batch plan):** A2.2's hook rewrite showed `api.getInstruments({ ...params, cursor: pageParam }, signal)`. The existing `client.ts` defines `getInstruments(params?: { sector?: string; kind?: string }, signal?)` — the `params` object does NOT have a `cursor` field. The call compiles but `cursor` is silently dropped. The fix: update the client function signature to accept `cursor` and `includeTotal` in the params object, with a concrete diff in the plan.

### Monolithic CLIs are not callable functions — verify before assuming an importable API

**The pitfall:** the plan shows code that imports a function from an existing script (e.g., `import { precomputeShipCorridorInsights } from './precompute-ship-corridor-insights'`) and calls it with a progress callback (e.g., `onProgress: (rowsWritten) => ...`). The implementer copies the snippet verbatim, the import fails (or worse, silently no-ops), and the diagnostic story is opaque.

**The pattern:** before writing any plan step that calls into an existing script as a library, **verify the script's API surface with `grep -nE "^export " <script>` and a 50-line header read**. If the script is a monolithic CLI — top-level `await main()` with `process.argv` parsing, no exported functions — the plan MUST spawn it as a subprocess (`child_process.spawn('npx', ['tsx', scriptPath, ...args])`) and observe side effects (DB row counts, log output, output files) rather than calling it as a function.

**The grep that catches this before the plan is written:**

```bash
# For any script the plan will depend on
grep -nE "^export |^async function|^function " scripts/<dependency>.ts | head -20

# If empty → it's a CLI, not a library. Spawn it as a subprocess instead.
```

**Concrete sub-patterns the grep reveals:**

| What you find | What the plan should do |
|---|---|
| `export async function foo(...)` | Call it directly with typed args |
| `export const foo = (...)` | Call it directly |
| No `export` keywords (only top-level `await main()`) | Spawn as subprocess with `child_process.spawn`; observe side effects (DB polls, log lines, output files) |
| Mix: a few `export` helpers + a top-level `main()` | The CLI orchestrator probably isn't exported. Plan should either spawn the CLI OR use only the exported helpers — not both |

**Real example (2026-07-11, T6 staleness execution plan):** The plan's original Task 6 (`probe-stall.ts`) wrote `const { precomputeShipCorridorInsights } = await import('./precompute-ship-corridor-insights'); const result = await precomputeShipCorridorInsights({ persona, limit, concurrency, onProgress: (rowsWritten) => ... });`. The actual file at `scripts/insights/precompute-ship-corridor-insights.ts:1-100` is a monolithic CLI: `import { PrismaClient, Prisma } from '@prisma/client'; ... async function main() { ... } main().catch(...)`. Zero top-level exports. The import returns an empty object; `precomputeShipCorridorInsights` is `undefined`; `await undefined({...})` throws `TypeError: undefined is not a function` at runtime with no clue about why.

**The fix at plan-write time** (not at subagent-runtime): run `grep -nE "^export " scripts/insights/precompute-ship-corridor-insights.ts` → empty output → rewrite Task 6 to spawn the script as a subprocess and poll the DB row count every 10 seconds. The downstream `probe-stall.ts` then becomes:

```typescript
import { spawn } from 'child_process';
// ... Prisma polling loop watching ship_corridor_insights row count
const child = spawn('npx', ['tsx', scriptPath, '--persona', persona, '--limit', String(limit), '--concurrency', String(concurrency)], { ... });
child.stdout?.on('data', (chunk) => process.stdout.write(`[child] ${chunk}`));
```

**Why this is hard to catch later:** TypeScript's import of an undefined symbol compiles cleanly (the runtime object is typed `any` via the dynamic `import()`). The bug surfaces at first execution, deep inside a subagent's tool-call loop, with no diff against the plan to point at. **Catch it at plan-write time** with the grep above.

**Companion rule for plan-write time:** any plan step that says `await import('./some-script')` and immediately calls something on the imported object is a red flag. Either the script has exports (verify with the grep) or the plan should spawn it.

### "Skip the cross-LLM review for plans < 2KB" is wrong; the size heuristic is outdated

**The pitfall:** the rule of thumb "cross-LLM review is mandatory for plans >2KB" is from an era when plans were typically <5KB. The 2026-06-13 followups-batch plan was 2,300+ lines and ~135KB — well past the 2KB threshold — but the more interesting observation is **even small plans benefit from a Pass 2 buildability review**. The Pass 2 of the followups-batch plan caught 8 Tier 1 items that Pass 1 missed (Path arithmetic, engine mismatch, method-name mismatch, composite cursor, transaction-boundary bug). A 5KB plan touching the DB or the wire format still benefits from a Pass 2.

**The new heuristic:** **any plan that touches (a) a database, (b) a multi-language contract, (c) a deploy topology, or (d) more than 5 tasks gets a 2-pass review regardless of size.** Pass 1 is the gap-analysis brief; Pass 2 is the buildability brief with the "do NOT re-flag the already-patched issues" list. Skip Pass 2 only for plans that are pure documentation, a one-line bug fix, or a config tweak.

## Consumer-First Language (for consumer-facing apps)

When writing plans for apps used by regular people (not travel agents, not developers, not domain experts), **every UI label, section title, and data field must be evaluated for consumer comprehension before it goes into the plan.**

### Checklist — run this on every task that surfaces data to users

1. **Would my mom understand this label?** If not, rewrite it. "Tips included" ✅ — "Gratuities included" ❌. "Ship size" ✅ — "Gross tonnage" ❌.
2. **Does this help someone decide?** If it's trivia for an industry insider, drop it. Propulsion type, registry port, IMO number, build cost — skip. How new is the ship? How big does it feel? What can I do onboard? — keep.
3. **Did I translate enums before displaying?** Never show raw `"partial"` or `"not_included"`. Show "Some included" or "Not included". Never show a numeric score without a human label ("Great" ⭐⭐⭐⭐, not "82").
4. **Are section titles phrased as user questions?** "Is it expensive?" ✅ — "Value comparison" ❌. "Good to know" ✅ — "Risk flags" ❌. "What's included" ✅ — "Inclusions matrix" ❌.
5. **Did I hide empty sections?** If data is null, the entire section disappears — no "N/A", no empty cards, no placeholder text.
6. **Did I write the label → display mapping?** Include a table in the plan task showing PG field → consumer label → display text for each inclusion status. This prevents the implementer from guessing.

### Pitfall: surfacing every PG column

When the database has 40+ columns per entity, the instinct is to show them all. Fight this. The plan should explicitly list what to **exclude** and why. Example:

> Do NOT show: builder, flag, registry port, propulsion type, build cost — these are travel-agent data points.

**Reference:** `references/consumer-first-labels.md` — field-by-field label mapping tables for common cruise entities (ships, cruise lines, ports, itineraries). Load this when writing plans that surface PG data in the the companion mobile app mobile app.

## Remember

```
Bite-sized tasks (2-5 min each)
Exact file paths
Complete code (copy-pasteable)
Exact commands with expected output
Verification steps
DRY, YAGNI, TDD
Frequent commits
Dependency-chain tracing (not just usage audits)
Data truncation = bug, not feature request
Consumer-first language for consumer-facing apps
Precompute architecture for expensive features (Redis → Postgres → fallback)
```

**A good plan makes implementation obvious.**
**A closed plan prevents wasted sessions.**
**A traced dependency chain prevents silently wrong ordering.**
