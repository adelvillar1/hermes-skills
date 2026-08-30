---
name: write-session-recap
description: Draft a structured session recap at docs/recaps/SESSION-RECAP-YYYY-MM-DD.md after a working session. Detects what changed via git, finds active plans in docs/plans/, walks each plan's acceptance criteria with the user to mark met/unmet/partial, updates plan statuses, and PROPOSES specific text updates for the contract docs (TECHNICAL-DOCUMENTATION.md, FUNCTIONAL-SPECIFICATIONS.md, docs/features/*.md) that need to stay in sync with the changes. Use when the user says "write a recap", "wrap up the session", "we're done for today", or at the natural end of a working session. Closes the plan→build→recap→document loop. Never auto-commits.
---

# write-session-recap

Drafts a structured session recap and closes the plan/build/recap/document loop. The recap is the post-work journal: what shipped, which acceptance criteria were met, which contract docs need updating, and what's left.

This skill is the most behaviorally complex of the four because it does three things in one pass: capture what happened, update plan status, and **propose actual text** for contract-doc updates rather than just listing what should change.

## Why "propose text" instead of "remind"

A reminder ("update `docs/features/ai-chat.md`") is what most workflow tools do. The user reads the reminder, sighs, copies the relevant info from the recap, opens the doc, and writes the update. The friction is enough that the doc update gets deferred — sometimes forever.

Proposing actual text closes that gap. The skill drafts the doc-update text *in the recap response*, the user reviews it, and approves or edits in place. The doc gets updated in the same session as the work that necessitated it. That's the only way the contract-doc discipline survives long-term.

The trade-off: proposed text might miss nuance the user has in their head but didn't write down. The mitigation is **always propose, never auto-write**. The user is the editor of last resort.

## Resource files

| File | When to read |
|------|--------------|
| `templates/recap.md.template` | Always |
| Project's `CLAUDE.md` | Always — to know which contract docs exist and the housekeeping protocol |
| Project's `docs/plans/*.md` with `status: active` | Always — to find the contract being worked on |
| Project's most recent `docs/recaps/*.md` | Always — to see the previous recap, learn the project's recap style, and find the cutoff for "what changed since" |
| Project's `TECHNICAL-DOCUMENTATION.md` | When proposing updates to it |
| Project's `FUNCTIONAL-SPECIFICATIONS.md` | When proposing updates to it |
| Project's `docs/features/*.md` for any touched feature | When proposing updates to operational reference |

---

## Workflow

### 1. Pre-flight checks

```bash
[ -d docs/recaps ] || echo "WARNING: docs/recaps/ does not exist — run /skill:init-project-structure first or just mkdir docs/recaps"
[ -f CLAUDE.md ] && echo "OK: CLAUDE.md present"
ls docs/plans/*.md 2>/dev/null > /dev/null && echo "OK: plans dir has files" || echo "INFO: no plans found"
ls docs/recaps/*.md 2>/dev/null > /dev/null && echo "OK: recaps dir has files" || echo "INFO: no prior recaps"
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
git diff --stat $(git log --pretty=format:'%H' -- "$LAST_RECAP" 2>/dev/null | tail -1)..HEAD 2>/dev/null
git diff --stat HEAD                       # uncommitted on top
```

Read the most recent prior recap to understand the project's recap style and what was already covered.

### 3. Find active plans

```bash
grep -l '^status: active' docs/plans/*.md 2>/dev/null
```

For each active plan:
- Read it in full
- Note the acceptance criteria (the checkboxes)
- Check whether the file changes align with the plan's "Files to be touched" section
- Note the plan's "Linked artifacts" — these are the contract docs that need updating

If there's no active plan but the session clearly worked on a feature, ask the user: "I see substantial feature work but no active plan in `docs/plans/`. Is this maintenance work, or did you skip the planning step? If the latter, we can backfill a plan for the record."

### 4. Decide recap shape

Two shapes:

**Maintenance recap** — when there's no active plan and the work is small (bug fixes, dependency bumps, infra tweaks, doc cleanup). Skip the acceptance criteria walk and the contract-doc proposal section. Keep it brief.

**Feature recap** — when there's an active plan or substantial new work. Full template with criteria walk and contract-doc proposals.

Ask the user which shape if it's ambiguous.

### 5. Walk acceptance criteria with the user (feature recap only)

For each active plan, walk its acceptance criteria one at a time. For each criterion:

- Read the criterion to the user
- State your assessment: ✅ met / ⏸️ partial / ❌ not met / ⏭️ deferred
- Briefly justify based on the file changes you observed
- Ask the user to confirm or correct

After walking all criteria, if every box is now checked, plan to update the plan's `status` from `active` to `completed` and the `updated` field to today.

If criteria are partial or unmet, leave the plan `active` and note the open criteria in the recap so they're picked up next session.

### 6. Propose contract-doc updates

This is the load-bearing step. For each touched area, check whether the matching contract docs need updating.

**Process for each affected feature/area:**

a. Identify the feature area from the file changes (e.g., changes in `app/api/ai-chat/` → AI Chat feature; changes in `prisma/schema.prisma` adding columns → Database schema; changes in `lib/auth/` → Authentication).

