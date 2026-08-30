---
name: project-wrapup
description: "Use when wrapping up a working session — verifies the handoff to the next session is clean. Checks for existing recap, stale project memory, uncommitted changes, plan status transitions, deferred doc-update debts, and runs drift checks. Use when user says 'wrap up', 'we're done', 'sign off', 'end session', 'close out'."
version: 2.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [project-management, session-end, handoff, verification, methodology]
    related_skills: [project-warmup, draft-feature-plan, write-session-recap, branch-sync-protocol, computation-cascade-map, data-drift-detection]
---

# Project Wrapup

The end-of-session counterpart to `project-warmup`. Where warmup READS everything a fresh session needs, wrap-up VERIFIES that everything the next session will need has been written or noted. It's the final gate before the user closes the session.

## When to Use

- User says "wrap up", "we're done", "shut it down", "sign off", "end session", "close out", or any session-end phrasing
- After `/recap` has been run (if needed), or alone for trivial sessions where no recap was warranted
- At the very end of any session that touched anything — even a one-line fix benefits from a 30-second drift check

## What This Skill Does (and Does NOT Do)

**Does:**
- Verifies a recap exists for today (or that the session was trivial enough to skip one)
- Checks project memory "Today's state" bullets for staleness and proposes updates
- Surfaces uncommitted changes and asks for explicit disposition
- Checks for draft plans that should be promoted to active before the next session
- Checks for active plans that should be flipped to completed/abandoned
- Aggregates deferred doc-update debts across recent recaps and escalates repeat offenders (3+ sessions in a row)
- Kills session-registered processes at session end (dev servers, watchers, tunnels, docker compose stacks / dev containers started this session — see `session-process-registry`)
- Verifies local env file edits are mentioned in the recap
- Runs drift checks: project memory ≤300 lines, local env gitignored, all pointer paths resolve, no secret leaks
- Drafts a one-sentence next-session preview

**Does NOT:**
- Walk acceptance criteria (that's `write-session-recap`'s job)
- Propose contract-doc updates (that's `write-session-recap`'s job)
- Write a new recap file (if missing, defers to `/recap`)
- Auto-commit, auto-stash, or auto-discard changes
- Auto-promote draft plans or auto-flip active plans without user confirmation

## Workflow

### 1. Pre-flight

```bash
[ -f CLAUDE.md ] || [ -f PROJECT.md ] || { echo "no project memory file"; exit; }
[ -d docs/recaps ] || [ -d .hermes/recaps ] && echo "OK: recaps dir" || echo "WARN: no recaps dir"
git status --short
```

### 2. Verify recap exists for today

```bash
TODAY=$(date +%Y-%m-%d)
RECAP="docs/recaps/SESSION-RECAP-${TODAY}.md"
[ -f "$RECAP" ] && echo "OK: today's recap" || echo "MISSING: no recap yet"
```

If recap is missing, ask user: "Was this a trivial session (typo, dependency bump, one-line fix), or do you want to run `/recap` first?"

### 3. Check "Today's state" for staleness

Read the "Today's state" section of the project memory file. Compare against:
- The latest recap's Summary and Plans worked on
- Recent commits (`git log --since="$(date -v-7d +%Y-%m-%d)" --pretty=format:'%h %s' --no-merges`)

For each stale bullet, propose an update. Show before/after. Ask for approval. If deferred, note staleness in the wrap-up report.

### 4. Surface uncommitted changes

```bash
git status --short
```

If uncommitted changes exist, list them and ask user to choose:
- **Commit now** — user handles commit
- **Hold over** — note in wrap-up report, next session's `/warmup` will see the dirty tree
- **Stash** — `git stash push -m "wrap-up YYYY-MM-DD"` (with explicit user approval)
- **Discard** — only with explicit user confirmation (destructive)

If working tree clean: say so.

### 4b. Check ALL worktrees for unpushed commits (critical for multi-service projects)

If the project has independent worktrees (e.g., `.worktrees/pipeline-worker/`, `.worktrees/scraper/`), verify each one:

