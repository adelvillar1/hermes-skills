---
name: write-session-recap
description: "Use at the natural end of a working session after implementation. Drafts a structured session recap at docs/recaps/SESSION-RECAP-YYYY-MM-DD.md. Detects what changed via git, finds active plans, walks acceptance criteria with the user, updates plan statuses, and PROPOSES specific text updates for contract docs (TECHNICAL-DOCUMENTATION.md, FUNCTIONAL-SPECIFICATIONS.md, docs/features/*.md). Trigger on 'write a recap', 'wrap up the session', 'we're done for today'. Never auto-commits."
version: 2.1.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [project-management, session-recap, documentation, claude-md]
    related_skills: [session-warmup, session-wrapup, draft-feature-plan]
---

# Write Session Recap

Drafts a structured session recap and closes the plan/build/recap/document loop. The recap is the post-work journal: what shipped, which acceptance criteria were met, which contract docs need updating, and what's left.

## When to Use

- User says "write a recap", "wrap up the session", "we're done for today"
- User indicates functionality is completed or shipped (the natural close-out point for any non-trivial feature)
- Natural end of a working session after implementation
- After completing non-trivial work that touched an active plan
- Before switching to a new task area — the recap closes the current context cleanly so the next task starts from a known state

## Why "Propose Text" Instead of "Remind"

A reminder ("update docs/features/ai-chat.md") is what most workflow tools do. The user reads the reminder, sighs, copies the relevant info, opens the doc, and writes the update. The friction is enough that the doc update gets deferred — sometimes forever.

**Proposing actual text closes that gap.** The skill drafts the doc-update text in the recap response, the user reviews it, and approves or edits in place. The doc gets updated in the same session as the work. That is the only way the contract-doc discipline survives long-term.

**The trade-off:** proposed text might miss nuance the user has in their head. The mitigation is **always propose, never auto-write.** The user is the editor of last resort.

## Resource Files

| File | When to read |
|------|--------------|
| templates/recap.md.template | Always |
| Project's CLAUDE.md | Always — to know which contract docs exist |
| Project's docs/plans/*.md with status: active | Always — to find the contract being worked on |
| Project's most recent recap | Always — for style reference and "what changed since" cutoff |

**Recap path detection:** This project may use either docs/recaps/SESSION-RECAP-YYYY-MM-DD.md (Hermes convention) or docs/daily-recaps/YYYY-MM-DD.md (other convention). Check both locations with ls -t to find which pattern is in use. Use that path throughout the session. If neither exists yet, default to docs/recaps/SESSION-RECAP-YYYY-MM-DD.md.

| Project's TECHNICAL-DOCUMENTATION.md | When proposing updates to it |
| Project's docs/features/*.md for any touched feature | When proposing updates to operational reference |

---

## Workflow

### 1. Pre-flight checks

```bash
[ -d docs/recaps ] || echo "WARNING: docs/recaps/ does not exist — create it or run init-project-structure"
[ -f CLAUDE.md ] && echo "OK: CLAUDE.md present"
ls docs/plans/*.md 2>/dev/null >/dev/null && echo "OK: plans dir has files" || echo "INFO: no plans found"
ls docs/recaps/*.md 2>/dev/null >/dev/null && echo "OK: recaps dir has files" || echo "INFO: no prior recaps"
```

### 2. Detect what changed in this session

Gather raw inputs:

```bash
# What's currently uncommitted (work-in-progress this session)
git status --short

# What's been committed since the last recap
LAST_RECAP=$(ls -t docs/recaps/SESSION-RECAP-*.md 2>/dev/null | head -1)
if [ -n "$LAST_RECAP" ]; then
  LAST_RECAP_DATE=$(basename "$LAST_RECAP" .md | sed 's/SESSION-RECAP-//')
  git log --since="$LAST_RECAP_DATE 00:00:00" --pretty=format:'%h %s' --no-merges
else
  git log --pretty=format:'%h %s' --no-merges -20
fi

# Files changed since last recap (committed + uncommitted)
git diff --stat HEAD
git diff --stat HEAD  # uncommitted on top
```

Read the most recent prior recap to understand the project's recap style and what was already covered.

### 3. Find active plans

```bash
grep -l '^status: active' docs/plans/*.md 2>/dev/null
```

For each active plan:
- Read it in full
- Note the acceptance criteria
- Check whether file changes align with the plan's "Files to be touched" section
- Note the plan's "Linked artifacts" — these are the contract docs that need updating

If there is no active plan but the session clearly worked on a feature, ask the user: "I see substantial feature work but no active plan in docs/plans/. Is this maintenance work, or did you skip the planning step?"

