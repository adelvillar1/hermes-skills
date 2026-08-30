# Production Sync Pitfalls

## Run from staging container, not locally

The sync script (`sync-to-production-v3.ts`) must run from inside the staging Railway container via `railway ssh`, NOT from the local machine.

**Why:** The staging container connects to the staging DB via internal Railway networking (`postgres-8f8d.railway.internal:5432`) which is orders of magnitude faster than the external proxy (`ballast.proxy.rlwy.net:44567`). A sync that times out locally (300s) completes in seconds from the container.

```bash
# Correct: run from staging container
railway ssh --service vibrant-tranquility -- "npx tsx scripts/sync-to-production-v3.ts"

# Wrong: run locally (cross-network latency, timeouts)
DATABASE_URL="$STAGING_DB" npx tsx scripts/sync-to-production-v3.ts
```

The container already has `DATABASE_URL` (staging) and `PROD_DATABASE_URL` (production) set as env vars. No need to pass them.

## Data verification prevents shotgun updates

The sync script compares `updatedAt` timestamps to detect changed records. But Prisma's `@updatedAt` decorator fires on ANY column update — so when a pipeline job changes `departureDate` on 57K itineraries, all their `updatedAt` timestamps get bumped, and the sync re-upserts every row even though the actual data is identical.

**The fix:** After `diffMaps` identifies timestamp-mismatched records, `filterUnchangedRecords()` fetches both source and target rows and compares them column-by-column (excluding timestamp fields via MD5 hash). Records with identical data are moved to "unchanged."

**Verification:** After any sync, check the output for `(N data-verified unchanged)` — this shows how many false positives were filtered. A healthy sync should show 0 or very few actual updates.

```bash
# Dry-run to verify before syncing
railway ssh --service vibrant-tranquility -- "npx tsx scripts/sync-to-production-v3.ts --dry-run"
```

## BYTEA tables need special handling

Tables with BYTEA columns (hero images: `ship_hero_images`, `port_hero_images`, `region_hero_images`) cannot be synced via standard Prisma upserts. Prisma's query engine doesn't handle binary column comparison/upsert well.

**Current approach:** These tables are commented out in TABLE_CONFIGS with a note: "imageData Bytes, use psql COPY or re-fetch on target."

**Options for syncing BYTEA tables:**
1. `psql COPY` pipe (like `syncEmbeddingTable()` for pgvector) — TRUNCATE target + COPY from source
2. Manual psql script: `pg_dump` from staging → `psql` restore to production
3. Add a `bytea: true` flag to TABLE_CONFIGS and implement a dedicated handler (similar to `pgvector: true`)

**When adding a new entity with hero images:** Add the table to TABLE_CONFIGS immediately, even if the sync handler needs to be written. The admin pipeline page checks migration records AND data presence — an empty table on production with data on staging will show as out of sync.

## Migration record cleanup

Stale records in `_prisma_migrations` cause the admin pipeline page (`/api/admin/migration-status`) to show "Migrations out of sync" even when the schema is identical.

**Causes:**
- Migration file renamed (e.g., `20260529000000_add_region_hero_images` → `20260615000000_add_region_hero_images`) — old record persists in `_prisma_migrations`
- Migration files deleted from local repo but records remain in production
- Manual table creation + Prisma migration = duplicate records

**Detection:**
```bash
# Compare migration records between environments
railway ssh --service vibrant-tranquility -- "psql \"\${DATABASE_URL%%\?*}\" -t -c \"SELECT migration_name FROM _prisma_migrations WHERE finished_at IS NOT NULL ORDER BY migration_name;\"" | grep -v "Using SSH" | sort > /tmp/staging_migs.txt
psql "$PROD_DB" -t -c "SELECT migration_name FROM _prisma_migrations WHERE finished_at IS NOT NULL ORDER BY migration_name;" | sort > /tmp/prod_migs.txt
diff /tmp/staging_migs.txt /tmp/prod_migs.txt
```

**Cleanup procedure:**
1. Identify stale records (in one env but not the other, with no corresponding local file)
2. Delete stale records from the environment that has them
3. If a migration exists in production but not staging AND the local file exists, run `prisma migrate deploy` on staging
4. If a migration exists in production but not staging AND the local file does NOT exist, insert a matching record on staging
5. Verify: both environments should have identical migration lists
6. Verify: `prisma migrate status` should say "Database schema is up to date!" on both

**Safe deletion:**
```sql
-- Delete a specific stale migration record
DELETE FROM _prisma_migrations WHERE migration_name = 'old_migration_name';
```

This is safe when the schema changes are already applied through other means (renamed migration, manual application, etc.).

## Cross-env migration status endpoint

The admin pipeline page at `/api/admin/migration-status` queries `_prisma_migrations` from BOTH staging and production, compares the lists, and shows `inSync: true/false`. It blocks cross-environment pipeline jobs when `inSync === false`.

The endpoint uses `STAGING_DATABASE_URL` and `PROD_DATABASE_URL` env vars (set on the staging Railway service). If either is missing, that environment is silently excluded from the report.
