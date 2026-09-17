# Interrupted Subagent Collateral Damage (2026-08-06)

A subagent reported `status=interrupted` but had actually modified the tree in the wrong places — deleting 7 files outside its scope while leaving its actual assignment untouched.

## Signature
- Summary is generic/short, mentions interruption reason
- `git diff --stat` shows DELETIONS that don't match task scope
- The files the task was SUPPOSED to modify are untouched

## Recovery
1. Run `git status --short` immediately on `interrupted` — don't trust the summary
2. Classify each changed file: unauthorized deletion vs. legitimate prior deletion vs. new creation
3. Check for active references before assuming a deletion is safe: `grep -rn "<base-name>" src/`
4. Restore unauthorized deletions with `git restore <file>` (not wholesale `git checkout`)
5. Complete the actual task that was left untouched

## Chained Pitfall — Surgical Revert
After identifying collateral damage, revert surgically — `git checkout -- <dir>` RESTORES intentionally-deleted files too, resurrecting stale duplicates. Use `git restore <file>` per-file.

## Mechanical Replacement Misses
A subagent reported success on a "replace all FontAwesome icons" task. Post-task grep revealed 16 misses — the replacement dict used wrong-shaped keys (`fa-bolt` instead of `fas fa-bolt`), making all `.replace()` calls no-ops. Always run the verification grep yourself after a mechanical replacement task.
