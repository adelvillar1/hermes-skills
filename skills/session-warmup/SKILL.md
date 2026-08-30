---
name: session-warmup
description: Load context for a fresh session by reading CLAUDE.md, the most recent session recaps in docs/recaps/, any active plans in docs/plans/, and the relevant docs/ files for the upcoming task. Use at the start of any non-trivial session, when picking up work that was deferred from a previous session, when the user says "where did we leave off", "what's open", "continue from yesterday", "pick up where we left off", "warm up", "what was I working on", or any continuity phrasing. Also use when a fresh session asks a topic-specific deep question that requires reading a specific docs/features/ or docs/architecture/ file before answering accurately. This skill closes the navigability gap created by slimming CLAUDE.md from monolithic to router-style — it ensures the assistant has actively loaded the right context before answering, rather than guessing from the slim router alone.
---

# session-warmup

Loads context for a fresh Claude session by actively reading the right files BEFORE answering. Closes the navigability gap that the slim CLAUDE.md created — the slim file tells Claude where things are, but a passive pointer index doesn't enforce that those files actually get read at the start of work.

## Why this skill exists

The original monolithic CLAUDE.md (often 2,000+ lines on a mature project) burned a quarter of every session's context window before the user typed anything, but it had one virtue: a fresh session loaded the *entire* project context up front. Zero latency on context access. Zero risk of misnavigating to the wrong file.

The slim CLAUDE.md (≤ 300 lines) trades that for token efficiency. Most sessions only touch one or two areas, so the slim version is a clear win in expected context cost. But the cost is that any topic-specific question now requires Claude to (1) recognize from the slim router which docs/ file is relevant, (2) read it, (3) then answer. For most sessions this is fine. For sessions that need cross-cutting context — exactly the sessions that were frustrating before slimming — there's a real risk Claude misses context the monolithic version would have surfaced automatically.

This skill bridges the gap. Run it at session start (or when picking up deferred work) and Claude actively reads the right files instead of relying on lazy on-demand navigation.

## Two operating modes

**Heavyweight mode (session start, user-invoked via `/skill:session-warmup`)**:
Read CLAUDE.md, the latest 1-3 recaps, all active plans, the contract docs' tables of contents. Build a session-state summary. Ask the user what they want to work on. Based on the answer, read the relevant `docs/features/` or `docs/architecture/` files. Hand off ready.

**Lightweight mode (mid-session topic load, auto-triggered)**:
When the user asks a topic-specific deep question and the relevant docs/ file hasn't been read this session yet, read it silently first, then answer from loaded context. No summary, no questions, just bridge the navigability gap and respond.

The skill description above is broad enough to auto-trigger on continuity phrasings (heavyweight) AND on topic-specific questions in fresh sessions (lightweight). The explicit skill command `/skill:session-warmup` is the entry point for the heavyweight mode.

## Resource files

| File | When to read |
|------|--------------|
| `templates/session-state-summary.md` | Heavyweight mode — used as the output shape for the state summary you present to the user |
| Project's `CLAUDE.md` | Always — to know the docs/ tree and pointer index |
| Project's `docs/recaps/SESSION-RECAP-*.md` | Heavyweight mode — read the latest 1-3 |
| Project's `docs/plans/*.md` with `status: active` | Heavyweight mode — read all in full |
| Project's `TECHNICAL-DOCUMENTATION.md` | Heavyweight mode — table of contents only (don't read the whole file) |
| Project's `FUNCTIONAL-SPECIFICATIONS.md` | Heavyweight mode — table of contents only |
| Project's `docs/features/<name>.md` or `docs/architecture/<name>.md` | Both modes — read the file matching the user's task |

---

## Workflow — heavyweight mode

### 1. Detect which mode

If the user explicitly invoked `/skill:session-warmup`, or said any of: "where did we leave off", "what's open", "warm up", "continue from yesterday", "pick up where we left off", "what was I working on", "catch me up" — go to heavyweight mode.

If the user asked a topic-specific deep question in a fresh session and the relevant doc hasn't been loaded yet — go to lightweight mode.

If neither applies — this skill probably shouldn't have triggered. Defer back to normal behavior.

### 2. Confirm the project uses this methodology

```bash
[ -f CLAUDE.md ] || { echo "no CLAUDE.md — this skill requires the slim-claude-md methodology. Use /skill:init-project-structure to set up first."; exit; }
[ -d docs/recaps ] && echo "OK: recaps dir present" || echo "INFO: no recaps yet (new project)"
[ -d docs/plans ] && echo "OK: plans dir present" || echo "INFO: no plans yet"
```

If `CLAUDE.md` is missing entirely, this skill can't run — tell the user to initialize the methodology first.

### 3. Read the foundational files

Read in this order (these may already be auto-loaded by Kimi, but verify):

