# Pickup Runbook — Template + Worked Example

This is the template structure for a pickup runbook. The worked example at the bottom is excerpted from a real session (stock-predictor, day-2, 2026-06-12).

---

## Template

```markdown
# Pickup Runbook — Next Session (YYYY-MM-DD+)

> **Audience:** the next person (or future me) who opens a session and needs to know where to start. {ONE-LINE PROJECT STATE}.
>
> **Read first:** `CLAUDE.md` → `docs/STATE-SNAPSHOT.md` → this file → `docs/recaps/SESSION-RECAP-YYYY-MM-DD-{RUN-N}.md` (today's recap).

---

## Current state (1 line)

**{ONE SENTENCE — where the project is right now.}**

## Where the project is, what works, what doesn't

### ✅ Works (don't break this)
- {Working piece 1} — {proof: "tsc --noEmit exits 0, 154/154 vitest pass"}
- {Working piece 2} — {proof}

### ⚠️ Has known follow-ups (don't try to "fix" these — they're deliberate)
1. **{Follow-up 1}** — {one-line "why this is deliberate"}
2. **{Follow-up 2}**

### ❌ Doesn't exist (this is the work for the next session)
1. **{Missing piece 1}**
2. **{Missing piece 2}**

---

## Recommended next-session flow

### Step 0: cold-start (5 min)
```bash
cd /path/to/repo
git status && git log --oneline -5
wc -l CLAUDE.md docs/STATE-SNAPSHOT.md docs/recaps/SESSION-RECAP-{TODAY}.md
# Verify clean: working tree clean, latest commit = {SHA} (or newer)
# Verify file paths in CLAUDE.md all exist.
```

### Step 1: read in order
1. CLAUDE.md
2. STATE-SNAPSHOT
3. {Today's recap}
4. {The 5 plan files if relevant}

### Step 2: pick ONE follow-up (do NOT try to do all)
{Recommended first task with concrete files to open and what the deliverable looks like.}

### Step 3: cross-LLM review the plan before writing code
Per {user profile memory reference}, the next plan should be reviewed by a different LLM. Use the `multi-model-review` skill.

### Step 4: ship incrementally
Per the project methodology ({skill name}), use `delegate_task` for non-trivial features. Don't dispatch all at once — do {N} first, ship, then {M}.

### Step 5: update the docs as you go
Per CLAUDE.md housekeeping protocol §{N}: {the rules about updating today's state, recaps, STATE-SNAPSHOT, and topical docs}.

---

## Common commands (copy-paste)

```bash
# === Web ===
cd apps/web
./node_modules/.bin/tsc --noEmit
./node_modules/.bin/vitest run
npm run lint:all

# === API ===
cd apps/api
uv venv
uv pip install -e ".[dev]"
uv run pytest tests/ -v
uv run uvicorn src.main:create_app --factory --reload --port 8000

# === Worker ===
cd apps/worker-relationship-ingest
uv venv
uv pip install -e ../api
uv run python -m src.__main__ run-incremental

# === Git ===
git status
git log --oneline -10
git push -u origin {branch}
```

## Pinned conventions (do NOT deviate)
- {Convention 1: default branch, file naming, env var naming}
- {Convention 2: TS↔JSON, Pydantic alias=}
- {Convention 3: intent suffixes, no Manager/Provider/Worker/Helper}
- {Convention 4: no module-level singletons, no globalThis clobber}
- {Convention 5: no secrets in code, *.db gitignored, Schema.parse at build}

## Watch out for
- **{Gotcha 1: e.g. "npm ci + Husky prepare — never pass --ignore-scripts in CI"}**
- **{Gotcha 2: e.g. "globalThis.X = X is the IIFE-clobber pattern — banned"}**
- **{Gotcha 3: e.g. "happy-dom getComputedStyle returns empty for CSS custom properties"}**
- **{Gotcha 4: e.g. "exactOptionalPropertyTypes requires conditional spread"}**
- **{Gotcha 5: e.g. "React act() requires IS_REACT_ACT_ENVIRONMENT + NODE_ENV=test"}**
- **{Gotcha 6: e.g. "worker and API are separate services — no Python imports across"}**

## Open question for the user (NOT to be auto-answered)
> "The {prior plan} is done. The next milestone is {next plan}. Do you want to:
> A. {Option 1: scope the full plan}
> B. {Option 2: scope the most-leverage piece first}
> C. {Option 3: do smaller tech-debt items first}"
> Use the `clarify` tool. Do NOT start coding without an answer.

---

## Files this runbook assumes (verify all exist)
- CLAUDE.md
- docs/STATE-SNAPSHOT.md
- docs/recaps/SESSION-RECAP-YYYY-MM-DD-{RUN}.md
- {plan files}
- {architecture files}
- {config files}

## TL;DR
1. {Read order}
2. {The question to ask}
3. {Pick ONE follow-up, not all}
4. {Cross-LLM review before coding}
5. {Ship incrementally}
```

---

## Worked example (excerpted from stock-predictor, day-2, 2026-06-12)

The actual runbook for that session (`docs/recaps/SESSION-RECAP-2026-06-12-PICKUP-2-NEXT.md`) followed this template. The key sections in the real one were:

1. **Audience + read-first chain** — pointed at the day-2 recap and the prior pickup
2. **Current state (1 line)** — "TS side is at parity for v1 (mock data drives every screen). The 5 active plans are functionally complete. The next milestone is the **Python backend plan**."
3. **What works (don't break this)** — 5 bullets: web, api, worker, lint chain, naming
4. **What has known follow-ups (don't "fix")** — 5 deliberate deferrals listed
5. **What doesn't exist (the work for the next session)** — 7 follow-ups (Python backend, EDGAR, bilateral-bridge, real REST endpoints, anti-slop, rail collapse, node-link diagram)
6. **Recommended next-session flow** — Step 0-4 with concrete commands; recommended first task: "Task B1: Real SQLAlchemy ORM models for the 10 Zod schemas" with the 3+7 batching strategy
7. **Common commands (copy-paste)** — 3 service blocks + git
8. **Pinned conventions** — 10 rules
9. **Watch out for** — 7 gotchas (npm ci + Husky, globalThis, happy-dom, exactOptionalPropertyTypes, noUncheckedIndexedAccess, React act(), worker/api isolation)
10. **Open question (A/B/C)** — full Python plan / EDGAR + worker / smaller TS follow-ups
11. **Files this runbook assumes** — 14 paths
12. **TL;DR** — 5 numbered steps

The full document was 188 lines, well within the 150-250 line target.

---

## Notes for the agent writing a pickup runbook

- **The structure is mandatory, the wording is not.** Don't copy the example verbatim — the example is one project's voice. Match your project's tone.
- **The A/B/C question is the most important section.** It's the next session's first turn. If the question is bad, the next session will flounder.
- **The "don't break this" section is a real time-saver.** The next session's agent will be tempted to "fix" things that look broken. Listing the deliberate deferrals up-front saves 30 minutes of confused exploration.
- **Pin the conventions by quoting them.** "Do NOT deviate" is more useful than "follow the conventions."
