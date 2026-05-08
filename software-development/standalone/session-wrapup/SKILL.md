---
name: session-wrapup
description: "Use at the very end of a working session. Verifies a recap exists, checks CLAUDE.md freshness, surfaces uncommitted changes, checks plan statuses, escalates deferred doc-update debts, runs drift checks, and drafts a next-session preview. Companion to session-warmup — wrapup is the writing-side, warmup is the reading-side. Trigger on 'wrap up', 'we're done', 'sign off', 'close out', or any session-end phrasing."
version: 2.1.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [project-management, session-handoff, claude-md, verification]
    related_skills: [session-warmup, write-session-recap, draft-feature-plan, project-knowledge-graph]
---

# Session Wrapup

Final handoff verification at the end of a working session — ensures the next session has everything it needs to pick up cleanly.

## When to Use

- User says "wrap up", "wrap up the session", "we're done", "shut it down", "sign off", "end session", "close out" — any session-end phrasing
- After /recap has been run (if recap was needed)
- Even for trivial sessions that did not need a recap — the drift check and uncommitted-work disposition still matter

## What This Skill Does

**Does:**
- Verifies a recap exists for today (or that the session was trivial enough to skip one)
- Checks CLAUDE.md "Today's state" bullets for staleness and proposes updates
- Surfaces uncommitted changes and asks for explicit disposition
- Checks for draft plans that should be promoted to active before the next session
- Checks for active plans that should be flipped to completed or abandoned
- Aggregates Doc updates deferred across the latest 3-5 recaps and escalates repeat offenders (same deferral 3+ sessions in a row)
- Verifies CLAUDE.local.md edits this session are noted in the recap
- Runs the drift check: wc -l CLAUDE.md ≤ 300, git status clean of CLAUDE.local.md, all pointer paths resolve, no secret leaks in newly tracked files
- Drafts a one-sentence next-session preview and proposes injecting it into CLAUDE.md or the recap

**Does NOT:**
- Walk acceptance criteria — that is write-session-recap's job
- Propose contract-doc updates — that is write-session-recap's job
- Write a new recap file — if a recap is missing, defers to /recap
- Auto-commit, auto-stash, or auto-discard — never
- Auto-promote draft plans or auto-flip active plans without user confirmation

## Workflow

### 1. Pre-flight

```bash
[ -f CLAUDE.md ] || { echo "no CLAUDE.md — this skill requires the slim-claude-md methodology"; exit; }
[ -d docs/recaps ] && echo "OK: recaps dir present" || echo "WARN: no recaps dir"
[ -d docs/plans ] && echo "OK: plans dir present" || echo "INFO: no plans dir"
git status --short
```

If CLAUDE.md is missing, this skill cannot run — tell the user and exit.

### 2. Verify a recap exists for today

```bash
TODAY=$(date +%Y-%m-%d)
RECAP="docs/recaps/SESSION-RECAP-${TODAY}.md"
[ -f "$RECAP" ] && echo "OK: today's recap exists at $RECAP" || echo "MISSING: no recap for today"
```

If missing, ask the user:
- "Was this a trivial session where a recap is not warranted? (typo, dependency bump, one-line fix)"
- "Or do you want to run /recap first before wrapping up?"

If trivial, proceed and note "session was intentionally recap-free." If they want a recap, defer to /recap and tell the user to re-run /wrapup after.

If the recap exists, read it in full.

### 3. Project new knowledge to the knowledge graph

If `~/.hermes/scripts/project-knowledge-index.py` exists and the FalkorDB container is running:

```bash
# Re-index to pick up new recap, plan updates, doc changes
python3 ~/.hermes/scripts/project-knowledge-index.py index

# Query for cross-project connections relevant to this session
python3 ~/.hermes/scripts/project-knowledge-index.py query "<key terms from session>" --limit 3
```

This serves two purposes:
1. **Auto-projection** — any new or changed artifacts (recap, updated plan, modified CLAUDE.md, new skill) get indexed into the knowledge graph automatically. Zero manual steps.
2. **Cross-project discovery** — the query surfaces connections from OTHER projects that match this session's work. Include these in the wrap-up report as "Did you know?" findings.

