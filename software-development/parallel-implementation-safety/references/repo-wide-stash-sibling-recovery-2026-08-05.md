# Repo-wide stash sweeps sibling WIP — incident & recovery (2026-08-05)

Project: the wine-club app monorepo (React + Hono + Drizzle). Subagent dispatched to add a
wine-lineup editor to `EventForm` in `web/src/pages/WineClub.tsx`; a sibling subagent was
concurrently implementing backend routes/auth work (uncommitted) in the same working tree.

## What went wrong

1. Subagent finished its edits (web/src/lib/api.ts + WineClub.tsx) and ran `tsc` — clean.
2. ESLint reported one error in WineClub.tsx (`react-hooks/set-state-in-effect`, line ~1028).
3. To check whether the error was pre-existing, the subagent ran **`git stash`** (repo-wide,
   unscoped), then eslint on the stashed-away tree. It was pre-existing.
4. **The stash had captured the sibling's uncommitted backend WIP too** (api/src/routes/*,
   api/src/db/schema.ts, shared/src/index.ts, drizzle journal, Portal.tsx — 10 files).
5. `git stash pop` **failed**: "Your local changes to web/src/lib/api.ts would be overwritten
   by merge" — the sibling had rewritten `api.ts` during the stash window.
6. Net effect: working tree lost the sibling's backend files AND the subagent's own
   WineClub.tsx editor. Everything was preserved only inside `stash@{0}`.

## Recovery sequence that worked

```bash
# 1. Confirm the stash is intact; list its files
git stash show --name-status stash@{0}

# 2. Extract every stashed file for comparison
for f in <files>; do
  mkdir -p /tmp/stash-files/$(dirname $f)
  git show stash@{0}:$f > /tmp/stash-files/$f
done

# 3. Superset check (see script below): for each file, is every unique non-empty
#    stash line present in the working tree?
#    - api.ts: YES — sibling's rewrite had re-integrated all stashed lines plus new work
#      → keep working-tree version, do NOT restore from stash
#    - 9 other files: NO — content vanished from working tree → restore

# 4. Restore vanished files from the stash
git checkout stash@{0} -- <paths...>
# 5. Immediately unstage — checkout-from-stash stages the restore; sibling WIP must stay unstaged
git restore --staged <paths...>

# 6. Re-verify superset for ALL stashed files, then drop
git stash drop stash@{0}

# 7. Re-run typecheck across all affected packages (web, api, shared)
```

## Superset-check script

Compares whitespace-stripped line sets; prints any stash-only lines (= lost content).

```python
import subprocess

repo = "/path/to/repo"
files = ["web/src/lib/api.ts", "..."]  # every file in the stash

all_ok = True
for f in files:
    stash = subprocess.run(["git", "show", f"stash@{{0}}:{f}"],
                           cwd=repo, capture_output=True, text=True).stdout
    work = open(f"{repo}/{f}").read()
    s = {l.strip() for l in stash.splitlines() if l.strip()}
    w = {l.strip() for l in work.splitlines() if l.strip()}
    missing = s - w
    if missing:
        all_ok = False
        print(f"LOST CONTENT in {f}: {len(missing)} lines")
        for m in sorted(missing)[:5]:
            print("   ", m[:100])
    else:
        print(f"superset-ok: {f}")
print("ALL STASH CONTENT PRESENT IN WORKING TREE:", all_ok)
```

A plain `diff` is useless for the superset question: the sibling's rewrite shifted every line
number, so line-oriented diff shows ~the whole file changed while semantically nothing was lost.
Set comparison of stripped lines is the correct granularity.

## Signals used to triage

- `stat -f "%Sm %N" <files>` + `date` — sibling's files had an mtime from *before* the stash
  moment (reset by the stash, never re-touched) → their content was gone, not mid-edit.
- Marker greps (`eventWines` in schema.ts, `EventWineCreateSchema` in shared, `updateWine`
  in WineClub.tsx) — fast "is the content in the working tree at all?" probes.

## Lessons

- The `react-hooks/set-state-in-effect` error was pre-existing and **not worth the blast
  radius of a repo-wide stash** to prove. Line-number inspection or `git show HEAD:file |
  npx eslint --stdin` answers the same question non-destructively.
- The recovery obligation extends to the sibling's files the stash captured, not just yours —
  dropping the stash after restoring only your own files destroys someone else's WIP.
- `git checkout stash@{0} -- <path>` stages the restored files; remember `git restore --staged`.
