---
name: project-warmup
description: "Use when starting a fresh session on a project that uses structured methodology — loading context from project memory files, recent recaps, active plans, and relevant docs before answering. Use when picking up deferred work or when the user asks 'where did we leave off', 'continue from yesterday', or names a topic-specific deep question."
version: 3.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [project-management, context-loading, session-start, methodology, continuity]
    related_skills: [project-wrapup, draft-feature-plan, write-session-recap]
---

# Project Warmup

Load context for a fresh session by actively reading the right project files BEFORE answering. Closes the navigability gap that slim project memory creates — a slim router file tells you where things are, but passive pointers don't enforce that those files actually get read.

## When to Use

- Starting a non-trivial session on a project with structured methodology
- Picking up work deferred from a previous session
- User says: "where did we leave off", "what's open", "continue from yesterday", "pick up where we left off", "warm up", "what was I working on"
- A topic-specific deep question in a fresh session where the relevant doc hasn't been loaded yet

## Assumptions

This skill assumes the project uses a **slim methodology**:
- A slim project memory file (e.g., `CLAUDE.md`, `PROJECT.md`, `.hermes/project-context.md`) in the project root
- A gitignored local env file with credentials (e.g., `CLAUDE.local.md`, `.env.local`)
- A `docs/` or `.hermes/docs/` tree with topical docs, recaps, and plans
- Plan-as-contract files in `docs/plans/` or `.hermes/plans/`
- Session recaps in `docs/recaps/` or `.hermes/recaps/`

If the project has none of these, this skill is not applicable.

## Three Operating Modes

**Heavyweight mode (session start):**
Read the project memory file, latest 1-3 recaps, all active plans, and contract doc tables of contents. Build a session-state summary. Ask the user what they want to work on. Then read the relevant feature/architecture docs. Hand off ready.

**Lightweight mode (mid-session topic load):**
When the user asks a topic-specific deep question and the relevant doc hasn't been read this session, read it silently first, then answer from loaded context. No summary, no questions — just bridge the gap and respond.

**Plan-review mode (mid-session inventory):**
When the user says "let's review the active and draft plans", "show me all plans", or any plan-inventory request. Extract statuses from frontmatter across all plan files, build a sorted summary table (active first, then draft, then blocked, with counts), read the active plans in full, identify open acceptance criteria and deferred items, and present a clean plan inventory alongside key open questions. Do NOT assume plans live in a single directory — probe `docs/plans/`, `.hermes/plans/`, and any other known directories recursively for `.md` files containing `status:` frontmatter.

## Workflow — Heavyweight Mode

### 1. Confirm methodology is in use

```bash
[ -f CLAUDE.md ] || [ -f PROJECT.md ] || [ -f .hermes/project-context.md ] || echo "WARNING: no project memory file found"
[ -d docs/recaps ] || [ -d .hermes/recaps ] && echo "OK: recaps dir present" || echo "INFO: no recaps yet"
[ -d docs/plans ] || [ -d .hermes/plans ] && echo "OK: plans dir present" || echo "INFO: no plans yet"
```

If no project memory file exists, tell the user this skill requires structured project memory and suggest initializing it.

**Resilience note — working directory:** The shell tool may not have a default working directory set for your project, or may have a wrong default. If `cd <project>` fails, probe with `find ~ -maxdepth 5 -name "CLAUDE.md" 2>/dev/null | head -5` to discover the correct project root, then set it explicitly for subsequent commands.  

If the `find` command returns nothing (directory not found, glob mismatch, or CWD issue), fall back to the `search_files` tool — it does not depend on the terminal's working directory. Search broad, then narrow:

```
search_files(path="<home_dir>", pattern="CLAUDE.md", limit=10)
search_files(path="<home_dir>", pattern="PROJECT.md", limit=10)
```

A `search_files` match returns full paths. Use the result to set `workdir` on subsequent terminal commands. Note case sensitivity — the actual project directory may use `Projects` (capital P) vs `projects`.

**Multi-repo projects (e.g., rewrite/v2 alongside legacy):** When a project has been rewritten or migrated, there may be two directories (e.g., `~/Desktop/project` legacy + `~/Desktop/project-v2` new). If you find multiple directories matching the project name, surface both in the state summary and ask which the user wants to work in. Do not silently pick one — the wrong repo means loading stale or irrelevant context.

