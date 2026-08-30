---
name: post-edit-error-attribution
description: Attribute post-edit errors via a HEAD-swap check.
---

# Post-edit error attribution

When a linter, typechecker, test suite, or build surfaces an error after you've edited code, the two failure moves are:

- **Absorbing blame** — assuming you caused it and scope-creeping into fixing unrelated code mid-task. This bloats the diff, muddies review, and risks breaking out-of-scope behavior.
- **Dismissing without proof** — assuming it's pre-existing and moving on. If it's actually your regression, you ship it.

Both are avoided by one cheap check: **run the same check against the HEAD version of the file.**

## When this fires

- ESLint / tsc / pytest / build reports an error after your edits, and the error location is in code you don't remember touching.
- A test fails after your change, but the failing test covers a different feature.
- You need to honestly report "did my change introduce any new errors?" to a reviewer or parent agent.

## The protocol (30 seconds)

Swap in the HEAD version of the file, run the same check, restore yours — chained so the restore can't be forgotten:

```bash
cp path/file.tsx /tmp/mine.tsx
git show HEAD:path/file.tsx > path/file.tsx
npx eslint path/file.tsx        # or tsc --noEmit / pytest / the failing check
cp /tmp/mine.tsx path/file.tsx  # restore immediately, same command chain
```

A reusable wrapper lives at `scripts/head-swap-check.sh`.

Compare outputs:

| HEAD result | Attribution | Action |
|---|---|---|
| Identical error(s) | Pre-existing | Report with evidence; move on |
| Clean | You introduced it | Fix it, re-run |
| Different / fewer errors | You introduced the delta | Fix the delta |

## Decision after attribution

**Pre-existing:** Report it with evidence — don't silently fix unrelated code mid-task unless asked. Example:

> `eslint` → 1 error: `react-hooks/set-state-in-effect` at `Foo.tsx:769` in the **untouched Signups component**. Verified pre-existing by running the same check against the `git show HEAD` version (identical 1 error). **Zero new errors introduced by this change.**

That gives the reviewer evidence, not a claim. If the pre-existing issue is trivial and obviously safe, offer to fix it as a separate change — don't fold it into the current diff.

**Introduced:** Fix it, then re-run the check to confirm clean.

## Pitfalls

1. **Re-run the final verification after swap/restore.** The swap-restore cycle is easy to botch (forgetting the restore, editor overwriting mid-swap). After restoring, run the build/check once more so the final verification reflects the exact on-disk state, and confirm with `git status --short` / `git diff --stat` that only your intended files are modified.
2. **Scope the check to the files you touched.** In a large codebase, `npx eslint .` surfaces a wall of pre-existing noise that drowns your signal. Lint your files: `npx eslint src/pages/Foo.tsx src/lib/bar.ts`.
3. **Don't absorb blame.** If it's pre-existing, don't say "I introduced an error, let me fix it." Report the attribution honestly.
4. **Don't dismiss without proof.** "It's probably pre-existing" is a guess; the HEAD swap is 30 seconds. An unproven dismissal that turns out to be your regression is far costlier.
5. **New files have no HEAD.** `git show HEAD:path` fails for brand-new files — the error is necessarily yours (the file didn't exist before). For renamed files, use the original path at HEAD.
