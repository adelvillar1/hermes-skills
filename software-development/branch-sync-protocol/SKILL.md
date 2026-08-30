---
name: branch-sync-protocol
category: software-development
description: >
  Prevents silent code divergence across branches with independent worktrees.
  When a fix is applied to one branch but not the other, the production worker
  runs old code while you think it's running new code. This has caused
  multi-week data corruption, cascading TypeScript errors, and multiple
  failed pipeline runs.
trigger:
  - pushing code to any branch that has an independent worktree
  - modifying files in shared directories (scripts/, lib/, server/, app/, prisma/)
  - deploying to pipeline-worker or scraper-worker
  - adding new Prisma models or migrations (sync both `prisma/schema.prisma` AND `prisma/migrations/` to scraper)
  - fixing a bug and claiming "this is done"
  - syncing changes between staging and main
  - starting a session (warmup) or ending a session (wrapup)
---

# Branch Sync Protocol

The project has multiple branches with independent worktrees and shared code directories. When you modify a file that exists in more than one branch, you MUST check and update all branches before claiming the work is done.

## Branch topology

| Branch | Worktree | Deploys to | Sync mode | Shared code |
|--------|----------|------------|-----------|-------------|
| develop | main dir | local only | source | Full app |
| staging | main dir | Railway (vibrant-tranquility) | source | Full app |
| main | (merge from staging) | Railway (production) | source | Full app |
| pipeline-worker | `.worktrees/pipeline-worker` | Railway (pipeline-worker) | **full** | All shared dirs + lib/server/app |
| scraper | `.worktrees/scraper` | Railway (practical-rejoicing) | **scraper_src** | `scraper-worker/src/` (full) + `prisma/schema.prisma` |

**Normal flow**: `develop` → `staging` → `main`. Development happens on `develop`; staging deploys from `staging` branch; production deploys from `main`.

**Sync modes:**
- **full** — rsync `scripts/insights/`, `lib/knowledge-graph/`, `lib/embeddings/`, `lib/insights/`, `lib/route-corridors/`, `prisma/schema.prisma`, plus full dirs `lib/`, `server/`, `app/`. The pipeline-worker Dockerfile copies from the worktree root so it needs everything.
- **scraper_src** — rsync `scraper-worker/src/` (full, `--delete`) + `scraper-worker/package.json` + `prisma/schema.prisma`. The scraper Dockerfile only copies `scraper-worker/` and `prisma/`, so `lib/`, `server/`, `app/` drift is irrelevant. But `scraper-worker/src/` IS in the Docker build and must be synced. Drift in `lib/`, `server/`, `app/` on the scraper branch is irrelevant noise — those dirs aren't in the Docker build.

## Service-specific config files — NEVER merge across services

Some files at the repo root are **per-service**, not per-branch. The classic case is `railway.toml`:

- `main` has a `railway.toml` for the main app (e.g., `dockerfilePath = "Dockerfile"`, `healthcheckPath = "/api/health"`, no startCommand)
- A worker branch (e.g., `feat/oddsportal-worker`, `pipeline-worker`) has its own `railway.toml` (e.g., `dockerfilePath = "Dockerfile.worker"`, `startCommand = "python -m src.worker.oddsportal run"`, `healthcheckPath = ""`)

Railway uses the file as the authoritative source of truth and auto-resets dashboard settings to match it on every redeploy. **If you merge the worker's `railway.toml` into main, the main service deploys the worker image.** The main app is replaced by a non-HTTP process → 502 on every endpoint.

**Rule**: When merging a worker branch into main, ALWAYS exclude these files:
- `railway.toml` (per-service)
- `Dockerfile.worker` (per-service, if separate from main's `Dockerfile`)
- Any `Procfile`, `nixpacks.toml`, `startCommand`-equivalent
- Any `.dockerignore` that's service-specific (e.g., the worker may have Playwright/Chromium deps the main app doesn't want)

**The trick**: the worker branch's `railway.toml` is sacred to the worker. Don't merge it into main, and don't sync main's toml into the worker branch.

**Verification before ANY merge that touches these files (both directions)**:
```bash
# See what the merge is going to change
git log --oneline -- <file> | head -5
git diff <source-branch>...<target-branch> -- <file>
# If the diff is changing a per-service config, do NOT merge that file
# Use `git checkout <target-branch> -- <file>` after merge to restore the target's version
```

