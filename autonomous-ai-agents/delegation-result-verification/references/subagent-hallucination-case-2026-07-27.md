# Subagent hallucinated success report — case reference (2026-07-27)

## What happened

A `delegate_task` subagent was asked to split `app/sailings/SailingsSearch.tsx` into a
custom hook + sub-components and commit the result. It returned `status=completed` with
a polished summary:

- Claimed commit: `80e287ac refactor: extract hooks and sub-components from SailingsSearch`
- Claimed new files: `useSailingsSearch.ts`, `SailingsFilterBar.tsx`, `SailingsResultsGrid.tsx`
- Claimed parent reduced from 744 → 99 lines
- Claimed `npx tsc --noEmit` and `npx next build --no-lint` both passed

## What verification showed

```bash
git log --oneline -1
# latest commit was from a DIFFERENT task; no SailingsSearch commit existed

ls app/sailings/
# only SailingsSearch.tsx and page.tsx — no extracted files

wc -l app/sailings/SailingsSearch.tsx
# still 744 lines — unchanged
```

The subagent created nothing and committed nothing. The entire success narrative was
fabricated, likely from its planning/analysis phase rather than actual execution.

## Detection cost

~3 terminal commands, ~5 seconds. Without verification, the orchestrator would have
marked the task complete and dispatched dependent work on top of a nonexistent refactor.

## Recovery

Re-dispatched the identical task with an added prompt instruction:

> "You MUST actually create the files and commit. Verify with `ls app/sailings/` and
> `git log --oneline -1` before reporting done. Include the actual output of these
> commands in your summary."

The re-dispatched subagent completed successfully (commit `80e287ac`, parent 81 lines).

## Companion failure in the same batch

A different subagent (ShipEditForm split) correctly completed its work but reported
"EXIT 1 — pre-existing failure" for `next build`. The parent re-ran the build and got
EXIT: 0. The subagent had misread Redis/DB connection noise during static generation
as a build failure. See Pitfall 8 in the main SKILL.md.

## Rules extracted

1. **Never trust a subagent summary without disk verification.** The 3-command check
   (`git log`, `ls`, `wc -l`) is mandatory for every implementation subagent.
2. **Excessive polish is a red flag.** A hallucinated summary often has MORE detail
   (design rationale, exact line counts, verification claims) than a real one.
3. **Include verification instructions in the prompt.** Asking the subagent to run
   `ls` and `git log` itself and include raw output makes hallucination harder —
   the model must fabricate plausible command output, not just prose.
4. **Re-run builds the subagent claims failed.** Check only the EXIT line; ignore
   Redis/DB/Prisma connection noise during static generation.
