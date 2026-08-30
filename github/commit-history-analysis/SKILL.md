---
name: commit-history-analysis
description: Use when analyzing git history for project retrospectives.
---

# Commit History Analysis

Turn a repository's git history into project intelligence: the arc of the build, which workstreams were hardest, when phases happened, and where effort concentrated. This is *temporal/narrative* analysis — distinct from static code inspection (LOC, languages) which is `codebase-inspection`.

## When to use

- "What can you infer from my git activity?" / project retrospectives
- "Which feature was hardest / took the most work?"
- "How did the project evolve over time?"
- Validating a user's intuition about where effort went ("the bulk of fixes were in X")
- Writing a project retrospective document

## Core workflow

### 1. Get the TRUE history — do not trust the local clone

Local clones are often squashed or shallow. The real record is on the remote.

```bash
# Local count (may be misleading)
git log --all --oneline | wc -l

# True count per branch via GitHub API — read the Link header for the total
gh api "repos/<owner>/<repo>/commits?sha=main&per_page=1" -i 2>/dev/null \
  | grep -i '^link:' | grep -oE 'page=[0-9]+>; rel="last"' | grep -oE '[0-9]+'
```

If the remote has far more commits than local, pull the full log via the API into a temp file and analyze that — NOT the local `git log`:

```bash
gh api "repos/<owner>/<repo>/commits?sha=main&per_page=100" --paginate \
  -q '.[] | "\(.commit.author.date)|\(.commit.author.name)|\(.commit.message | split("\n")[0])"' \
  > /tmp/gh_commits.txt
```

This gives a pipe-delimited `date|author|subject` file that's easy to slice with `cut`/`grep`.

### 2. Compute the headline metrics

- **Date range**: first and last commit timestamps.
- **Commit type distribution**: `cut -d'|' -f3 | sed -E 's/^([a-z]+)(\(.*)?[!:].*/\1/' | sort | uniq -c | sort -rn`
- **Monthly volume**: `cut -d'|' -f1 | cut -dT -f1 | cut -d'-' -f1,2 | sort | uniq -c`
- **Hour-of-day / day-of-week**: reveals work rhythm (weekend builder? evening bursts?).
- **Busiest days**: `cut -d'|' -f1 | cut -dT -f1 | sort | uniq -c | sort -rn | head`

### 3. The fix:feat ratio arc (the most revealing signal)

Compute fix vs feat counts per month. The ratio tells the project's maturity story:

| Ratio | Meaning |
|---|---|
| < 1.0 | Building — more features than fixes (greenfield) |
| ~ 1.0 | Stabilizing — fixes catching up |
| > 1.5 | Crunch — fix-heavy, paying down debt |
| > 3.0 | Hardening — almost pure fixing, model crystallizing |
| drops back < 1.0 | Renaissance — building cleanly again |

A spike then collapse (e.g. schema-churn 57 → 6 month-over-month) marks the moment a subsystem "finished."

### 4. Per-workstream categorization + difficulty ranking

Bucket commits into domains by keyword, then rank by BOTH volume and fix rate — they are different axes:

- **Volume** (commit count) = where effort went.
- **Fix rate** (fixes / total in domain) = how hard it was per unit of work.

Interpret fix-rate bands:
- **45%+** = integration surfaces / inference layers (everything converges, or no ground truth)
- **40%** = multi-source integration / geographic rendering
- **35%** = normalization / bottom-up discovery
- **~25%** = deliberately-designed, additively-built systems (pivots, not patches)
- **~34%** = deterministic computation (same inputs → same outputs, breaks least)

The pattern: integration surfaces and inference layers are hardest per-commit; deterministic engines are easiest per-commit (not because simple, but because reproducible).

### 5. Reconstruct the narrative chronologically

For each workstream, print its commits oldest-first and read them as a story. The commit messages reveal phases (discovery → normalization → scale → stabilization), abandoned approaches (reverts, "pivot to X"), and edge cases the data forced ("handle Antarctica collapse").

## Pitfalls

- **Shallow local clone**: the #1 trap. Always check the remote's true count first (step 1). Analyzing a squashed local log gives a wildly incomplete picture.
- **Loose keyword buckets**: words like "port", "ship", "map" appear in both data-layer AND UI commits. Use strict regex buckets and **spot-check 20-30 samples** before trusting a count. Report categorization as "keyword-based, a strong signal not a precise audit."
- **macOS has no `tac`**: reverse a file with `tail -r` instead of `tac`.
- **`rtk`/wrapper intercepting greps**: if a grep returns nonsense ("N matches in N files"), the shell wrapper is mangling it — extract values programmatically (e.g. python regex) instead.
- **Don't print secrets**: when pulling DB URLs or tokens from local config to run verification queries, extract them to a temp file programmatically and reference via `$(cat /tmp/...)` — never echo them into the transcript.
- **Job records lie; data doesn't**: for pipeline/insight verification, count actual table ROWS, not job-status records. Jobs can show `failed`/`cancelled` while the data completed (a recurring UI/status artifact). Trust `SELECT COUNT(*)` over the job table.

## Verification queries (project-agnostic shape)

When a user claims "X is done," verify against real data:
```bash
DATABASE_URL="<extracted-from-config>" npx tsx -e "
import { PrismaClient } from '@prisma/client';
const p = new PrismaClient();
// COUNT(*) each relevant table; print rows. Don't trust status fields.
"
```
Note: `railway run` may not inject `DATABASE_URL` for ad-hoc scripts — extract it from the project's local env/config file and pass explicitly. Prisma raw SQL on Postgres needs camelCase columns double-quoted (`"jobType"`, `"startedAt"`).

## Deliverable

For a retrospective, structure as: headline numbers → monthly arc table → per-workstream sections (each with its difficulty type) → difficulty ranking table → key patterns/lessons → "the product that emerged" inventory. See `references/command-recipes.md` for the exact slicing commands.
