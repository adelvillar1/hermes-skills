---
name: write-pickup-runbook
description: "Use when a session ends and the next session needs a forward-looking handoff document. The pickup runbook is the cold-start guide the next agent reads FIRST after CLAUDE.md and STATE-SNAPSHOT — it states the current state, what works, what doesn't, and the recommended next-session flow. Distinct from write-session-recap (which is a backward-looking journal) — the pickup runbook is forward-looking instructions. Triggers: 'write a pickup runbook', 'next-session handoff', 'cold-start guide', 'forward-looking doc', end of any non-trivial session."
tags: [project-management, session-end, handoff, documentation, methodology]
---

# Write a Pickup Runbook

The forward-looking handoff document for the next session. Distinct from `write-session-recap` (backward-looking journal of what shipped today). The pickup runbook is **what the next agent should do**, the recap is **what just happened**.

## When to Use

- At the end of a **non-trivial session** where the next session needs more than the recap
- When the prior session's "next steps" are non-obvious (not just "fix bug X")
- When the next session should **ASK a clarifying question** before starting (the A/B/C pattern)
- When there are multiple follow-ups and the next session should pick ONE, not all of them

## When NOT to Use

- **Trivial sessions** (typo, one-line fix, dep bump) — skip the recap AND the pickup runbook
- When the next steps are obvious from the recap alone (no A/B/C question, no follow-up triage)
- When the session is part of a longer plan the next session will continue directly (the plan IS the pickup)

## The 8-section structure (in order)

1. **Audience + read-first chain** — who is this for, what should they read in order (CLAUDE.md → STATE-SNAPSHOT → this file → today's recap)
2. **Current state (1 line)** — single sentence summarizing where the project is
3. **What works (don't break this)** — bullets listing the working pieces, with the specific check that proves it (e.g. "tsc --noEmit exits 0, vitest 154/154 pass")
4. **What has known follow-ups (don't "fix" — they're deliberate)** — bullets listing the deliberate deferrals, with a one-line "why" each
5. **What doesn't exist (the work for the next session)** — bullets listing the missing pieces
6. **Recommended next-session flow** — Step 0 (cold-start), Step 1 (read), Step 2 (ask), Step 3 (ship). Include the exact `git status && git log --oneline -5` commands
7. **Common commands (copy-paste)** — the exact terminal commands the next session will run, grouped by service (web, api, worker)
8. **Pinned conventions (do NOT deviate)** — the rules the next session must follow (naming, file structure, env vars, intent suffixes, etc.)
9. **Watch out for** — gotchas specific to the project (npm quirks, env var namespaces, happy-dom limitations, etc.)
10. **Open question for the user (NOT to be auto-answered)** — if the next session's first turn should be a `clarify` call, state the A/B/C question here. End with: "Use the `clarify` tool to ask. Do NOT start coding without an answer."

## Anti-patterns

- **Don't conflate with the recap.** The recap is "what happened today" (past tense, journal voice). The pickup runbook is "what to do next" (future tense, instructions voice). Different audiences, different purposes. If they're the same document, you have a recap, not a pickup runbook.
- **Don't make it longer than the recap.** Target: 10-20K lines / 150-250 lines. If it's longer, you're writing the next session's work, not the handoff.
- **Don't make it shorter than 4-5K.** If it's trivial, the user is doing the work, not the agent — skip it.
- **Don't list "all the things that need doing."** Pick ONE follow-up, with 2-3 alternatives as A/B/C. The next session's first turn is to ASK, not to do all 7.
- **Don't say "in the next session" without saying which concrete file or task to open.** Be specific: "Open `apps/api/src/contract/instrument.py` and add the SQLAlchemy declarative class" beats "next session: backend work."
- **Don't assert existence of symbols you haven't grepped.** "Use `api.reservations.create()`, which exists in api.ts" — when it doesn't — forces the next session into a deviation decision it shouldn't have to make. Only claim existence for what's in the working tree now; cite file:line; name the layer (backend route vs frontend client) when the two disagree. See `references/claim-hygiene-verify-existence-assertions.md`.

## How it gets read

The next session's `project-warmup` reads in this order:
1. `CLAUDE.md` (project memory, hard rules, today's state)
2. `docs/STATE-SNAPSHOT.md` (entity/model counts)
3. **The most recent pickup runbook** (this artifact)
4. The day's recap(s)

So the pickup runbook is the **THIRD** thing read. It bridges "what's true right now" (STATE-SNAPSHOT) and "what to do next" (the actual plan). Keep it terse — by the time the agent reads it, they've already absorbed the project state.

## File naming

The repo convention in stock-predictor and similar projects:

- `docs/recaps/SESSION-RECAP-YYYY-MM-DD-PICKUP.md` — the first pickup runbook of the day
- `docs/recaps/SESSION-RECAP-YYYY-MM-DD-PICKUP-2-NEXT.md` — the Nth pickup runbook of the day (the `2-NEXT` suffix means "the runbook for the next session, written in the 2nd recap cycle")
- `docs/recaps/PICKUP-RUNBOOK-YYYY-MM-DD.md` — simpler alternative

The "RUN-N" suffix is for when there are multiple recaps in the same day (e.g. day-1 recap, day-2 recap, day-2 pickup). Each session produces a recap, and may produce a pickup runbook.

## Relationship to other skills

- `write-session-recap` — the backward-looking journal; this skill's complement
- `project-warmup` — the cold-start reader that consumes pickup runbooks
- `project-wrapup` — the end-of-session verification that may trigger writing a pickup runbook
- `project-methodology` — the umbrella for project lifecycle

## Checklist before committing

- [ ] Does the file have the 8-section structure (or do I have a good reason to skip a section)?
- [ ] Did I include the exact `git status && git log` cold-start commands?
- [ ] Did I include a copy-pasteable commands block for each service (web, api, worker)?
- [ ] Did I end with an A/B/C question if the next session should ask first?
- [ ] Is the document 150-250 lines, not 50 (too thin) or 500 (too long)?
- [ ] Does the file name follow the `SESSION-RECAP-YYYY-MM-DD-PICKUP[-N-NEXT].md` convention?

## Example template

See `references/pickup-runbook-template.md` for the full template with placeholder content and a worked example from a real session.
