# Worker tsc OOM + branch discipline (2026-07-08)

## tsc OOM

Including monorepo `lib/**` in `pipeline-worker/tsconfig.json` causes Railway build exit 134 (JS heap OOM).

**Fix:** self-contained `src/supervisor/contracts.ts` + `"include": ["src/**/*.ts"]` only. Local `npm run build` before push.

## Branch discipline (user correction)

Worker build/runtime fix → push **only** `pipeline-worker` or `scraper`. Never “also push staging” for a worker container fix. Staging/main = app; workers = own branches.

## Smoke test outline

Synthetic handoff on staging with monthKey `2099-01` (or similar):

1. `scrape_running` → wait ≥60s → zero supervisor runs
2. `scrape_complete` + success + all readiness → exactly one `pipeline_runs`, first job (e.g. `match_port_visits`)
3. Second tick idempotent
4. Cancel pending cascade jobs after verify

Full contract: `pipeline-advance-orchestrator/references/completion-driven-handoff.md`.
