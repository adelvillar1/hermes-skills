# Git Lock File Recovery

## When to use

- `git status`, `git add`, or `git commit` hangs indefinitely (timeout after 30s+)
- `git` commands return exit code 128 with no clear error message
- `.git/index.lock` exists and is stale (0 bytes, left by a crashed or timed-out previous command)
- Multiple `.git/index*` files appear (`.git/index 2`, `.git/index 3`, `.git/index 4`) from repeated failed attempts

## Symptoms

```bash
$ git status
# ... hangs for 30s, then exits 124 (timeout)

$ git add -A
error: exit code 128

$ ls -la .git/index*
.git/index         34.4K
.git/index 2      23.8K
.git/index 3      27.0K
.git/index 4      34.8K
.git/index.lock    0B
```

## Root causes

1. **Stale lock file** — a previous git command crashed or was killed, leaving `.git/index.lock` behind
2. **Duplicate index files** — macOS or other processes create numbered copies when the main index is locked
3. **Large repository** — `.next/` or `node_modules/` not in `.gitignore` causes git to scan thousands of files
4. **Concurrent git processes** — another tool (IDE, GitHub Desktop, etc.) is holding the lock

## Recovery steps

### Step 1: Kill any running git processes

```bash
ps aux | grep git | grep -v grep
# If any found, kill them: kill -9 <PID>
```

### Step 2: Remove stale lock files and duplicate indexes

```bash
cd /path/to/repo
rm -f .git/index.lock .git/index\ 2 .git/index\ 3 .git/index\ 4
```

Note: The space in `.git/index 2` requires escaping or quoting.

### Step 3: Verify git is responsive

```bash
git status
```

Should return instantly with the working tree status.

### Step 4: If still slow, check for untracked large directories

```bash
git status --short | wc -l
# If >1000, check .gitignore

cat .gitignore | grep -E "node_modules|\.next|dist|build"
# Ensure these are ignored
```

If `.gitignore` is missing or incomplete, add:

```
node_modules/
.next/
dist/
build/
*.log
```

### Step 5: If repository is corrupted, reset the index

```bash
# Nuclear option — rebuild index from HEAD
rm -f .git/index
git reset HEAD
```

This rebuilds the index from the current commit. Unstaged changes remain in the working tree.

## Prevention

- Always ensure `.gitignore` includes `node_modules/`, `.next/`, and other build artifacts
- Use `git add -A` sparingly on large repos; prefer `git add <specific-files>`
- Don't run concurrent git operations (e.g., `git status` in IDE while `git commit` in terminal)
- For CI/CD, use `git --no-optional-locks status` to avoid creating lock files

## Related

- `github-pr-workflow` — for the full PR lifecycle after git is working again
- `ci-github-actions` — if the lock issue is happening in CI (check for parallel jobs)
