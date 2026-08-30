---
name: tool-hooks
description: "Pre/post tool call hooks — event-driven guards that fire before and after specific tool calls. Catches mistakes early (secrets, type errors, broken tests) before they compound."
version: 1.0.0
author: Hermes Agent (adapted from ECC hooks system)
license: MIT
metadata:
  hermes:
    tags: [hooks, guards, quality, automation, safety]
    related_skills: [subagent-driven-development, requesting-code-review, test-driven-development, systematic-debugging]
---

# Tool Hooks

## Overview

Pre/post tool hooks are **behavioral guards** that fire automatically before or after specific tool calls. They catch mistakes at the moment they happen — not in review, not in CI, not when the user finds them.

**Core principle:** Every tool call is an opportunity to introduce a bug. Hooks are cheap insurance that catch the most common ones before they propagate.

## When to Use

**Always active** — this skill should be loaded for any development work. Hooks are lightweight checks that add seconds, not minutes.

**Deactivate when:**
- Pure research/reading sessions (no file edits, no commits)
- Quick one-off queries with no code changes

## Hook Registry

### Pre-Tool Hooks (fire BEFORE the tool call)

#### H1: Pre-Commit Secret Scan
**Trigger:** `terminal` tool with command containing `git commit`
**Action:** Search staged changes for common secret patterns
```
grep -rn 'API_KEY\|SECRET\|PASSWORD\|TOKEN\|PRIVATE_KEY' --include='*.py' --include='*.ts' --include='*.js' --include='*.env' . | grep -v '.env.example' | grep -v 'test' | grep -v '__pycache__'
```
**If found:** Block the commit. List the files and line numbers. Ask user to remove secrets.
**Severity:** BLOCKING — never commit secrets.

#### H2: Pre-Push Review Reminder
**Trigger:** `terminal` tool with command containing `git push`
**Action:** Remind yourself to verify:
- [ ] All modified files were intentionally changed
- [ ] No debug prints / console.logs / TODO comments left behind
- [ ] Tests pass on the changed files
- [ ] Type check passes (if applicable)
**If unchecked items:** Run the checks before pushing.

#### H3: Pre-Destructive Command Guard
**Trigger:** `terminal` tool with command matching `rm -rf`, `DROP TABLE`, `DELETE FROM`, `git reset --hard`, `git push --force`
**Action:** Verify the target is correct. For `rm -rf`, confirm it's not `/`, `~`, or the project root. For SQL deletes, confirm there's a WHERE clause.
**If dangerous:** Warn explicitly with the exact command and target.

### Post-Tool Hooks (fire AFTER the tool call)

#### H4: Post-Edit Type Check
**Trigger:** `patch` or `write_file` tool on a `.ts`, `.tsx`, `.py` (with type hints), or `.swift` file
**Action:** Run the appropriate type checker on the modified file:
- TypeScript: `npx tsc --noEmit --pretty 2>&1 | head -30`
- Python (if mypy configured): `mypy <file> --no-error-summary 2>&1 | head -20`
- Swift: `swift build 2>&1 | tail -20`
**If errors:** Fix them immediately — type errors in modified files are always the current task's responsibility.

#### H5: Post-Edit Test Run
**Trigger:** `patch` or `write_file` tool on a source file that has a corresponding test file
**Action:** Run the relevant tests:
- `pytest tests/<corresponding_test>.py -v --tb=short 2>&1 | tail -20`
- `npx jest <corresponding_test> --no-coverage 2>&1 | tail -20`
**If failures:** Investigate and fix before continuing. The edit likely broke something.

#### H6: Post-Write Syntax Check
**Trigger:** `write_file` tool creating a new file (not editing existing)
**Action:** Verify the file parses:
- `.py`: `python3 -c "import ast; ast.parse(open('<file>').read())"`
- `.json`: `python3 -c "import json; json.load(open('<file>'))"`
- `.yaml`/`.yml`: `python3 -c "import yaml; yaml.safe_load(open('<file>'))"`
- `.ts`/`.tsx`: `npx tsc --noEmit <file> 2>&1 | head -10`
**If parse errors:** Fix immediately — new files should never be created with syntax errors.

#### H7: Post-Commit Verification
**Trigger:** `terminal` tool with command containing `git commit`
**Action:** Verify the commit succeeded and check what was committed:
- `git log --oneline -1` — confirm the commit exists
- `git diff --stat HEAD~1` — verify the right files were included
**If wrong files:** Amend immediately with `git commit --amend`.

## Hook Execution Pattern

When a hook triggers, follow this sequence:

```
1. DETECT — identify which hook(s) apply based on the tool + arguments
2. CHECK — run the hook's verification command
3. DECIDE — based on result:
   - PASS → continue with the original tool call
   - WARN → continue, but report the finding to the user
   - BLOCK → stop, report the issue, do NOT proceed until resolved
4. LOG — note the hook result in your working context
```

## Severity Levels