```bash
# Main repo
git log --oneline origin/staging..HEAD 2>/dev/null || echo "Main repo: no unpushed commits"

# Pipeline-worker worktree
cd .worktrees/pipeline-worker 2>/dev/null && git log --oneline origin/pipeline-worker..HEAD 2>/dev/null || echo "Pipeline-worker: no unpushed commits"

# Scraper worktree
cd .worktrees/scraper 2>/dev/null && git log --oneline origin/scraper..HEAD 2>/dev/null || echo "Scraper: no unpushed commits"
```

If any worktree has unpushed commits that affect a deployed service, **surface this explicitly** and ask if they should be pushed. The user may have forgotten that `pipeline-worker` deploys from its own branch. Saying "everything good" when a worktree is 3 commits behind causes the service to run stale code — a process failure that wastes the user's time.

### 4c. Verify the DEPLOYED service is actually healthy (not just the repo)

Unpushed-commit checks only verify the git state. They do NOT verify that the live service on Railway is running the code you just pushed. After a merge to main that affects the main service's deploy config (railway.toml, Dockerfile, startCommand), explicitly verify the service is healthy — not just that the merge landed:

```bash
# Hit the main service's health endpoint (NOT the worker)
curl -sS -w "HTTP %{http_code}\n" "https://<main-app-url>/api/health"

# Hit a non-trivial endpoint to verify the actual app is up, not just the LB
curl -sS -w "HTTP %{http_code}\n" "https://<main-app-url>/api/calibration/market-odds?sport=mlb&start=2026&end=2026"

# If 502/503/504: the deploy likely broke something — check what was in the merge
```

**Why this matters**: git push + Railway auto-deploy is "the merge is live" but NOT "the live service is healthy." The `railway.toml` bug pattern (where a worker branch's config got merged into main and overrode the main service's deploy) only surfaces when the running service returns the wrong response. File-level checks don't catch it; only the live HTTP response does.

**Real example (elo-scenario-lab, 2026-06-02)**: After merging `feat/oddsportal-worker` to main, the worker's `railway.toml` overrode the main service's config. Git status was clean, no unpushed commits, drift checks passed. The 502 only appeared when hitting the actual URL. Caught because the user demanded real verification, not file-level checks.

**Pattern to bake into the wrapup report**:
- ✅ All commits pushed
- ✅ No worktree drift
- ✅ Drift checks pass
- ⭐ **The deployed service responds 200 to /api/health and at least one business endpoint** — the most important verification, often skipped because git is "clean"

**When to skip**: If no deploys were made this session (doc-only changes, planning work, no code touched), skip this step. The risk is zero.

**When to use**: After ANY merge to main, after ANY push that triggers Railway auto-deploy, after ANY worktree merge.

### 5. Check for plan status transitions

```bash
grep -l '^status: draft' docs/plans/*.md .hermes/plans/*.md 2>/dev/null
grep -l '^status: active' docs/plans/*.md .hermes/plans/*.md 2>/dev/null
```

**Draft plans**: ask "Promote to `active` before next session? Active plans get surfaced by warmup; draft plans don't."

**Active plans**: compare acceptance criteria against latest recap's criteria walk. If all criteria met but plan still `active`, propose flipping to `completed`. If no criteria touched this session, leave alone.

Apply approved transitions by editing plan frontmatter (`status:` and `updated:`).

### 6. Aggregate deferred-update debts and escalate repeat offenders

Read latest 3-5 recaps. Extract "Doc updates deferred (debt)" from each. Build a counter: how many consecutive recaps does each deferral appear in?

For deferrals appearing in **3+ consecutive recaps**, escalate:

> ⚠️ ESCALATION: "<update>" has been deferred 3 sessions in a row (recaps: 2026-04-06, 2026-04-07, 2026-04-08). Recommendation: address now, mark as accepted debt, or downgrade to tracked issue.

For deferrals appearing 1-2 times, just list them as known debt.