**False-positive find results:** Several common tools install `CLAUDE.md` in non-project locations. `/opt/homebrew/CLAUDE.md` belongs to the Homebrew package manager, NOT your project. When `find ~ -maxdepth 5 -name "CLAUDE.md"` returns multiple results, inspect each one — read the first few lines or check for known Homebrew/dotfiles directories. If the CWD contains a project name mention, prefer paths matching that name. If ambiguous, list candidates and ask.

**Missing project memory file:** If the working directory has no `CLAUDE.md`, `PROJECT.md`, or `.hermes/project-context.md`, it may be a fresh scaffold or a project that hasn't been initialized with this methodology yet. Check for `README.md`, `docs/` directory, or `package.json` as secondary signals. Flag the gap clearly: "This directory doesn't have a project memory file — the structured methodology isn't set up here yet. Proceeding without structured project context."

### 1b. Discover all user projects (heavyweight only)

Before reading any single project's files, survey ALL the user's projects to build a complete portfolio map. This prevents the common mistake of giving an incomplete picture (e.g., listing 5 projects when the user has 8), which wastes time re-establishing context.

```bash
# Scan known project directories
echo "--- ~/Desktop/ ---"
ls -1 ~/Desktop/ 2>/dev/null | grep -viE '\.DS_Store|\.localized|Screenshots|desktop\.ini|Icon\r' | head -20
echo "--- ~/Projects/ ---"
ls -1 ~/Projects/ 2>/dev/null | head -20
```

For each directory found, quickly identify whether it's a development project (vs a random folder) by probing for key signals:

```bash
for dir in ~/Desktop/my-project ~/Desktop/another-project; do
  [ -f "$dir/CLAUDE.md" ] || [ -f "$dir/package.json" ] || [ -f "$dir/setup.py" ] || \
  [ -f "$dir/requirements.txt" ] || [ -f "$dir/go.mod" ] || echo "?"
done
```

Build a quick portfolio index in your response:

> Projects detected: {project1} (Desktop), {project2} (Projects), {project3} (Desktop) — {N} total

**Why this matters:** Asking "what other projects do you have?" mid-conversation after you've already made claims about their portfolio signals you didn't do your discovery upfront. A 3-second directory scan avoids this entirely.

**⚠️ PITFALL — don't confuse directory presence with active development.** A project on the Desktop may be dormant, a one-time experiment, or the user's main focus. Surface the list and let the user correct. Do not infer priority from location alone.

**⚠️ PITFALL — the user's CLAUDE.md may not be named CLAUDE.md.** Some projects use alternative naming (e.g., `.claude/` directory configs). When probing for project identity, check multiple signals: `CLAUDE.md`, `.claude/settings.json`, `package.json` name field, `README.md` first line, `pyproject.toml` name field, or `Cargo.toml`.

### 1b. Check project knowledge graph health (cross-project memory)

Before reading any single project's files, check if the local FalkorDB-backed project knowledge graph is running. This powers cross-project recall — "what did we learn about X" returns results from any of the configured projects.

```bash
python3 ~/.hermes/scripts/project-knowledge-index.py doctor 2>/dev/null | head -30
```

If it returns the health check, log the key stats (container status, chunk count, project list) and include them in the state summary under a "Project knowledge graph" section. This lets the user know the cross-project memory is available for queries during the session.

If the doctor command fails (container not running), note it but don't block warmup — container wasn't part of the original methodology, so it's additive.

### 2. Read foundational files

Read in this order:
- **Project memory file** (e.g., `CLAUDE.md`) — the slim router. Pay attention to pointer index, hard rules, today's state.
- **Local env file** (e.g., `CLAUDE.local.md`) — gitignored credentials and URLs.

### 3. Read latest recaps

```bash
# Probe for common recap directory and file naming patterns
for dir in docs/daily-recaps docs/recaps .hermes/recaps docs/session-recaps; do
  [ -d "$dir" ] && ls -t "$dir"/*.md 2>/dev/null | head -3 && break
done
```

Read the most recent 1 in full. Read previous 2 in headlines only (Summary, Plans worked on, Open questions/next steps) for continuity.

