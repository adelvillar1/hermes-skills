---
name: git-history-analysis
description: "Use when mining git history for workstream insights."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [git, history, analytics, velocity, workstreams, retrospective]
    related_skills: [codebase-inspection, github-repo-management]
---

# Git History Analysis

Extract quantitative insights and narrative arcs from a repository's commit history. Use when the user asks "what can you infer from my git activity", wants a project retrospective, asks which areas were hardest, or frames hypotheses about their own work patterns that need evidence-based testing.

## When to Use

- User asks for insights from git/commit history
- User wants a project retrospective or "what took the most effort"
- User frames a hypothesis ("the bulk of fixes were in X") and wants it tested
- User asks about velocity, cadence, or work patterns
- User asks which feature/area was hardest or took longest

## Step 1: Get the FULL history

**Local clones are often shallow or squashed.** Always check GitHub first:

```bash
# Count commits on GitHub vs local
gh api "repos/OWNER/REPO/commits?sha=main&per_page=1" -i 2>/dev/null \
  | grep -i '^link:' | grep -oE 'page=[0-9]+>; rel="last"' | grep -oE '[0-9]+'
git log --all --oneline | wc -l
```

If GitHub has more, pull the full log via API:

```bash
gh api "repos/OWNER/REPO/commits?sha=main&per_page=100" --paginate \
  -q '.[] | "\(.commit.author.date)|\(.commit.author.name)|\(.commit.message | split("\n")[0])"' \
  > /tmp/gh_commits.txt
```

Format: `ISO_DATE|AUTHOR|MESSAGE` — pipe-delimited for downstream `cut -d'|'`.

## Step 2: Multi-dimensional analysis

Run these dimensions (batch independent queries in one terminal call):

| Dimension | Command pattern |
|---|---|
| Date range | `head -1` / `tail -1` of sorted dates |
| Commits by month | `cut -d'|' -f1 \| cut -dT -f1 \| cut -d'-' -f1,2 \| sort \| uniq -c` |
| Commit type | `cut -d'|' -f3 \| sed -E 's/^([a-z]+)(\(.*)?[!:].*/\1/' \| sort \| uniq -c \| sort -rn` |
| Hour of day | `cut -d'|' -f1 \| cut -dT -f2 \| cut -d: -f1 \| sort \| uniq -c` |
| Day of week | `date -j -f "%Y-%m-%d" "$d" "+%u"` (macOS) or `date -d "$d" "+%u"` (Linux) |
| Authors | `cut -d'|' -f2 \| sort \| uniq -c \| sort -rn` |
| Busiest days | `cut -d'|' -f1 \| cut -dT -f1 \| sort \| uniq -c \| sort -rn \| head -10` |

## Step 3: Domain classification via keyword buckets

Classify commits into workstreams using **strict** regex patterns. Critical rules:

1. **Use strict patterns** — ambiguous words cause false positives. "port" catches UI fixes about port *labels*; "ship" catches ship *cards*. Add `\b` word boundaries and exclude UI terms.
2. **Spot-check samples** — always `head -30` the matched commits to verify the bucket is clean.
3. **Buckets can overlap** — a commit can touch pipeline + UI. Acknowledge this; don't force mutual exclusivity.
4. **Separate signal from noise** — run a "strict" pass (high-confidence keywords) and a "broad" pass, report both.

Example bucket patterns (adapt per project):

```bash
# Data pipeline (strict)
grep -icE 'scrap|pipeline|junction|coherence|enrich|ingest|harvest|corridor|falkor|precompute|insight|materialized|redis|cache|worker|job|cron|dedup|upsert|prisma|jsonb|embedding|graph|signature|stale|drift|backfill|orphan|run_log|batch|delta'

# UI/frontend (strict)
grep -icE '\bui\b|button|modal|layout|css|style|render|component|sidebar|nav\b|responsive|mobile|viewport|scroll|font|color|theme|dark.mode|icon|loading|spinner|tooltip|dropdown|form.*(field|input)|tailwind|className|z-index|overflow'
```

## Step 4: Difficulty metrics

**Fix rate** = fixes / total commits in domain. This is the primary difficulty proxy:

```bash
total=$(cut -d'|' -f3 gh_commits.txt | grep -icE "$PATTERN")
fixes=$(cut -d'|' -f3 gh_commits.txt | grep '^fix' | grep -icE "$PATTERN")
echo "$fixes / $total = $(( fixes * 100 / total ))%"
```

Interpretation bands (empirical, from this project):
- <25%: clean / well-understood domain
- 25-35%: normal feature development
- 35-45%: hard problem, significant iteration
- >45%: very hard, likely inference/fuzzy matching with no ground truth

**Schema churn** as exploration signal: count commits mentioning schema/migration/column/table/model/relation. A sharp drop (e.g., 57→6) marks model crystallization.

**Exploration signal**: count reverts + rewrites + rebuilds + experiments. High counts = discovery phase, not maintenance.

## Step 5: Chronological reconstruction

For individual features, pull the full chronological commit list:

```bash
grep -iE "$FEATURE_PATTERN" gh_commits.txt | tail -r | cut -d'|' -f1,3 | sed 's/T.*Z|/ | /'
```

(`tail -r` reverses on macOS; use `tac` on Linux.)

Look for:
- **Big-bang vs. drip**: compressed burst (days) vs. steady trickle (months)
- **Architecture pivots**: "replace X with Y" commits (e.g., three rendering engines in 7 weeks)
- **Manual labor disguised as commits**: N consecutive "add X more overrides" commits
- **Resolution beats**: package extraction, "mark plan completed", fix-rate collapse
- **Product discipline**: "hide feature — not ready yet" commits

## Step 6: Synthesis format

Present findings as:
1. **Headline number** (the one stat that frames everything)
2. **Table** comparing domains/workstreams on commits + fix rate + timing
3. **Chronological narrative** — the arc from blank slate to current state, month by month
4. **Strategic takeaway** — what the pattern means for future work (not just what happened)

When the user frames a hypothesis, structure as: "You're right, AND here's the nuance" — confirm, then add the dimension they didn't see (e.g., "yes it was the most fixes, but it was really a *May* story").

## Pitfalls

1. **Local ≠ GitHub history.** Squashed/rebased clones lose months of history. Always compare counts first.
2. **Keyword false positives.** "port" matches UI port labels. "ship" matches ship cards. Use strict patterns + spot-check.
3. **Overlapping buckets.** A route-map commit about SVG caching is both "route maps" and "pipeline". Report overlap honestly.
4. **Commit count ≠ effort.** One "feat: complete UI migration" commit can be days of work. One "fix: add 5 more overrides" is 10 minutes. Use commit count as *direction*, not magnitude.
5. **Fix rate is a proxy, not truth.** A 46% fix rate could mean "hard problem" or "sloppy first pass". Cross-reference with the chronological log to distinguish.
6. **`tac` doesn't exist on macOS.** Use `tail -r` instead.