**After merge — restore the target's per-service config**:
```bash
# After merging main → worker (or worker → main):
git checkout <target-branch> -- railway.toml
git commit -m "fix: restore <target> railway.toml after merge"

**Real example — worker→main (elo-scenario-lab, 2026-06-02)**: The `feat/oddsportal-worker` branch was merged into main. The worker's `railway.toml` (with `dockerfilePath = "Dockerfile.worker"`, `startCommand = "python -m src.worker.oddsportal run"`) was brought into main. Railway auto-deployed the main service (`distinguished-energy`) using the worker image. Result: every endpoint returned 502 because the worker process has no HTTP server. The fix was a separate commit on main that restored the pre-worker `railway.toml` (with `dockerfilePath = "Dockerfile"`, `healthcheckPath = "/api/health"`). The worker branch kept its own `railway.toml` unchanged.

**Real example — main→worker (elo-scenario-lab, 2026-06-04)**: The OPPOSITE direction. `main` was merged into `feat/oddsportal-worker` (fast-forward) to bring football scraper code to the worker. Main's `railway.toml` (with `healthcheckPath = "/api/health"`, `dockerfilePath = "Dockerfile"`) overwrote the worker's config (which had `healthcheckPath = ""`, `dockerfilePath = "Dockerfile.worker"`, `startCommand`). The worker is a CLI process with no HTTP port — Railway's healthcheck hit a non-existent endpoint and the service was marked unhealthy. Fix: restored the worker's `railway.toml` and pushed. **Lesson**: fast-forward merges silently overwrite per-service config files. Before merging ANY direction, check `git diff <source>...<target> -- railway.toml` and exclude it if the diff changes service-specific settings.

**Related check**: After merging a worker branch, verify the deploy is healthy:
```bash
# Check the main service health (NOT the worker service)
curl -sS -w "HTTP %{http_code}\n" "https://<main-app-url>/api/health"
# If 502, the toml was probably overwritten — restore the main one
```

## Warmup: Run drift detection FIRST

At every session start, run the drift detection script. It checks all shared directories across all worktrees and reports divergence:

```bash
bash scripts/detect-branch-drift.sh
```

If drift is found, fix it BEFORE starting any other work. Options:
- `bash scripts/detect-branch-drift.sh --fix` — interactive mode, confirms before overwriting
- Manual rsync (see Full-rsync pattern below)

The drift script detects both **content drift** (same filename, different content — e.g., a bug fix on staging that's missing from the worktree) and **existence drift** (file present on one branch but not the other — e.g., a new module added to staging). It uses `diff -rq` which reports `Files A and B differ` for content drift and `Only in X: filename` for existence drift. For full-sync directories (`lib/`, `server/`, `app/`), it shows up to 10 specific differing filenames so you can triage severity.

The script filters out generated artifacts (run logs in `scripts/insights/runs/`, `.tsbuildinfo` files) so it only reports real source code divergence. The `diff -rq` pattern uses both `/runs/` and `/runs:` filters because the output format varies (`Only in path/runs:` without trailing slash vs `path/runs/file.md` with one).

The script is configured with per-worktree sync modes. `pipeline-worker` uses `full` (checks all shared directories + full-sync dirs). `scraper` uses `schema_only` (only checks `prisma/schema.prisma`). This matches what each Docker build actually includes — scraper's build only copies `scraper-worker/` and `prisma/`, so drift in `lib/` or `server/` is irrelevant noise.

To add a new worktree, edit `WORKTREES` in `scripts/detect-branch-drift.sh` with format `branch:path:sync_mode`.

## Shared directories

These directories contain code used by multiple branches. A change in one MUST be propagated:

**Always shared** (specific subdirs):
- `scripts/insights/` — used by both staging and pipeline-worker
- `lib/knowledge-graph/` — used by both staging and pipeline-worker
- `lib/embeddings/` — used by both staging and pipeline-worker
- `lib/insights/` — used by both staging and pipeline-worker
- `lib/route-corridors/` — used by both staging and pipeline-worker
- `prisma/schema.prisma` — used by ALL branches

**Full-sync directories** (when >2 files diverge, rsync the ENTIRE directory):
- `lib/` — utility modules, hooks, AI chat, redis, all shared code
- `server/` — API routes that reference insight modules and Prisma models
- `app/` — pages and components that reference routers and insight types

## Mandatory: Push ALL branches before marking work done

**After every commit+push to staging, you MUST also push to pipeline-worker (and scraper if schema changed) before claiming the task is complete or moving on.** This is not optional — the user has corrected this multiple times.

Checklist after pushing staging:
1. ✅ Staging pushed
2. ✅ Main merged from staging and pushed
3. ✅ Pipeline-worker: merge staging → pipeline-worker, resolve conflicts, push
4. ✅ Scraper: only if `prisma/schema.prisma` changed — copy + push

**Preferred sync method: git merge (not rsync).** When the worktree is close to staging, `git merge staging` from inside the worktree preserves history and is faster than rsync. Only use the full-rsync pattern below when branches have diverged so much that merge conflicts become unresolvable.

```bash
# Preferred: merge from inside the worktree
cd .worktrees/pipeline-worker
git merge staging -m "merge: sync from staging"
# Resolve conflicts (see Conflict resolution below)
git push
```

**Conflict resolution rule**: for shared pipeline files (`lib/pipeline-jobs/`, `scripts/sync-to-production-v3.ts`, `pipeline-worker/src/index.ts`), take the **staging** version (`--theirs` in a merge from staging). The staging branch is the source of truth — pipeline-worker copies must match. For `pipeline-worker/src/index.ts`, staging is also authoritative since it defines the job registry the app depends on.

```bash
# Quick conflict resolution for shared files
cd .worktrees/pipeline-worker
git checkout --theirs lib/pipeline-jobs/registry.ts scripts/sync-to-production-v3.ts pipeline-worker/src/index.ts
git add -A
git commit -m "merge: sync pipeline updates from staging (conflict resolution: take staging for shared files)"
git push
```

After merge + push: verify the worktree compiles (`npx tsc --noEmit`).

## The full-rsync pattern (CRITICAL)

**When more than 2 files diverge in a shared directory, do NOT copy files one at a time.** Individual file copies cause cascading TypeScript errors because stale imports reference deleted modules.

Instead, rsync entire directories:

```bash
# Pipeline-worker: full sync (lib, server, app, insights, prisma)
for dir in scripts/insights lib/knowledge-graph lib/embeddings lib/insights lib route-corridors server app; do
  rsync -av --delete "$dir/" ".worktrees/pipeline-worker/$dir/"