If no recaps exist, note "this is the first session" in the state summary.

**Resilience note:** Recap directories vary by project — `docs/daily-recaps/`, `docs/recaps/`, `.hermes/recaps/`, etc. Filenames may be `YYYY-MM-DD.md`, `SESSION-RECAP-YYYY-MM-DD.md`, or `recap-YYYY-MM-DD.md`. Probe broadly with `ls -t <dir>/*.md` rather than relying on a single glob pattern.

### 3b. Verify post-recap work via git log

Recaps are written at a session's natural breakpoint, but work often continues after the recap is filed. Before building the state summary, verify what happened after the latest recap:

```bash
# Get the timestamp of the latest recap file
LATEST_RECAP=$(ls -t docs/recaps/SESSION-RECAP-*.md 2>/dev/null | head -1)
if [ -n "$LATEST_RECAP" ]; then
  RECAP_DATE=$(date -r "$LATEST_RECAP" "+%Y-%m-%d %H:%M")
  echo "Latest recap: $LATEST_RECAP ($RECAP_DATE)"
  echo "--- Post-recap commits ---"
  git log --since="$RECAP_DATE" --oneline -30
fi
```

Cross-reference each commit message against the recap's "Open questions / next steps" and "Doc updates deferred" sections. A commit that says "fix: ..." or "feat: backfill ..." likely closed one or more items. **Do not present recap open items as still-open if git log shows they were addressed.** Also cross-reference against the project memory file's "Today's state" — if commits touch areas listed as "Open gaps", those may no longer be accurate. Mute anything the commits have resolved.

### 4. Find and read active plans

```bash
# Common plan locations and patterns
grep -rl '^status: active' docs/plans/*.md .hermes/plans/*.md 2>/dev/null
```

For each active plan, read it in full. These are the contracts the next chunk of work operates against. The state summary should show each plan's acceptance criteria and their met/partial/unmet status.

**Resilience note:** Plans may live in `docs/plans/`, `.hermes/plans/`, or as `docs/feature-<name>.md` files directly. Search recursively under `docs/` for files containing `^status: active`, not just the two canonical directories.

**Cross-reference against recaps for stale plan statuses.** The recap's "Plans worked on" section may claim specific plans were marked `completed`, but plan files are often not updated to match. After reading step 3's recaps:
1. Collect all plan slugs from the recap's "Plans worked on" table that it says are completed
2. Grep for those same plan files: if any still show `status: active`, note the discrepancy in the state summary as stale data
3. Do NOT silently report these as "active" in the state summary — flag them as stale

