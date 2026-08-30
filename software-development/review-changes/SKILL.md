---
name: review-changes
description: "Use when performing a structured code review on recent changes. Performs risk-aware review using change detection, impact analysis, and test coverage checks via the knowledge graph."
version: 2.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [code-review, knowledge-graph, testing, changes, impact-analysis]
    related_skills: [debug-issue, refactor-safely]
---

# Review Changes

Perform a thorough, risk-aware code review using the knowledge graph.

## When to Use

- Reviewing a PR, branch, or set of recent commits
- Assessing the risk of a proposed change
- Identifying missing test coverage for modified code
- Providing a structured merge recommendation

## Workflow

### 1. Detect changes

Run `detect_changes` to get a risk-scored analysis of what changed.

### 2. Find impacted execution paths

Run `get_affected_flows` to discover which execution paths are impacted by the changes.

### 3. Check test coverage

For each high-risk function identified, run `query_graph` with pattern `tests_for` to check if the changed code has corresponding tests.

### 4. Measure blast radius

Run `get_impact_radius` to understand how far the effects of the change propagate.

### 5. Suggest improvements

For any untested or risky changes, propose specific test cases or improvements.

## Output Format

Group findings by risk level (high / medium / low) with:
- What changed and why it matters
- Test coverage status
- Suggested improvements
- Overall merge recommendation

## Token Efficiency Rules

- ALWAYS start with `get_minimal_context(task="<your task>")` before any other graph tool.
- Use `detail_level="minimal"` on all calls. Only escalate to "standard" when minimal is insufficient.
- Target: complete any review/debug/refactor task in ≤5 tool calls and ≤800 total output tokens.

## Common Pitfalls

1. **Reviewing without risk context.** Always use `detect_changes` first so high-risk changes get the most attention.
2. **Assuming tests exist.** Always verify coverage with `query_graph` pattern `tests_for`.
3. **Ignoring downstream callers.** A safe-looking change can break callers you didn't trace.
4. **Skipping the merge recommendation.** The review isn't complete until you've given a clear go / no-go / go-with-caveats signal.
5. **Missing project-specific hard-rule verification for external-service scripts.** When the change touches scripts that call FalkorDB, Redis, or DB proxies, check that the code follows the repo’s hard rules — for example, that `closeFalkorDB()` is called synchronously before `process.exit()`, including inside the `catch` handler, and that environment assertions do not over-constrain valid internal-host usage. See `references/falkordb-script-review-patterns.md` for a concrete checklist.
6. **Inconsistent CLI conventions within a script directory.** When a new script lives alongside siblings that already use a shared argument parser (`lib-cli-args.ts`, `commander`, etc.), prefer reusing the existing helper. A custom parser that drops `--help`, changes flag names, or redefines `--confirm` semantics creates friction and surprises.

## Verification Checklist

- [ ] Changes detected and risk-ranked via `detect_changes`
- [ ] Impacted execution paths identified via `get_affected_flows`
- [ ] Test coverage verified for high-risk functions via `query_graph`
- [ ] Blast radius measured via `get_impact_radius`
- [ ] Merge recommendation provided with rationale