### 6b. Process cleanup sweep (session-process-registry)

Before hand-off, sweep the process registry so this session doesn't leave dev servers, watchers, or tunnels running on the local machine:

```bash
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py sweep --kill
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py orphans
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py docker-orphans
```

- `sweep --kill` kills exactly what this session registered during work (each start during the session should have registered via the `session-process-registry` skill) — including registered compose projects and standalone containers. Quote its summary line in the wrap-up report (`N killed, M pruned, K alive-left`).
- `orphans` is report-only: if it lists unregistered leftovers (typical after a session that crashed before wrapup), show the list and kill only pids the user explicitly approves.
- `docker-orphans` lists compose projects and dev-shaped containers running but not registered — show the list; bring stacks down (`--down-projects` / `--stop-containers`) only with explicit user approval. Volumes are never removed.
- If another Hermes session on this machine is actively working, do NOT kill its registered entries — let its own wrapup sweep them.

### 7. Verify local env changes noted in recap

Ask user: "Did you edit the local env file this session? (rotate a credential, add a new env, change a URL)?"

If yes:
- Check if recap has a "Local env changes" section
- If not, propose adding a one-line entry (high-level, never paste secrets)
- If approved, edit the recap

If no: skip.

### 8. Drift checks

**Schema drift:**
```bash
STAGING_PG_PASSWORD="$STAGING_DB_PW" python3 scripts/detect-schema-drift.py --cron 2>&1 | tail -10
```

**Branch drift (multi-worktree projects):**
```bash
bash scripts/detect-branch-drift.sh
```

If branch drift is found and the session touched shared code directories (`scripts/insights/`, `lib/`, `server/`, `app/`, `prisma/`), sync the worktrees BEFORE considering the session done. See `branch-sync-protocol` skill for the full rsync pattern.

The drift script automatically runs `npx tsc --noEmit` on full-sync worktrees after checking file divergence. This catches stale imports and missing modules that file-level sync alone can't detect. If TypeScript errors are found, fix them before considering the wrap-up complete — they indicate the worktree has stale references that will cause runtime failures.

**Data drift (staging vs production entity counts):**
```bash
bash scripts/detect-data-drift.sh
```

If data drift exceeds 5% on any insight table (>30% on insight tables is critical — production serving stale recommendations), surface the drift and suggest a sync. Never push to production without explicit user approval.

**Project memory size:**
```bash
wc -l CLAUDE.md  # or PROJECT.md — should be ≤300 lines
[ $(wc -l < PROJECT.md) -le 300 ] && echo "OK" || echo "WARN: over 300 lines"

git check-ignore -v PROJECT.local.md 2>/dev/null && echo "OK: local env gitignored" || echo "WARN: not gitignored"
git status --short | grep -q PROJECT.local.md && echo "FAIL: local env in git status" || echo "OK: local env invisible"

# Verify docs pointer paths in project memory resolve
for f in $(grep -oE 'docs/[a-zA-Z0-9_/.-]+\.md' PROJECT.md); do
  [ -e "$f" ] || echo "MISS: $f referenced in PROJECT.md does not exist"
done
```

Secret-leak grep on tracked files modified this session:
```bash
git diff --name-only HEAD~1..HEAD 2>/dev/null | xargs -I {} grep -lEn 'postgres:[a-zA-Z]{15}|password\s*[:=]\s*[A-Z]|github_pat_|sk_live_|sk_test_' {} 2>/dev/null
```

Report any failures. If project memory is over the line budget, propose moving content out next session.

### 9. Draft next-session preview

Based on:
- Active plans with unmet criteria → "pick up <plan> at criterion <X>"
- Held-over uncommitted work → "uncommitted: <files>"
- Open follow-ups from this session's recap → "follow-up: <thing>"
- Escalated debts → "escalated debt: <thing>"

Draft single-sentence preview, e.g.:

