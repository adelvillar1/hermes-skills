# Session Wrap-Up Report — {{YYYY-MM-DD}}

> Final handoff verification. Output shape used by the session-wrapup skill. Presented to the user as a single response at session end. Not written to disk.

## Recap status

{{One of:}}
- ✅ **Recap exists** at `docs/recaps/SESSION-RECAP-{{YYYY-MM-DD}}.md`
- ⏭️ **Recap intentionally skipped** — session was trivial ({{reason}})
- ⚠️ **Recap missing** — recommend running `/recap` before wrapping up. (Skill defers and exits.)

## CLAUDE.md "Today's state" check

{{One of:}}
- ✅ **Current** — bullets accurately reflect recent state, no updates needed
- 🔄 **Updated** — proposed and applied {{N}} bullet changes (see diff above)
- ⏸️ **Stale, deferred** — {{N}} bullets appear outdated but updates were deferred to a future session. Flagged as known debt.

## Working tree disposition

{{One of:}}
- ✅ **Clean** — nothing held over
- 📌 **Held over** — {{N}} files uncommitted, will be visible to next session's `/warmup`:
  ```
  {{git status --short output}}
  ```
- ✅ **Stashed** — `git stash push -m "wrap-up {{YYYY-MM-DD}}"` (user approved)
- ✅ **Committed** — user committed {{N}} files in commit {{hash}}

## Plan status transitions

{{For each plan that changed status this wrap-up:}}
- `{{plan filename}}`: `{{old status}}` → `{{new status}}` ({{reason}})

{{If no transitions:}}
- No plan status changes this session.

## Deferred doc-update debts (across recent recaps)

{{Aggregated from latest 3-5 recaps' "Doc updates deferred" sections.}}

**1-2 deferrals (tracked, not escalated):**
- {{deferred update}} — first deferred {{YYYY-MM-DD}}, {{N}} sessions ago

**⚠️ Escalated (3+ consecutive deferrals):**
- {{deferred update}} — deferred in recaps: {{YYYY-MM-DD}}, {{YYYY-MM-DD}}, {{YYYY-MM-DD}}. **Recommendation**: address now, mark as accepted technical debt, or downgrade to a tracked issue.

{{If no debts:}}
- ✅ No deferred doc updates outstanding.

## CLAUDE.local.md changes

{{Only include if the user said yes when asked about CLAUDE.local.md edits:}}
- ✅ Edits noted in today's recap: "{{high-level description from the recap}}"
- ⚠️ Edits NOT noted in today's recap — proposed adding entry, {{applied | deferred}}

{{If no edits:}}
- No `CLAUDE.local.md` changes this session.

## Drift checks

| Check | Result |
|-------|--------|
| `wc -l CLAUDE.md` | {{N}} lines ({{✅ ≤300 | ⚠️ over budget}}) |
| `git check-ignore CLAUDE.local.md` | {{✅ gitignored | ⚠️ NOT gitignored}} |
| `git status` shows `CLAUDE.local.md`? | {{✅ no | ⚠️ FAIL}} |
| `docs/` pointer paths in CLAUDE.md resolve | {{✅ all resolve | ⚠️ {{N}} missing}} |
| Secret-leak grep on session's modified tracked files | {{✅ no leaks | ⚠️ FOUND in {{file}}}} |

## Next session preview

{{Single-sentence preview drafted from active plans + held-over work + open follow-ups + escalated debts.}}

> {{preview}}

**Injected into:**
- {{✅ CLAUDE.md "Today's state" | ⏸️ deferred}}
- {{✅ Today's recap "Open questions / next steps" | ⏸️ deferred}}

---

## Hand-off

{{Final summary line, e.g.:}}

> Session wrapped up. Recap exists. Today's state is current. Working tree clean. Plans up to date. Drift checks passed. Next session preview injected. **Safe to close.**

{{Or, if there are warnings:}}

> Session wrapped up with warnings: {{list}}. The user's call on whether to address now or carry forward.
