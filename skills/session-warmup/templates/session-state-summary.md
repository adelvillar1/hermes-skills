# Session State — {{YYYY-MM-DD}}

> Output shape for the heavyweight session-warmup mode. The skill fills this in and presents it to the user as a single response, then asks "What do you want to work on?"

## Last session

**Date**: {{YYYY-MM-DD of latest recap}}
**Summary**: {{one-line summary from the recap's Summary section}}
**Plan worked on**: `{{plan filename if any}}`

## Active plans

{{For each plan with status: active in docs/plans/}}

### `{{plan filename}}` — {{Feature name}}

- **Created**: {{YYYY-MM-DD}}
- **Last updated**: {{YYYY-MM-DD}}
- **Acceptance criteria progress**: {{N met}} / {{M total}} ({{P partial}}, {{Q unmet}})
- **Next criterion to address**: {{first unchecked criterion verbatim}}
- **Linked artifacts to update on completion**: {{from the plan's Linked artifacts section}}

{{If no active plans: "No active plans. Use `/plan-feature` to draft one before non-trivial work."}}

## Open follow-ups (cumulative debt across recent recaps)

{{Aggregated from "Open questions / next steps" and "Doc updates deferred" sections of the latest 1-3 recaps. De-duplicate. Show as a flat list with the recap date each item came from.}}

- {{follow-up}} (from recap {{YYYY-MM-DD}})
- {{follow-up}} (from recap {{YYYY-MM-DD}})

{{If no open follow-ups: "No open follow-ups — clean slate."}}

## CLAUDE.local.md changes (recent)

{{Only if the recent recaps mention CLAUDE.local.md edits. High-level only — never paste secret values.}}

- {{date}}: {{high-level description}}

{{If none: omit the section entirely.}}

## Today's state (from CLAUDE.md)

{{Verbatim from the "Today's state" section of CLAUDE.md.}}

## Files I've already loaded

- `CLAUDE.md`
- `CLAUDE.local.md`
- {{latest recap filename}}
{{- additional recaps if read in headlines mode}}
- {{each active plan filename}}
- {{any docs/features/ or docs/architecture/ files relevant to the task — added after the user names a task}}

---

**What do you want to work on?**
