---
name: worker-durable-handoff
version: 1.0.0
description: Completion-driven durable handoff records between worker services in a shared-DB monorepo.
category: software-development
status: active
created: 2026-07-08
updated: 2026-07-08
---

# Durable worker handoffs (completion-driven)

Use when one worker service must record a durable, completion-driven state that another worker service reads to start a cascade or next phase.

## Triggers

- A service like `scraper-worker` runs a multi-day job and must signal `pipeline-worker` only when the job is truly complete.
- The trigger must be **completion-driven**, not calendar-driven (e.g., never `dayOfMonth === 1`).
- A single Prisma/PostgreSQL database is shared across worker services (Railway-style services or monorepo worktrees).

## Core principles

1. **One table owns the handoff state.** Prefer a single model like `monthly_scrape_handoffs` keyed by a unique `monthKey` (or equivalent domain key).
2. **Status is explicit and final.** `scrape_complete` + `success=true` is the only signal that allows the reader to start work. Other statuses (`scrape_running`, `scrape_failed`, `scrape_needs_review`) must block the cascade.
3. **Readiness, not duration.** Completion means all required readiness flags are true (e.g., ships/itineraries, port schedules, matching, MV refresh). Never infer completion from elapsed time or calendar date.
4. **Upsert for idempotency.** Re-runs on the same key should clear stale completion data and reset to the running state.
5. **No destructive/prod actions auto-queued.** The handoff writer should not schedule production sync, bulk recompute, or replication. Those stay behind human gates.

## Implementation steps

1. Add the Prisma model on the shared schema branch (e.g., `develop`), generate the client, deploy the migration.
2. In each worker package that touches the model, **run `prisma generate` locally** so the package's Prisma client includes the new model. Do not assume the root workspace copy is enough if the package uses its own `node_modules/@prisma/client`.
3. Duplicate shared constants/types inside each worker's `rootDir`. Do not import from outside the worker's `tsconfig rootDir` (e.g., `lib/pipeline-jobs/...`) because TypeScript will reject cross-root imports.
4. Write the handoff helper using `upsert` on the unique key. Use `Prisma.JsonNull` for JSON nulls, not plain `null`, and type JSON inputs as `Prisma.InputJsonValue` or `Prisma.JsonValue`.
5. Wire `markScrapeRunning` at suite start; use progressive `updateScrapeReadiness` mid-suite; call `markScrapeComplete` only at true end; `markScrapeFailed` on fatal abort.
6. On the **reader** side (e.g. pipeline-worker): supervisor tick starts work only when `canStartCascade` — never calendar day alone.
7. Verify import smoke **and** that writer symbols have call sites in the worker `index.ts` (file existence alone is not wired).

## Progressive readiness (multi-phase / multi-day)

| API | When | Status outcome |
|-----|------|----------------|
| `markScrapeRunning` | suite start | `scrape_running` |
| `updateScrapeReadiness` | after a phase (ships done, ports still going) | stays `scrape_running` if any flag false; only `scrape_complete` when **all** true |
| `markScrapeComplete` | true end | `scrape_complete` iff all readiness true; else terminal `scrape_needs_review` (blocks cascade) |
| `markScrapeFailed` | fatal | `scrape_failed` |

**Trap:** using only `markScrapeComplete` for mid-flight updates turns “still scraping ports” into `scrape_needs_review` and blocks the cascade until a human intervenes.

## Multi-day maintenance must not be day-locked only

If maintenance is gated with only `dayOfMonth === MONTHLY_PIPELINE_DAY`, work that continues past day 1 never finishes after the calendar rolls. Continue while this month's handoff is still `scrape_running`:

```ts
const continueSuite =
  dayOfMonth === MONTHLY_PIPELINE_DAY || handoff?.status === 'scrape_running';
```

Stop continuous all-month scraping once handoff is complete/failed/needs_review.

## Pitfalls

- **Cross-root imports / worker tsc OOM (2026-07-08).** Prefer local contract duplicates inside each worker `rootDir`. On **pipeline-worker**, never set `"include": ["../lib/**/*.ts"]` or `"rootDir": ".."` — Railway `tsc` OOMs (~4GB, exit 134). Self-contain contracts under `src/supervisor/contracts.ts`. See `references/worker-tsc-oom-and-branch-discipline-2026-07-08.md`.
- **Worker-only branch for build fixes (user hard rule, 2026-07-08).** Fix + push **only** `pipeline-worker` or `scraper`. Do not also merge into develop/staging “for completeness.” Staging deploys the app, not the worker.
- **Prisma JSON type mismatch.** Use `Prisma.JsonNull` / `Prisma.InputJsonValue` (see `references/prisma-json-handoff-patterns.md`).
- **Stale Prisma client.** Re-run `prisma generate` at repo root (and worker package with `--schema=../prisma/schema.prisma` if it has its own client).
- **Writing success too early.** Mid-suite partials stay `scrape_running` via progressive updates — not `scrape_needs_review`.
- **Calendar triggers.** Multi-day scrapes must not start the cascade on day-of-month alone.
- **Writer file without call sites.** Subagents often drop a helper and leave `index.ts` unwired. Parent: `rg markScrapeRunning scraper-worker/src/index.ts` must hit.
- **Dual cascade.** If scraper still schedules `corridor_computation` while a pipeline-worker supervisor also walks cascade steps, jobs race. Once the supervisor owns the cascade, remove the scraper's one-off schedule.

## Verification

- `npx prisma generate` (root / worker as needed).
- Import smoke or worker-local `npm run build` (prefer over monorepo-wide tsc that times out).
- `rg` call sites for handoff writer + supervisor tick in entrypoints.
- **Staging smoke (SQL, monthKey e.g. `2099-01`):** (1) seed `scrape_running` → wait >1 supervisor tick → assert 0 cascade runs; (2) flip to `scrape_complete`+success → wait → assert exactly one `pipeline_runs` with `triggeredBy=post-scrape-supervisor` and first job enqueued; (3) second tick still one run; (4) cancel remaining jobs so full cascade does not burn staging.
- Negative tests: `scrape_running` / `scrape_failed` / `scrape_needs_review` must not start cascade.

## Deploy topology (writer vs reader branches)

| Piece | Where it lives |
|-------|----------------|
| Handoff table + migration | `develop` → staging DB (`migrate deploy`); also copy migration into worker branches for client generate |
| Writer | `scraper` branch / `.worktrees/scraper` |
| Reader (supervisor tick) | `pipeline-worker` branch / `.worktrees/pipeline-worker` |
| Admin visibility | `staging` app only |

Promote finished develop work to workers with **surgical file copy + index patch**, not full-commit cherry-pick when branches have diverged (see `pipeline-worker-deployment` → `references/surgical-worktree-promote-2026-07-08.md`).

## Locked readiness decisions (this product)

1. `portSchedulesDone` **required** (multi-day port suite is part of monthly ingest).
2. Scraper finishes **match + MV** before complete; reader re-gates / re-runs match only if gate fails.
3. Block notify: Admin UI only for v1.
4. Synthetic handoff tests: SQL only.

## References

- `references/prisma-json-handoff-patterns.md` — JSON typing recipe (2026-07-08).
- `references/worker-tsc-oom-and-branch-discipline-2026-07-08.md` — tsc OOM, worker-only push, smoke outline.
- Plan: `docs/plans/2026-07-08-post-scrape-cascade-supervisor.md`.
- Related: `pipeline-advance-orchestrator` → `references/completion-driven-handoff.md`.
- Related: `pipeline-worker-deployment` → surgical worktree promote.