done
cp prisma/schema.prisma .worktrees/pipeline-worker/prisma/schema.prisma
cd .worktrees/pipeline-worker && npx prisma generate --schema=prisma/schema.prisma

# Scraper: scraper-worker/src + schema + migrations sync (Docker copies scraper-worker/ + prisma/)
rsync -av --delete scraper-worker/src/ .worktrees/scraper/scraper-worker/src/
cp scraper-worker/package.json .worktrees/scraper/scraper-worker/package.json
cp prisma/schema.prisma .worktrees/scraper/prisma/schema.prisma
rsync -av --delete prisma/migrations/ .worktrees/scraper/prisma/migrations/   # CRITICAL: includes new migration directories
cd .worktrees/scraper && npx prisma generate --schema=prisma/schema.prisma
# Do NOT rsync lib/, server/, app/ to scraper — they aren't in the Docker build
# But DO sync scraper-worker/src/ + prisma/ — it's the worker's entire codebase
```

**Real example (2026-05-23):** Pipeline-worker was 74 files behind staging. Copying one file (`delta-utils.ts`) led to discovering T4 was running stale season-based code. Then copying `lib/insights/` revealed 4 stale files including deleted ones still imported by routers. One file at a time took 6 iterations before the worktree compiled. The full rsync fixed everything in one pass.

## Automatic type checking

The drift detection script (`detect-branch-drift.sh`) now automatically runs `npx tsc --noEmit` on full-sync worktrees after checking file divergence. This catches import errors, missing modules, and stale references that only surface at compile time — the exact failure mode where pipeline-worker ran scripts referencing deleted `season` modules.

The typecheck runs by default. Use `--no-typecheck` to skip it (e.g., during quick checks where TypeScript hasn't been installed yet). The script exits 1 if TypeScript errors are found, even if file drift has been resolved.

The typecheck only runs on **full-sync** worktrees (pipeline-worker). Schema-only worktrees (scraper) have a different Docker build context and tsconfig, so they're excluded.

## Verification after sync

After rsyncing and pushing both branches:

```bash
# 1. TypeScript must compile clean in the worktree (automatic via drift script)
bash scripts/detect-branch-drift.sh   # includes tsc --noEmit for pipeline-worker

