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

# Run the PR's NEW tests: extract only new files into the working
# tree, run the runner, then remove them and confirm clean.
git show origin/<head>:apps/api/src/routes/foo.ts > apps/api/src/routes/foo.ts
git show origin/<head>:apps/api/src/routes/foo.test.ts > apps/api/src/routes/foo.test.ts
npx vitest run apps/api/src/routes/foo.test.ts
rm apps/api/src/routes/foo.ts apps/api/src/routes/foo.test.ts
git status --short    # MUST be back to pre-review state
```

Limitations:
- Works cleanly only when the PR **adds** files. If it modifies existing files, extraction would dirty shared source — verify via CI or ask the user instead.
- Test extraction works when imports resolve against unchanged files (e.g. a new route + its test importing existing helpers). Verify imports exist on the base branch first (`grep` the symbol).
- Vitest/jest runners use esbuild — passing tests do **not** prove typecheck. Note typecheck as unverified unless you ran `tsc`.

## Check the PR against its own plan

Agent loops often commit a plan file in the PR. Diff the PR against the plan's acceptance criteria — agents sometimes claim a deviation is "approved scope" when the plan itself forbids it (e.g. an LoC cap the diff exceeds). Flag deviations explicitly; accept or bounce them, never let them pass silently.

## Merging

Merge only through GitHub (`gh pr merge <N> --merge` or web UI) so CI and deploy webhooks fire normally — never by locally merging the agent's branch. After merging: pull the base branch locally, then transition the plan's status field (e.g. `active → completed`, recording any accepted AC deviations) and update the plan index as a small follow-up commit.

## Pitfalls

1. **Blank approve failure looks like a gh bug** — it's GitHub policy on same-account PRs. Use `--comment`.
2. **`gh pr checks` failing ≠ CI failing** — distinguish token-scope 403s from real check failures before reporting "CI red" or "no CI".
3. **Extraction review left dirty tree** — always end with `git status --short` and confirm you restored the pre-review state.
4. **Trusting "excluded from canonical suite" claims** — when the PR body blames a pre-existing test failure, confirm it fails on the base branch too before excusing it.
