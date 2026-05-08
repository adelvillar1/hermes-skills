# Session State — {{YYYY-MM-DD}}

> Output shape for the heavyweight project-warmup mode.

## Last session

**Date**: {{YYYY-MM-DD of latest recap}}
**Summary**: {{one-line summary from the recap's Summary section}}
**Plan worked on**: `{{plan filename if any}}`

## Active plans

{{For each plan with status: active in docs/plans/ or .hermes/plans/}}

### `{{plan filename}}` — {{Feature name}}

- **Created**: {{YYYY-MM-DD}}
- **Last updated**: {{YYYY-MM-DD}}
- **Acceptance criteria progress**: {{N met}} / {{M total}} ({{P partial}}, {{Q unmet}})
- **Next criterion to address**: {{first unchecked criterion verbatim}}

{{If no active plans: "No active plans."}}

## Project knowledge graph

**Docker container**: {{running or stopped}}
**Corpus**: {{N chunks across M projects}}
**Projects indexed**: {{project list}}

## Deferred blockers / hard-won lessons from recent sessions

{{From the most recent recap(s): any schema drift, failed migrations, corrupted data, manual patches to environments, connection-drop issues, or uncredited environment state. These are NOT optional notes — they are blockers that will silently break work if ignored. Priority over generic follow-ups because they are time-bombs discovered in prior sessions.}}

- {{blocker}} (from recap {{YYYY-MM-DD}})

## Open follow-ups

{{Aggregated from latest 1-3 recaps. De-duplicate.}}

- {{follow-up}} (from recap {{YYYY-MM-DD}})

## Today's state

{{Verbatim from project memory file.}}

## Files already loaded

- Project memory file
- Local env file
- {{recaps, active plans, feature docs}}

---

**What do you want to work on?**
