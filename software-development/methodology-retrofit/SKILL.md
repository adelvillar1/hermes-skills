---
name: methodology-retrofit
description: Patch methodology predating the current skill standard.
---

# Methodology Retrofit

Audit and retrofit methodology onto an existing project that already has methodology files but predates the current skill standard. This is the "predates skill" case — the project has structure but is missing current-standard pieces.

## When to Use

- A project has CLAUDE.md, CLAUDE.local.md, and a docs/ tree but predates the `init-project-structure` / `slim-claude-md` standard
- The user says "initialize this existing project" on a repo that already has methodology files
- A project was scaffolded manually or with an earlier version of the skill
- CLAUDE.md is already slim (≤ 300 lines) but missing the methodology enforcement rule
- TECHNICAL-DOCUMENTATION.md or FUNCTIONAL-SPECIFICATIONS.md exist but are empty scaffolding with `<add-when-implemented>` markers

## When NOT to Use

- Project has no CLAUDE.md at all → use `slim-claude-md` (NEW mode) or `init-project-structure`
- CLAUDE.md is bloated (> 300 lines) → use `slim-claude-md` (EXISTING mode)
- Project is truly greenfield → use `init-project-structure`
- Project has no methodology files → use `slim-claude-md` (NEW mode)

## Detection

Run this before defaulting to NEW or EXISTING:

```bash
[ -f CLAUDE.md ] && echo "CLAUDE.md: $(wc -l < CLAUDE.md) lines"
[ -f CLAUDE.local.md ] && echo "CLAUDE.local.md: exists" || echo "CLAUDE.local.md: MISSING"
[ -f TECHNICAL-DOCUMENTATION.md ] && echo "TECHNICAL-DOCUMENTATION.md: exists" || echo "TECHNICAL-DOCUMENTATION.md: MISSING"
[ -f FUNCTIONAL-SPECIFICATIONS.md ] && echo "FUNCTIONAL-SPECIFICATIONS.md: exists" || echo "FUNCTIONAL-SPECIFICATIONS.md: MISSING"
[ -d docs ] && echo "docs/ contents: $(ls docs/)" || echo "docs/: MISSING"
git check-ignore -v CLAUDE.local.md 2>/dev/null && echo "CLAUDE.local.md: gitignored" || echo "CLAUDE.local.md: NOT ignored"
```

## Gap Audit

Check each piece against the current standard:

| Piece | Current standard | Check |
|-------|------------------|-------|
| CLAUDE.md ≤ 300 lines | Yes/No | `wc -l CLAUDE.md` |
| CLAUDE.local.md gitignored | Yes/No | `git check-ignore -v CLAUDE.local.md` |
| All docs/ pointers resolve | Yes/No | `for f in $(grep -oE 'docs/[a-zA-Z0-9_/.-]+\.md' CLAUDE.md \| sort -u); do [ -e "$f" ] && echo "OK $f" || echo "MISS $f"; done` |
| Methodology enforcement rule | Present in hard rules? | `grep -c "subagent dispatch\|subagent\|2-stage review" CLAUDE.md` |
| TECHNICAL-DOCUMENTATION.md filled | Real content vs `<add-when-implemented>`? | `grep -c "add-when-implemented" TECHNICAL-DOCUMENTATION.md` |
| FUNCTIONAL-SPECIFICATIONS.md filled | Real content vs `<add-when-implemented>`? | `grep -c "add-when-implemented" FUNCTIONAL-SPECIFICATIONS.md` |
| docs/features/ populated | Files present? | `find docs/features -type f \| wc -l` |
| docs/plans/README.md exists | Yes/No | `[ -f docs/plans/README.md ] && echo yes` |
| docs/recaps/ has recaps | Yes/No | `find docs/recaps -name '*.md' -not -name '.gitkeep' \| wc -l` |

**A "predates skill" project** has most of the structural pieces but 2+ gaps from the table above. Don't overwrite what's there — patch only the gaps.

## Workflow

### 1. Run the detection checklist

Execute the detection block above. If the project is missing most pieces, it's NOT a retrofit case — redirect to `slim-claude-md` or `init-project-structure`.

### 2. Run the gap audit

Execute the gap audit table. Present findings to the user as a table with columns: Piece | Current State | Standard | Gap?.

### 3. Propose a slim retrofit

For each gap, propose the fix:

| Gap | Fix |
|-----|-----|
| CLAUDE.md missing methodology enforcement | Patch hard rules: add the `subagent dispatch` → 2-stage review line |
| TECHNICAL-DOCUMENTATION.md is scaffolding | Fill with real codebase content: stack, schema, endpoints, auth, deployment |
| FUNCTIONAL-SPECIFICATIONS.md is scaffolding | Fill with real feature content: flows, screens, edge cases |
| docs/features/ is empty | Create per-feature deep-dive docs |
| Broken docs/ pointers in CLAUDE.md | Patch CLAUDE.md or create missing files |
| CLAUDE.local.md not gitignored | Add to .gitignore |

### 4. Confirm with user

Present the gap table and proposed fixes. Get approval before writing.

### 5. Execute the retrofit

Patch CLAUDE.md for methodology enforcement and pointer fixes. Fill contract docs with real codebase content (read models, routes, schemas to populate them). Create feature docs from actual feature implementations. Add new pointers to CLAUDE.md for created files.

### 6. Verify

```bash
wc -l CLAUDE.md  # should be ≤ 300
git check-ignore -v CLAUDE.local.md
for f in $(grep -oE 'docs/[a-zA-Z0-9_/.-]+\.md' CLAUDE.md | sort -u); do
  [ -e "$f" ] && echo "OK   $f" || echo "MISS $f"
done
grep -c "add-when-implemented" TECHNICAL-DOCUMENTATION.md FUNCTIONAL-SPECIFICATIONS.md  # should be 0
```

## Pitfalls

1. **Do not overwrite existing content.** Only patch gaps. Real content already in the project takes precedence over templates.
2. **Do not ask "overwrite or abort".** The user explicitly asked to initialize — they signaled intent. Skip the guard question.
3. **Do not restructure what's already working.** If docs/ pointers resolve and the tree is populated, leave it alone.
4. **Do not create duplicate feature docs.** If a feature is already described in a topical doc, don't create a redundant features/ file — just add a pointer.
5. **Read the codebase before filling contract docs.** Don't invent schema/API/deployment facts — read models.py, routes, docker-compose.yml, deployment scripts to get real values.

## Things to Avoid

1. Do not invent project facts. Read the codebase to fill contract docs.
2. Do not put real secret values in any tracked file.
3. Do not duplicate content between CLAUDE.md and docs/ files.
4. Do not add stat tables to topical docs — counts go in `docs/STATE-SNAPSHOT.md`.
5. Do not add "Updated YYYY-MM-DD" markers.
6. Do not commit automatically — the user owns the commit.

## Verification Checklist

- [ ] CLAUDE.md ≤ 300 lines
- [ ] CLAUDE.local.md gitignored
- [ ] All docs/ pointers resolve
- [ ] Methodology enforcement rule present in hard rules
- [ ] TECHNICAL-DOCUMENTATION.md has real content (0 `<add-when-implemented>` markers)
- [ ] FUNCTIONAL-SPECIFICATIONS.md has real content (0 `<add-when-implemented>` markers)
- [ ] docs/features/ populated (if features exist in codebase)
- [ ] No secrets leaked in tracked files
