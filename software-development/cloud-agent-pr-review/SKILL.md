---
name: cloud-agent-pr-review
description: Review/merge PRs from a second (cloud) agent instance.
---

# Cloud Agent PR Review

A second agent instance (e.g. a cloud the harness on a VPS) works the same repo
asynchronously and hands back work as **GitHub PRs from `agent/*` branches**. The
local agent is the reviewer and merger. First full cycle verified 2026-08-16
(the D&D VTT project, PRs #1 and #2).

This is the GitHub-PR counterpart of `delegation-result-verification`: the PR body's
self-reported gate output ("tests pass, typecheck clean, smoke-triage PASS") is the
same kind of self-report as a subagent dispatch summary — **claims to verify, not
evidence**.

## Branch ownership rules (typical co-dev contract — confirm the project's own)

- `agent/*` branches are cloud-owned: never check out, commit to, rebase, or delete.
  Review as PRs on GitHub only.
- Before any non-trivial local task: `git fetch --all --prune` + `gh pr list` and
  check open agent PRs for area overlap. Surface overlaps to the user before starting.
- Never force-push shared branches (`main`/`staging`/`develop`) — the cloud clone
  pulls them.
- Merge cloud PRs through GitHub only (`gh pr merge` or web UI), never by locally
  merging an agent branch — merges must fire CI and deploy webhooks normally.

## Verification without checkout

Branch rules forbid `git checkout agent/<slug>`. Verify the claimed gates by
materializing only the changed files into the working tree, running them, and
restoring clean:

```bash
mkdir -p <dir>   # directories new in the PR don't exist on the base branch
git show origin/agent/<slug>:path/to/file.ts > path/to/file.ts
git show origin/agent/<slug>:path/to/file.test.ts > path/to/file.test.ts
npx vitest run path/to/file.test.ts     # reproduces the claimed test gate
(cd apps/<pkg> && npx tsc --noEmit)     # reproduces the claimed typecheck
rm path/to/file.ts path/to/file.test.ts
git status -s                            # MUST show the tree restored clean
```

Also verify references resolve against the BASE branch — a PR that calls
`isDmOfCampaign(...)` only compiles if that helper exists on the base:

```bash
grep -n "export.*isDmOfCampaign" apps/api/src/auth/permissions.ts
```

Read the actual diff too (`git diff origin/<base>...origin/agent/<slug>`) — no
checkout needed for review reading, and check for forbidden paths (migrations,
`.github/`, `.env*`, secrets) the same way you would in any review.

## Same-account approval block

When the automation pushes under the user's own GitHub account,
`gh pr review --approve` fails with:

```
Review Can not approve your own pull request (addPullRequestReview)
```

Post the verdict as a comment instead: `gh pr review <n> --comment --body "..."`
with the verdict in the body ("LGTM — merging"). Formal approve/request-changes
only works once the automation has its own GitHub identity (bot account or GitHub
App). Flag this to the user ONCE as a setup improvement — don't work around it
per-PR.

## CI status may be unreadable with a limited PAT

`gh pr checks` and the `check-runs` REST endpoint can return
`403 Resource not accessible by personal access token` when the token lacks the
`checks:read` scope. **Do not conclude CI is absent** — check
`ls .github/workflows/` (or `git ls-tree origin/<base> --name-only .github/`)
first; the workflow file often exists and ran. Resolution is either the user adds
the scope, or the user eyeballs the Actions tab before merge — say which one
applies in the review comment.

## Merge + post-merge bookkeeping

1. Merge: `gh pr merge <n> --merge` (match the repo's merge-commit convention).
2. `git checkout <base> && git pull origin <base>` — local must track the merge.
3. Flip the PR's plan file (`docs/plans/...md`) to `status: completed` with a
   merge note recording any accepted AC deviations (e.g. LoC-cap overshoot whose
   bulk is test fixtures). Push that doc commit — the cloud instance pulls the
   status change on its next fetch and won't redo the work.
4. Close the matching gap entry in the project's plan index if there is one.
5. Note self-flagged deviations from the PR body in the review — a good cloud
   loop flags its own gate failures; verify the flag is honest and decide
   accept/reject explicitly, don't let it slide silently.

## What to verify independently (minimum bar per PR)

- [ ] Claimed test count reproduced locally (materialize-and-run above)
- [ ] Claimed typecheck reproduced locally
- [ ] Imports/symbols resolve against the base branch
- [ ] Auth/permission ordering read in the actual route code (gate-before-heavy-work)
- [ ] No forbidden paths, no production-code surprises in a "test-only" PR
- [ ] Plan caps (file count / LoC) checked against `git diff --stat`
- [ ] Docs/contract updates claimed in the PR actually present in the diff
