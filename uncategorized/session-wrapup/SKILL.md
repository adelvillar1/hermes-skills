---
name: session-wrapup
description: Final handoff verification at the end of a working session — ensures the next session has everything it needs to pick up cleanly. Verifies a recap exists for today (or confirms the session was trivial enough to skip), checks that CLAUDE.md "Today's state" is current, surfaces uncommitted changes for explicit disposition, checks for draft plans that should be promoted to active before the next session and active plans that should be flipped to completed/abandoned, aggregates deferred doc-update debts across recent recaps and escalates repeat offenders, verifies CLAUDE.local.md changes are noted in the recap, runs the drift checks (CLAUDE.md still ≤300 lines, no secret leaks, all pointer paths resolve), and drafts a one-sentence next-session preview that gets injected into CLAUDE.md or the recap. Use at the very end of a working session, after /recap if recap was needed, or alone for trivial sessions where no recap was warranted. Companion to session-warmup — wrap-up is the writing-side of the handoff, warmup is the reading-side. Use when the user says "wrap up", "wrap up the session", "we're done", "shut it down", "sign off", "end session", "close out", or any session-end phrasing.
---

# session-wrapup

The end-of-session counterpart to `session-warmup`. Where warmup READS everything a fresh session needs, wrap-up VERIFIES that everything the *next* session will need has been written or noted. It's the final gate before the user closes the session.

## What this skill does (and what it intentionally doesn't do)

**Does:**
- Verifies a recap exists for today (or that the session was trivial enough to skip a recap)
- Checks `CLAUDE.md` "Today's state" bullets for staleness and proposes updates
- Surfaces uncommitted changes and asks the user for explicit disposition
- Checks for draft plans that should be promoted to `active` before the next session
- Checks for active plans that the session may have moved to `completed` or `abandoned` without anyone updating the status
- Aggregates `Doc updates deferred` across the latest 3-5 recaps and escalates repeat offenders (same deferral 3+ sessions in a row)
- Sweeps session-registered processes at session end (kills registered dev servers/watchers/tunnels; report-only orphan scan — see `session-process-registry`)
- Syncs the cross-harness skills library (`~/.agents/skills`): commits/pushes session-created portable skills, repairs broken symlinks (via `sync-skills.sh`)
- Verifies CLAUDE.local.md edits this session are mentioned in the recap (high-level only, never paste secrets)
- Runs the drift check: `wc -l CLAUDE.md` ≤ 300, `git status` clean of `CLAUDE.local.md`, all pointer paths in CLAUDE.md resolve, no secret leaks in any newly tracked files
- Drafts a one-sentence "next session preview" and proposes injecting it into CLAUDE.md "Today's state" or the recap (so `/skill:session-warmup` picks it up automatically next session)

**Does NOT:**
- Walk acceptance criteria — that's `write-session-recap`'s job
- Propose contract-doc updates — that's `write-session-recap`'s job
- Write a new recap file — if a recap is missing, the skill defers to `/skill:write-session-recap`
- Auto-commit — never
- Auto-update CLAUDE.local.md — never
- Auto-promote or auto-flip plans — proposes the change, asks for confirmation, then applies

The relationship to `write-session-recap`:
- **Recap** captures *what happened* in this session (substance)
- **Wrap-up** verifies the *handoff* to the next session (gating)
- Recap is heavy and takes 5-15 minutes for a feature session. Wrap-up is light and should take 30-90 seconds.
- For trivial sessions (typo fix, dependency bump), recap can be skipped but wrap-up still has value because uncommitted-work disposition and drift checks still matter.

## Resource files

| File | When to read |
|------|--------------|
| `templates/wrapup-report.md` | Always — fixed-shape handoff report |
| Project's `CLAUDE.md` | Always — for "Today's state" check, drift check, pointer index |
| Project's `docs/recaps/SESSION-RECAP-$(date +%Y-%m-%d).md` | Always — verify it exists; read it if it does |
| Project's `docs/recaps/SESSION-RECAP-*.md` (latest 3-5) | Always — for the deferred-update debt aggregation |
| Project's `docs/plans/*.md` | Always — for status transitions check |