**⚠️ PITFALL — recaps themselves can be wrong.** If a session was "drifting and acting erratically" (user's words), the recap may incorrectly claim a plan was completed when work was actually unfinished. Cross-reference against the project memory file's "Today's state" section — it's maintained more carefully and is a second source of truth. If the CLAUDE.md says "scaffold done, orchestrator pending" but the recap says "✅ Completed," trust the CLAUDE.md and flag the recap as stale. The plan file itself (`status: active` + unchecked ACs) is the ultimate authority — if the plan file disagrees with the recap, the plan file wins.

**Check recent recaps for deferred blockers before building:** If the latest recap describes schema drift, a patched-but-untested environment, a failed migration, or manual DB surgery on a target environment, surface these in the state summary before the user chooses what to work on. A schema mismatch between `schema.prisma` and the actual database has caused hours of wasted debugging in prior sessions. Detect it early.

**⚠️ PITFALL — never report plan statuses from in-session cached memory later in the session.**
During warmup (step 4), you read all active plan files. But if the user asks "what's pending" or "what plans are open" several turns later, do NOT list from memory — the files may have been modified mid-session, or the user may consider work done that you don't remember. Before ANY response that enumerates plan statuses, run:
```bash
grep -rl '^status: active' docs/plans/*.md .hermes/plans/*.md 2>/dev/null
```
Then read the frontmatter of any file you're about to reference. This adds 2 seconds and prevents the user from having to re-litigate completed work. Breaking this rule is a high-friction mistake.

### 5. Read contract-doc tables of contents

Read just the headings of the project's contract docs (commonly `docs/technical-documentation.md`, `docs/functional-specifications.md`, or `.hermes/docs/technical-documentation.md`). Don't read the full files. The goal is knowing what sections exist so you can navigate to the right one when the user names a topic.

```bash
grep -riE '^##? ' docs/technical-documentation.md docs/functional-specifications.md 2>/dev/null | head -20
grep -riE '^##? ' .hermes/docs/technical-documentation.md .hermes/docs/functional-specifications.md 2>/dev/null | head -20
```

**Resilience note:** Contract docs may live at project root or in `docs/`. Filenames are often lowercase or kebab-case. Search relative paths first, then root as fallback.

### 6. Build the session-state summary

Use `templates/session-state-summary.md` as the shape. Present this summary to the user:

- **Last session**: date and 1-line summary from the most recent recap
- **Active plans**: list each active plan filename + 1-line summary + criteria progress (note stale-plan discrepancies found in step 4)
- **Deferred blockers**: surfaced from recent recaps (schema drift, environment patches, manual DB surgery — things that will silently break work if ignored)
- **Open follow-ups**: aggregated from "Open questions / next steps" and "Doc updates deferred" across latest 1-3 recaps, minus items git log showed as resolved (step 3b)
- **Local env changes**: any noted in recent recaps (high-level only, never paste secrets)
- **Today's state**: from the project memory file
- **Files already loaded**: project memory, local env, recaps, plans, contract docs TOC

Then ask: **"What do you want to work on?"**

### 7. Scan sibling projects for relevant patterns

Once the user names a task, probe sibling/previous projects in the workspace for existing solutions before writing any new code. This is the single highest-leverage implementation step:

```bash
# Find sibling projects
ls ~/Desktop/ | grep -iE "project|app" | head -10

# Check for relevant patterns in scripts, dependencies, and code
# Example: if the task is PDF-to-image rendering, search for:
grep -r "napi-rs/canvas\|pdf-to-images\|pdftoppm\|renderPdfPagesAsImages" ~/Desktop/<sibling>/*/scripts/ ~/Desktop/<sibling>/*/package.json 2>/dev/null

# Example: if the task is AI vision extraction, search for:
grep -r "callVisionExtraction\|extraction.*vision\|kimi.*vision\|haiku.*vision" ~/Desktop/<sibling>/*/src/ 2>/dev/null
```

**When to apply this:** Every non-trivial implementation task. Not just infrastructure -- patterns (batch validation UX, AI extraction prompts, supplier matching, data migration scripts) may already exist in sibling projects.

**Why it matters:** The user expects existing solutions to be reused. Inventing new approaches wastes time, introduces avoidable errors, and draws the correction "I already solved this pattern on the X project. Why aren't we reusing that?" -- a high-friction signal.

If a pattern is found, load it and adapt it rather than building from scratch. Also consider saving the discovered pattern as a skill or reference file for future reuse.

### 8. Read relevant feature/architecture docs

Once the user names a task or area, identify which `docs/features/<name>.md`, `docs/architecture/<name>.md`, or `.hermes/docs/<name>.md` files match. Read them. If the task crosses multiple areas, read multiple files.

If there's no existing doc for the area, don't fabricate one — just note the gap and proceed.

**When the task involves infrastructure, pipeline jobs, deployment, or service topology, read the relevant section of TECHNICAL-DOCUMENTATION.md in full.** The user expects existing infrastructure to be used — skipping this and reinventing with ad-hoc scripts is a high-friction mistake.

### 8. Hand off

> Context loaded. Last session was {{date}}: {{one-line summary}}. Active plan: {{plan-filename}} at {{N/M criteria met}}. Open follow-ups: {{count and one-liner}}. I've also read {{docs/features/X.md}} for the task you mentioned. Ready to work — what's first?

---

## Optional After-Handoff — Skill Extraction Survey

After delivering the state summary, if the user asks a meta-question like "what skills can be extracted from this project?" or starts drilling into specific domains (scraper pipeline, mobile, insights, etc.), switch to survey mode rather than answering inline.

### Survey methodology

For each domain the user asks about:

1. **Check existing skills** — Use `skills_list()` and filter by category. Look for both exact matches and umbrella skills that might subsume it. **Do not assume a skill doesn't exist because the name is slightly different.** In this project, `dual-emit-llm-generation` existed when I was about to create `dualemit-generation-pattern` — the names differed by a single hyphen and word order.

2. **Read the matching skill(s)** — Call `skill_view(name)` on any candidate. Don't guess what they cover. A skill named `port-visit-matching` might cover far more than just matching (e.g., scraper architecture, branch discipline, resume-from-crash).

3. **Survey the project's implementation** — Use `search_files` and `ls` to see the actual code/scripts/docs. Check the project memory file's pointer index.

4. **Categorize into 3 buckets:**
   - **Already covered** — existing skills + reference docs cover it thoroughly. Say so explicitly.
   - **Partially covered** — existing skill exists but is missing details. Patch it.
   - **Needs creation** — no skill covers the pattern. Propose a class-level name.

5. **Propose action** — Present the assessment to the user with a clear recommendation. State what you found and what you'd create, patch, or skip. Don't ask "should I look" — do the look, then report.

### Pitfalls

- **Always call `skill_view()` before creating.** The skill registry may have near-miss names. `dualemit-generation-pattern` vs `dual-emit-llm-generation` looks different enough to miss in a list but is conceptually identical. A 3-second `skill_view` call prevents duplicates.
- **Existing skills are often broader than their names suggest.** `port-visit-matching` covers scraper architecture, branch discipline, and resume-from-crash — not just port matching. Read the content before declaring a gap.
- **One-shot scripts are NOT skills.** A pattern must be recurring (3+ instances in the codebase or 2+ sessions of similar work) to warrant extraction. The social media pipeline was correctly left as-is because it's a thin, low-frequency pipeline. Don't force extraction where there's no depth.
- **Class-level names, not session artifacts.** Skill names should describe the pattern, not the session: `cross-env-data-comparison` ✓, `port-visit-progress-script` ✗.

- **Thin skills are valid — they're compressed memory offloads.** Not every skill needs to be a deep pattern with reference files. A skill that stores a single curl command (`gif-search`), a one-line check (`pre-push-type-check`), or a port-conflict cleanup pattern (`python-local-dev-server`) is doing important work: keeping facts out of the 2.2K char memory store. These are not "needs work" or "trash" — they're working as designed. Only flag a skill as genuinely stale/duplicate if there's a better skill that fully supersedes it (e.g., `pipeline-script-audit` → `pipeline-script-verification`). The user explicitly corrects overly aggressive quality grading — "you don't have tiered memory yet, so that's why some stuff is moved to low level skills."

- **Consolidation signal: session-level delivery summary.** When a user asks "how much have we delivered across projects in N days?" and you produce a multi-project tally, that's a high-value reference to save. Add a `references/delivery-timeline.md` under the project's primary skill (or `project-warmup`) that captures the date-range tally. Next time they ask, you don't need to re-build from session search — the reference has the numbers. Keep it: project name, commit count, lines changed, key features shipped, and production deploys. Bump when the user asks again or after a significant push.

---

## Workflow — Lightweight Mode

### 1. Identify the topic

Examples:
- "explain how the AI Chat pipeline works" → topic: AI Chat
- "what's the auth flow look like?" → topic: Authentication
- "where do we handle payment failures?" → topic: Billing

### 2. Find the matching doc

Look at the project memory file's pointer index. Find the matching feature or architecture doc. Pick the most specific if multiple might match.

If no matching file exists, don't fabricate — answer from what's in the project memory and tell the user "there's no dedicated doc for this area yet."

### 3. Read it silently

Read the file without announcing it to the user. If large and the question is narrow, use chunked reads.

### 4. Answer from loaded context

Respond to the original question with the doc content informing your answer. Don't make a big deal about having read the file; just answer well. The value is invisible navigation, not visible ceremony.

---

## Common Pitfalls

1. **Running heavyweight warmup mid-session.** If the user is already deep in work, the summary is interrupting. Use lightweight mode mid-session.
2. **Reading every file in docs/.** That defeats the point of slim project memory. Only read files matching the user's stated task or recent recaps' active areas.
3. **Fabricating session state from the memory file alone.** The whole point is reading recaps and plans. If those are missing, say so explicitly.
4. **Pasting secret values from local env files into the summary or anywhere else.**
5. **Asking a long batched question before work starts.** The state summary is one block plus one question ("what do you want to work on?"). Don't pile on six questions.
6. **Claiming to have read files you didn't read.** Trust depends on accuracy here.
7. **Replacing recap or planning with this skill.** This is the *opening* bracket of the loop, not the closing.
8. **Suggesting features or improvements without verifying they do not already exist.** The user has expressed strong frustration about this. Before proposing any suggestion, enhancement, or alternative approach, verify the current state: read the relevant feature docs, latest recaps, active plans, and check the codebase for existing implementations. Suggesting something that already exists is a high-friction mistake. Always verify first, then suggest what is actually missing.

17. **🚨 Stale plan discrepancies between recaps and plan files.** When a recap claims a plan is \"completed\" but the plan file still shows `status: active`, surface this as a discrepancy in the state summary — don't silently report it as active. The recap and plan file disagree, and the user needs to resolve which is canonical. This session: the recap was wrong, plan file was correct. Cross-reference recaps against plan files during step 4 and flag mismatches explicitly.

18. **🚨 Verify actual product features before creating any marketing content, social copy, demo videos, or public-facing material that references what the product does.** Do NOT assume, extrapolate, or invent features based on what a product "should" have. This session: I created social media posts and ASCII video scenes describing product features (water clarity data, specific dollar amounts) that don't exist in the app — the user called this out as hallucination. Before writing any description of what a product does, read the relevant docs/features/*.md, the project memory file's feature summary, or the actual code/schema. Every claim in public-facing material must trace back to a documented feature. Publishing false claims about a commercial product damages trust with paying customers.

   **Signal that triggers this:** If the user says "I suggest you read up on the functional specifications before we engage" or similar, STOP what you're doing and study the docs. Do not argue, do not continue building. They are telling you that you've fabricated features. Read every relevant feature doc, cross-reference every data point, then fix the work before proceeding. This is a hard-rule-level correction, not a suggestion.

   **Real UI reference check:** If the user provides a screenshot or attaches an image of the actual product UI, study it carefully — every card background color, icon, data field, and layout pattern is now canon. Your composition must match what's shown, not what you think makes sense. The user knows what their product looks like; guessing or abstracting is a high-friction mistake.
9. **Leading with verbose explanation instead of action.** The user prefers action-first communication. When context is loaded and you know the state, state the action or result first. Explanation follows only if needed or when asked. A long narrative before getting to the point is a skill signal — course-correct immediately.
10. **Reporting plan statuses from cached memory instead of re-reading files.** This is the single most common source of stale-status errors. Before any response that enumerates plan statuses (even if you read them during warmup), re-read the plan files or grep for active statuses. Breaking this rule is a high-friction mistake the user has flagged repeatedly. See step 4's ⚠️ PITFALL for the exact command.
11. **Writing ad-hoc scripts without checking the existing pipeline job registry first.** Many projects have a pipeline job system with 30+ pre-built jobs. Before writing any new script for data generation, enrichment, prewarming, or batch operations, check the registry AND the script it points to. Writing a new script when a pipeline job already handles the task is a high-friction mistake.

12. **Prefer quick experiments over verbose analysis when evaluating new tools.** When the user proposes a new tool, approach, or alternative, the fastest path to an answer is to run it and measure — not to theorize about why it might or might not work. Download the binary, run the command, check the output. If it fails, the error tells you why in seconds. A paragraph of reasoning before touching the tool is time wasted; the data point is what matters. The user explicitly prefers this: "we needed that data point to know for sure" and "you need to be able to experiment quickly to know what works and what doesn't." A 30-second test that proves something doesn't work is more valuable than a 2-minute explanation of why you think it won't work.

19. **🚨 Subagent delegate_task filesystem isolation.** When delegating file creation tasks to subagents via delegate_task, the subagent writes files in its own isolated workspace, NOT in the actual project directory. The subagent's summary may claim "file written successfully" but the file will not exist in ~/Projects/<project>/. This is not a bug — it is how the sandbox works. After delegation:
    - Verify the file exists in the real project directory: `ls -la apps/api/src/routes/recommendations.js`
    - If missing, write it yourself from the subagent's detailed summary (the summary is typically detailed enough to reconstruct the file)
    - For critical files, skip delegation entirely and write them yourself
    - Pre-delegation pattern: provide the full project path in the context so the subagent can at least CD there, but still verify afterward
13. **Starting new workstreams before closing current ones.** When a task branches, finish the branch or explicitly defer it before starting another. Six open workstreams with zero closed means the user's time is spent context-switching instead of shipping.
14. **Not checking for duplicate files.** Manual file operations (downloads, saves, copy-paste) can create files with " 2.md", " (1).md" suffixes. Before reading a plan or doc, check `ls` for duplicates — the wrong copy may be stale or partial. If duplicates exist, ask which is canonical or use the one with the most recent `updated:` frontmatter.
15. **Always establish cross-environment baselines before reporting progress deltas.** When a scraper run, backfill, or data job is in progress, reporting "X new records found" from staging alone is misleading — those records may already exist in production and you're just catching staging up to parity. Before stating a delta, query BOTH staging and production to establish the true baseline. A "16,744 new itineraries" claim that ignores the production baseline will be corrected by the user — those count as already-existing data, not new findings. This applies to all entity counts: itineraries, port visits, ships, corridors. When in doubt, compare staging vs production first.
16. **Follow the meta-rule: update plan files immediately on completion.** When work for a plan is confirmed complete, update the plan file's `status: active → completed` and bump `updated: YYYY-MM-DD` in the same turn. Do NOT defer this to recap or wrapup. Plan file updates are cheap — a single `patch` call. The cost of deferring is that every subsequent warmup re-surfaces the work as still pending, forcing the user to re-confirm it was done. This applies to draft → cancelled transitions as well.

17. **🚨 ABSOLUTE RULE: ZERO production Railway operations without explicit user approval in the current turn.** This covers: `railway variables set` on production, `railway up/deploy/redeploy` targeting production, pushing to `main`, creating/deleting services in production, or any Railway CLI command with `--environment production`. Staging approval does NOT extend to production. If the user is not present in the current turn to approve, do nothing on production. This is the highest-priority rule — treating a commercial SaaS product with paying customers like a dev sandbox is not acceptable. The CLAUDE.md hard rule about production requiring approval applies to every operation, not just DB writes.

18. **👥 Write for the audience, not the technology.** When creating content visible to the user's customers or end users (social media posts, video scripts, marketing copy, public-facing descriptions), use ZERO technical jargon. No "pipeline", "cache", "synthesis", "tri-stage", "API", "DeepSeek", "backend", "Ollama", or any implementation detail. Describe what the tool does for the user, not how it works internally. The audience for a B2B SaaS product is the end customer — they care about outcomes, not architecture. In this project, travel advisors are the audience; copy should sound like one advisor talking to another, not a developer reading release notes.

20. **Over-engineering verification sweeps.** When the user asks you to verify or audit something, start with a representative sample and surface findings early. Don't run all 47 scripts as background tasks, don't build elaborate harnesses, don't queue everything at once. If the user says "why don't you run just a sample," you're over-engineering. Run 5-10, report, then expand.

---

## How This Fits Into the Cycle

```
warmup → plan → build → recap → wrapup → (next session) warmup → ...
```

| Stage | Skill | Purpose |
|-------|-------|---------|
| warmup | project-warmup | Load context, surface open follow-ups |
| plan | draft-feature-plan | Draft a contract for non-trivial work |
| build | (implementation) | The actual work |
| recap | write-session-recap | Walk criteria, propose doc updates |
| wrapup | project-wrapup | Verify handoff to next session |

Warmup is optional for trivial sessions but high-value for sessions needing continuity.

## References / Support Files

- `templates/session-state-summary.md` — output shape for the state summary (copy and fill)
- `references/stale-data-verification.md` — how to verify dynamic data against live DB instead of trusting snapshot files
- `references/project-infrastructure-checklist.md` — checklist to consult before writing new scripts (check pipeline registry, existing APIs, generators first)
- `references/post-scraper-data-cascade.md` — full dependency map of what happens after a monthly scraper run: port matching → corridors → enrichment → FalkorDB sync → LLM insights (T1-T7) → aggregation → graph projection → narratives → cache → production sync. Critical path, estimated times, key tables written, and common gotchas.
