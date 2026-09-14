# Pipeline Registry Audit

Audit a pipeline/job registry against actual application usage. Find stale jobs,
missing pipeline steps, and dependency gaps BEFORE hardening or modifying the pipeline.

## When to Use

- User says "audit the pipeline", "what jobs are needed vs dead", "deep dive the pipeline", "harden the pipeline"
- Before any pipeline modification: adding, removing, or reordering steps
- After schema migrations that may have orphaned pipeline steps
- When tables drift between environments (missing TABLE_CONFIGS is often the cause)

## Workflow

### 1. Extract the full pipeline definition

Read the pipeline phase/step configuration:
- In the cruise-advisor platform: `lib/pipeline-jobs/post-scraper-phases.ts`
- Look for: phase numbers, step names, job IDs, optional flags

```bash
# Extract all jobIds from pipeline phases
grep "jobId:" lib/pipeline-jobs/post-scraper-phases.ts | sed "s/.*jobId: '//;s/'.*//" | sort -u
```

### 2. Extract the full job registry

Read the job registry that maps job IDs to scripts:
- In CI: `lib/pipeline-jobs/registry.ts`
- Look for: jobId → script paths, worker type, prerequisites, options

```bash
# Extract all registered job IDs
grep "^  [a-z_]*: {" lib/pipeline-jobs/registry.ts | sed "s/: {//;s/  //g" | grep -v label | sort -u
```

### 3. Find the diff: registered vs in-pipeline

```bash
# Jobs in registry but NOT in monthly pipeline
comm -23 <(registry_ids) <(pipeline_phase_ids)
```

These are either: (a) standalone/on-demand tools, (b) pre-scraper steps, (c) dead code, or
(d) **MISSING from pipeline — jobs that should run but don't**.

### 4. Check actual app usage for each job

For each job's output table(s), search the app + server code:

```bash
# Check if a table/computed field is used by the app
grep -rn 'table_name\|modelName\|fieldName' app/ server/ --include='*.ts' --include='*.tsx' | grep -v registry | grep -v node_modules
```

Key patterns to look for:
- **Direct Prisma queries**: `prisma.modelName.findMany()` — actively used
- **Raw SQL references**: `FROM table_name` — actively used
- **Zero hits outside registry** — likely dead or only used as intermediate data

### 5. Verify all scripts exist

```bash
# Check every script path from registry
for script in $(grep "scripts/" lib/pipeline-jobs/registry.ts | grep -oE "scripts/[^']*" | sort -u); do
  [ -f "$script" ] && echo "EXISTS  $script" || echo "MISSING $script"
done
```

### 6. Map the full data dependency tree

Starting from new data arriving (ships, itineraries, port_visits), trace EVERY downstream
table and computation. Key questions:

1. What tables depend on `ship_itineraries`?
2. What tables depend on `route_corridors`?
3. What tables depend on `falkordb_sync`?
4. What content/embedding tables depend on insights?
5. What jobs produce tables that OTHER jobs read as input?

Build a top-to-bottom dependency tree. Compare it against the pipeline phase order.
**Missing steps in the pipeline appear as dependencies that exist in the app but have
no corresponding pipeline step.**

### 7. Classify each job

| Category | Action | Description |
|----------|--------|-------------|
| In pipeline, app uses it | ✅ Keep | Working as designed |
| In pipeline, app doesn't use it | ❌ Remove | Dead computation |
| NOT in pipeline, app uses it | ⚠️ ADD to pipeline | Gap — data goes stale |
| NOT in pipeline, standalone tool | 🔄 Keep standalone | Diagnostics, one-off tools |
| NOT in pipeline, run-once | 🔄 Keep standalone | Bootstrap/initial setup |
| Duplicate registry entry | ❌ Remove duplicate | Same script, different job ID |

### 8. Check for duplicate/orphaned registry entries

Common patterns:
- Same script registered under two job IDs (one stale)
- Registry entry with wrong script path
- Job in pipeline with no registry entry
- Script exists but no registry entry (orphan script)

### 9. Check sync script coverage

If the project has a cross-environment sync script (e.g., `sync-to-production-v3.ts`):
- Verify ALL tables produced by pipeline jobs are in the `TABLE_CONFIGS`
- Missing tables silently drift — no error, no warning
- Cross-reference: every table written by a pipeline job should appear in TABLE_CONFIGS

```bash
# Extract tables from sync script
grep "name:" scripts/sync-to-production-v3.ts | grep -oE "'[^']+'" | sort -u

# Compare against tables known to be produced by pipeline
```

## Common Findings

| Finding | Root Cause | Fix |
|---------|-----------|-----|
| Table drifts between envs | Missing from sync script TABLE_CONFIGS | Add table config with correct natural key |
| Job has persona/season options but schema dropped those columns | Schema evolution outpaced registry | Update registry options, fix natural keys |
| Same script registered twice | Registry evolved; old entry never removed | Remove stale entry |
| Job not in pipeline but app uses its output | Incrementally added; never added to phases | Add to correct phase after dependency |
| Corridor-derived tables missing from sync | New enrichment table added but sync not updated | Add to TABLE_CONFIGS with clearConflictOnInsert |

## Output Format

Produce a structured audit document with:
1. Full dependency tree (top-to-bottom)
2. Job-by-job table: in-pipeline, app-used, verdict
3. Missing-from-pipeline list with recommended phase placement
4. Dead/orphaned jobs to remove
5. Sync script coverage gaps
6. Recommended phase redesign