---

## Workflow

### 1. Pre-flight

```bash
[ -f CLAUDE.md ] || { echo "no CLAUDE.md — this skill requires the slim-claude-md methodology"; exit; }
[ -d docs/recaps ] && echo "OK: recaps dir present" || echo "WARN: no recaps dir"
[ -d docs/plans ] && echo "OK: plans dir present" || echo "INFO: no plans dir"
git status --short
```

If `CLAUDE.md` is missing, this skill can't run — tell the user and exit.

### 2. Verify a recap exists for today

```bash
TODAY=$(date +%Y-%m-%d)
RECAP="docs/recaps/SESSION-RECAP-${TODAY}.md"
[ -f "$RECAP" ] && echo "OK: today's recap exists at $RECAP" || echo "MISSING: no recap for today"
```

If the recap is missing, ask the user one of:
- "Was this a trivial session where a recap isn't warranted? (typo, dependency bump, one-line fix)"
- "Or do you want to run `/skill:write-session-recap` first before wrapping up?"

If trivial, proceed and note in the wrap-up report that the session was intentionally recap-free. If they want a recap, defer to `/skill:write-session-recap` and tell the user to re-run `/skill:session-wrapup` after.

If the recap exists, read it in full — the wrap-up will reference its contents in the verification steps.

### 3. Check `CLAUDE.md` "Today's state" for staleness

Read the "Today's state" section of `CLAUDE.md`. Compare against:
- The latest recap's Summary and Plans worked on
- Recent commits (`git log --since="$(date -v-7d +%Y-%m-%d)" --pretty=format:'%h %s' --no-merges`)
- Any references to "last pipeline run", entity counts, "open gaps" — are they still accurate?

For each bullet that looks stale, propose an update. Show the user the proposed before/after text. Ask for approval per bullet or for the whole batch.

If approved, edit `CLAUDE.md` in place. If deferred, note the staleness in the wrap-up report so it's surfaced as a known debt.

If the bullets are current, say so explicitly: "Today's state in CLAUDE.md is current — no updates needed."

### 4. Surface uncommitted changes

```bash
git status --short
```

If uncommitted changes exist, list them and ask the user one of:
- **Commit now** — they handle the commit, the skill confirms after
- **Hold over** — the skill notes "uncommitted: <files>" in the wrap-up report and tells the user the next session's `/skill:session-warmup` will see the dirty tree
- **Stash** — `git stash push -m "wrap-up YYYY-MM-DD"` (with explicit user approval)
- **Discard** — only with explicit user confirmation in the current turn (this is destructive, treat it like any destructive op)

Don't auto-decide. The disposition is the user's call. Just surface and ask.

If the working tree is clean, say so: "Working tree clean — nothing held over."

### 5. Check for plans that need status transitions

```bash
grep -l '^status: draft' docs/plans/*.md 2>/dev/null
grep -l '^status: active' docs/plans/*.md 2>/dev/null
```

**For each draft plan**: ask the user "Plan `<filename>` is in draft. Should it be promoted to `active` before the next session, or stay draft? Active plans get surfaced by `/skill:session-warmup`; draft plans don't."

**For each active plan**: read it. Compare its acceptance criteria against the latest recap's criteria walk. If the recap marked some criteria met that aren't reflected in the plan file (which would be a bug — the recap skill is supposed to update the plan), flag it. If all criteria are met but the plan is still `active`, propose flipping to `completed`. If no criteria were touched this session, leave the plan alone.

Apply approved status transitions by editing the plan file's frontmatter (`status:` and `updated:`).

### 6. Aggregate deferred-update debts and escalate repeat offenders

Read the latest 3-5 recaps from `docs/recaps/`. Extract the "Doc updates deferred (debt)" section from each. Build a counter: how many consecutive recaps does each specific deferral appear in?

For deferrals appearing in 3+ consecutive recaps, **escalate** in the wrap-up report:

```
⚠️ ESCALATION: "<deferred update>" has been deferred 3 sessions in a row (recaps: 2026-04-06, 2026-04-07, 2026-04-08).
   Recommendation: address now, mark as accepted technical debt, or downgrade to a tracked issue.
```

