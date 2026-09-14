# Parent–child file race (the D&D VTT project admin surfaces, 2026-07-21)

## Context
Implementing `docs/plans/2026-07-21-comprehensive-admin-surfaces.md` Phase 1 (accounts console) while a background leaf subagent was also assigned the same API files.

## Timeline
1. Parent shipped Phase 0 (schema, audit, AdminShell, `/admin/health`) and committed.
2. Parent dispatched Phase 1 subagent on `admin.ts`, `auth.ts`, `session.ts`, UI panels.
3. Live transcript froze after exploratory reads (~30s); no process; no disk writes.
4. Parent continued Phase 1 on the same paths.
5. Concurrent writes corrupted shared files; typecheck failed with duplicate/orphan syntax.

## Corruption patterns observed
- Double `const patchAccountBody = z.object(...)` and half-open `function accountListFields`
- Login handler with two suspend checks and two `createSession` calls mid-block
- `loadAccountFlags` body duplicated after an early `return`
- Tool warnings: modified by sibling subagent after last read

## What worked
- Full-file rewrite via a single write of known-good source (not incremental patch)
- Immediate `npm run typecheck` + `npm run test -w @the D&D VTT project/api`
- Commit Phase 1 before starting Phase 2–3 on the same router
- Parent-only for remaining phases on `admin.ts`; new UI leaves (`CampaignsPanel`, etc.) as separate files

## What did not work
- Further `patch` ops after corruption
- Waiting for the stalled async delegation to "finish cleanly"

## Takeaway
Exclusive path ownership + stall timeout ≥3 min + full-file rewrite recovery.

---

# Pre-commit sibling race caught by the patch tool (the wine-club app api.ts, 2026-08-05)

## Context
Multi-subagent feature wave (wine lineup, self-service cancel, member self-edit, password reset) on `web/src/lib/api.ts`. Two subagents' scopes overlapped on the same file.

## What happened
- Agent read `api.ts` (614 lines), researched backend contracts, then issued its first `patch`.
- The patch **failed at match time** with: *"file was modified by sibling subagent 'sa-...' — re-read the file before writing"* — and the "did you mean" suggestions **displayed the sibling's new content** (the `EventWine` interface already existed).
- Correct recovery: re-read the entire file (now 642 lines; sibling had landed the wine-lineup types + multipart `wines` serialization), audited the sibling's work against the backend/shared zod schemas, then added only the still-missing methods (`members.selfUpdate`, `signups.cancel`, `reservations.cancel`, `auth.forgotPassword`, `auth.resetPassword`). Final `tsc` clean.

## Key insights
1. **The patch tool's fuzzy-matcher failure is an early-warning race detector.** It fires *before* any commit or corruption — the `old_string` no longer exists because the sibling inserted content. Never retry the stale patch unchanged; re-read first.
2. **Scope overlap is invisible at dispatch time.** Both subagents were legitimately assigned "the api.ts changes"; the overlap was only discoverable mid-flight. When a sibling-race warning fires, assume part of your task is already done and switch mode from *implement* to *verify + complete the delta*.
3. **Audit the sibling's work against the wire contract before adopting it.** Here the sibling's `wines: EventWine[]` (required) deviated from the task spec (`wines?: EventWine[]`) — but checking the backend proved every events response always includes `wines`, so the required field was *more* correct. Verify against handlers/schemas; don't "fix" deviations blindly.
4. **Report residual spec deviations to the parent.** The sibling's adopted shape plus one spec mismatch (typed-vs-actual response shape on stub endpoints) were surfaced in the summary rather than silently papered over.
