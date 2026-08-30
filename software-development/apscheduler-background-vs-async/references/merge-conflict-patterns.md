# Merge patterns for long-running project repos

Patterns observed when merging feature branches back to main in long-running project repos. These apply broadly — not specific to any one project.

## Pattern: cumulative recap merge conflict

**Symptom**: `git merge <worktree>` produces a conflict in a `SESSION-RECAP-*.md` file (or any "running journal" doc). The conflict markers look like:

```
<<<<<<< HEAD
---

## Session 8: ...
<content from main>
=======
>>>>>>> feat/<branch>
```

The worktree side is **empty** between the markers.

**Root cause**: The project's house rule is that session recaps are **cumulative** — each session appends to the running recap, never replaces. When:
1. The worktree's branch was created, the recap had a Session N.
2. Meanwhile, main got a Session N+1 (or N+2) committed separately (a hotfix, a parallel session, a manual push).
3. When the worktree tries to merge, the cumulative additions from main (after the branch point) conflict with the worktree's existing recap state.

**Resolution**: Keep main's side. The worktree's side is empty because the branch hasn't seen main's additions yet — once merged, main's Session N+1 will appear in the worktree's history too. The worktree's own Session N+2 (added after the merge candidate was created) will be re-applied on top.

```bash
# See the conflict
git status
git diff docs/recaps/SESSION-RECAP-YYYY-MM-DD.md

# Surgical resolution: drop the worktree's empty side
python3 <<'PYEOF'
import sys
path = sys.argv[1]
with open(path) as f: content = f.read()
# Remove the empty feat/<branch> side
old = '\n=======\n>>>>>>> feat/<branch>'
new = ''
content = content.replace(old, new)
# Remove the <<<<<<< marker line
old = '\n<<<<<<< HEAD\n---\n\n## Session'
new = '\n---\n\n## Session'
content = content.replace(old, new)
with open(path, 'w') as f: f.write(content)
print('Conflict resolved — kept main\'s cumulative content.')
PYEOF

git add docs/recaps/SESSION-RECAP-YYYY-MM-DD.md
git commit -m "Merge feat/<branch>: ... (conflict in SESSION-RECAP resolved: kept main's cumulative content)"
```

**Verification**:
```bash
# No conflict markers remain
grep -E "^(<<<<<<<|=======|>>>>>>>)" docs/recaps/SESSION-RECAP-*.md
# All sessions are present in order
grep "^## Session " docs/recaps/SESSION-RECAP-*.md
```

**Anti-pattern**: Resolving by taking the worktree's side. This drops Session N+1 from main and creates a regression.

## Pattern: main advanced N commits while you worked in the worktree

**Symptom**: `git fetch origin` and `git status` shows:
```
Your branch is ahead of 'origin/main' by 3 commits.
```

Or `git checkout main && git pull` (or `git merge origin/main` from the worktree) shows multiple unrelated commits from a parallel session.

**Root cause**: Another session (or a manual push) made commits on main while you were working in a worktree. Common causes:
- A hotfix was committed directly to main for production issues
- A parallel session ran a recap/plan that's still useful
- A teammate pushed their own work

**Resolution strategy**:
1. **If the main commits are docs-only (recaps, plans, STATE-SNAPSHOT)**: don't squash, don't cherry-pick. Just `git merge origin/main` (or `git merge main` from the worktree) and resolve any conflicts as you go. The docs land on your branch too.
2. **If the main commits touch code that conflicts with your work**: you need a real merge. Review each commit, resolve conflicts, and commit. The merge preserves history and lets you re-verify with the full pytest suite.
3. **If the main commits are unrelated and your work is feature-scoped**: do a clean fast-forward if possible; otherwise `git merge --no-ff` to keep the topology clean.

**Don't rebase through shared branch points.** If main has commits your worktree doesn't, **don't rebase** — rebasing rewrites history and breaks the merge topology for any other worktrees. Use `git merge` instead.

## Pattern: feature worktree behind main by N commits

**Symptom**: `git fetch && git status` in your worktree shows "3 commits behind main".

**What to do**:
1. **If your work is in flight** (uncommitted, or commits not yet pushed): merge main into your branch first, resolve conflicts, then continue.
2. **If your work is complete and you're about to push+merge to main**: just `git push` and `git checkout main && git merge <your-branch>`. The merge will fast-forward if your branch is based on the old main HEAD, or will be a merge commit if it's not.

**Anti-pattern**: pushing and hoping for the best. Always `git fetch` and `git status` before any push to verify your branch isn't behind.

## Pattern: when the deploy is sacred and the worktree is just a sandbox

If the production deployment is sacred (e.g., it must not be broken by a half-baked merge), follow this pre-merge protocol:

1. **Push the worktree branch**: `git push origin <branch>`
2. **Verify GitHub sees the new commits**: `gh api repos/<owner>/<repo>/commits?per_page=3`
3. **On main, do a `git fetch` and verify the relationship**: `git log --oneline origin/main..HEAD` (should show what you'll be merging)
4. **For first-time deploys to a new service**: point the deploy target (e.g. Railway) at the feature branch (not main) for the first deploy, watch the build, verify health
5. **Only after the build is healthy**: merge to main and push

This is the "test on a branch, ship on main" pattern. The branch deployment catches env-var / build issues without polluting main with a broken build.

## Pattern: after merge, always smoke-test the deploy

Don't trust "code merged, must be working" — verify the live deploy reflects the new code and is healthy:

```bash
# 1. Confirm GitHub has the new commits
gh api repos/<owner>/<repo>/commits?per_page=3 | jq -r '.[] | "\(.sha[0:8])  \(.commit.message | split("\n")[0])"'

# 2. Confirm local + origin are in sync
git log --oneline -3
git fetch origin && git log --oneline origin/main -3
# Local and origin HEAD should match

# 3. Confirm the production service is healthy and has the new code
# For Railway:
railway logs --service <service-name> | tail -20
# Look for: deployment success messages, scheduler boot, new code paths firing

# 4. Smoke-test the affected endpoints
curl -sS https://<production-url>/api/<endpoint> | head
# Compare response shape to pre-merge expectations
```

**Real example**: After a Session 9 merge (the oddsportal scraper), production was returning 502 on the calibration endpoint. Looking at the Postgres schema revealed a `market_odds_history` table was missing from production — a pre-existing data issue, not introduced by the merge. But the user couldn't have known that without the smoke test. **Always verify after deploy.**
