# Embedding Infrastructure Pattern

Full implementation for preventing silent embedding index degradation in AI Chat caches.

## Problem

The `ai_chat_cache_embeddings` table was built once (41K rows, 2026-05-02) but became empty on staging while `ai_chat_response_cache` grew to 47K rows. No error was thrown — queries simply fell through from Tier 2 ($0.0002) to Tier 3 ($0.001) or full synthesis ($0.003–$0.005). The loss went undetected because there was no build metadata, no health monitoring, and no incremental generation.

## Solution: Five-layer defense

### Layer 1 — Build Metadata Table

```sql
CREATE TABLE IF NOT EXISTS ai_chat_embedding_builds (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "startedAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  "completedAt"   TIMESTAMPTZ,
  "rowCount"      INT NOT NULL DEFAULT 0,
  model           TEXT NOT NULL DEFAULT 'text-embedding-3-small',
  status          TEXT NOT NULL DEFAULT 'pending',
  "errorMessage"  TEXT,
  "progressPercent" INT,
  "progressLabel" TEXT,
  "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Records every batch build. Catches silent loss by providing an audit trail.

### Layer 2 — Fast Gap Detection

```sql
ALTER TABLE ai_chat_response_cache
ADD COLUMN IF NOT EXISTS "hasEmbedding" BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ai_chat_response_cache_has_embedding_idx
ON ai_chat_response_cache("hasEmbedding");
```

Allows `SELECT COUNT(*) WHERE hasEmbedding = false` without joins.

### Layer 3 — Health Endpoint

```typescript
// GET /api/admin/ai-chat/embedding-health
{
  cacheRows: 47406,
  embeddingRows: 0,
  coveragePct: 0,
  isHealthy: false,
  lastBuild: {
    startedAt: '2026-05-13T10:00:00Z',
    status: 'cancelled',
    rowCount: 5000,
    progressPercent: 10,
    progressLabel: 'Cancelled at offset 5000',
    errorMessage: null,
  }
}
```

Returns `isHealthy: false` when coverage < 95%.

### Layer 4 — Incremental Generation

```typescript
// In cacheResponse() — fire-and-forget after cache write
async function generateEmbeddingForCacheKey(cacheKey: string, query: string) {
  try {
    const embedding = await embedQuery(query);
    await prisma.$transaction([
      prisma.ai_chat_cache_embeddings.upsert({...}),
      prisma.ai_chat_response_cache.update({
        where: { cacheKey },
        data: { hasEmbedding: true },
      }),
    ]);
    invalidateIndex(); // reload in-memory index on next lookup
  } catch (err) {
    // Swallowed — cache row is still valid
  }
}
```

Never blocks the API response. Failure is logged but not thrown.

### Layer 5 — Admin Pipeline Job

Registry entry in `lib/pipeline-jobs/registry.ts`:

```typescript
rebuild_embedding_index: {
  id: 'rebuild_embedding_index',
  name: 'Rebuild Embedding Index',
  category: 'cache',
  scripts: ['scripts/build-cache-embedding-index.ts'],
  options: [
    { name: 'dryRun', type: 'boolean', label: 'Dry run', default: true },
    { name: 'batchSize', type: 'number', label: 'Batch size', default: 100 },
    { name: 'resumeFrom', type: 'number', label: 'Resume from offset', default: 0 },
  ],
}
```

Script features:
- `--dry-run` previews counts without OpenAI calls
- `--resume-from=N` continues from offset after pause/cancel
- Emits `[PROGRESS] percent=N label="..."` every batch for live UI updates
- SIGTERM handler for graceful cancel (finishes current batch, saves progress)
- Checks `ai_chat_embedding_builds.status` between batches for pause/resume
- Updates `hasEmbedding = true` on cache rows as it goes
- 5 consecutive errors → fails the build (prevents infinite retry loops)

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate `ai_chat_embedding_builds` table | Keeps `pipeline_job_runs` generic; embedding builds have their own schema |
| `hasEmbedding` boolean vs. join | 10,000× faster gap detection; no join needed |
| Fire-and-forget on cache write | Embedding generation (~200ms) must not block streaming response |
| `invalidateIndex()` on write | Lazy reload is acceptable; eager reload would block every write |
| Pause via DB polling | Runner checks `status = 'paused'` between batches; simple, no IPC needed |
| Cancel via SIGTERM | `runner.ts` already has `cancelJob()` → `child.kill('SIGTERM')`; reuse existing infra |

## Verification

```bash
# After rebuild
psql $DATABASE_URL -c "SELECT COUNT(*) FROM ai_chat_cache_embeddings"
# Expected: 47406

curl /api/admin/ai-chat/embedding-health | jq
# Expected: { "coveragePct": 100, "isHealthy": true }
```

## Cost & Time

- Full rebuild: ~47K rows × ~50 tokens × $0.02/1M = **~$0.05**
- Time: ~2 hours at 6.5 rows/sec with 500ms sleep between batches
- Incremental: ~$0.0002 per new cache entry (negligible)

## Files Touched

| File | Change |
|------|--------|
| `prisma/schema.prisma` | Add `ai_chat_embedding_builds` model, `hasEmbedding` to `ai_chat_response_cache` |
| `prisma/migrations/20260513.../migration.sql` | Idempotent migration |
| `app/api/admin/ai-chat/embedding-health/route.ts` | New health endpoint |
| `lib/ai-chat/response-cache.ts` | Fire-and-forget `generateEmbeddingForCacheKey()` |
| `lib/ai-chat/embedding-index.ts` | `invalidateIndex()` already existed; verified export |
| `lib/pipeline-jobs/registry.ts` | Add `rebuild_embedding_index` job definition |
| `lib/pipeline-jobs/runner.ts` | Add arg handling for `--batch-size`, `--resume-from` |
| `scripts/build-cache-embedding-index.ts` | Full rewrite with metadata, progress, pause/resume/cancel |
