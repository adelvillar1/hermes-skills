# FalkorDB script review checklist

Concrete signals to check when reviewing a script that touches FalkorDB or follows the same pattern as `scripts/insights/cleanup-falkordb-extends-orphans.ts`.

## Must-haves

1. **Synchronous resource cleanup before exit**
   - `await closeFalkorDB()` must complete before `process.exit()` is called.
   - This applies to the success path **and** the `catch` path.
   - Avoid fire-and-forget patterns like `Promise.all([...]).then(() => process.exit(1))`.

2. **Correct env handling**
   - Do not assert that `FALKORDB_HOST` equals a hardcoded public proxy when the project’s `falkordb-client.ts` also allows internal Railway hosts (`falkordb.railway.internal`, `falkordb-bqp.railway.internal`).
   - Prefer validating that the host/port/password are set and non-default, not that they match a specific hostname.

3. **CLI convention reuse**
   - If the script lives in `scripts/insights/`, reuse `lib-cli-args.ts` (`parseInsightArgs`, `requireConfirmOrDryRun`) rather than hand-rolling a parser that lacks `--help` or redefines `--confirm`.

## Anti-patterns seen in the wild

- `main().catch(err => { ... Promise.all([closeFalkorDB(), ...]).then(() => process.exit(1)) })` — cleanup may not finish.
- Hardcoding `STAGING_HOST = 'trolley.proxy.rlwy.net'` and then asserting `host !== expectedHost` — blocks internal-host usage.
- Reimplementing `--dry-run` / `--confirm` semantics when a shared helper already exists.

## Reference files

- `lib/knowledge-graph/falkordb-client.ts` — canonical client defaults.
- `CLAUDE.md` — hard rules around `closeFalkorDB()`, `process.exit()`, and destructive operations.
- `scripts/insights/lib-cli-args.ts` — shared argument parser for insight scripts.
