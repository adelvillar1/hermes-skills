---
name: paired-agent-pr-review
description: "Review PRs from a paired cloud agent (agent/* branches)."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [code-review, github, pull-request, multi-agent, cloud-agent]
    related_skills: [review-changes]
---

# Paired-Agent PR Review

Reviewing PRs authored by another agent instance (cloud VPS, async worker) that pushes under the user's own GitHub account from branches you must not touch (e.g. `agent/*`).

## When to Use

- A paired/cloud agent opened a PR and the user asks you to review or merge it
- The repo has branch-ownership rules forbidding checkout of the author's branches
- The PR body contains agent self-reported gate output ("tests pass", "typecheck clean")

## The three ways this differs from a normal review

### 1. You cannot formally APPROVE a same-account PR

If the cloud agent pushes under the user's GitHub account, GitHub rejects approval:

```
Review Can not approve your own pull request (addPullRequestReview)
```

Fall back to a comment review and say approval was intended:

```bash
gh pr review <N> --comment --body "...(intended: approve)..."
```

Long-term fix to suggest once: give the cloud agent its own GitHub identity (bot account or GitHub App) — that also fixes attribution.

### 2. CI status may be unreadable — check before trusting it

If the PAT lacks `checks:read`, both of these fail with `Resource not accessible by personal access token`:

```bash
gh pr checks <N>                                   # GraphQL statusCheckRollup
gh api repos/<owner>/<repo>/commits/<sha>/check-runs
```

This is a **token-scope gap, not "no CI"**. Verify gates locally (below) and ask the user to confirm CI green in the Actions tab before merging — or request the `checks:read` scope.

### 3. Never trust the PR body's self-reported gates

"npm test exit 0, 4/4 pass" in an agent-authored PR body is an **unverified assertion**. Reproduce the critical gate yourself before recommending merge.

## Review without checking out the agent's branch

Branch-ownership rules (e.g. "never check out `agent/*`") don't block a full verification review:

```bash
git fetch --all --prune

# Diff and stats without checkout
git diff origin/<base>...origin/<head> --stat
git diff origin/<base>...origin/<head> -- path/to/file

# Read full files at the PR head — diffs alone miss context
git show origin/<head>:path/to/file

# Run the PR's NEW tests — materialise in a SCRATCH tree, never the shared clone.
# Writing PR files into a shared clone dirties state other sessions read and makes
# this run's own `git status` check meaningless; the residue then gets blamed on
# "a concurrent session" that never existed.
SCRATCH=/opt/data/cache/scratch/pr-review-$(date +%s); mkdir -p "$SCRATCH"
git archive origin/<head> | tar -x -C "$SCRATCH"     # PR tree, no .git, clone untouched
ln -s "$PWD/node_modules" "$SCRATCH/node_modules"    # reuse installed deps
cd "$SCRATCH" && npx vitest run apps/api/src/routes/foo.test.ts
cd -; git status --short                             # shared clone MUST still be empty
```

Limitations:
- Works cleanly only when the PR **adds** files. If it modifies existing files, extraction would dirty shared source — verify via CI or ask the user instead.
- Test extraction works when imports resolve against unchanged files (e.g. a new route + its test importing existing helpers). Verify imports exist on the base branch first (`grep` the symbol).
- Vitest/jest runners use esbuild — passing tests do **not** prove typecheck. Note typecheck as unverified unless you ran `tsc`.

## Verify status claims by measurement, not by framing

A pre-flight or review report states status; the reader needs the numbers behind it. These five checks are what turn a confident sentence into a verifiable one — commands and interpretation table in `references/ref-arithmetic.md`.

- **Staleness is a count, not a claim.** A head that carries `Merge origin/<base> … (refresh #N)` is *not* current. Quote `git rev-list --count origin/<base> --not origin/<head>` plus the head commit's date. A refresh freezes the gap; it does not close it.
- **Merge order comes from code, not from merge-tree.** Two PRs can merge cleanly in either order and still have a runtime dependency. Grep the sibling head for a shim that names the other PR ("added on the still-open T5 PR, unmerged") and quote it. A clean `git merge-tree --write-tree` proves textual compatibility only — say so before recommending an order.
- **Containment has direction.** `git rev-list --left-right --count A...B` prints LEFT=A-only / RIGHT=B-only. RIGHT=0 means B fully contains A: report *promoted*, never "behind". Before alleging a rewrite from any asymmetry, re-run with `--no-merges` and name the pattern — a `--no-ff` release flow permanently leaves main carrying merges the lane below lacks.
- **An ancestry gap is not a content gap.** A commit absent from a branch by SHA may be present by content, because a cherry-pick or rebase creates a duplicate. Compare `git show <sha> | git patch-id --stable` and the blobs of the files it touched (`git rev-parse <ref>:<path>`) before calling anything "missing", and never recommend merging a lane back to "close" such a gap — it is ancestry churn.
- **Test counts are expanded counts.** `grep -c 'it('` counts blocks, but `it.each(table)` expands at runtime; check for `it.each`/`test.each` before disputing a PR's test total.

## Check the PR against its own plan

Agent loops often commit a plan file in the PR. Diff the PR against the plan's acceptance criteria — agents sometimes claim a deviation is "approved scope" when the plan itself forbids it (e.g. an LoC cap the diff exceeds). Flag deviations explicitly; accept or bounce them, never let them pass silently.

## Merging

Merge only through GitHub (`gh pr merge <N> --merge` or web UI) so CI and deploy webhooks fire normally — never by locally merging the agent's branch. After merging: pull the base branch locally, then transition the plan's status field (e.g. `active → completed`, recording any accepted AC deviations) and update the plan index as a small follow-up commit.

## Pitfalls

1. **Blank approve failure looks like a gh bug** — it's GitHub policy on same-account PRs. Use `--comment`.
2. **`gh pr checks` failing ≠ CI failing** — distinguish token-scope 403s from real check failures before reporting "CI red" or "no CI".
3. **Extraction review left dirty tree** — always end with `git status --short` and confirm you restored the pre-review state.
4. **Trusting "excluded from canonical suite" claims** — when the PR body blames a pre-existing test failure, confirm it fails on the base branch too before excusing it.
5. **Residue in the shared clone** — extract to a scratch tree (see above); a review that dirties the clone it is reviewing cannot honestly report a clean tree, and its own writes look like someone else's leftovers.
6. **Reading a deploy status from a retired platform** — commit-status contexts keep reporting the platform that posted them. When a repo migrates deploy providers, old-context `success` is not evidence the new platform deployed. Read the current deploy section of the repo's own docs before calling a merge deployed, and label any legacy-context claim as ambiguous.
7. **Quoting a remembered number as current** — indexes, counts, and heads move. Re-measure the fact in the run that reports it; a pinned value needs a date and a re-measure instruction, or it becomes a standing falsehood.