### 4. Detect closed open items from previous recaps

Before proposing new open items, close old ones. Read the most recent prior recap and extract its "Open questions / next steps" section. Cross-reference each open item against this session's commits (from step 2):

```bash
git log --since="$LAST_RECAP_DATE" --pretty=format:'%s' --no-merges
```

For each open item from the prior recap:
- If a commit message clearly addresses it (e.g., commit "fix: correct FalkorDB label casing" → open item "Fix label casing in projection scripts"), mark it **resolved** in the current recap with the commit hash
- If the item was explicitly cancelled by the user (e.g., "cancel the insight resolvers idea"), mark it **cancelled**
- If neither, carry it forward to the current recap's open items

This auto-resolves old open items instead of carrying them forward indefinitely. The current recap should never list open items that were already closed by commits in this session.

### 5. Detect plan status changes from commits

After gathering commits (step 2), cross-reference against active plans:

1. Read the most recent prior recap's "Plans worked on" section
2. Collect any plans the prior recap mentioned as still active
3. Check if commit messages or file changes in this session complete any of those plans
4. If a plan's acceptance criteria appear fully met by the commits, propose flipping it to completed during the criteria walk

This prevents plans from lingering as active after the work is committed, even if the user didn't explicitly call it out.

### 6. Decide recap shape

**Maintenance recap** — no active plan, work is small (bug fixes, dependency bumps, infra tweaks, doc cleanup). Skip the acceptance criteria walk and contract-doc proposal section. Keep it brief.

**Feature recap** — active plan or substantial new work. Full template with criteria walk and contract-doc proposals.

Ask the user which shape if it is ambiguous.

### 7. Walk acceptance criteria with the user (feature recap only)

For each active plan, walk its acceptance criteria one at a time. For each criterion:

- Read the criterion to the user
- State your assessment: completed / partial / not met / deferred
- Briefly justify based on the file changes you observed
- Ask the user to confirm or correct

After walking all criteria, if every box is now checked, update the plan's status from active to completed and the updated field to today.

If criteria are partial or unmet, leave the plan active and note the open criteria in the recap.

### 8. Propose contract-doc updates

This is the load-bearing step. For each touched area, check whether the matching contract docs need updating.

**Process for each affected feature/area:**

a. Identify the feature area from file changes (e.g., changes in app/api/ai-chat/ → AI Chat feature).

b. For each relevant contract doc, propose an update:

**docs/features/<name>.md** — operational reference. Likely needs the most detail. Propose actual markdown text, not "you should add a section about X."

**TECHNICAL-DOCUMENTATION.md** — summary developer-onboarding contract. Likely a short addition (1-3 sentences) to the relevant section.

**FUNCTIONAL-SPECIFICATIONS.md** — user-flow contract. Update if user-visible behavior changed. If purely internal (refactor, performance), say "No update needed — change is not user-visible."

c. Format proposed updates as:

```markdown
### Proposed update: docs/features/ai-chat.md -- "Two-call pipeline"

<actual proposed text in markdown, ready to paste>
```

d. After proposing all updates, ask: "Should I apply these updates to the docs, defer them, or modify them first?"

e. If the user approves, apply each update by editing the relevant file. If they want modifications, make them and re-propose. If they defer, note each deferred update in the recap as a known debt.

**Critical:** never apply doc updates without explicit per-update or batch approval.

### 9. Note any CLAUDE.local.md changes

If CLAUDE.local.md was edited this session, add an explicit recap line (high-level only, never paste secrets):

```markdown
## CLAUDE.local.md changes
- Updated <section>: <what changed at high level>
```

This is the only trace of CLAUDE.local.md changes in version control.

### 10. Draft the recap

Use templates/recap.md.template, fill it in:

