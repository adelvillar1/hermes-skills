---
name: git-history-analytics
description: "Use when asked for insights/trends from git history."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, github, analytics, velocity, commit-history, forensics, metrics]
    related_skills: [codebase-inspection, github-repo-management]
prerequisites:
  commands: [gh, git]
---

# Git History Analytics

Turn a repository's commit history into insights: development velocity, the
build→stabilize→harden maturity arc, work rhythm (hours/days), deploy cadence,
and where the debugging effort actually goes (fix attribution by category).

## When to Use

- "What can you infer from my git activity / commit history?"
- "How has this project evolved over time?"
- "Where do most of the fixes go?" / "which area is the biggest time sink?"
- "What's the velocity / cadence on this repo?"
- Any request for trends, patterns, or a narrative from commit data.

## CRITICAL — Verify history depth BEFORE analyzing (the #1 pitfall)

**Never draw conclusions from a local `git log` without first confirming the
local clone holds the full history.** Local working copies are routinely
shallow (`git clone --depth N`), squashed, or rebased, and will silently show a
fraction of the real record. In one real session the local clone showed **50
commits all dated July**, while GitHub held **2,583 spanning Feb–Jul** — the
local view would have produced a completely wrong analysis.

Always cross-check local vs remote first:

```bash
# Local count (all branches)
git log --all --oneline | wc -l

# Remote true count — read the rel="last" page number from the Link header
gh api "repos/{owner}/{repo}/commits?sha={branch}&per_page=1" -i 2>/dev/null \
  | grep -i '^link:' | grep -oE 'page=[0-9]+>; rel="last"' | grep -oE '[0-9]+'
```

If they diverge materially, **pull the history from GitHub, do not analyze the
local clone.** See `references/recipes.md` for the full pull command.

## Workflow

1. **Verify depth** (above). Decide local vs GitHub as the source of truth.
2. **Pull the full log** into a flat `date|author|subject` file (recipes §1).
3. **Compute the standard dimensions** (recipes §2): by month, by hour (convert
   to the user's TZ), by day-of-week, commit-type distribution, busiest days,
   authorship split, deploy cadence.
4. **Build the maturity curve** — fix:feat ratio per month (recipes §3).
5. **Attribute fixes by category** with strict keyword buckets + spot-check
   (recipes §4). Cross-check against per-file churn.
6. **Narrate**, don't just tabulate — lead with the arc, name the phases.

## Interpreting the fix:feat maturity curve

The monthly `fix`-to-`feat` commit ratio is the single most informative signal:

| fix:feat | Phase | Reading |
|---|---|---|
| < 1.0 | 🟢 Building | Greenfield; shipping more than repairing |
| ~1.0 | 🟡 Stabilizing | Fixes catch up to features |
| > 2.0 | 🔴 Hardening / crunch | Paying down debt; little new feature work |
| rebounds to < 1 after a spike | 🟢 Renaissance | The hardening worked; building cleanly again |

A single month that dominates the lifetime fix count (e.g. ~half of all fixes
in one month) is a "wall" — name it and connect it to the volume spike.

## Pitfalls

1. **Shallow/squashed local clone** — see CRITICAL above. Verify depth first.
2. **Loose keyword buckets misattribute fixes.** Words like `port`, `ship`,
   `map` appear in both pipeline fixes AND UI fixes (`port label too small`,
   `ship card`). Use strict, anchored patterns and **spot-check 20–30 samples**
   before trusting a bucket count. Report the method and its caveat.
3. **Commit-message analysis is a signal, not an audit.** Say so. For precision,
   cross-check with per-file churn (`git log --grep='^fix' --stat`) on the
   relevant directories.
4. **Timezone.** `gh api` returns UTC. Convert hours to the user's local TZ
   before describing their "work rhythm" or you'll mislabel their day.
5. **Merge commits inflate counts.** `Merge branch 'develop' into staging` etc.
   are noise for velocity — note them and, for deploy cadence, count them
   *separately* (staging-merge vs prod-merge ratio = the staging gate).
6. **Agent-authored commits hide in the user's name.** Much agent-assisted work
   is committed under the user's identity. The explicit agent-author count is a
   floor, not the true figure — say "at least N" and note the recency cluster.

## Support files

- `references/recipes.md` — copy-paste command recipes: full-history pull, all
  standard dimensions, maturity curve, strict fix-attribution buckets.
- `scripts/history_report.sh` — re-runnable: pulls full history via `gh api` and
  prints the standard dimension tables. Pass `owner/repo` and a branch.
