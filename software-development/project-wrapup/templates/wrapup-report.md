# Session Wrap-Up Report — {{YYYY-MM-DD}}

> Final handoff verification. Output shape for project-wrapup. Presented as a single response at session end.

## Recap status

- ✅ **Recap exists** at `docs/recaps/SESSION-RECAP-{{YYYY-MM-DD}}.md`
- ⏭️ **Recap intentionally skipped** — session was trivial ({{reason}})
- ⚠️ **Recap missing** — recommend running `/recap` before wrapping up

## Project memory "Today's state" check

- ✅ **Current** — bullets accurately reflect recent state
- 🔄 **Updated** — proposed and applied {{N}} bullet changes
- ⏸️ **Stale, deferred** — {{N}} bullets appear outdated but updates were deferred

## Working tree disposition

- ✅ **Clean**
- 📌 **Held over** — {{N}} files uncommitted, visible to next session's `/warmup`
- ✅ **Stashed** — `git stash push -m "wrap-up {{YYYY-MM-DD}}"` (user approved)
- ✅ **Committed** — user committed {{N}} files

## Plan status transitions

{{For each plan that changed status:}}
- `{{filename}}`: `{{old}}` → `{{new}}` ({{reason}})

{{If none:}} No plan status changes this session.

## Deferred doc-update debts

**1-2 deferrals (tracked):**
- {{deferred update}} — first deferred {{YYYY-MM-DD}}

**⚠️ Escalated (3+ consecutive deferrals):**
- {{deferred update}} — deferred in recaps: {{dates}}. **Recommendation**: address now, mark as accepted debt, or downgrade to tracked issue.

## Local env changes

{{Only if user said yes:}}
- ✅ Edits noted in recap
- ⚠️ Edits NOT noted — proposed entry, {{applied|deferred}}

## Drift checks

| Check | Result |
|-------|--------|
| `wc -l PROJECT.md` | {{N}} lines ({{✅ ≤300 | ⚠️ over budget}}) |
| Local env gitignored | {{✅ | ⚠️}} |
| Local env visible in git status? | {{✅ no | ⚠️ FAIL}} |
| `docs/` pointer paths resolve | {{✅ all | ⚠️ N missing}} |
| Secret-leak grep on modified tracked files | {{✅ no leaks | ⚠️ FOUND}} |

## Process cleanup

- ✅ **Registry swept** — {{N}} process(es) killed, {{M}} pruned, {{K}} alive-left (`sweep --kill` summary)
- ⚠️ **Unregistered orphans found** — {{list}}; user disposition: {{killed approved pids | holding}}
- ✅ **Registry empty** — no registered processes remain

## Next session preview

> {{preview}}

**Injected into:** {{✅ project memory | ⏸️ deferred}} / {{✅ recap | ⏸️ deferred}}

---

## Hand-off

Session wrapped up. {{final summary}}. Safe to close.

{{Or with warnings:}} Session wrapped up with warnings: {{list}}. User's call on whether to address now or carry forward.
