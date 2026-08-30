# Claim hygiene: every "exists" assertion in a handoff must be verified

Handoffs and phase plans routinely assert prerequisites: "use `api.reservations.create()`, which exists in api.ts", "the X helper already handles Y". These claims are written from the authoring session's *belief* about what it left behind — planned, documented, or half-landed work reads the same as shipped work in a recap.

## Real case (2026-07-31, pampa-wineclub Phase 6b)

The phase instruction directed the next session to wire the landing page to `api.reservations.create()` and `api.reservations.availability()`, "which exist in api.ts". They did not — the `reservations` group in api.ts had only `list`/`adminCreate`/`update`/`remove`. The backend routes they'd wrap did exist, so the claim was directionally right, operationally false. The receiving session caught it by reading api.ts before writing dependent code, made a minimal additive fix, and flagged the deviation in its report.

## Rules for the AUTHOR of a handoff

1. **Only assert existence for symbols you can grep in the working tree right now.** If you *intend* to add a helper in this session, add it first, then reference it. Never write "X exists" about work that is still in your head.
2. **Cite the exact location**: `api.reservations.availability()` in `web/src/lib/api.ts:360`, not "the availability helper in the api client".
3. **Distinguish layers explicitly**: "the backend route exists (`api/src/routes/reservations.ts`) but the frontend client method does not — Phase 6b must add it." A handoff that names the gap costs the next session nothing; one that papers over it costs a deviation decision.
4. **State the contract, not just the name**: request/response shapes (or a pointer to the zod schema that defines them) so the next session doesn't have to reverse-engineer the endpoint.

## Rules for the RECIPIENT of a handoff

1. **Verify every "exists" claim against source in the same pass as reading the files you'll edit.** One grep per claimed symbol.
2. **If false, check the layer below** (routes, schemas, DB) to size the gap: one-line additive client addition vs. missing feature.
3. **Additive gap + task impossible without it → make the minimal fix, proceed, flag it.** Signature-changing or feature-sized gap → stop and surface as a blocker.
4. **Always name the deviation in the final report**: what was claimed, what was there, what you did, why it was safe.

The full recipe lives in `regression-claim-verification` under "Prerequisite-existence claims".
