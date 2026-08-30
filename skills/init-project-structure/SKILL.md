---
name: init-project-structure
description: Scaffold a brand-new project with the full structured methodology — slim CLAUDE.md, gitignored CLAUDE.local.md, docs/ tree, docs/plans/ for plan-as-contract files, docs/recaps/ for session recaps, plus top-level TECHNICAL-DOCUMENTATION.md and FUNCTIONAL-SPECIFICATIONS.md as developer/user contracts. Asks 2-env (staging→production) vs 3-env (staging→canary→production) topology. Use when starting a new project from scratch and the user wants the full plan/build/recap/document workflow. For projects that just need slim memory without the contracts layer, use init-project-memory or slim-claude-md instead.
---

# init-project-structure

Scaffolds a new project with the full methodology: project memory, contract docs, plans directory, recaps directory, branch topology, and the housekeeping protocol — all wired together so the plan/build/recap/document cycle works from day one.

This is the heavyweight init skill. For lighter projects (solo work, prototypes, libraries) use `init-project-memory` or `slim-claude-md` directly — they scaffold the same `CLAUDE.md` + `docs/` tree but skip the contract docs.

## What this skill produces

A new project with:

- **`CLAUDE.md`** — slim router (≤ 300 lines) with hard rules, branch topology, pointer index, common commands, today's state, contracts table, housekeeping protocol, session protocol
- **`CLAUDE.local.md`** — gitignored env file with section headers and `<paste-here>` placeholders
- **`.gitignore`** — entry for `CLAUDE.local.md` (creates `.gitignore` if absent, conservatively)
- **`docs/`** tree with subdirectories: `architecture/`, `features/`, `plans/`, `recaps/`, plus optional `pipeline/` and `scripts/` if the project needs them
- **`docs/plans/README.md`** — explains the plan-as-contract convention and how to use the `draft-feature-plan` skill
- **`TECHNICAL-DOCUMENTATION.md`** — top-level developer-onboarding contract with section scaffolding
- **`FUNCTIONAL-SPECIFICATIONS.md`** — top-level user-flow contract with section scaffolding
- **`docs/STATE-SNAPSHOT.md`**, **`docs/BUSINESS-CONTEXT.md`**, **`docs/TROUBLESHOOTING.md`** — empty stubs

## Composes with `slim-claude-md`

This skill **uses** `slim-claude-md`'s templates as its foundation for the `CLAUDE.md` and `CLAUDE.local.md` structure. Don't duplicate that work. Read those templates from `~/.hermes/skills/slim-claude-md/templates/` (or `~/.hermes/skills/slim-claude-md/templates/` when using Claude Code) and substitute placeholders, then layer the contract-doc additions on top.

## Resource files

| File | When to read |
|------|--------------|
| `~/.hermes/skills/slim-claude-md/templates/CLAUDE.md.template` | Always — base for project CLAUDE.md |
| `~/.hermes/skills/slim-claude-md/templates/CLAUDE.local.md.template` | Always — base for project CLAUDE.local.md |
| `~/.hermes/skills/slim-claude-md/templates/housekeeping-protocol.md` | Always — inlined into CLAUDE.md |
| `templates/CLAUDE.md.template.simple` | When user picks 2-env topology — supplements the slim-claude-md base with 2-env hard rules and topology table |
| `templates/CLAUDE.md.template.full` | When user picks 3-env topology — supplements with 3-env rules including the canary validation gate |
| `templates/TECHNICAL-DOCUMENTATION.md.template` | Always |
| `templates/FUNCTIONAL-SPECIFICATIONS.md.template` | Always |
| `templates/docs-plans-README.md.template` | Always — written into `docs/plans/README.md` |

---

## Workflow

### 1. Pre-flight checks