- `CLAUDE.md` — the slim router. Pay special attention to the "Where to find things" pointer index, the hard rules, and "Today's state".
- `CLAUDE.local.md` — the gitignored env file (auto-loaded by Kimi; just confirm it's in context).

### 4. Read the latest recaps

```bash
ls -t docs/recaps/SESSION-RECAP-*.md 2>/dev/null | head -3
```

Read the most recent 1 in full. Read the previous 2 in headlines (just the Summary, Plans worked on, and Open questions / next steps sections — skip the prose body) to get a continuity arc, not just a snapshot.

If there are zero recaps, skip this step and note "this is the first session" in the state summary.

### 5. Find and read active plans

```bash
grep -l '^status: active' docs/plans/*.md 2>/dev/null
```

For each active plan, read it in full. These are the contracts the next chunk of work is operating against. The state summary should show each active plan's acceptance criteria and their current met/partial/unmet status (which the user has been updating via `/skill:write-session-recap`).

If there are zero active plans, note "no active plans" in the state summary. The user might be about to draft one with `/skill:draft-feature-plan`.

### 6. Read contract-doc tables of contents

Read just the headings of `TECHNICAL-DOCUMENTATION.md` and `FUNCTIONAL-SPECIFICATIONS.md` (if they exist). Don't read the full files. The goal is knowing what sections exist so you can navigate to the right one when the user names a topic.

```bash
grep -E '^##? ' TECHNICAL-DOCUMENTATION.md 2>/dev/null
grep -E '^##? ' FUNCTIONAL-SPECIFICATIONS.md 2>/dev/null
```

### 7. Build the session-state summary

Use `templates/session-state-summary.md` as the shape. Fill in:

- **Last session**: date and 1-line summary from the most recent recap
- **Active plans**: list each active plan filename + 1-line summary + criteria progress (e.g. "3/5 met, 1 partial, 1 not started")
- **Open follow-ups**: aggregated from "Open questions / next steps" and "Doc updates deferred" across the latest 1-3 recaps. This is the cumulative debt the user has been deferring.
- **CLAUDE.local.md changes**: any noted in recent recaps (high-level only, never paste secret values)
- **Today's state** (from CLAUDE.md): the small dynamic bullets

Present this summary to the user as a single response. Then ask: **"What do you want to work on?"**

### 8. Based on the user's answer, read the relevant feature/architecture docs

Once the user names a task or area, identify which `docs/features/<name>.md` or `docs/architecture/<name>.md` files match, using CLAUDE.md's pointer index. Read them. If the task crosses multiple areas, read multiple files.

If the task touches an area with no existing doc (a new feature), don't fabricate one — just note that there's no existing documentation for this area yet and proceed.

### 9. Hand off

Tell the user something like:

> Context loaded. Last session was {{date}}: {{one-line summary}}. Active plan: {{plan-filename}} at {{N/M criteria met}}. Open follow-ups: {{count and one-liner}}. I've also read {{docs/features/X.md, docs/architecture/Y.md}} for the task you mentioned. Ready to work — what's first?

This is the "ready" signal. The user is now working with a session that has the right context loaded, not one that's guessing from the slim router alone.

---

## Workflow — lightweight mode

### 1. Identify the topic

The user asked something topic-specific. Examples:
- "explain how the AI Chat pipeline works" → topic: AI Chat
- "what's the auth flow look like?" → topic: Authentication
- "where do we handle payment failures?" → topic: Billing

### 2. Find the matching doc

Look at CLAUDE.md's "Where to find things" pointer index. Find the matching `docs/features/<name>.md` or `docs/architecture/<name>.md`. If multiple files might match, pick the most specific.

If no matching file exists, don't fabricate one — just answer from what's in CLAUDE.md and tell the user "there's no dedicated doc for this area yet."

### 3. Read it

Read the file silently (no announcement to the user). If the file is large and the question is narrow, you can use chunked Read with `offset`/`limit` — but most docs/features/ files should be small enough for a single Read.

### 4. Answer the user's question from loaded context

Now respond to the original question with the doc content informing your answer. Don't make a big deal about having read the file; just answer well.

The user shouldn't have to know that this skill ran. The lightweight mode's value is invisible navigation, not visible ceremony.

---

## Things to avoid

- **Do not run heavyweight warmup mid-session.** If the user is already deep in work, the heavyweight summary is interrupting. Lightweight mode is the right call mid-session.
- **Do not read every file in `docs/`.** That defeats the point of the slim CLAUDE.md. Only read files that match the user's stated task or the recent recaps' active areas.
- **Do not fabricate session state from CLAUDE.md alone.** The whole point is reading the recaps and plans. If those are missing, say so explicitly — don't bluff.
- **Do not paste secret values from `CLAUDE.local.md`** into the session state summary or anywhere else.
- **Do not ask the user a long batched question before the work starts.** The state summary is one block of context plus one question ("what do you want to work on?"). Don't pile on six questions before they've even started.
- **Do not claim to have read files you didn't read.** If a docs/features/ file matched but you didn't actually Read it, don't tell the user you did. The trust depends on accuracy here.
- **Do not run this skill at the start of every session reflexively.** Trivial sessions (one-line bug fix, dependency bump) don't need heavyweight warmup. Use the lightweight mode for those — or skip entirely.
- **Do not replace `/skill:write-session-recap` or `/skill:draft-feature-plan` with this skill.** This is the *opening* bracket of the loop, not the closing. The cycle is `warmup → plan → build → recap`. Each step has its own skill.
- **Do not assume the user wants the warmup output committed anywhere.** It's a state summary delivered to the user in conversation. Nothing gets written to disk.

## How this fits into the cycle

The full feature loop is now five-stage, not four:

```
warmup → plan → build → recap → document
```

| Stage | Skill | Purpose |
|-------|-------|---------|
| warmup | session-warmup | Load context for the session, surface open follow-ups |
| plan | draft-feature-plan | Draft a contract for non-trivial work |
| build | (no skill — that's the user) | Implementation |
| recap | write-session-recap | Walk acceptance criteria, propose doc updates, close the loop |
| document | (handled by recap's propose-text feature) | Update contract docs |

Warmup is the new precursor. It's optional for trivial sessions but high-value for sessions that need continuity from prior work or context-heavy areas.