# 2. Dry-run the fixed scripts against real DB
DATABASE_URL="$STAGING_DB" USE_FALKORDB=true \
  npx tsx scripts/insights/precompute-cruise-line-insights.ts --dry-run

# 3. Confirm both branches pushed
git -C .worktrees/pipeline-worker log --oneline -1
git -C . log --oneline -1
```

### Prisma model name verification

`tsc --noEmit` does NOT catch Prisma model name mismatches (both `prisma.routeCorridor` and `prisma.route_corridors` are valid JS property access). After copying files, verify model references:

```bash
cd .worktrees/pipeline-worker
grep -rn "prisma\.\w\+" scripts/insights/ | while read line; do
  model=$(echo "$line" | grep -oE 'prisma\.(\w+)' | head -1 | cut -d. -f2)
  grep -q "model $model " prisma/schema.prisma || echo "⚠️ model '$model' not in Prisma schema"
done
```

## Column name verification for raw SQL

After fixing raw SQL in delta functions, verify column names against the actual database — `tsc --noEmit` cannot catch wrong column names in `$queryRawUnsafe`:

```bash
psql "$DATABASE_URL" -At -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'cruise_line_dep_hashes' ORDER BY ordinal_position;"
```

## Reverse sync: cherry-pick from main → develop

When a fix lands on `main` (or `staging`) before `develop`, do NOT merge production into develop — that's backwards per the branch topology (`develop → staging → main`). Instead, cherry-pick individual commits:

```bash
# 1. See what's on main but not develop
git log --oneline develop..main

# 2. Cherry-pick the fix commits in order (oldest first)
git cherry-pick <hash1> <hash2>