- **Filename**: docs/recaps/SESSION-RECAP-$(date +%Y-%m-%d).md
- **Today's date** in the title
- **Summary** (1-2 sentences capturing the session's headline accomplishment)
- **Plan link**: filename(s) of plans worked on, with each criterion's status
- **Commits**: table of hashes + messages from git log since last recap
- **What was added / fixed / changed**: prose, organized by area
- **Files changed**: grouped list
- **Doc updates applied**: list of contract docs updated this session
- **Doc updates deferred**: list of contract docs that need updating but were not, with reason and target for next session
- **CLAUDE.local.md changes**: if applicable
- **Open questions / next steps**: what is still TBD
- **Notes**: free-form observations, gotchas

If a recap file already exists for today, append to it rather than overwriting. Multi-session days are real.

### 11. Update plan statuses

For each plan completed this session, edit its frontmatter:

```yaml
status: completed   # was: active
updated: YYYY-MM-DD
```

For plans still in progress, just bump updated. Do not change status.

### 12. Verify

```bash
# Confirm the recap was written
cat docs/recaps/SESSION-RECAP-$(date +%Y-%m-%d).md | head -20

# Confirm any plan status updates
grep '^status:' docs/plans/*.md

# Confirm doc updates did not break anything obvious
git diff --stat docs/ TECHNICAL-DOCUMENTATION.md FUNCTIONAL-SPECIFICATIONS.md
```

### 13. Hand off

Tell the user:
- "Recap drafted at docs/recaps/SESSION-RECAP-YYYY-MM-DD.md."
- If doc updates were applied: "Updated <list>. Review the diff before committing."
- If doc updates were deferred: "Deferred updates to <list>. They are noted in the recap so they get picked up next session."
- If a plan was completed: "Marked <plan-filename> as completed."
- **Do NOT commit or push.**

### 14. Handle post-recap work (amendments)

Sometimes significant work happens *after* the daily recap was written — a production build fix, a hotfix deploy, or a follow-up session on the same calendar day.

**Rule:** Do NOT overwrite or inline-edit the original recap. Add a `## Post-recap: <title>` section at the bottom. This preserves the original recap as an accurate snapshot of what was known at session-end, while also recording the follow-up work.

Post-recap section format:

```markdown
---

## Post-recap: Production Build Fix (2026-04-30 evening)

The initial `staging → main` merge crashed the build — [brief explanation of what failed].

**Root cause:** [one-liner].

**Fix:** [what was changed].

| Hash | Message |
|------|---------|
| `7016a23` | fix(reports): convert UnpaidRow[] to string[][] for exportToCSV type match |

Pushed to staging (SUCCESS), then merged to main (deployed to production successfully).
```

**When to use:** Significant work that materially affects the session's outcomes (build fix, feature shipped to production, data fix deployed). Not for trivial follow-ups.

Also update `CLAUDE.md` Today's state to note the post-recap work so the next session has continuity.

## Things to Avoid

1. **Do not auto-write contract doc updates without user approval.** Propose, get approval, then apply.
2. **Do not invent acceptance criteria status.** Walk them with the user. The user is the only one who knows whether something genuinely meets the criterion.
3. **Do not overwrite a recap from earlier today.** Append for same-day sessions. Add a `## Post-recap:` section for significant work after the original recap was written.
4. **Do not generate the recap purely from git diff.** Diffs are evidence, not narrative. The recap should capture intent (why something was done).
5. **Do not skip the contract-doc proposals** even if they are inconvenient. That is the entire point of the skill.
6. **Do not commit anything.** The user owns commits.
7. **Do not paste any secret content from CLAUDE.local.md.** Reference changes at a high level only.
8. **Do not mark a plan completed if criteria are partial.** Status changes require unambiguous confirmation.
9. **Do NOT mark a plan completed when the core behavior doesn't work.** A plan with 47 steps where the auto-advance orchestrator isn't wired is not done — the scaffold (schema, UI, API) is just the foundation. Be honest: "Steps 1-3 of Phase 2 are built, but the auto-advance engine that makes the pipeline self-driving doesn't exist yet." This preserves trust. The user will call out premature completion — it's worse to backtrack than to be upfront about partial progress.
9. **Do not propose doc updates for areas the session did not actually touch.** Use the file diff as ground truth.
10. **Do not write a recap longer than the session warrants.** A 30-minute typo session needs a 5-line recap.
11. **Do not lead with verbose explanation in the recap.** State the result concisely. The recap is factual, not narrative.
12. **Do not suggest future improvements in the recap that already exist in a plan or elsewhere.** Before listing next steps or open questions, verify those items are not already planned or implemented.

## Verification Checklist

- [ ] Recap written to docs/recaps/SESSION-RECAP-YYYY-MM-DD.md (or appended if same day)
- [ ] Next steps and open questions captured
- [ ] Plan statuses updated (completed or remaining active with updated field)
- [ ] Open items from prior recap auto-resolved if commits closed them (step 4)
- [ ] Contract doc updates proposed as actual markdown text
- [ ] Approved doc updates applied to the relevant files
- [ ] Deferred doc updates listed in recap with reason and target
- [ ] CLAUDE.local.md changes noted at high level (no secrets)
- [ ] Next steps and open questions captured
- [ ] Plan statuses updated (completed or remaining active with updated field)
- [ ] Open items from prior recap auto-resolved if commits closed them (step 4)
- [ ] Files changed grouped by area
- [ ] User explicitly told NOT to commit yet
