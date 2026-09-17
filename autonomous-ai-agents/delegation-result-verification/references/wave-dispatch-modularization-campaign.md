# Wave-Dispatched Refactoring Campaigns (verified 2026-07-27)

A large multi-target refactor (splitting N monolithic files into modules) is best run as a
**wave-dispatched campaign** rather than one giant parallel batch or a long serial loop.
This pattern was validated on a 9-target modularization of the production
codebase (3 tRPC routers, 1 router-merge, 5 React components; 51 files, +8,434/−7,348)
with **zero build failures across all 9 tasks** — despite two subagent failures that the
wave structure caught cleanly.

## The pattern

1. **Plan first, with a per-task verification gate baked in.** Every task in the plan
   carries the SAME mandatory gate: `npx tsc --noEmit` after each module, then
   `npx next build --no-lint` (the exact command the deploy builder runs — NOT just tsc)
   before commit. Writing the gate into the plan means it gets copied verbatim into every
   subagent prompt.

2. **Group targets into waves by directory disjointness.** Subagents writing to disjoint
   directories can run in parallel safely; subagents touching overlapping paths must be
   serialized. Example waves:
   - Wave 1: the largest/highest-risk target ALONE (establishes the pattern, lowest blast radius).
   - Wave 2: 2 targets in disjoint dirs (`server/routers/` vs `lib/pipeline-jobs/`).
   - Wave 3: 3 targets in disjoint dirs (`server/routers/value/`, `app/app/ships/`, `app/sailings/`).
   - Wave 4: remaining disjoint targets.

3. **Verify between EVERY wave, before dispatching the next.** Run the 3-command
   hallucination check (Pitfall 7) + re-run the build yourself (Pitfall 8) for each task
   in the wave. Only when all are green do you dispatch the next wave. This is the key
   property: a hallucination or misread failure in wave N is caught and re-dispatched
   BEFORE wave N+1 goes out, so bad state never propagates.

4. **Re-dispatch failures with explicit anti-hallucination instructions.** When a task
   fails verification, re-dispatch it (often alongside the next wave's disjoint targets)
   with: "You MUST actually create the files and commit. Verify with `ls` and
   `git log --oneline -1` before reporting done. Include the ACTUAL output of these
   commands in your summary."

## Why it works

- **Parallelism where safe, isolation where not.** Batching by disjoint directory gets
  ~3x throughput without write races.
- **Bounded blast radius.** The largest risk goes first, alone. Failures are contained
  to one wave and verified before anything builds on top.
- **The gate is non-negotiable and uniform.** Because the build command is in the plan
  and copied into every prompt, no subagent gets to substitute a weaker check (e.g. tsc
  alone). This is the direct lesson of an earlier 8-failed-Railway-build loop where
  subagents ran `tsc --noEmit` but the deploy builder ran `next build`.

## Anti-patterns this avoids

- **One giant parallel batch of all 9 targets** — a single hallucination or write race is
  hard to isolate, and you can't verify incrementally.
- **Pure serial dispatch** — correct but ~3x slower; wastes the safe parallelism.
- **Trusting subagent self-reports and pushing at the end** — this is how a fabricated
  commit ships. Verify per-wave, per-task.

## Concrete subagent-prompt skeleton (per target)

```
PROJECT: <abs path>   BRANCH: develop

REFERENCE: <an already-completed split in the repo> — copy its exact pattern.
<the pattern, e.g. sub-routers export PLAIN OBJECTS; only the barrel calls router()>

PROCEDURE GROUPING (verified from source): <which symbols go to which new file>

MANDATORY VERIFICATION (from lessons learned):
1. npx tsc --noEmit after each module
2. script -q /tmp/nb-<tag>.txt npx next build --no-lint 2>&1; echo "EXIT: $?"  → expect EXIT: 0
   (build output has Redis/DB noise during static gen — IGNORE it, check ONLY the EXIT line)
3. NEVER sed/awk for imports — use the patch tool
4. Commit with EXACT file paths (git add <specific paths>); NEVER git add -A

CRITICAL: You MUST actually create the files and commit. Verify with `ls <dir>` and
`git log --oneline -1` before reporting done. Include the ACTUAL output in your summary.

REPORT: git log --oneline -1, the EXIT code, wc -l of the parent after, ls of new files.
```