# 3. If tsconfig.tsbuildinfo conflicts, accept --ours (it's a build artifact)
git checkout --ours tsconfig.tsbuildinfo
git add tsconfig.tsbuildinfo
git cherry-pick --continue --no-edit
```

**`tsconfig.tsbuildinfo` is ALWAYS a build artifact** — it regenerates on next `tsc`/`pnpm run build`. Never hand-resolve conflicts in it. Always `--ours` and continue.

Every warmup runs three independent drift checks. Each catches a different class of problem:

| Check | Script | Catches | Exit code |
|---|---|---|---|
| Schema | `python3 scripts/detect-schema-drift.py --cron` | Prisma columns missing from PG (or vice versa) | 1 on drift |
| Code (branch) | `bash scripts/detect-branch-drift.sh` | Stale files in worktree branches vs staging | 1 on drift, `--fix` to auto-sync |
| Data | `bash scripts/detect-data-drift.sh` | Production row counts lagging behind staging (>5% threshold) | 1 on drift |

All three are required warmup checks per CLAUDE.md hard rules. If any reports drift, fix it before starting other work.

**Anti-patterns**

| Anti-pattern | What happened | The damage |
|---|---|---|
| Push to staging only, expect pipeline-worker to deploy | Pushed `feat(scripts): add regenerate-stale-route-maps` to staging, expected pipeline-worker to pick it up. The most recent pipeline-worker deploy was 22 days old (`f51323a5` on 2026-06-04). Pushing staging did NOT trigger a new pipeline-worker deploy — its Railway service watches the `pipeline-worker` BRANCH, not staging. Discovered when `ls /app/scripts/regenerate-stale-route-maps.ts` on the worker returned "No such file or directory" 5 minutes after the staging push. | Hidden assumption that "branch topology with auto-deploy = staging push deploys all services" is wrong. Pipeline-worker and scraper are SEPARATE Railway services on SEPARATE branches. Each has its own auto-deploy hook tied to its own branch. **Verify deployment by SSH'ing to the container and `ls`-ing the expected file** — don't trust that the push "should" have deployed. |
| Worker build fails → push fix to staging/develop | Fixed pipeline-worker `tsc` OOM (tsconfig included `../lib/**/*.ts`), then also merged/pushed develop+staging. User: **"you pushed to the wrong branch, the build failed on the pipeline worker and you pushed the changes to staging."** | Worker-only build/runtime fixes → **only** `git push origin pipeline-worker` (or `scraper`). Staging does not rebuild those services. Optional monorepo mirror on develop is never a substitute for the worker branch push. |
| Cherry-pick full multi-surface develop commit onto worker | Cherry-pick conflicted on app UI + scraper index + divergent `JOB_REGISTRY` / worktree-only extras (news sync). | Prefer **surgical copy** of worker-critical paths + hand-patch worktree-only extras. Do not overwrite worktree `index.ts` wholesale with develop. |
| Copy single files one at a time | Copied delta-utils.ts, then family-insights, then lib/insights — each reveal more stale imports | 6 iterations before worktree compiled. Each "fix" broke something else. |
| Copy without checking transitive deps | Direct import ok, but sub-imports missing (`dual-emit-schemas.ts`) | Runtime crash on prompt schema resolution |
| Prisma model name mismatch | Staging uses `route_corridors`, pipeline-worker copy had `routeCorridor` | Script crashes on drift check query — `tsc --noEmit` doesn't catch this |
| Wrong column name in raw SQL | Used `dh.updated_at` but the column is `dh.computed_at` | Runtime SQL error: "column does not exist". `$queryRawUnsafe` bypasses all type checking. |
| Aggregate in WHERE clause | `COUNT(s.id)` inside WHERE — SQL execution order forbids aggregates in WHERE | Runtime SQL error in T7 cruise-line insights job. Use a subquery with GROUP BY instead. |
| Push one branch, forget the other | Pushed staging, went to write recap, never pushed pipeline-worker | Production worker runs old code for weeks |
| Deploy mid-job | Pushed code improvements while 2h inference job was running | Job killed, all compute wasted. Deploy AFTER job completes. |
| Stale Prisma schema on worktree | Pipeline-worker `schema.prisma` was 341 lines behind staging (missing `corridor_profiles`, `route_signature_map`, etc.) | TypeScript errors on models that exist in PG but not in the worktree's Prisma client. |
| Stale Prisma schema on scraper | Scraper `schema.prisma` was 554 lines behind staging (missing `corridor_dep_hashes`, `advisor_events`, `port_3d_maps`, etc.) | `prisma generate` produces an incomplete client. Scraper code referencing missing models fails at runtime. |
| Migration files not synced to scraper branch | Schema changes + migration were committed to staging but only `prisma/schema.prisma` was copied to scraper, NOT the new `prisma/migrations/20260619000000_*/` directory. `prisma generate` ran on the updated schema (so the model definitions existed) but the scraper branch's `prisma/migrations/` was still on the old version. When the scraper-worker deployed, it regenerated its Prisma client from the schema file, but the schema had no `model port_schedule_snapshots {}` block — the migration was a separate file. Symptom: "Cannot read properties of undefined (reading 'create')" at runtime when code does `prisma.port_schedule_snapshots.create()`. | The full-rsync pattern for scraper must include `prisma/migrations/` AS WELL AS `prisma/schema.prisma`. The schema file and migration directory are two different artifacts — a migration can add columns to existing models without changing the schema's `model` blocks. Copy the entire `prisma/` directory (except `dev.db*`), or list both `prisma/schema.prisma` and `prisma/migrations/` explicitly. After syncing, verify with `diff -rq prisma/ <worktree>/prisma/`. |
| Guess-and-check debugging loop on Prisma | Spent 5 iterations trying `execSync('npx prisma generate')` in `prisma.ts`, changing `package.json` build scripts, switching Dockerfile CMD to `npm start`, adding `realpath` to the schema path — none fixed the "Cannot read properties of undefined" error. The real cause was the scraper branch missing the schema/migration files. | Before modifying build/CI/Dockerfile code to "fix" a deployment issue, verify the deployed code's source files match what you expect. One `diff -rq prisma/schema.prisma <worktree>/prisma/schema.prisma` would have caught this in 30 seconds. The Rule of Three: if two fix attempts don't resolve the issue, stop and trace the actual deployed artifact back to its source. The problem is rarely where you think it is. |
| `set -euo pipefail` kills `diff` in scripts | `diff file1 file2 | wc -l` exits 1 when files differ; `pipefail` propagates this, crashing the script | Branch drift detection silently failed on the scraper worktree. Always use `$(diff ... || true | wc -l)` in `set -e` scripts. |
| Blindly rsyncing full tree to scraper | Copied `lib/`, `server/`, `app/` to scraper worktree unnecessarily | Those dirs aren't in the scraper Dockerfile — copying them inflates the worktree with code that never runs and creates false drift alerts. Only sync `prisma/schema.prisma` to scraper. |
| `diff -rq` path format varies | `diff -rq` outputs `Only in path/runs:` without trailing slash; grep for `/runs/` misses it | Drift check reported pipeline-worker as diverged when only run logs differed. Filter both `/runs/` and `/runs:` patterns. |
| Silent data lag | Pipeline computed 20,927 corridor dep hashes on staging, production had 11,362 (45.7% drift) | Production serving stale insights for weeks with no alert. Add `detect-data-drift.sh` to warmup checks. |
| One-at-a-time file copying | Copying 1 file → discover broken import → copy another → discover another stale dep | 6 iterations. Full rsync of lib/, server/, app/ fixed everything in one pass. |
| No typecheck after sync | Files in sync but pipeline-worker references `season` which was removed on staging | Job fails at runtime with undefined import. `tsc --noEmit` would have caught it immediately. Drift script now runs typecheck automatically. |
| Multi-commit partial sync | Pushed 3 commits on staging (tile URL, colors, backgrounds) but only merged the first into pipeline-worker before subsequent commits landed | Pipeline-worker had the tile URL change but ran with old building colors. Verify every commit from the feature's git log exists in the worktree: `git log --oneline staging ^pipeline-worker` to see what's missing. |
| Partial file sync within one commit | Changed 4 files on staging (refresh script, migrate-environments.ts, sync script, precompute script). Pushed precompute to pipeline-worker but forgot migrate-environments.ts — the Phase 7 MV refresh function signature changed (added `targetUrl` param) but pipeline-worker still had the old 2-arg call. | Pipeline-worker's `migrate-environments.ts --phase=7` crashes with "Expected 3 arguments, but got 2" at runtime. When a commit touches files in BOTH `scripts/` (shared) AND `scripts/migrate-environments.ts` (shared), list every modified file and push ALL of them to the worker branch — not just the ones that seem most relevant. |
| `sync-to-production-v3.ts` changes not pushed to pipeline-worker | Rewrote `syncEmbeddingTable()` from TRUNCATE+COPY to incremental on staging, pushed to staging and main, forgot pipeline-worker worktree. | Pipeline-worker runs stale sync logic. This script is in the shared `scripts/` directory and must be pushed to all branches. Check `git diff --name-only` against ALL worktrees after changing any file in `scripts/`. |
| Running sync from local machine | Ran `sync-to-production-v3.ts` locally with DATABASE_URL pointing at staging. Cross-network latency caused 300s timeout on ship_itineraries (57K rows). | Always `railway ssh --service vibrant-tranquility` and run the sync from inside the staging container. Internal Railway networking is orders of magnitude faster than external proxy connections. |
| New file imported but not committed | Changed `index.ts` to import from a new `additive-port-visit-matching.ts` module, committed and pushed, but the new file was untracked (`??`) and never `git add`-ed. Railway pulled the commit, built with `tsc \|\| true` (which swallows missing-module errors), and crashed at runtime with `Cannot find module`. | Always run `git status` before committing in a worktree. Any `??` file that is imported by a committed file MUST be `git add`-ed. Railway health checks may pass (old deployment still running) while the new one crashes on startup — check deploy status, not just service status. |
| Sync re-writes rows with identical data | Pipeline job changed `departureDate` on 57K itineraries, Prisma's `@updatedAt` auto-bumped timestamps on all of them. Sync saw timestamp mismatch and re-upserted every row even though the data was identical. | The sync script now has a data verification step (`filterUnchangedRecords`) that compares actual column values (excluding timestamps) before writing. Verify with `--dry-run --table=ship_itineraries` — should show 0 updates if data is truly in sync. |
| New table missing from sync TABLE_CONFIGS | `region_hero_images` migration applied to production, but the table has 0 rows because it was never added to `sync-to-production-v3.ts` TABLE_CONFIGS. Admin pipeline page shows data gap. | After adding a new table with a migration, ALWAYS add it to TABLE_CONFIGS in the sync script. BYTEA tables (hero images) need special handling — Prisma upserts don't handle binary columns well. Use `psql COPY` or the existing `syncEmbeddingTable()` pattern. See `references/production-sync-pitfalls.md`. |
| Content drift vs existence drift | Staging had bug-fixed files while worktree had stale versions of the same filenames | Both are caught by `diff -rq` — `Files A and B differ` (content) vs `Only in X: filename` (existence). The drift script checks for both. |
| Feature code on main, worker branch not updated | Football scraper commits (`3d6c63d`, `d5bd2f4`) landed on `main` but `feat/oddsportal-worker` was never updated. The scraper worker runs the worker branch's code, so the football scraper never deployed. Scheduler showed only 5 American sports in results. | After adding feature code that a worker service needs, ALWAYS check `git branch --contains <commit>` and merge into the worker branch. Don't assume main == deployed. The worker has its own branch, its own Dockerfile, and its own deployment cycle. |
| Scraper branch drift not detected (schema_only blind spot) | `detect-branch-drift.sh` was configured with `schema_only` sync mode for scraper, meaning it only checked `prisma/schema.prisma`. But `scraper-worker/src/` had drifted significantly — the scraper branch had a working `pipelinePoll()` while staging had a dead stub. The drift script reported "SYNCED" because schema.prisma matched. | `scraper-worker/src/` IS in the Docker build and must be checked for drift. The sync mode is now `scraper_src` (checks `scraper-worker/src/` + `prisma/schema.prisma`). If you add a new worktree, check what the Dockerfile actually copies — `schema_only` is only safe if the Dockerfile truly only copies `prisma/`. |
| File copied over module export boundary | Commit `83376d45` overwrote `scraper-worker/src/tasks/additive-port-visit-matching.ts` (a module with `export async function additivePortVisitingMatching()`) with a standalone CLI script (no exports, runs `main()` at bottom). `index.ts` imported `{ additivePortVisitMatching }` which resolved to `undefined`. `tsc \\|\\| true` masked the TS2305 error. | When a file exists in BOTH `scraper-worker/src/tasks/` (as a module) AND `scripts/` (as a standalone CLI), never copy the standalone version over the module version. They look similar but have different headers/footers. The module has `export`, the script has `main().catch()`. After syncing, run `npx tsc --noEmit \\| grep <filename>` to verify imports resolve. |
| Fix on main, develop left behind | PDF export fixes (`79b11676` compact layout, `dbbaa383` tRPC wiring) landed on `main` but `develop` was 2 commits behind. The API route on develop still used raw Prisma with wrong data shape — most PDF fields rendered blank. `git log develop..main` showed the gap but wasn't checked until a deep dive. | After pushing fixes to staging/main, run `git log develop..main` to check for orphaned commits. Cherry-pick them onto develop (never merge main → develop — that's backwards). Resolve `tsconfig.tsbuildinfo` conflicts with `--ours`. |
| `tsc \|\| true` on worker hides errors that block main app build | Scraper-worker Dockerfile uses `(tsc \|\| true)` to avoid blocking deploys on non-critical type errors. But when `scraper-worker/src/` is synced to staging, `pnpm run build` runs strict `tsc` on the whole project — any type error in `scraper-worker/src/` blocks the staging deploy. 4 errors found: `PipelinePhase` not re-exported, `latitude`/`longitude` on `itinerary_ports` (non-existent fields), `cheerio.Cheerio` missing type argument, `completeTask` called with string instead of `TaskResult` object. | After syncing `scraper-worker/src/` to staging, ALWAYS run `pnpm run build` and fix every type error in the synced files. The worker's `tsc \|\| true` is NOT a substitute — it just defers the errors to the staging build. |
| Type re-export missing | `monthly-corridor-phases.ts` imported `PipelinePhase` from `post-scraper-phases.ts` but didn't re-export it. `MonthlyCorridorTimeline.tsx` imported `{ PipelinePhase }` from `monthly-corridor-phases` → `TS2305: declares locally but not exported`. | When module A imports a type from module B and module C imports that type from module A, add `export type { TypeName };` in module A. This is transitive re-export. |
| Prisma select on non-existent relation fields | `post-pipeline.ts` selected `latitude`/`longitude` from `itinerary_ports` relation, but those fields are on `cruisemapper_ports`, not `itinerary_ports`. `tsc \|\| true` masked it. | Before selecting fields from a Prisma relation, verify the fields exist on the related model in `prisma/schema.prisma`. If coordinates are needed from `itinerary_ports`, look them up from `cruisemapper_ports` by `portName` join. |

## References

- `scripts/detect-branch-drift.sh` — automated drift detection, run at every warmup
- `scripts/detect-schema-drift.py` — Prisma/PG schema drift detection
- `references/production-sync-pitfalls.md` — sync-to-production workflow: run from staging, data verification, BYTEA handling, migration record cleanup