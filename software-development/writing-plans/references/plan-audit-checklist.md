# Plan Audit Checklist

Used when reviewing a plan's completion status (e.g., user says "I thought we finished that").

## Steps

1. **Read the plan** — extract frontmatter status, every AC, and any phase structure.
2. **Verify each AC against live evidence** — not comments or labels:
   - Prisma schema columns and models exist?
   - Route/API endpoint files exist and return expected shape?
   - Pipeline job registered in `registry.ts` with expected options?
   - Build script supports required flags (dry-run, resume, progress)?
   - DB data confirms (e.g., build records, row counts, coverage %)?
3. **Classify**: ✅ Done | ⚠️ Partial (explain gap) | ❌ Not done.
4. **For ⚠️ Partial**: document the functional delta. Is it a hard gap (AC unmet) or a minor optimization (AC met but inefficient)?
5. **Report honestly**: a plan is `completed` when all ACs are functionally met, even if a minor optimization remains.

## Signals That a Plan Is Complete

- All ACs verified against code/data (not just comments).
- Minor inefficiencies don't block completion (e.g., unconditional re-generation vs. conditional check — works either way, just costs more).
- No `status: active` plans that the user confirms are done.
- Build/migration evidence in DB confirms deployment.

## Anti-patterns

- Leaving a plan `active` because "there's always something to optimize" — that scope creep never ends.
- Trusting code comments over live data — comments lie, DB doesn't.
- Re-reading the entire plan body each warmup — frontmatter status should gate this.

## Audit-time check: deferred ACs that left the codebase in a partial state

When a plan is audited as `completed` but one or more ACs were deferred mid-implementation (subagent timeout, type errors, scope shrink), the audit must verify the **user-visible consequence** of each deferral, not just the commit message.

**The pattern:**

1. Find every commit message containing "deferred", "AC X.Y deferred", "reverted", or "follow-up". Each one is a candidate.
2. For each deferral, identify the **downstream consumer** that depends on the deferred AC. Ask: does the downstream code render correctly today, or does it render with null/missing data?
3. Verify the deferred state in code:
   - `git log --grep="deferred" --oneline` — find all deferral commits
   - For each, `grep` the related UI/server code for `null` returns or empty data paths
   - Check that the *user-visible output* (not just the code) actually matches the AC

**Real example (2026-07-02, itinerary-data-parity plan):** AC4.1 ("extract `buildEnrichedPorts` helper") was deferred after two subagent timeouts. The commit message said "UI parity is in place." The audit's question: does the share page UI render the new env-data badges?

- Code-level check: yes, `formatCrowdingBadge` and `formatPortCostBadge` are imported and called conditionally.
- Data-level check: NO — `getByShareToken` still returns `crowding: null, portCost: null` because the helper extraction (which would have unified the data path) was reverted.

The plan is `completed` per the AC list, but a future session will see working code that silently renders nulls. The audit must call this out: "AC4.1 deferred; UI renders correctly but receives null data for the new fields until follow-up lands."

**The rule:** an AC marked "deferred" in a commit message is not a closed item. It's a known gap with a downstream consequence that the next auditor (or the next user) will hit. The audit checklist must include checking for these gaps and surfacing them in the recap.

## Audit-time check: AC verification grep matched the wrong thing

When an AC verification command is a `grep` for a literal string, the implementation may have legitimately moved the literal behind a helper function (e.g., `formatPortTypeLabel('departure')` returns `'Embarkation'` at runtime). The grep returns 0 matches even though the rendered output contains the string. The audit must distinguish:

- **Implementation correctly delegates the literal to a helper** — verify the helper returns the literal and the caller invokes it. AC is met.
- **Implementation missed the AC entirely** — the caller doesn't invoke the helper, the helper doesn't exist, or the helper returns the wrong value. AC is not met.

The verification should accept either a literal-in-source match OR a code-traceable path through a helper whose return-type signature contains the literal.

See `draft-feature-plan/references/multi-surface-feature-parity.md` § "AC verification gotcha: helper functions vs literal strings" for the full pattern.