For deferrals appearing 1-2 times, just list them as known debt without escalation.

If there are no deferrals, say so: "No deferred doc updates outstanding."

### 6b. Process cleanup sweep (session-process-registry)

Before drafting the report, sweep the process registry so this session doesn't leave dev servers, watchers, or tunnels running on the local machine:

```bash
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py sweep --kill
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py orphans
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py docker-orphans
```

- `sweep --kill` kills exactly what this session registered during work (each start should have registered via `session-process-registry`) — including registered compose projects/containers. Quote its summary in the wrap-up report.
- `orphans` is report-only: show unregistered leftovers and kill only pids the user explicitly approves. Skip entries belonging to another actively-working Hermes session on this machine.
- `docker-orphans` lists unregistered compose projects + dev containers (report-only); down/stop only with explicit user approval.

### 7. Verify CLAUDE.local.md changes are noted in recap

Ask the user: "Did you edit `CLAUDE.local.md` this session? (rotate a credential, add a new env, change a URL)"

If yes:
- Check if the recap has a "CLAUDE.local.md changes" section that mentions it
- If not, propose adding a one-line entry to the recap (high-level only, never paste secret values)
- If approved, edit the recap to add the line

If no, skip this step.

### 8. Skills library sync (cross-harness)

If the session created or edited reusable SKILL.md knowledge, make sure the canonical library is consistent and every harness sees the same version.

```bash
cd ~/.agents/skills || exit 0
dirty=$(git status --short | head -20)
if [ -n "$dirty" ]; then
    echo "=== skills library: uncommitted changes ==="
    git status --short
    echo "→ commit + push: git add -A && git commit -m 'chore: sync skills from session' && git push"
fi
broken=$(find ~/.hermes/skills ~/.claude/skills -maxdepth 1 -type l ! -exec test -e {} \; -print 2>/dev/null | wc -l | tr -d ' ')
[ "$broken" -gt 0 ] && echo "WARN: $broken broken skill symlinks — run bash ~/.agents/skills/sync-skills.sh"
```

- If the canonical library has uncommitted changes: commit them (`chore: sync skills library — <what changed>`) and push, then verify with `git ls-remote origin refs/heads/main` (SSH; the gh REST token is unreliable for recently-created repos).
- If a session-created skill is Hermes-locked (references delegate_task, cronjob, mnemosyne, kanban, or `hermes <subcommand>` CLI), it belongs in `~/.hermes/skills/` only — never commit it to `~/.agents/skills` (see the `skills-meta-library` skill for the classification scan and full workflow).
- If symlinks are broken or a harness was touched manually, run `bash ~/.agents/skills/sync-skills.sh` — it relinks hermes/claude, merge-imports WorkBuddy, and reports broken links. **Never run `npx skills add ... -a '*'` as a substitute** — its reconcile step deletes agent-dir entries it doesn't manage and would wipe the Hermes-locked skills.
- Report in the wrap-up summary: skills committed/pushed, or "skills library clean".

### 9. Drift check

```bash
echo "=== drift check ==="
wc -l CLAUDE.md
[ $(wc -l < CLAUDE.md) -le 300 ] && echo "OK: ≤300 lines" || echo "WARN: CLAUDE.md is over 300 lines — content has crept in"

git check-ignore -v CLAUDE.local.md 2>/dev/null && echo "OK: CLAUDE.local.md gitignored" || echo "WARN: CLAUDE.local.md not gitignored"
git status --short | grep -q CLAUDE.local.md && echo "FAIL: CLAUDE.local.md showing in git status" || echo "OK: CLAUDE.local.md invisible to git"

# Verify all docs/ pointer paths in CLAUDE.md resolve
for f in $(grep -oE 'docs/[a-zA-Z0-9_/.-]+\.md' CLAUDE.md); do
  [ -e "$f" ] || echo "MISS: $f referenced in CLAUDE.md does not exist"
done
```

Plus a secret-leak grep against any tracked files modified this session:

```bash
git diff --name-only HEAD~1..HEAD 2>/dev/null | xargs -I {} grep -lEn 'postgres:[a-zA-Z]{15}|password\s*[:=]\s*[A-Z]|github_pat_|sk_live_|sk_test_' {} 2>/dev/null
```

Report any failures. If CLAUDE.md is over the line budget, propose moving content out as part of the next session. If a pointer path is missing, propose creating the file or fixing the pointer.

### 10. Draft a next-session preview

Based on:
- Active plans with unmet criteria → "pick up `<plan>` at criterion `<X>`"
- Held-over uncommitted work → "uncommitted: `<files>`"
- Open follow-ups from this session's recap → "follow-up: `<thing>`"
- Escalated debts from step 6 → "escalated debt: `<thing>`"

Draft a single-sentence preview, e.g.:

> Next session: pick up `2026-04-08-cabin-scoring` at criterion 3 (cabin scores in Postgres), follow up on AI Chat hallucination case from today's recap, address deferred `docs/features/billing.md` update (3rd deferral).

Propose injecting this preview into one of:
- **CLAUDE.md "Today's state"** as the last bullet (`/skill:session-warmup` picks it up first thing)
- **The recap's "Open questions / next steps"** section
- **Both**

Recommendation: both. CLAUDE.md gets it for immediate pickup; the recap gets it for the historical record.

Edit on approval.

### 11. Generate the wrap-up report

Use `templates/wrapup-report.md` as the shape. Fill in the results from each step above. Present to the user as a single response.

### 12. Hand off

Tell the user something like:

> Session wrapped up. Recap exists, "Today's state" is current, working tree is {{clean | held-over with X files}}, plans status is {{up to date | flipped Y plans}}, drift checks passed. Next session preview: "{{preview}}". Safe to close.

If anything failed (missing recap, drift over budget, escalated debt the user didn't address), surface those as **warnings** in the hand-off, not blockers. The user owns the call on whether to leave the session in a partial-handoff state.

---

## Things to avoid

- **Do not run wrap-up before the substantive work is done.** This skill is the closing gate, not a mid-session check.
- **Do not run wrap-up as a substitute for `/skill:write-session-recap`.** They have different scopes. If a recap is needed, defer to `/skill:write-session-recap` and re-run `/skill:session-wrapup` after.
- **Do not auto-commit, auto-stash, or auto-discard** uncommitted changes. The disposition is always the user's call.
- **Do not auto-promote draft plans or auto-flip active plans** without explicit user confirmation. Status changes are decisions, not housekeeping.
- **Do not paste secret values** into the wrap-up report or anywhere else. CLAUDE.local.md changes are referenced at high level only.
- **Do not duplicate the recap's criteria walk or doc-update proposals.** That's the recap skill's responsibility. Wrap-up assumes the recap (if any) has already been run.
- **Do not block the user from closing the session** because of warnings. Surface failures clearly but let the user decide whether to address them now or carry them forward.
- **Do not generate a multi-page wrap-up report.** The whole point is a fast (30-90 second) verification gate. If the wrap-up takes longer, the report is too verbose.
- **Do not write anything to disk that isn't a small targeted edit** to CLAUDE.md, the recap, or a plan's status field. No new files. No long appends.

## How this fits into the cycle

The full feature loop is now six-stage:

```
warmup → plan → build → recap → wrapup → (next session) warmup → ...
```

| Stage | Skill | Purpose |
|-------|-------|---------|
| warmup | session-warmup | Load context for the session, surface open follow-ups |
| plan | draft-feature-plan | Draft a contract for non-trivial work |
| build | (no skill — that's the user) | Implementation |
| recap | write-session-recap | Walk acceptance criteria, propose doc updates, capture substance |
| **wrapup** | **session-wrapup** | **Verify handoff to next session is clean** |

Recap is the substantive end-of-session task. Wrap-up is the final gate that ensures recap actually happened (or was skipped intentionally), drift hasn't crept in, plans are in the right state, debts haven't piled up silently, and the next session has a clean preview to start from.

The cycle compresses for trivial work: skip warmup, skip plan, skip recap, but **don't skip wrap-up** if the session touched anything — even a one-line bug fix benefits from a 30-second drift check and uncommitted-work disposition.