If the indexer or container is not available, skip silently. This is a soft feature.

### 4. Check CLAUDE.md "Today's state" for staleness

Read the "Today's state" section of CLAUDE.md. Compare against:
- The latest recap's Summary and Plans worked on
- Recent commits (git log --since="$(date -v-7d +%Y-%m-%d)" --pretty=format:'%h %s' --no-merges)
- Any references to "last pipeline run", entity counts, "open gaps" — are they still accurate?

For each bullet that looks stale, propose an update. Show the user proposed before/after text. Ask for approval.

If approved, edit CLAUDE.md in place. If deferred, note the staleness in the wrap-up report so it is surfaced as a known debt.

If the bullets are current, say so explicitly.

### 5. Surface uncommitted changes

```bash
git status --short
```

If uncommitted changes exist, list them and ask the user one of:
- **Commit now** — they handle the commit, you confirm after
- **Hold over** — note "uncommitted: <files>" in the wrap-up report
- **Stash** — git stash push -m "wrap-up YYYY-MM-DD" (with explicit user approval)
- **Discard** — only with explicit user confirmation in the current turn (destructive)

Do not auto-decide. The disposition is the user's call.

### 6. Check for plans that need status transitions + resolved open items

```bash
grep -l '^status: draft' docs/plans/*.md 2>/dev/null
grep -l '^status: active' docs/plans/*.md 2>/dev/null
```

**For each draft plan**: ask "Should it be promoted to active before the next session, or stay draft? Active plans get surfaced by /warmup; draft plans do not."

**For each active plan**: read it. Compare acceptance criteria against the latest recap. If all criteria are met but the plan is still active, propose flipping to completed. If no criteria were touched this session, leave the plan alone.

**Auto-resolve open items from recap**: Read the latest recap's "Open questions / next steps" section. Cross-reference against git log since the recap was written:

```bash
LATEST_RECAP=$(ls -t docs/recaps/SESSION-RECAP-*.md 2>/dev/null | head -1)
if [ -n "$LATEST_RECAP" ]; then
  RECAP_DATE=$(date -r "$LATEST_RECAP" "+%Y-%m-%d %H:%M")
  git log --since="$RECAP_DATE" --oneline -30
fi
```

For each open item: if a post-recap commit resolves it, flag it as resolved in the wrap-up report so it is NOT carried forward to the next session. If the user cancelled it earlier in this session (e.g., during conversation), do not list it either.

Apply approved status transitions by editing the plan file's frontmatter (status: and updated:).

### 7. Aggregate deferred-update debts and escalate repeat offenders

Read the latest 3-5 recaps from docs/recaps/. Extract the "Doc updates deferred (debt)" section from each. Build a counter: how many consecutive recaps does each specific deferral appear in?

For deferrals appearing in 3+ consecutive recaps, **escalate** in the wrap-up report.

For deferrals appearing 1-2 times, list them as known debt without escalation.

If there are no deferrals, say so.

### 8. Verify CLAUDE.local.md changes are noted in the recap

Ask: "Did you edit CLAUDE.local.md this session? (rotate a credential, add a new env, change a URL)"

If yes, check if the recap has a "CLAUDE.local.md changes" section. If not, propose adding a one-line entry (high-level only, never paste secret values).

### 9. Drift check

```bash
wc -l CLAUDE.md
[ $(wc -l < CLAUDE.md) -le 300 ] && echo "OK: ≤300 lines" || echo "WARN: CLAUDE.md is over 300 lines"

git check-ignore -v CLAUDE.local.md 2>/dev/null && echo "OK: gitignored" || echo "WARN: CLAUDE.local.md not gitignored"
git status --short | grep -q CLAUDE.local.md && echo "FAIL: CLAUDE.local.md in git status" || echo "OK: CLAUDE.local.md invisible to git"

# Verify all docs/ pointer paths in CLAUDE.md resolve
for f in $(grep -oE 'docs/[a-zA-Z0-9_/.-]+\.md' CLAUDE.md); do
  [ -e "$f" ] || echo "MISS: $f referenced in CLAUDE.md does not exist"
done
```

