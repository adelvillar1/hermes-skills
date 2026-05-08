# Hermes Skills — by Alejandro Del Villar

A collection of Hermes Agent skills for structured project methodology, cross-project knowledge management, and developer productivity. Every skill here was extracted from real production workflows across multiple SaaS products.

## Skills Index

### 🏆 Project Methodology (recommended)

| Skill | Purpose |
|-------|---------|
| [project-methodology](software-development/project-methodology/SKILL.md) | **Single integrated lifecycle** — warmup → plan → build → recap → wrapup in one skill. Loads context, drafts plans, writes recaps, verifies handoffs. Includes templates and reference files. |

One skill. One cycle. Nothing falls through the cracks.

### Individual Methodology Skills

If you prefer granular control, the cycle is also available as individual skills:

```
warmup → plan → build → recap → wrapup → (next session) warmup → ...
```

| Stage | Skill | Purpose |
|-------|-------|---------|
| Start | [project-warmup](software-development/project-warmup/SKILL.md) | Load project context, surface open follow-ups, check knowledge graph |
| Plan | [draft-feature-plan](software-development/draft-feature-plan/SKILL.md) | Draft a feature plan with acceptance criteria |
| Plan | [writing-plans](software-development/writing-plans/SKILL.md) | Write bite-sized implementation plans |
| Plan | [plan](software-development/plan/SKILL.md) | Plan mode — write markdown plan, no execution |
| Plan | [plan-execution-preparation](software-development/plan-execution-preparation/SKILL.md) | Scope precisely before building |
| Build | *(implementation)* | The actual work |
| Recap | [write-session-recap](software-development/write-session-recap/SKILL.md) | Draft session recap, walk acceptance criteria |
| Wrap | [session-wrapup](software-development/session-wrapup/SKILL.md) | End-of-session verification |
| Wrap | [project-wrapup](software-development/project-wrapup/SKILL.md) | Verify handoff to next session |

### Project Scaffolding

| Skill | Purpose |
|-------|---------|
| [init-project-structure](software-development/init-project-structure/SKILL.md) | Scaffold a new project with full methodology — CLAUDE.md, docs, contracts |
| [slim-claude-md](software-development/slim-claude-md/SKILL.md) | Restructure bloated CLAUDE.md into slim router + topical docs |

### Codebase Onboarding

| Skill | Purpose |
|-------|---------|
| [codebase-survey](software-development/codebase-survey/SKILL.md) | Survey an existing codebase — architecture, complexity, scope |
| [tech-stack-evaluation](software-development/tech-stack-evaluation/SKILL.md) | Evaluate whether the tech stack fits the project's goals |

### Cross-Project Knowledge

| Skill | Category | Purpose |
|-------|----------|---------|
| [project-knowledge-graph](devops/project-knowledge-graph/SKILL.md) | DevOps | FalkorDB-backed semantic index across all projects |

The `project-knowledge-graph` skill integrates with the methodology cycle — when `project-warmup` runs at session start, it checks the knowledge graph health and surfaces cross-project connections. When `session-wrapup` runs at session end, it automatically re-indexes new knowledge.

---

## Installation

Each skill can be installed individually:

```bash
# Install a methodology skill
hermes skills install https://raw.githubusercontent.com/adelvillar1/hermes-skills/main/software-development/project-warmup/SKILL.md --name project-warmup

# Install the knowledge graph
hermes skills install https://raw.githubusercontent.com/adelvillar1/hermes-skills/main/devops/project-knowledge-graph/SKILL.md --name project-knowledge-graph
```

Replace `project-warmup` with any skill name from the index above.

---

## About the author

**Alejandro Del Villar** — B2B SaaS founder and Hermes Agent power user. Building cruiseintelligence.com and other products. These skills were extracted from real production workflows solving actual problems across multiple projects. No theory — everything here has been battle-tested.