> Next session: pick up `2026-04-08-cabin-scoring` at criterion 3 (cabin scores in Postgres), follow up on AI Chat hallucination case from today's recap, address deferred `docs/features/billing.md` update (3rd deferral).

Propose injecting into:
- **Project memory "Today's state"** as the last bullet (warmup picks it up first thing)
- **The recap's "Open questions / next steps"** section

Recommendation: both.

### 10. Generate wrap-up report

Use the template at `templates/wrapup-report.md` as the shape. Fill in results from each step above. Present as a single response.

### 11. Hand off

> Session wrapped up. Recap exists|skipped, "Today's state" is current|updated|deferred, working tree is {{clean|held-over|stashed|committed}}, plans status is {{up-to-date|flipped}}, drift checks {{passed|warnings}}. Next session preview: "{{preview}}". Safe to close.

If drift check scripts timeout (e.g., the DB is under heavy load from a VACUUM FULL), note it as a skipped check in the report — not a failure. Re-run at the next warmup when the DB load has settled. Do NOT increase the terminal timeout to wait it out during wrapup; the session is ending.

If anything failed, surface as warnings, not blockers. The user owns the call.

## Common Pitfalls

1. **Running wrap-up before substantive work is done.** This skill is the closing gate, not a mid-session check.
2. **Forgetting worker branches.** If shared scripts were modified this session, verify the changes were pushed to `pipeline-worker` and/or `scraper` worktree branches too. A missing push to worker branches means the Railway deployment will run stale code. See `project-warmup` references/warmup-git-branch-checks.md § "shared script parity".
2. **Running wrap-up as a substitute for recap.** Recap captures substance; wrap-up verifies handoff. If recap needed, defer to `/recap` and re-run wrap-up after.
3. **Auto-committing, auto-stashing, or auto-discarding.** Disposition is always the user's call.
4. **Auto-promoting draft plans or auto-flipping active plans.** Status changes are decisions, not housekeeping.
5. **Pasting secret values into the wrap-up report.** Local env changes are referenced at high level only.
6. **Duplicating recap's criteria walk or doc-update proposals.** Wrap-up assumes recap already ran.
7. **Duplicating recap's criteria walk or doc-update proposals.** Wrap-up assumes recap already ran.
8. **Generating a multi-page wrap-up report.** Should be a fast (30-90 second) verification gate. If it takes longer, it's too verbose.
9. **Failing to track post-mortem action items across sessions.** When a recap or post-mortem lists structural action items ("Add CI check for X", "Document Y in playbook"), those items disappear from view the moment the session ends. During wrap-up, if a recent post-mortem exists (check `docs/operations/` for files matching `*postmortem*` or `*post-mortem*`), verify each of its action items: if an item was supposed to add a script, CI check, or doc section, grep for evidence it was done. Surface unimplemented items as deferred blockers in the wrap-up report. Post-mortems without follow-through are pure waste — the same bugs recur because the structural fix was never implemented.
10. **🚨 Drafting next-session preview from stale plan statuses instead of git log.** Plan files can be stale (status: active but work completed in prior sessions). Recap files can carry forward open items from before today. Before drafting the next-session preview, ALWAYS run `git log --since="YYYY-MM-DD 00:00:00" --oneline --no-merges` to confirm which commits are from TODAY. Only reference open items that today's commits actually touched. If a plan file says `status: active` but git log shows all its tasks were completed before today, the plan is stale — propose flipping it to completed in the wrap-up, don't include it in the preview. The user will correct you immediately if you suggest work that's already done.
11. **🚨 The `patch` tool can corrupt TypeScript template literals.** When old_string or new_string contains `\n` escape sequences (needed for multi-line template literals in TS), the patch tool converts them to literal backslash-n characters in the file, corrupting the code. This happened twice in one session editing `server/routers/health.ts`. **Workaround:** use `terminal` with Python for replacements involving TypeScript template literals or any code containing `\n` escapes. See `references/patch-tool-ts-template-literal-corruption.md`.

## References

- `templates/wrapup-report.md` — output shape for the wrap-up report
