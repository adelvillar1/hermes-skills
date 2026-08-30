# Merge Conflict Handling: Stash + Cross-Branch Commit Recovery

**Scenario:** Changes were committed to the wrong branch (`main`) and need to be moved to the correct branch (`develop` → `staging`). Using `git stash` + `checkout` + `stash pop` can trigger add/add merge conflicts when the target branch already has divergent versions of the same files.

## Pattern: Safe Reapplication

```bash
# 1. Identify what files the commit touched
git show --name-only HEAD

# 2. Checkout the commit's tree into a temp dir  (optional, as safety copy)
mkdir /tmp/committed-files && git checkout HEAD -- . && cp -r . /tmp/committed-files/

# 3. Reset source branch back to remote state
git reset --hard origin/main

# 4. Switch to target branch
git checkout develop && git pull origin develop

# 5. Cherry-pick the commit hash
git cherry-pick <COMMIT_HASH>
# If this conflicts, resolve in the usual way and: git cherry-pick --continue

# 6. Push
git push origin develop
```

## Pattern: Manual Resolution When Stash Pop Conflicts

When `git stash pop` already failed and left a merge in progress:

```bash
# Inspect conflict markers  
git status --short | grep -E "^UU|^AA|^DD"

# For each conflicted file, decide:
git checkout --ours lib/path/to/file.ts    # keep target branch version
git checkout --theirs lib/path/to/file.ts  # keep stashed (source) version

# After resolving, stage and continue
git add lib/path/to/file.ts
git merge --continue

# If unrecoverable:
git merge --abort
git checkout -- .
git clean -fd    # removes untracked files/dirs
```

## Pitfall: `--theirs` vs `--ours` in rebase

In a **merge**, `--ours` = current branch (the one you switched TO), `--theirs` = the branch being merged IN (the stashed changes).

In a **rebase**, this flips: `--ours` = the incoming branch, `--theirs` = the current branch. Be careful when resolving rebase conflicts.

## Pitfall: "Theirs" Re-introduces Already-Fixed Imports

When you've fixed a file locally (e.g., changing `import { X }` to `import X` because the component switched from named to default export), and then resolve a merge conflict by accepting "theirs" (`git checkout --theirs <file>`), the remote's old version brings back the old import style.

**Result:** The file has BOTH import styles — your fix AND the old import. This produces build errors like:
```
the name `X` is defined multiple times
previous definition of `X` here
`X` redefined here
```

**Detection after conflict resolution:**
```bash
# Check for duplicate import lines in recently conflicted files
git diff --name-only --diff-filter=U  # files that had conflicts
grep -n "^import " app/some-file.tsx | sort | uniq -d  # find duplicate import lines
```

**Fix:**
1. After conflict resolution, inspect the imports section of each conflicted file
2. The old import (lines 15-17) will be lower in the file than the new import (lines 3-5)
3. Delete the old duplicate lines
4. Verify the file compiles: `npx tsc --noEmit app/some-file.tsx`

**Prevention:**
- After `git checkout --theirs <file>`, always re-verify the file's import section
- Apply fix patches in the same order: fix the imports first, THEN fix type errors
- Search for remaining named imports of the changed component: `grep -rn "import { ComponentName } from" app/`

## Avoiding the Problem

- Prefer `git cherry-pick` over `git stash` + `git stash pop` for moving work between branches.
- If you must stash, stash only tracked files (`git stash -- `) and never stash untracked files across branches.
- Before switching branches with uncommitted changes, always check `git status` for untracked files that could collide.
- When resolving merge conflicts in files where you changed import styles, manually inspect the combined result rather than blindly accepting "theirs" or "ours".
