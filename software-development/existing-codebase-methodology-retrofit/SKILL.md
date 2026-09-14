---
name: existing-codebase-methodology-retrofit
description: Retrofit methodology files to current standards.
---

# Existing Codebase Methodology Retrofit

When a project already has methodology files but predates current skill standards.

## When to Use

Trigger when ALL of these are true:
- `CLAUDE.md` exists with substantial content (≥ 100 lines)
- `docs/` tree exists (architecture/, features/, plans/, recaps/)
- `CLAUDE.local.md` exists and is gitignored
- Contract docs (`TECHNICAL-DOCUMENTATION.md`, `FUNCTIONAL-SPECIFICATIONS.md`) contain empty `<add-when-implemented>` scaffolding OR have no real codebase content
- The user said "initialize this project properly" or similar

## When NOT to Use

- Greenfield project with no existing files → use `init-project-structure` or `slim-claude-md`
- CLAUDE.md is bloated (> 300 lines) but contracts are already current → use `slim-claude-md` EXISTING mode
- No existing methodology files at all → use `init-project-structure`

## What This Skill Produces

- **CLAUDE.md** — patched to current standard (methodology enforcement, updated topology, feature pointers)
- **TECHNICAL-DOCUMENTATION.md** — filled with real codebase content (not empty scaffolding)
- **FUNCTIONAL-SPECIFICATIONS.md** — filled with real feature content (not empty scaffolding)
- **docs/features/** — populated with per-feature deep-dive docs
- **CLAUDE.local.md** — updated with current hosting env refs

## Workflow

### 1. Audit existing methodology

```bash
wc -l CLAUDE.md TECHNICAL-DOCUMENTATION.md FUNCTIONAL-SPECIFICATIONS.md CLAUDE.local.md
grep -c "<add-when-implemented>" TECHNICAL-DOCUMENTATION.md FUNCTIONAL-SPECIFICATIONS.md
# >0 means contracts are empty scaffolding — must fill with real content
```

Read all methodology files. Read codebase: models, schemas, routes, frontend components.

### 2. Identify gaps vs. current standard

| Check | Standard | If missing |
|-------|----------|------------|
| Methodology enforcement in hard rules | `subagent dispatch` + 2-stage review rule | Add to hard rules |
| Topology table accuracy | Current hosting/target | Update |
| Today's state accuracy | Current env, no migration-in-progress | Update |
| Contract doc content | Real features/stack | Fill from codebase |
| Feature docs in docs/features/ | Per-feature deep dives | Create |

### 3. Fill contract docs with real content

**TECHNICAL-DOCUMENTATION.md** — Read and extract:
- Tech stack from `package.json`, `requirements.txt`, `Dockerfile`
- Database schema from models.py / schema.prisma / SQL files
- API endpoints from route files
- Auth from auth modules
- Deployment from docker-compose.yml, deployment/ configs

**FUNCTIONAL-SPECIFICATIONS.md** — Read and extract:
- User flows from frontend pages/components
- Features from README, user guide, route handlers
- Edge cases from error handling in routes
- Role hierarchy from auth modules

### 4. Patch CLAUDE.md

- Add methodology enforcement line to hard rules
- Update topology table if hosting/target changed
- Update today's state bullets
- Add feature doc pointers under "Features"
- Update common commands (deploy command)

**Hosting change cascade** (e.g., DigitalOcean → Railway):
When the user changes hosting target mid-session, patch ALL of these:
- Hard rules (default deploy target line)
- Topology table (production row)
- Today's state (remove migration-in-progress, set active)
- Common commands (replace deploy command)
- CLAUDE.local.md (env refs, remove migration section)

### 5. Create feature docs

For each major feature area, create `docs/features/<name>.md`:
- Purpose, data model, API endpoints, frontend components, edge cases
- Cross-reference from FUNCTIONAL-SPECIFICATIONS.md

### 6. Verify

```bash
wc -l CLAUDE.md  # should be ≤ 300
git check-ignore -v CLAUDE.local.md  # should match
for f in $(grep -oE 'docs/[a-zA-Z0-9_/.-]+\.md' CLAUDE.md | sort -u); do
  [ -e "$f" ] && echo "OK   $f" || echo "MISS $f"
done
grep -c "<add-when-implemented>" TECHNICAL-DOCUMENTATION.md FUNCTIONAL-SPECIFICATIONS.md
# Should be 0 after fill
```

## Things to Avoid

1. **Do not overwrite existing substantive content** — preserve existing docs/ files, only fill what's empty scaffolding
2. **Do not leave `<add-when-implemented>` markers** — if the codebase has real content, fill it in
3. **Do not skip the hosting cascade** — when hosting changes, patch all 5 locations (hard rules, topology, today's state, commands, CLAUDE.local.md)
4. **Do not create duplicate feature pointers** — if a feature is mentioned in both Features and Reference sections, keep only the Features pointer
5. **Do not commit** — leave working tree for user review

## Pitfall — typo in file path

When writing multiple files in a batch, a typo in the path creates a file in a wrong directory (e.g., `the school-dismissal SaaS-saas-maas-migrated` instead of `the school-dismissal SaaS-saas-migrated`). Always verify with `ls` after writing, and clean up the typo directory immediately.

## Verification Checklist

- [ ] CLAUDE.md ≤ 300 lines
- [ ] CLAUDE.local.md gitignored and invisible to git
- [ ] All docs/ pointers resolve (only expected MISS: `docs/recaps/SESSION-RECAP-YYYY-MM-DD.md`)
- [ ] Zero `<add-when-implemented>` markers remain in contract docs
- [ ] TECHNICAL-DOCUMENTATION.md has real stack/schema/API/auth/deployment content
- [ ] FUNCTIONAL-SPECIFICATIONS.md has real features/flows/edge-cases content
- [ ] docs/features/ has per-feature deep dives
- [ ] Methodology enforcement rule in CLAUDE.md hard rules
- [ ] Hosting/target consistent across hard rules, topology, today's state, commands
- [ ] No duplicate docs/ pointers