Also grep newly tracked files for accidentally-leaked secrets.

Report any failures. If CLAUDE.md is over the line budget, propose moving content out.

### 10. Draft a next-session preview

Based on:
- Active plans with unmet criteria → "pick up <plan> at criterion <X>"
- Held-over uncommitted work → "uncommitted: <files>"
- Open follow-ups from this session's recap → "follow-up: <thing>"
- Escalated debts → "escalated debt: <thing>"

Draft a single-sentence preview. Propose injecting it into:
- **CLAUDE.md "Today's state"** as the last bullet (/warmup picks it up next session)
- **The recap's "Open questions / next steps"** section

Recommendation: both. Edit on approval.

### 11. Generate the wrap-up report

Use templates/wrapup-report.md as the shape. Fill in results from each step. Present as a single response.

### 12. Hand off

Tell the user something like:

> Session wrapped up. Recap exists. "Today's state" is current. Working tree is {{clean | held-over with X files}}. Plans status is {{up to date | flipped Y plans}}. Drift checks passed. Next session preview: "{{preview}}". Safe to close.

If anything failed (missing recap, drift over budget, escalated debt the user did not address), surface those as **warnings** in the hand-off, not blockers.

## Things to Avoid

1. **Do not run wrap-up before substantive work is done.** This is the closing gate, not a mid-session check.
2. **Do not run wrap-up as a substitute for /recap.** They have different scopes. If a recap is needed, defer to /recap and re-run wrap-up after.
3. **Do not auto-commit, auto-stash, or auto-discard.** The disposition is always the user's call.
4. **Do not auto-promote draft plans or auto-flip active plans** without explicit user confirmation.
5. **Do not paste secret values** into the wrap-up report or anywhere else.
6. **Do not duplicate the recap's criteria walk or doc-update proposals.** Wrap-up assumes the recap (if any) has already been run.
7. **Do not block the user from closing the session** because of warnings. Surface failures clearly but let the user decide.
8. **Do not generate a multi-page wrap-up report.** The whole point is a fast (30-90 second) verification gate.
9. **Do not write anything to disk that is not a small targeted edit.** No new files. No long appends.
10. **Do not suggest features or improvements that already exist.** Before recommending anything, verify it is not already implemented by checking the codebase, recaps, and feature docs.
11. **Do not lead with verbose explanation in the wrap-up report.** State the result clearly and concisely. The user prefers action-first communication.
12. **Do not deflect or make excuses when the wrap-up reveals an error.** Own it, acknowledge it, and suggest a fix.

## How This Fits Into the Cycle

```
warmup → plan → build → recap → wrapup → (next session) warmup → ...
```

| Stage | Skill | Purpose |
|-------|-------|---------|
| warmup | session-warmup | Load context for the session, surface open follow-ups |
| plan | draft-feature-plan | Draft a contract for non-trivial work |
| build | (user work) | Implementation |
| recap | write-session-recap | Walk acceptance criteria, propose doc updates, capture substance |
| **wrapup** | **session-wrapup** | **Verify handoff to next session is clean** |

Recap is the substantive end-of-session task. Wrapup is the final gate.

## Verification Checklist

- [ ] Recap exists or trivial-skip confirmed
- [ ] CLAUDE.md "Today's state" checked for staleness
- [ ] Uncommitted changes surfaced with explicit disposition
- [ ] Draft → active and active → completed/abandoned transitions reviewed
- [ ] Deferred doc-update debts aggregated; repeat offenders escalated
- [ ] CLAUDE.local.md edits noted in recap (high-level only)
- [ ] Drift checks passed: ≤300 lines, gitignored, paths resolve, no secret leaks
- [ ] Next-session preview drafted and proposed for injection
- [ ] Plan statuses cross-referenced against recap (step 5); stale active plans flagged
- [ ] Open items from prior recap auto-resolved if commits closed them (step 5)

See also: `references/plan-lifecycle.md` for the full plan staleness prevention cycle.