```bash
[ -f CLAUDE.md ] && wc -l CLAUDE.md && echo "WARNING: CLAUDE.md already exists" || echo "OK: no CLAUDE.md"
[ -f TECHNICAL-DOCUMENTATION.md ] && echo "WARNING: TECHNICAL-DOCUMENTATION.md already exists" || echo "OK"
[ -f FUNCTIONAL-SPECIFICATIONS.md ] && echo "WARNING: FUNCTIONAL-SPECIFICATIONS.md already exists" || echo "OK"
[ -d .git ] && echo "OK: git repo" || echo "WARNING: not a git repo yet"
```

If any of those exist, **stop** and ask the user whether to overwrite or abort. Never silently overwrite a file the user might care about.

If `.git` is missing, ask whether to `git init` first or abort. Don't init silently — that's a meaningful state change.

### 2. Gather project facts (one batched question)

Ask the user via a single AskUserQuestion with these fields:

1. **Project name** (for the H1 of CLAUDE.md and the title of TECHNICAL-DOCUMENTATION.md)
2. **One-line description** (for the subtitle and the FUNCTIONAL-SPECIFICATIONS.md intro)
3. **Production URL** (if any — leave blank if pre-launch)
4. **Repo URL** (GitHub/GitLab/etc.)
5. **Topology**: pick one of:
   - `simple` — 2 environments (`develop` local → `staging` Railway → `main` Railway production)
   - `full` — 3 environments (`develop` local → `staging` → `canary` → `main`)
   - `single-branch` — solo project with just `main` (no separate env, deploys are immediate)
6. **Hosting platform** (Railway / Vercel / Fly / AWS / self-hosted / other) — affects what goes in `CLAUDE.local.md` section headers
7. **Stack** (e.g. "Next.js + Postgres + Redis" or "Python FastAPI + Postgres" or "Go + SQLite") — affects which CLAUDE.local.md sections to seed
8. **Does this project have a data pipeline or many scripts?** (yes/no) — determines whether to create `docs/pipeline/` and `docs/scripts/`

If the user wants to skip the question and accept defaults, fall back to: `simple` topology, Railway hosting, generic Postgres stack, no pipeline, no scripts directory.

### 3. Create the directory structure

```bash
mkdir -p docs/architecture docs/features docs/plans docs/recaps
# Conditionally:
mkdir -p docs/pipeline docs/scripts   # only if project has pipeline/scripts
```

### 4. Write `CLAUDE.md` from the right template

- Read `~/.hermes/skills/slim-claude-md/templates/CLAUDE.md.template` as the base.
- Read `templates/CLAUDE.md.template.simple` or `templates/CLAUDE.md.template.full` (or skip both for `single-branch`) for the topology-specific rules and table.
- Substitute placeholders: `{{PROJECT_NAME}}`, `{{ONE_LINE_DESCRIPTION}}`, `{{PRODUCTION_URL}}`, `{{REPO_URL}}`, `{{DEFAULT_BRANCH}}`, branch table rows.
- Inline the housekeeping protocol from `~/.hermes/skills/slim-claude-md/templates/housekeeping-protocol.md`.
- Inline the Contracts section from the slim-claude-md base template (already present).
- Write to project root.
- The output must be ≤ 300 lines. If it overshoots, the topology-specific rules block is too verbose — trim.

### 5. Write `CLAUDE.local.md`

- Read `~/.hermes/skills/slim-claude-md/templates/CLAUDE.local.md.template`.
- Substitute branch/env structure based on topology pick.
- Leave actual secrets as `<paste-here>` — never invent values.
- Write to project root.

### 6. Update `.gitignore`

Add `CLAUDE.local.md` to `.gitignore`. If `.gitignore` doesn't exist, create it with that line plus the standard ignores for the project's stack (`node_modules/`, `.next/`, `__pycache__/`, `target/`, etc.) — but be conservative and tell the user what was added.

### 7. Write `TECHNICAL-DOCUMENTATION.md`

