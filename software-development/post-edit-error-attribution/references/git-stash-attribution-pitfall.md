# Pitfall: git stash for error attribution in shared/dirty worktrees

**Date:** 2026-08-05 (pampa-wineclub campaign)

## Context

While verifying a UI edit, `eslint` surfaced 1 error in code I hadn't touched. To prove it pre-existing, I used:

```bash
git stash -q && ./node_modules/.bin/eslint web/src/pages/Home.tsx && git stash pop -q
```

It worked — the error count matched (pre-existing confirmed), and `pop` restored cleanly. But the worktree had **14 modified files** from sibling tasks in a parallel campaign.

## Why stash is the wrong default here

`git stash` operates on the entire worktree, not the file being checked:

1. **Yanks concurrent work out mid-flight** — sibling agents' in-progress edits vanish from disk for the duration of the check. If any of them read/write the filesystem concurrently, they see a phantom-clean tree.
2. **Failed pop scrambles everything** — a conflict, interruption, or error during `pop` leaves 14 files' worth of other people's work in stash limbo. Recovery is possible but expensive and stressful in an autonomous (no-user-present) run.
3. The HEAD-swap protocol in SKILL.md (`cp` + `git show HEAD:file` + `cp` back) is strictly safer: it touches exactly one file, and the restore is chained in the same command.

## Rule

- Clean single-author worktree (`git status --short` shows only your files): `git stash` is acceptable.
- Multi-file or multi-agent worktree: always use the HEAD-swap check (`scripts/head-swap-check.sh`).
- If you did stash in a shared worktree, immediately verify the restore after pop: `git status --short` and `git diff --stat` should match the pre-stash state.

## Verification that worked in this session

```bash
cd <repo> && git stash -q && ./node_modules/.bin/eslint web/src/pages/Home.tsx 2>/dev/null | grep -cE "error"; git stash pop -q && echo "RESTORED"
# → 2 (error-line count includes the message banner; identical to post-edit run)
# then: git status --short && git diff --stat  → confirmed all 14 files back
```
