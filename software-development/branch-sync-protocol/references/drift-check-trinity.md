# Drift Check Trinity

Three independent drift checks run at every warmup. Each catches a different class of problem.

## Schema Drift (`detect-schema-drift.py`)

**Catches**: Prisma schema columns missing from PG, or PG columns missing from Prisma. Raw SQL referencing columns not in the schema.

**Location**: `scripts/detect-schema-drift.py`

**Usage**: `STAGING_PG_PASSWORD="$STAGING_DB_PW" python3 scripts/detect-schema-drift.py --cron`

**Key patterns caught**:
- Columns added via raw SQL but never added to Prisma schema
- `@map` decorator mismatches (camelCase in Prisma vs snake_case in PG)
- Tables that exist in PG but not in Prisma (missing models)

## Branch Drift (`detect-branch-drift.sh`)

**Catches**: Stale files in worktree branches vs staging. Both content drift (same filename, different content) and existence drift (file present in one branch but not another).

**Location**: `scripts/detect-branch-drift.sh`

**Usage**: `bash scripts/detect-branch-drift.sh` (check + typecheck), `bash scripts/detect-branch-drift.sh --fix` (auto-sync + typecheck), `bash scripts/detect-branch-drift.sh --no-typecheck` (skip TypeScript check)

**TypeScript compilation check**: The script automatically runs `npx tsc --noEmit` on full-sync worktrees (pipeline-worker) after drift detection. This catches import errors, missing modules, and stale references that files-in-sync doesn't detect — like the T4 failure where pipeline-worker ran a script still referencing `season` that was removed from staging. Only full-sync worktrees are typechecked; schema-only worktrees (scraper) have a different tsconfig and Docker build context. Use `--no-typecheck` to skip when TypeScript isn't available.

**Worktree sync modes**:
- `pipeline-worker`: `full` — syncs `scripts/insights/`, `lib/knowledge-graph/`, `lib/embeddings/`, `lib/insights/`, `lib/route-corridors/`, `prisma/schema.prisma`, plus full dirs `lib/`, `server/`, `app/`
- `scraper`: `schema_only` — only syncs `prisma/schema.prisma`. Docker build only copies `scraper-worker/` + `prisma/`, so syncing `lib/` or `server/` is wasted effort and creates false drift alerts.

**macOS bash 3.2 compatibility**:
- No `mapfile` — use `IFS=$'\n' read -d '' -r -a` instead
- No negative array subscripts (`${arr[-1]}`) — use `${arr[${#arr[@]}-1]}`
- `diff | wc -l` exits 1 when files differ — add `|| true` in `set -euo pipefail` scripts
- `diff -rq` outputs `Only in path/runs:` without trailing slash — filter both `/runs/` and `/runs:` patterns

## Data Drift (`detect-data-drift.sh`)

**Catches**: Production row counts lagging behind staging. Silent data lag where pipeline computed new rows on staging that never reached production.

**Location**: `scripts/detect-data-drift.sh`

**Usage**: `bash scripts/detect-data-drift.sh` (default 5% threshold), `bash scripts/detect-data-drift.sh --threshold 10` (custom threshold), `bash scripts/detect-data-drift.sh --json` (machine-readable)

**Tables checked** (19):
- Core entities: cruise_lines (active), ships (active), ship_itineraries (active), cruisemapper_ports, route_corridors
- Insight tables: corridor_profiles, corridor_persona_fit, corridor_line_presence, corridor_upgrade_insights (T2), corridor_family_insights (T4), cruise_line_insights (T7), ship_corridor_insights (T6), corridor_value_density (T5), corridor_seasonal_profiles
- Computed assets: ship_repositioning_events, sea_distances, corridor_dep_hashes, cruise_line_dep_hashes, content_embeddings

**Drift calculation**: `max(staging, prod) > 0 ? abs(staging - prod) / max(staging, prod) * 100 : 0`

**First-run results (2026-05-23)**:
| Table | Staging | Prod | Drift |
|---|---|---|---|
| corridor_dep_hashes | 20,927 | 11,362 | **45.7%** |
| corridor_family_insights | 6,715 | 4,554 | **32.1%** |
| ship_corridor_insights | 669 | 477 | **28.6%** |
| route_corridors | 20,927 | 18,166 | **13.1%** |
| corridor_profiles | 20,927 | 18,158 | **13.2%** |