---
name: project-wrapup
description: "Use when wrapping up a working session — verifies the handoff to the next session is clean. Checks for existing recap, stale project memory, uncommitted changes, plan status transitions, deferred doc-update debts, and runs drift checks. Use when user says 'wrap up', 'we're done', 'sign off', 'end session', 'close out'."
version: 2.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [project-management, session-end, handoff, verification, methodology]
    related_skills: [project-warmup, draft-feature-plan, write-session-recap]
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

### 7. Verify local env changes noted in recap

Ask user: "Did you edit the local env file this session? (rotate a credential, add a new env, change a URL)?"

If yes:
- Check if recap has a "Local env changes" section
- If not, propose adding a one-line entry (high-level, never paste secrets)
- If approved, edit the recap

If no: skip.

### 8. Drift check

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

If anything failed, surface as warnings, not blockers. The user owns the call.

## Common Pitfalls

1. **Running wrap-up before substantive work is done.** This skill is the closing gate, not a mid-session check.
2. **Running wrap-up as a substitute for recap.** Recap captures substance; wrap-up verifies handoff. If recap needed, defer to `/recap` and re-run wrap-up after.
3. **Auto-committing, auto-stashing, or auto-discarding.** Disposition is always the user's call.
4. **Auto-promoting draft plans or auto-flipping active plans.** Status changes are decisions, not housekeeping.
5. **Pasting secret values into the wrap-up report.** Local env changes are referenced at high level only.
6. **Duplicating recap's criteria walk or doc-update proposals.** Wrap-up assumes recap already ran.
7. **Blocking the user from closing the session** because of warnings. Surface failures clearly but let the user decide.
8. **Generating a multi-page wrap-up report.** Should be a fast (30-90 second) verification gate. If it takes longer, it's too verbose.

## References

- `templates/wrapup-report.md` — output shape for the wrap-up report