b. For each relevant contract doc, propose an update:

   **`docs/features/<name>.md`** — operational reference. Likely needs the most detail. Propose:
   - New sub-sections for genuinely new capabilities
   - Updated sub-sections for behavior changes
   - Removed sub-sections for deleted features
   - Always include actual proposed markdown text in the recap response, not "you should add a section about X"

   **`TECHNICAL-DOCUMENTATION.md`** — summary developer-onboarding contract. Likely a short addition:
   - Update the relevant section by name (e.g. "Section 5: API Reference")
   - Propose 1-3 sentences of actual text
   - If the change is small enough that the section's existing summary still holds, say so explicitly: "No update needed — the existing section 5 summary still accurately describes the API."

   **`FUNCTIONAL-SPECIFICATIONS.md`** — user-flow contract. Update if user-visible behavior changed:
   - Propose specific text for the affected user flow
   - If the change is purely internal (refactor, performance, cleanup), say: "No FUNCTIONAL-SPECIFICATIONS.md update needed — change is not user-visible."

c. Format proposed updates as:
   ```markdown
   ### Proposed update: `docs/features/ai-chat.md` § "Two-call pipeline"

   <actual proposed text in markdown, ready to paste>
   ```

d. After proposing all updates, ask the user: "Should I apply these updates to the docs, defer them, or modify them first?"

e. If the user approves, apply each update by editing the relevant file. If they want modifications, make them and re-propose. If they defer, note each deferred update in the recap as a known debt.

**Critical**: never apply doc updates without explicit per-update or batch approval. Proposing is the skill's value-add; deciding is the user's.

### 7. Note any `CLAUDE.local.md` changes

If `CLAUDE.local.md` was edited this session (you can ask the user — git won't tell you because it's gitignored), add an explicit recap line:

```markdown
## CLAUDE.local.md changes
- Updated <section>: <what changed at high level — never paste secrets>
```

This is the only trace of CLAUDE.local.md changes in version control.

### 8. Draft the recap

Read `templates/recap.md.template`, fill it in:

- **Filename**: `docs/recaps/SESSION-RECAP-$(date +%Y-%m-%d).md`
- **Today's date** in the title
- **Summary** (1-2 sentences capturing the session's headline accomplishment)
- **Plan link**: filename(s) of plans worked on, with each criterion's status
- **Commits**: table of hashes + messages from `git log` since last recap
- **What was added / fixed / changed**: prose, organized by area
- **Files changed**: grouped list
- **Doc updates applied**: list of contract docs updated this session, with one-line summary of each
- **Doc updates deferred**: list of contract docs that need updating but weren't, with the reason and a note for the next session
- **CLAUDE.local.md changes**: if applicable
- **Open questions / next steps**: what's still TBD, what to pick up next session
- **Notes**: any free-form observations, gotchas, things future sessions should know

If a recap file already exists for today, append to it rather than overwriting. Multi-session days are real.

### 8b. Process cleanup sweep (session-process-registry)

At the natural end of the session, sweep the process registry so dev servers, watchers, and tunnels started this session don't keep running after hand-off:

```bash
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py sweep --kill
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py orphans
python3 ~/.hermes/skills/software-development/session-process-registry/scripts/process_registry.py docker-orphans
```

- `sweep --kill` kills exactly what this session registered during work; quote its summary in the recap's Notes section (e.g., "wrapped up: 2 dev servers killed, registry empty").
- `orphans` and `docker-orphans` are report-only: list leftovers in Open questions only if the user should decide about them; never auto-kill unregistered pids or auto-down unregistered stacks. Entries belonging to another actively-working Hermes session stay untouched. Docker volumes are never removed.

### 9. Update plan statuses

For each plan that was completed this session, edit its frontmatter:

```yaml
status: completed   # was: active
updated: YYYY-MM-DD
```

For plans that are still in progress, just bump `updated`. Don't change `status`.

### 10. Verify

```bash
# Confirm the recap was written
cat docs/recaps/SESSION-RECAP-$(date +%Y-%m-%d).md | head -20

# Confirm any plan status updates
grep '^status:' docs/plans/*.md

# Confirm doc updates didn't break anything obvious
git diff --stat docs/ TECHNICAL-DOCUMENTATION.md FUNCTIONAL-SPECIFICATIONS.md
```

### 11. Hand off

Tell the user:
- "Recap drafted at `docs/recaps/SESSION-RECAP-YYYY-MM-DD.md`."
- If doc updates were applied: "Updated <list of contract docs>. Review the diff before committing."
- If doc updates were deferred: "Deferred updates to <list>. They're noted in the recap so they get picked up next session."
- If a plan was completed: "Marked `<plan-filename>` as completed."
- "Don't commit yet — review the recap and any doc updates first."

**Do NOT commit or push.**

---

## Things to avoid

- **Do not auto-write contract doc updates without user approval.** Propose, get approval, then apply. Per-doc or as a batch.
- **Do not invent acceptance criteria status.** Walk them with the user. The user is the only one who knows whether something genuinely meets the criterion vs "looks like it does in the diff".
- **Do not overwrite a recap from earlier today.** Append. Some days have multiple sessions.
- **Do not generate the recap purely from `git diff`.** Diffs are evidence, not narrative. Use them to inform questions, but the recap should capture intent (why something was done) which only the user can provide. Ask, don't guess.
- **Do not skip the contract-doc proposals** even if they're inconvenient. That's the entire point of the skill. If the user objects to the friction, that's a signal the methodology is too heavy for their work — refuse politely and tell them to use a maintenance recap or skip this skill.
- **Do not commit anything** — recap, plan updates, contract doc updates. The user owns commits.
- **Do not paste any secret content from `CLAUDE.local.md`** into the recap. Reference the change at a high level only.
- **Do not mark a plan completed if the user says criteria are partial.** Status changes require unambiguous confirmation.
- **Do not propose doc updates for areas the session didn't actually touch.** Use the file diff as the ground truth for which contract sections to consider — don't speculate.
- **Do not write a recap longer than the session warrants.** A 30-minute typo session needs a 5-line recap, not 200 lines.