| Level | Behavior | Examples |
|-------|----------|----------|
| **BLOCKING** | Never proceed. Fix or escalate. | Secret in commit, destructive command on wrong target |
| **WARNING** | Proceed, but report immediately. | Type error in non-critical file, test failure in unrelated suite |
| **INFO** | Proceed silently, note for final review. | TODO comment added, console.log left in |

## Custom Hooks

Users can define project-specific hooks by adding them to their project's `AGENTS.md` or a `.hermes/hooks.md` file:

```markdown
## Custom Hooks

### Post-Edit: Prisma Client Regeneration
**Trigger:** Any edit to `prisma/schema.prisma`
**Action:** `npx prisma generate`
**Severity:** BLOCKING — app won't start with stale client.

### Pre-Commit: Lint Check
**Trigger:** `git commit`
**Action:** `npm run lint -- --fix`
**Severity:** WARNING — auto-fix what's possible, report the rest.
```

## Built-in: `verify_on_stop` — the post-edit verification nudge

Hermes ships with a built-in post-edit hook that fires after `write_file` or `patch` and demands fresh verification evidence (`pnpm run test/lint/build`) before letting the session end. Source: `agent/verification_stop.py:build_verify_on_stop_nudge()`.

**How it decides to fire:**
1. Walks the list of changed paths to find candidate project roots (git root or marker root).
2. Calls `project_facts_for(cwd)` to detect the project's manifest, package manager, and **static** list of `verifyCommands` (e.g., `pnpm run test`, `pnpm run lint`, `pnpm run build`).
3. Looks up the SQLite verification evidence ledger at `~/.hermes/verification_evidence.db` for the current session+root.
4. If no recent `verification_event` exists OR the most recent edit timestamp is newer than the most recent verification, fires the nudge.

**Critical limitation — no path filter:**
The hook does NOT filter changed paths by file type. Editing a markdown file, a skill reference, or a spike HTML triggers the exact same nudge as editing `lib/route-map/pathfinder.ts`. The `verifyCommands` list is a static project-level commands list, not a per-file-type dispatch.

**Available levers (none of them are path-aware):**

| Lever | Effect | Trade-off |
|---|---|---|
| `HERMES_VERIFY_ON_STOP=0` env var | Disables the hook globally | Loses protection on real production code edits |
| `agent.verify_on_stop: false` in `~/.hermes/config.yaml` | Same as env var, persistent | Same trade-off |
| Move spike work to `~/spikes/<project>/` or `/tmp/spike-NNN/` | Hook's `_git_root()` check doesn't match, so it doesn't fire | Workflow change, not a config change |

**Recommended approach:** keep the hook enabled (it catches real bugs on production code) and put spike/throwaway work **outside the project root**. This enforces the spike→production separation at the tooling layer.

**Detection pattern:** the user complains "every time I save a spike file the system tells me to run pnpm test/lint/build." The fix is the spike-location change above, not disabling the hook.

**Anti-pattern:** reflexively disabling the hook globally because it's noisy during spike work, then forgetting to re-enable it for production code.

## Integration with Other Skills

- **subagent-driven-development:** Hooks fire in the controller session. Subagents get their own hooks instructions via context. Include relevant hooks in every delegation context.
- **requesting-code-review:** Hooks catch issues before they reach review. If hooks are active, reviewers can focus on design and logic instead of syntax and secrets.
- **test-driven-development:** H5 (Post-Edit Test Run) reinforces the TDD cycle by running tests after every edit.

## Pitfalls

- **Don't over-hook.** Not every tool call needs a hook. Hooks on `read_file` or `search_files` are pure noise. Hook only on side-effecting tools: `patch`, `write_file`, `terminal` (for commits/pushes).
- **Hook latency matters.** A hook that takes 30 seconds (full test suite) defeats the purpose. Run targeted checks: single file type check, single test file, not the full suite.
- **Hooks are not reviews.** They catch mechanical errors (syntax, secrets, type mismatches). They don't catch design issues, logic bugs, or spec compliance. You still need the 2-stage review process.
- **Don't duplicate what the tool already does.** `write_file` already runs syntax checks on `.py`, `.json`, `.yaml`, `.toml`. Don't re-run `ast.parse` on Python files — the tool does it. Focus hooks on what the tool doesn't check (type errors, test failures, secrets).
- **Subagent hooks are advisory.** When delegating to subagents, include hook instructions in context but don't expect them to be as reliable as controller-side hooks. Verify critical hooks (type check, test run) in the controller after subagent completion.

## Quick Reference

```
Before git commit → scan for secrets (H1)
Before git push → review checklist (H2)
Before destructive command → verify target (H3)
After editing .ts/.tsx/.py/.swift → type check (H4)
After editing source with tests → run tests (H5)
After creating new file → syntax check (H6)
After git commit → verify commit content (H7)
```

**Hooks are cheap insurance. The 30 seconds they cost prevents 30 minutes of debugging.**