Read `templates/TECHNICAL-DOCUMENTATION.md.template`, substitute project facts, write to project root. The template includes a section scaffold (Tech Stack, Architecture, Database Schema, API Reference, Auth, Scripts, Deployment) so the user can fill in as the project grows. Each section is intentionally short and references the matching `docs/` file rather than duplicating.

### 8. Write `FUNCTIONAL-SPECIFICATIONS.md`

Read `templates/FUNCTIONAL-SPECIFICATIONS.md.template`, substitute project facts, write to project root. Includes section scaffold (Authentication, User Flows, Features, Admin, Edge Cases) with the same short-and-link approach.

### 9. Write `docs/plans/README.md`

Read `templates/docs-plans-README.md.template`, write to `docs/plans/README.md`. This explains the plan-as-contract convention, the ISO date filename format (`YYYY-MM-DD-<slug>.md`), the plan template structure, and how to use the `draft-feature-plan` skill.

### 10. Write empty stubs

Create empty placeholder files so the docs/ tree pointers in CLAUDE.md aren't broken:

- `docs/STATE-SNAPSHOT.md` — with a header explaining the snapshot is empty until the project has data
- `docs/BUSINESS-CONTEXT.md` — with placeholder sections for founder context, target market, revenue model
- `docs/TROUBLESHOOTING.md` — with placeholder header
- `docs/architecture/overview.md` — with placeholder pointing at the project's stack and the rest of CLAUDE.md
- `.gitkeep` files in empty `docs/features/`, `docs/recaps/`, `docs/plans/` (so they survive git operations)

### 11. Verify

```bash
wc -l CLAUDE.md                           # should be ≤ 300
git check-ignore -v CLAUDE.local.md       # should match the .gitignore line
git status --short                        # CLAUDE.local.md must NOT appear
ls TECHNICAL-DOCUMENTATION.md FUNCTIONAL-SPECIFICATIONS.md
ls docs/plans/README.md
# Walk every docs/ pointer in the new CLAUDE.md and confirm:
for f in $(grep -oE 'docs/[a-zA-Z0-9_/.-]+\.md' CLAUDE.md); do
  [ -e "$f" ] && echo "OK   $f" || echo "MISS $f"
done
```

### 12. Hand off

Tell the user:

- "Project structure scaffolded. CLAUDE.local.md is gitignored and has placeholder sections — fill in the actual credentials before any DB or API work."
- "TECHNICAL-DOCUMENTATION.md and FUNCTIONAL-SPECIFICATIONS.md are scaffolded with empty sections. Update them as features ship — the recap workflow will prompt for it."
- "Plans live in `docs/plans/` with ISO date filenames. Use `/skill:draft-feature-plan` to draft one before significant work."
- "Recaps live in `docs/recaps/` with ISO date filenames. Use `/skill:write-session-recap` at the end of each session."
- "Don't commit yet — review the scaffold first."

**Do NOT commit.** The user owns the first commit on a new project.

---

## Things to avoid

- **Do not invent project facts.** If the user doesn't answer a question, use the documented default — don't make something up.
- **Do not write any real secrets** in any tracked file. `CLAUDE.local.md` is the only place, and it must be gitignored before writing.
- **Do not pre-fill `TECHNICAL-DOCUMENTATION.md` or `FUNCTIONAL-SPECIFICATIONS.md` with hypothetical content.** Leave the sections as scaffolding with `<add-when-implemented>` markers. The user fills them as features ship.
- **Do not create `docs/pipeline/` or `docs/scripts/`** unless the user said the project has those things. Empty directories with no purpose are noise.
- **Do not set up any hooks, GitHub Actions, or CI configuration.** Out of scope. This is documentation scaffolding only.
- **Do not commit or push.** Always.
- **Do not assume the project is a Next.js Postgres Railway app.** Read the user's stack answer and adapt section headers accordingly. A Python FastAPI project shouldn't get `prisma migrate` commands in its CLAUDE.md.
