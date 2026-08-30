---
title: Inference Asset Guardian
description: |
  Treat inferred/cached/generated assets as expensive, non-throwaway resources.
  Every inference costs time and money; poorly planned code that skips dry runs
  destroys both. This skill enforces safe patterns for any work that produces
  or mutates AI-generated, scraped, or computed assets.
version: 1.1.0
name: inference-asset-guardian
---
# Inference Asset Guardian
# Inference Asset Guardian

> **Core principle:** Inference is not a throwaway asset. It has real costs — both time and money. A session must treat inferred assets with care.

## 1. Mandatory Dry-Run Protocol

Before ANY bulk operation that produces, updates, or mutates inferred assets:

1. **Dry-run first** — always. No exceptions.
2. **Inspect output** on a small sample (≤ 3 records) before full execution.
3. **Verify idempotency** — re-running the same operation must not corrupt or duplicate.
4. **Log the dry-run output** (counts, sample diffs, expected vs actual) in the session.

### Anti-pattern (NEVER do this)
```
UPDATE port_guides SET "cleanedSections" = (...complex transform...) WHERE ...;
-- 500 rows affected
-- Oh no, data is corrupted. Re-run different SQL 8 more times.
-- Result: empty strings, stray newlines, lost Ollama-cleaned text.
```

### Correct pattern
```sql
-- Step 1: Dry-run on ONE row
SELECT "portSlug",
       "cleanedSections"->>'welcome' AS before,
       your_transform("cleanedSections"->>'welcome') AS after
FROM port_guides
WHERE "portSlug" = 'test-port';

-- Step 2: Human inspects before/after
-- Step 3: Only then, run on full set with RETURNING clause
UPDATE port_guides
SET "cleanedSections" = your_transform("cleanedSections")
WHERE "cleanedSections" IS NOT NULL
RETURNING "portSlug", length("cleanedSections"::text);
```

## 2. Asset Classification

| Asset type | Replacement cost | Protection level |
|------------|------------------|------------------|
| AI-generated text (Ollama/Claude/DeepSeek) | High — $$$ + API latency | **Immutable once approved**; version, don't overwrite |
| Embeddings / vector cache | Medium — recompute time | Dep-hash protected; never full recompute |
| Scraped raw data | Medium — re-scrape time | Preserve `rawSections`; clean into separate column |
| Precomputed insights (T1/T3/T5) | Very high — ~$144K / 3 weeks | Dep-hash protected; delta-only updates |
| PostgreSQL JSONB transforms | Low-Medium — but corruption cascades | Dry-run + sample verify + backup before bulk update |
| **Embedding indexes** | Low-Medium — ~2 hours + $0.05 | **Verify row-count parity after any DB restore/migration**; table can silently empty while cache corpus remains. **Never generate on production as a shortcut** — staging is the source of truth; production gets replicated from staging. **Gated rebuilds**: never rebuild inferred assets until upstream data (prompts, source corpus) is verified clean. **Embed from the right source**: if the source data (e.g., Ollama responses, port guides) is being regenerated to fix quality issues, the embedding rebuild must wait until the regeneration is complete — otherwise you embed the old/bad data. |
| Cache corpus without embeddings | Low — gradual degradation | Incremental generation on every cache write; health endpoint alerts when coverage < 95% |
## 3. Corruption Prevention Checklist

Before mutating inferred assets in bulk:

- [ ] Is there a `raw` / `source` column that is **untouched**?
- [ ] Did I run on 1 row first and inspect the result?
- [ ] Did I check for off-by-one errors in regex/replace?
- [ ] Did I verify empty-string results aren't accidental total wipes?
- [ ] Did I confirm the transform is idempotent (run twice = same result)?
- [ ] Is there a rollback plan (backup table, transaction, or source data)?

## 4. Recovery Rules

If corruption is detected:

1. **STOP immediately.** Do not "try another query" to fix it.
2. **Assess scope** — how many rows? Which columns?
3. **Restore from source** (`rawSections`, backup, re-scrape, re-infer) — never chain fix-up queries on corrupted data.
4. **Root-cause the transform** — why did it fail? Fix the logic, not the symptom.
5. **Re-dry-run the fix** on the restored data before applying.

## 5. Session Handoff Note

When a session ends with inferred assets in a **partial / dirty / corrupted** state:

- Document the exact state in the session summary.
- Flag which assets need re-generation vs. which are salvageable.
- Never leave the next session to discover corruption by accident.

## 6. Silent Degradation: When "Working" Means "Broken but Functional"

Some inferred assets degrade silently — the system keeps running, just more expensively or with lower quality. These are the most dangerous because there's no error to catch them.

### Embedding index drift
The `ai_chat_cache_embeddings` table can be empty while `ai_chat_response_cache` has 47K rows. Queries still work — they just fall through to more expensive tiers. No error is thrown.

**Detection:**
```bash
psql "$DATABASE_URL" -c "SELECT count(*) FROM ai_chat_response_cache;"
psql "$DATABASE_URL" -c "SELECT count(*) FROM ai_chat_cache_embeddings;"
```

**Rule:** After any DB restore, migration, or environment switch, verify inferred-asset tables have expected row counts. An empty embeddings table with a full cache is a silent failure mode.

**Rule — embed from verified source only:** If the source data is being regenerated (e.g., Ollama v4 rerun to purge poisoned prompts), the embedding rebuild must wait until regeneration completes. Embedding old/bad data defeats the purpose of the regeneration. The correct sequence is: (1) verify source is clean, (2) rebuild embeddings.

**Rule — staging is the source of truth, never production shortcuts:** The embedding index was once generated directly on production "as a shortcut" while staging remained empty. This creates a permanent mismatch: staging (the source of truth) has no index, production (the replica) has one that may be stale or lost on the next restore. Always generate inferred assets on staging first, then replicate to production via the standard sync mechanism (PG dump/restore, binary transfer, or pipeline replication). Never treat production as a shortcut for staging work.

### Cache corpus without embeddings
New cache entries from live synthesis don't auto-generate embeddings. Over weeks, the embedding index covers an ever-smaller fraction of the cache. Hit rate degrades gradually; no alert fires.

**Mitigation:**
1. **Build metadata table** — `ai_chat_embedding_builds` records every batch build with `startedAt`, `completedAt`, `rowCount`, `status`, `progressPercent`, `progressLabel`. This is the audit trail that catches silent loss.
2. **Fast gap detection** — add `hasEmbedding` boolean to the source table (`ai_chat_response_cache`) so `SELECT COUNT(*) WHERE hasEmbedding = false` finds gaps without joins.
3. **Health endpoint** — `GET /api/admin/ai-chat/embedding-health` returns `{ cacheRows, embeddingRows, coveragePct, isHealthy }`. Wire to alerting or admin dashboard.
4. **Incremental generation** — fire-and-forget embedding generation on every cache write. Never let the index drift again.
5. **Periodic full rebuild** — trigger via admin pipeline job with dry-run, pause/resume/cancel, and live progress reporting. Rebuild only after infrastructure (metadata + health + incremental) is in place.

**Reference:** See `references/embedding-infrastructure.md` for the full implementation pattern (schema, migration, API route, pipeline job registry, script rewrite, incremental hook).

### Source-data verification before embedding
Before any embedding build, verify the source corpus is the intended version. If the corpus has been or is being regenerated (e.g., Ollama v4 rewrite fixing poisoned prompts), embedding the old corpus produces a geometrically valid but semantically stale index. The index will match queries correctly but return outdated bodies.

**Correct sequence:**
1. Verify `source` column distribution (e.g., `source='ollama'` vs `source='template'`)
2. Confirm regeneration is complete (check `ai_chat_response_cache` timestamps or pipeline job status)
3. Only then trigger embedding rebuild

**Reference:** See `references/embedding-infrastructure.md` §"Source-data verification before embedding".

## 7. Hybrid Data Acquisition: Scraping + AI Synthesis

When expanding inferred assets (e.g., port guides), the cheapest path is usually:
1. **Scrape structured/raw data** from free sources (WhatsInPort, etc.) — zero AI cost
2. **Feed raw into Ollama** for cleanup/structuring — inference cost only for synthesis, not discovery
3. **Never use AI for discovery** when a scraper can do it — AI is for judgment, synthesis, and formatting

**Anti-pattern:** Using Ollama to "search the web" for port information. Ollama Cloud models have no built-in web search. They can only call functions you provide. Web search requires an external API (Brave, SerpAPI, etc.) + Ollama synthesis of results.

**Correct pattern:**
```typescript
// Step 1: Scrape or search (cheap)
const rawHtml = await scrapePortPage(portName); // or braveSearch(portName)

// Step 2: Extract structured data via Ollama (inference cost)
const structured = await ollama.chat([
  { role: 'system', content: 'Extract port guide sections from this HTML...' },
  { role: 'user', content: rawHtml },
]);

// Step 3: Store raw + structured separately
await prisma.port_guides.create({
  data: {
    portSlug,
    rawSections: rawHtml,        // immutable source
    cleanedSections: structured, // Ollama output
    ollamaModel: 'gemma4:31b-cloud',
  },
});
```

**Reference:** See `references/hybrid-data-acquisition.md` for multi-source scraping patterns, URL mapping strategies, Ollama and DeepSeek cleanup patterns, and the two-step AI web search architecture.

## 8. Taint Audit: Verify Data Is Actually Served Before Recomputing

When someone asks "is X tainted?" or "was this generated from bad data?", the instinct is to recompute everything. **Stop.** Before spending inference budget, trace the code path to determine if the data is even surfaced to users. Dead data — rows that exist in the DB but are never returned by any query — don't need recomputation regardless of their content.

### Taint audit checklist

1. **Identify all tables with the content type** — search for columns matching the content (narration, content, verdict, summary, etc.)
2. **Check prompt_version and computed_at** — correlate with known "bad" periods (e.g., before an axis reduction, before a prompt fix)
3. **Trace the code path** — find every consumer (API routes, AI Chat tools, frontend pages) and check:
   - What `WHERE` filters are applied? (personaId, season, status, etc.)
   - Do any filter values mismatch the actual data? (e.g., query filters by `personaId = 'couples'` but all rows have `persona_id = NULL`)
   - Are there fallback paths that silently return nothing?
4. **Cross-reference with intervention dates** — check if the table was truncated and recomputed after the "bad" period
5. **Classify each table:**
   - **Clean** — freshly recomputed after the bad period, served to users
   - **Dead** — not served (filter mismatch, orphaned rows, replaced by another table)
   - **Tainted** — served to users AND generated during the bad period → **this is the only category that needs recomputation**
6. **Only recomputed tainted tables.** Dead data can be truncated for hygiene but costs zero inference.

### Real example: corridor_insights (799K rows)

**Question:** "Are corridor narrations tainted by the old persona×season prompts?"

**Investigation:**
- `corridor_insights` had 799K rows with prompt_version `3.1.0` and computed_at in Apr–May 2026 (before axis reduction)
- Traced code path: `get-itinerary-insights.ts` queries `WHERE personaId = dbPersona`
- All 799K rows have `persona_id = NULL` — the query **always returns nothing**
- Meanwhile, `corridor_profiles` (1,307 rows) was computed from FalkorDB graph data (not from corridor_insights) and IS actively served
- **Classification:** corridor_insights = dead, corridor_profiles = clean, T7/T4/port_insights = clean (freshly recomputed)
- **Result:** 0 rows need recomputation. 799K dead rows can be truncated for hygiene.

### Key pitfall: "The query filter is always NULL"

A common dead-data pattern: the code queries `WHERE some_column = 'value'` but all rows have `some_column = NULL`. This is especially likely after an axis reduction where a column (like `persona_id`) was deprecated — old rows still have the column but it's never populated. The query silently returns empty results with no error. The data looks "live" (rows exist, timestamps are recent) but is functionally dead.

**Detection:** Run the actual consumer query against the table and check if it returns rows. If it returns 0 rows, the data is dead regardless of how many rows the table has.

### Key pitfall: "The query filter maps to a value that doesn't exist" (persona ID contract drift)

A variant of the NULL-filter pattern: the code queries `WHERE persona_id = 'group-multigen'` but all rows have `persona_id = 'family'`. The resolver's `personaMap` translates the UI ID (`families`) to a DB persona ID (`group-multigen`) that doesn't exist in the table. The query silently returns 0 rows. Unlike the NULL case, the data IS there — it's just behind a different key than the resolver expects.

**Detection:** Run `SELECT DISTINCT persona_id FROM <insight_table>` and compare against the values that the resolver's `personaMap` produces for each UI profile ID. If any mapped value is missing from the DB's distinct list, that persona silently returns null for every itinerary.

**Also check:** UI profiles that have no entry in `personaMap` at all (passthrough IDs) AND no matching DB rows. And UI profiles that exist as buttons but were never included in the generation pipeline's `ALL_PERSONA_IDS` list — these will never have DB rows regardless of mapping.

**Real example (2026-07-10):** 3 of 6 persona buttons on every sailing page silently returned null: `families` (mapped to `group-multigen`, DB has `family`), `adventure` (no mapping, no DB rows, never in generation grid), and `all` (expected — no persona-keyed insights for this ID). The `families` case is the most impactful: 22,595 T6 rows with `persona_id = 'family'` were invisible to the UI because the resolver asked for `group-multigen`.

See `dual-emit-llm-generation` skill → `references/persona-id-contract-audit.md` for the full diagnostic query set.

## 9. Identifier Migration Shield

When changing an identifier (hash, slug, foreign key) that downstream inference assets depend on, do NOT just update the identifier and hope. All assets keyed on the old identifier become orphans instantly. Instead, build a **migration shield**: a mapping table + resolver that lets consumers look up assets by either old or new identifier.

### When to use

- Changing a hash/signature algorithm
- Fixing an off-by-one error that changes which records get linked (e.g., matcher date range)
- Renormalizing a key that insights, SVGs, and AI-generated content reference
- Any change that would cause >5% of identifiers to shift

### The 5-step pattern

**1. Compute impact empirically.** Write a script that computes old vs new identifiers for ALL records, not a sample. Report:
- How many change (count + percentage)
- Whether any "stable" categories are affected (e.g., round-trips assumed safe but 12% actually change)
- How many downstream assets exist for the changing identifiers

Never assume categories are safe — test empirically. Grid-snapping, name matching, and rounding effects can break assumptions.

**2. Create a mapping table.** Store `old_identifier → new_identifier` pairs. Handle convergences where multiple old IDs map to the same new ID — the `new_identifier` column must NOT have a unique constraint. Use Prisma `@unique` on `old_identifier` only.

**3. Build a resolver utility.** Function that takes a new identifier, checks the mapping table, and returns the old identifier (or the input if no mapping exists). Use an LRU cache — the mapping set is finite and bounded. Batch variant for bulk lookups.

```typescript
// lib/route-corridors/resolve-signature.ts
const cache = new Map<string, string>(); // bounded LRU

export async function resolveSignature(newSig: string): Promise<string> {
  if (cache.has(newSig)) return cache.get(newSig)!;
  const mapping = await prisma.route_signature_map.findFirst({
    where: { newSignature: newSig },
  });
  const resolved = mapping?.oldSignature ?? newSig;
  if (cache.size > 10000) { const first = cache.keys().next().value!; cache.delete(first); }
  cache.set(newSig, resolved);
  return resolved;
}
```

**4. Wire into ALL consumers.** Search the codebase for every query against the identifier. Each consumer needs the resolver injected before the lookup. Common locations:
- API routes (tRPC procedures, REST endpoints)
- AI chat tool handlers
- Insight retrieval functions
- SVG/image generation endpoints
- Admin analytics queries

**5. Validate comprehensively.** After wiring, run a script that:
- Takes every new identifier from the mapping table
- Resolves it through the resolver
- Checks that a downstream asset exists at the resolved identifier
- Reports any gaps (0 gaps = success)

### Prisma migration pitfall

Prisma creates unique indexes (not constraints) via `CREATE UNIQUE INDEX`. To remove one, use `DROP INDEX`, not `ALTER TABLE DROP CONSTRAINT`:

```sql
-- ❌ Fails: "constraint does not exist"
ALTER TABLE route_signature_map DROP CONSTRAINT "route_signature_map_newSignature_key";

-- ✅ Correct
DROP INDEX "route_signature_map_newSignature_key";
```

This applies to any unique column constraint added via Prisma migration. Always check `\d+ tablename` to see whether it's an index or a constraint before writing DROP SQL.

### Real example: route signature migration (May 2026)

| Metric | Value |
|--------|-------|
| Active itineraries | 80,147 |
| Signatures changing | 17,826 (22%) |
| Distinct mapping pairs | 5,511 |
| Convergences (many old → one new) | 504 |
| Downstream consumers wired | 7 files, 9 call sites |
| Assets protected | ~18K corridors, ~18K SVGs, ~11K upgrade insights, ~2K seasonal profiles, ~98 ship-corridor insights |
| Validation result | 5,511/5,511 mappings resolve to assets — 0 gaps |

The resolver pattern avoided recomputing $144K+ worth of inference. The alternative (regenerate everything) would have taken weeks and significant API costs.

**⚠️ Dry-run correctness matters:** The initial dry-run simulated re-matching against `port_ship_visits.matchedItineraryId` — a column that is always NULL (matching lives in the junction table `port_visit_itineraries`). This falsely reported 99.5% of visits changing. The real impact was **additive only**: 0 existing junction rows changed, ~117K arrival-day visits needed to be added. Always verify your assumptions about which columns are populated before building simulations. Query `COUNT(column)` vs `COUNT(*)` to check if a column is actually used.

**⚠️ Impact analysis must match the actual mechanism:** The first analysis assumed only arrival ports would be affected, giving 5,511 changed signatures. Then a flawed dry-run reported 99.5% of all matches changing (324K/325K). Both were wrong in opposite directions. The correct approach: (1) determine whether the fix is additive or mutating, (2) measure against the actual data structure (junction table, not `matchedItineraryId`), (3) count precisely — each itinerary has at most one arrival port, so the ceiling is the number of itineraries, not a JOIN that multiplies.

**Topology cascade awareness:** A change that affects base data (e.g., port lists for itineraries) does NOT stop at the identifier level. It cascades through the entire derived data tree: signatures → corridors → families → clans → regions → deployments → repositioning events → ALL insights at every level → ALL FalkorDB projections → ALL SVGs. The migration shield protects asset *lookups* during transition, but the downstream recomputation still needs to happen. **Plan the full cascade before starting.** See `port-visit-matching` skill → "Topology cascade" pitfall for the complete dependency tree and 15-step rebuild order.

**SVGs: clear ALL when base data changes.** When route data changes, ALL route map SVGs are potentially stale — not just those whose signatures changed. Don't cherry-pick. SVGs are cheap to regenerate; selective deletion is error-prone and risks leaving stale maps. The user explicitly corrected this: "let's drop all the svg mini-maps and detail maps. it's better to recompute them."

**⚠️ Dep-hash NULL after topology rebuild causes full recompute:** When the topology (corridors, families, clans) is rebuilt, `corridor_dep_hashes.full_hash` gets set to NULL for all existing corridors. The delta detection logic (`getChangedCorridorIds` in `delta-utils.ts`) compares `full_hash IS DISTINCT FROM MD5(...)` — NULL is always distinct, so ALL corridors get flagged as changed, triggering a full recomputation of insights worth $144K+. **Fix:** After any topology rebuild, re-seed `full_hash` from current corridor data:
```sql
UPDATE corridor_dep_hashes dh
SET full_hash = MD5(COALESCE(CAST(rc.signature AS TEXT), '') || '|' || /* ...all 33 columns... */)
FROM route_corridors rc
WHERE dh.corridor_id = rc.id;
```
Only AFTER reseeding hashes should you run insight precompute jobs. Without this, the delta layer is blind and will try to recompute everything.

**⚠️ Delta detection reads the correct output table:** After the T1+T3+T5 consolidation into `corridor_profiles`, the delta detection in `getLastDeltaRun()` must query `corridor_profiles` (the new table), not `corridor_insights` (the old deprecated table). If the old table is empty (0 rows), `since = null` triggers a first-run full recomputation. Always verify the delta query targets the actual output table that holds computed insights.

**⚠️ Check what's already there BEFORE proposing any recompute or sync:** The instinct after finding a delta bug is "recompute everything" or "sync from production." **Stop.** Before proposing either, check actual row counts on BOTH environments. If staging already has the same data (identical counts, matching corridor IDs), neither action is needed — only the delta detection logic needs fixing. Proposing unnecessary work wastes the user's time and signals that you treat insights as disposable.

**Pre-flight checklist before any insight recomputation:**
1. `SELECT COUNT(*) FROM <output_table>` on staging — is the data already there?
2. `SELECT COUNT(*) FROM <output_table>` on production — same counts?
3. Compare corridor IDs: `SELECT signature, id FROM route_corridors ORDER BY signature` on both — do shared corridors have matching IDs?
4. Only if data is genuinely missing or stale should you propose recomputation or sync.
5. If data exists but delta detection is broken, fix the detection logic (dep hashes, table name references) — don't recompute.
6. **Never propose "sync from production" or "recompute" when staging already has the data.** This treats insights as disposable. The user has been explicit: "insights are not disposable, they cost money to generate" and "you are treating insights like a disposable asset." If delta detection was broken but the data survived, the fix is the delta logic — not a data operation.

**Table-rename completeness check:** After fixing a stale table reference in one file, grep ALL files for the old table name. A fix to `delta-utils.ts` that misses `precompute-corridor-insights.ts` (which hardcodes the table name in a `getLastDeltaRun()` call) leaves the bug half-fixed. The utility returns correct results for its own queries, but the caller still queries the empty old table and triggers a full recompute. Use:
```bash
grep -rn "old_table_name" scripts/ --include="*.ts" | grep -v "unrelated_tables\|node_modules"
```
The fix is not complete until this returns 0 hits for the old table name.

**Real example (2026-05-22):** After fixing dep hashes and the `corridor_insights` → `corridor_profiles` table reference in delta-utils, the agent proposed syncing production insights to staging. Both environments already had identical counts (18,158 corridor_profiles, 33,502 upgrade insights, etc.). The user had to point out: "if the data is still on staging we don't need to sync." The correct action was only the code fix — the data was never lost.

**Status:** Fix deployed to both `staging` and `scraper` branches (May 22 2026). All 3 phases executed:
- Phase 1: 116,671 arrival-day junction rows added (INSERT-only, zero existing rows touched)
- Phase 2: 24,167 of 117K signatures changed; 92,490 unchanged (79% of arrival ports land in same 1° grid bucket)
- Phase 3: 5,654 total signature map entries (362 new pairs added)
- SVGs: ALL 18,576 SVG rows cleared for on-demand regeneration (not cherry-picked)

Resolver active on staging — all new signature lookups transparently find old assets. **The fix was additive, not a full rebuild.** The user explicitly rejected the destructive approach (`--rematch` which deletes 1.2M rows) in favor of INSERT-only junction rows. When a fix is additive, the impact ceiling is the number of new records, not a JOIN that multiplies.

### Measured phased execution

When the user says "measured way" or "one step at a time" for a multi-phase operation on inference assets:

1. **Add phase control to the script** — `--phase=N` flag so each phase runs independently
2. **Execute Phase N live**, then **dry-run Phase N+1** before proceeding
3. **Report results after each step** — counts, what changed, what didn't
4. **Never chain phases automatically** — wait for user approval between each

Example flow:
```
Step 1: script --phase=1            → LIVE (add junction rows)
Step 2: script --phase=2 --dry-run  → preview signature changes
Step 3: (user approves)
Step 4: script --phase=2            → LIVE (recompute signatures + update map)
```

This prevents cascading failures where a flawed Phase 1 silently corrupts Phase 2's input.

### Additive over destructive for data migrations

When a bug fix affects how records are linked (e.g., expanding a date range to include an arrival day), the first instinct is often "rebuild everything" (`--rematch`, `TRUNCATE + recompute`, full regeneration). **This is almost always wrong for inference assets.** The correct approach is additive:

1. **INSERT only** — add the rows that were missing (e.g., arrival-day junction rows). Use `ON CONFLICT DO NOTHING` to guarantee idempotency.
2. **Measure delta** — count how many existing records actually change vs how many stay the same. Often 80%+ are unaffected because the change is orthogonal to existing data (e.g., arrival ports land in the same grid bucket as nearby ports already captured).
3. **Update the mapping layer** — if identifiers shift, extend the mapping table with new pairs. Never recompute from scratch.
4. **Regenerate only stale assets** — delete and rebuild only the assets whose inputs actually changed. The mapping layer protects the rest.

**Why additive wins:** A destructive rebuild of 1.2M junction rows takes 30-45 minutes and requires the matcher to re-process everything. An additive INSERT of 117K new rows takes seconds and risks zero data loss. The user explicitly enforces this preference — if you propose a destructive rebuild, expect correction.

## 10. AI Web Search Architecture: Two-Step Pattern

No major inference provider (Ollama Cloud, DeepSeek, Kimi, MiniMax) offers built-in web search. All require a **two-step pipeline**:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Search Layer   │────▶│  LLM Synthesis   │────▶│  Structured     │
│  (Brave/Serp)   │     │  (DeepSeek/      │     │  Output         │
│                 │     │   Ollama)        │     │  (JSONB)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Step 1: Search (External API)
- **Brave Search API**: ~$0.003/query, high quality, privacy-focused
- **SerpAPI**: ~$0.005/query, Google results, rich metadata
- **Google Custom Search**: $5/1000 queries, programmable

### Step 2: Synthesis (LLM)
Feed search results into the LLM with an extraction prompt. The LLM does NOT browse — it structures and synthesizes pre-fetched content.

**DeepSeek-v4-flash** (user's preferred model for this task):
- Supports OpenAI-compatible tool calls (`tools` parameter)
- Can orchestrate multi-step research by emitting function calls
- **Cannot search the web directly** — tool calls invoke functions YOU provide
- Use `base_url="https://api.deepseek.com"` with OpenAI SDK

**Example: DeepSeek with search tool:**
```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY,
  baseURL: 'https://api.deepseek.com',
});

const tools = [{
  type: 'function',
  function: {
    name: 'web_search',
    description: 'Search the web for cruise port information',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query' },
      },
      required: ['query'],
      additionalProperties: false,
    },
  },
}];

// DeepSeek decides to call web_search, your code executes it,
// then you feed results back for synthesis
const response = await client.chat.completions.create({
  model: 'deepseek-v4-flash',
  messages: [
    { role: 'system', content: 'You are a cruise port research assistant. Use web_search to find information, then synthesize structured port guides.' },
    { role: 'user', content: 'Create a port guide for Budapest' },
  ],
  tools,
});
```

### Provider Web Search Capability Matrix (May 2026)

| Provider | Built-in Search? | Tool Calling? | Correct Pattern |
|----------|-----------------|---------------|-----------------|
| **Ollama Cloud** (all 39 models) | ❌ No | ✅ `llama3-groq-tool-use` only | Search API → Ollama synthesis |
| **DeepSeek** (v4-flash, v4-pro) | ❌ No | ✅ OpenAI-compatible | Search API → DeepSeek synthesis |
| **Kimi** (k2.5, k2.6) | ❌ No | ❌ No | Search API → Kimi synthesis |
| **MiniMax** (m2, m2.5) | ❌ No | ❌ No | Search API → MiniMax synthesis |
| **OpenAI** (GPT-4o) | ✅ Yes (Browse) | ✅ Yes | Direct or Search API → GPT-4o |
| **Anthropic** (Claude) | ✅ Yes (via API) | ✅ Yes | Direct or Search API → Claude |
| **Perplexity** (r1-1776) | ❌ No* | ❌ No | *Perplexity API has search, but Ollama-hosted `r1-1776` does not |

**Key insight:** The only providers with native web search are OpenAI and Anthropic (and Perplexity's own API). All others require the two-step pattern.

### Cost-Optimized Model Selection

For the synthesis step, match model to task:
- **DeepSeek-v4-flash**: Fast, cheap, good for structured extraction from search results
- **Ollama Cloud (gemma4:31b)**: Flat-rate, good for bulk processing when volume is high
- **DeepSeek-v4-pro**: Higher quality, use when extraction accuracy is critical

**Never use AI for discovery** — always use a search API or scraper first. AI is for judgment, synthesis, and formatting.

**Reference:** See `references/hybrid-data-acquisition.md` for complete implementation patterns, prompt templates, and the WhatsInPort + DeepSeek two-source strategy.

---

> **Remember:** A single untested `UPDATE` on 500 rows can destroy hours of inference work. A 30-second dry-run saves hours of recovery.

> **Periodic audit reminder:** §23 introduces the four-failure-mode framework for auditing insight tables (T1–T7). The full SQL template with the 2026-07-13 T1–T7 audit findings lives at `references/insight-staleness-audit.md`. Run after every monthly pipeline, before each Phase-2 LLM campaign, and on user request.

## 23. Insight Table Staleness Audit (T1–T7)

Even after a single round of deprecation (e.g., the 2026-07-11 T6 cleanup), other insight tables may have the **same staleness pattern** but were not touched. A periodic audit surfaces orphan-FK rows, prompt-version rot, coverage gaps, and dead tables — across the entire insight taxonomy.

This audit was run 2026-07-13 on staging and surfaced three new plans (corridor_profiles orphan cleanup + 486 corridor gap-fill, corridor_upgrade_insights 1.1.0→1.2.0 refresh across 3 definitions, corridor_seasonal_profiles coverage-fill of 13,238 missing cells). Same root cause, same fix pattern as T6 — but unknown until the audit ran.

### The four-failure-mode framework

When auditing any insight table (T1–T7 plus adjacent derived tables), classify each by which failure modes are present. **A table can have 0–4 modes simultaneously.**

| Failure mode | Diagnostic | Indicator |
|---|---|---|
| **A. Orphan FK rows** | `WHERE <fk> NOT IN (SELECT id FROM <anchor_table>)` count > 5% | Stale rows pointing at deleted corridors / lines / families. Same root cause as T6 Phase-1 era. |
| **B. Prompt version rot** | `DISTINCT prompt_version` count > 1, OR oldest version <90 days old AND most rows are old version | `personas@1.1.0` rows coexisting with `1.2.0` rows, or all rows at `1.1.0` from a stale pipeline run. |
| **C. Coverage gap** | `SELECT <anchor> WHERE <fk> NOT IN (SELECT <fk> FROM <insight>)` count > 10% of anchors | Anchor exists in PG but no insight row exists. Different from orphans — these are anchors in the current world. |
| **D. Dead table** | No consumers reference the table in code (`grep -r`), OR `prompt_version` traces to a pre-consolidation era | Old replaced tables that haven't been physically dropped. Example: `corridor_insights` (legacy T1/T3/T5) is "dead" — superseded by `corridor_profiles`. |

### Audit script template

Place at `templates/audit-insights-t1-t7.sql` (see reference file). Run from staging (NOT production), pattern:

```sql
-- Per-table audit block. Repeat for each insight table.
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE <fk_col> IN (SELECT id FROM <anchor>)) AS valid,
  count(*) FILTER (WHERE <fk_col> NOT IN (SELECT id FROM <anchor>)) AS orphan,
  round(100.0 * count(*) FILTER (WHERE <fk_col> IN (SELECT id FROM <anchor>)) / count(*), 1) AS pct_valid,
  count(*) FILTER (WHERE deprecated_at IS NULL) AS active,
  count(*) FILTER (WHERE deprecated_at IS NOT NULL) AS deprecated
FROM <insight_table>;
```

Output parsing rules:
- **pct_valid < 80%** → Mode A present. Defer Phase-1 deprecation plan.
- **pct_valid 80–100% AND active < total - deprecated** → Mode A already partially cleaned.
- **pct_valid 100% AND active = total** → mostly clean; check Modes B + C.
- **All four counts near zero** → Mode D (dead). Consider TRUNCATE.

### Schema gotchas discovered 2026-07-13

These broke the first audit run. They will break yours if you forget them:

1. **`family_topology` PK is `family_id` (TEXT), NOT `id`.** The PK column is `family_id String @id @map("family_id")` (line 2781 of `prisma/schema.prisma`). All audit joins must use `ON ft.family_id = cfi.family_id`. The values are MD5-shaped hex strings (`caba8bf875dfd06de63bbc0e67c38165`), not UUIDs.

2. **`corridor_family_insights.family_id` references DIFFERENT tables per `family_grouping` value:**
   - `family_grouping='family'` or `'super_family'` → `family_topology.family_id`
   - `family_grouping='region'` → `regions.id` (UUID) OR region slug (e.g., `arabian-gulf-region-a4ab790c`). Heterogeneous encoding — some rows have UUIDs, some have slugs.
   - `family_grouping='clan'` → unknown FK target at audit time (not `route_clans.slug`, not `family_topology`). The 57 clan rows had zero valid refs against likely candidates. **Investigate before any cleanup.**

3. **T7 (`cruise_line_insights`) covers all 49 active cruise lines, zero orphans, zero inactive lines covered.** T7 is the model citizen — no audit action needed.

4. **`corridor_insights` (LEGACY T1/T3/T5) had `deprecated_at IS NULL` on 6,600 rows in 2026-07-13** — STATE-SNAPSHOT.md claims "TRUNCATED" but the table still has rows. **Don't trust doc-state vs DB-state without checking.** The 6,600 legacy rows coexist with the new `corridor_profiles` 24,627 rows.

5. **`corridor_dep_hashes` orphan corridors = `corridor_profiles` orphan corridors** — same set, 10,495 IDs, 100% overlap. Both share the same `corridor_id FK → route_corridors.id` reference, so they decay together. Fixing one without checking the other will leave the platform half-clean.

### Recommended sequencing per audit

When audit reveals Modes A + C simultaneously:

1. **Phase 1 — deprecation**: `UPDATE <insight> SET deprecated_at = NOW() WHERE <fk> NOT IN (SELECT id FROM <anchor>)`. Dry-run first, `--confirm` after. Mirror `deprecate-stale-t6.ts` exactly.
2. **Phase 2 — replacement**: identify what the new data should look like (recompute with current prompt version, or coverage-fill for missing anchors). ONLY after Phase 1 is verified.
3. **Order**: do `corridor_profiles` first (referenced by T2, T4, T7). Then `corridor_upgrade_insights`. Then coverage-fill tables (`corridor_value_density`, `corridor_seasonal_profiles`).
4. **Per user's 2026-07-11 rule**: "we never delete data until we have a proper replacement." Production deprecation runs only AFTER Phase 2 is verified on staging.

### Reference SQL template

The full audit script with all 7 tables + cross-table classification blocks lives at `references/insight-staleness-audit.md` (template form). Copy, adjust table/column names for new insight domains, re-run.

---

## 22. Race-Prone DELETE+INSERT Upsert Patterns in Concurrent Batched Inference

When running an LLM precompute script with concurrency > 1 across many ship × corridor × persona × season cells, the **upsert primitive matters more than the model choice**. A `DELETE FROM ... INSERT INTO ...` transaction — which looks correct in isolation — has a **race condition** that surfaces only at concurrency and produces a `Key (..., ...) already exists` storm on the unique constraint.

### The bug pattern (canonical example: T6 ship_corridor_insights)

`scripts/insights/precompute-ship-corridor-insights.ts:386` historically used:

```typescript
async function upsertT6(prisma, cell, narration, ...) {
  await prisma.$transaction([
    prisma.$executeRaw`DELETE FROM ship_corridor_insights WHERE ship_id=${...} AND corridor_id=${...} AND persona_id=${...} AND season=${...}::"InsightSeason"`,
    prisma.$executeRaw`INSERT INTO ship_corridor_insights (...) VALUES (...)`,
  ]);
}
```

When two concurrent workers target the **same `(ship_id, corridor_id, persona_id, season)` cell** (which happens whenever the campaign iterates over `(ship, corridor, season)` and `(corridor, ship, season)` overlapping grids, or when retrying after a transient failure), both transactions:

1. DELETE the row (or find nothing) — succeeds
2. INSERT a new row — both succeed at the application level
3. **One INSERT collides on the unique constraint** → `Key (...) already exists` (PG `23505`)
4. The other worker's INSERT may or may not have committed yet, depending on transaction isolation

The error message is misleading: it says "already exists" as if the row is stale, but it's actually a **race** between two concurrent INSERTs targeting the same cell.

### Real reproduction (2026-07-11, T6 Phase 2 campaign)

```
Raw query failed. Code: `23505`. Message: `Key (ship_id, corridor_id, persona_id)=(117b2542-..., c44ec2cc-..., family) already exists.`
[repeated 20+ times for adjacent corridors on the same ship]
Error: read ECONNRESET  ← FalkorDB socket died during crash
```

The campaign log (`scripts/insights/runs/20260711-1302-t6-phase2-campaign.log`, 272K) hit this storm on ship `117b2542…` (the saga ship) and then died with a `FalkorDB ECONNRESET` from unclosed sockets (related to the `closeFalkorDB()` rule).

### Three correct upsert patterns (pick one)

**Pattern A — `INSERT ... ON CONFLICT DO UPDATE`** (Postgres-native, idempotent, recommended):

```sql
INSERT INTO ship_corridor_insights (id, ship_id, corridor_id, persona_id, season, narration, ...)
VALUES (gen_random_uuid(), $1, $2, $3, $4::"InsightSeason", $5, ...)
ON CONFLICT (ship_id, corridor_id, persona_id, season)
DO UPDATE SET
  narration = EXCLUDED.narration,
  model_id = EXCLUDED.model_id,
  prompt_version = EXCLUDED.prompt_version,
  computed_at = NOW(),
  tokens_in = EXCLUDED.tokens_in,
  tokens_out = EXCLUDED.tokens_out,
  latency_ms = EXCLUDED.latency_ms,
  joint_fit_verdict = EXCLUDED.joint_fit_verdict,
  reinforcement_axes = EXCLUDED.reinforcement_axes,
  friction_axes = EXCLUDED.friction_axes,
  honest_mismatch = EXCLUDED.honest_mismatch
```

Single statement, atomic, no race. The DO UPDATE lets newer generations overwrite older ones naturally.

**Pattern B — `INSERT ... ON CONFLICT DO NOTHING`** (when you want first-write-wins semantics):

```sql
INSERT INTO ship_corridor_insights (...) VALUES (...) ON CONFLICT DO NOTHING
```

Cheaper than DO UPDATE, but means a re-run with new narration won't replace the old row. Only appropriate when you're sure you never want to overwrite.

**Pattern C — Per-cell advisory lock** (when you need to keep the DELETE+INSERT semantics):

```sql
BEGIN;
SELECT pg_advisory_xact_lock(hashtext($ship_id || $corridor_id || $persona_id || $season));
DELETE FROM ship_corridor_insights WHERE ...;
INSERT INTO ship_corridor_insights (...) VALUES (...);
COMMIT;
```

The advisory lock serializes workers targeting the same cell. Heavier than ON CONFLICT but preserves the "delete stale, insert fresh" intent.

### Detection: how to recognize this bug class in a campaign log

1. **Repeated `Key (col1, col2, ...) already exists` errors** with PG code `23505` and `Prisma.$executeRaw` invocations — that's a uniqueness violation, not a malformed query.
2. **All errors reference the same prefix** of the composite key (e.g., same ship_id, same persona_id) — that's the race window.
3. **Errors come in bursts** (10-50 in a row), not scattered — workers race in waves.
4. **Often followed by an unrelated socket error** (FalkorDB ECONNRESET, Redis disconnect) — the crash tears down other connections.

### Investigation: confirm the upsert is the actual root cause

```bash
# 1. Find the upsert function
grep -rn "DELETE FROM.*INSERT INTO\|\\\$transaction.*executeRaw" scripts/insights/ --include="*.ts"

# 2. For each one, check if it uses ON CONFLICT
grep -A5 "INSERT INTO" scripts/insights/precompute-*.ts | grep -c "ON CONFLICT"

# 3. Check the unique constraint that fired
# From the error message: "Key (col1, col2, col3)=(val1, val2, val3) already exists"
# The columns named in the error ARE the unique constraint columns.
# Confirm by querying PG:
psql "$STAGING_DB" -c "\\d ship_corridor_insights"  # look for UNIQUE constraints
```

### Fix priority

| Table | Upsert pattern | Fix urgency |
|---|---|---|
| `ship_corridor_insights` (T6) | DELETE+INSERT in `scripts/insights/precompute-ship-corridor-insights.ts:386` | High — Phase 2 campaign crashed on it |
| `cruise_line_insights` (T7) | Similar pattern likely | Audit before next T7 backfill |
| `corridor_upgrade_insights` (T2) | Already uses ON CONFLICT (line 724) | None |
| `corridor_family_insights` (T4) | Verify before next backfill | Audit |

### Companion rule — close FalkorDB before process.exit()

When the upsert bug triggers an unrecoverable crash and the script calls `process.exit()`, **the FalkorDB socket stays open** and the Node event loop keeps the process alive. The `ECONNRESET` that appears at the end of the campaign log is the symptom.

**Fix:** `await closeFalkorDB()` (or `falkordb.quit()`) before any `process.exit()` call. Already a project hard rule (memory importance 0.95), but worth restating here because this is the exact crash mode that surfaces it.

### Reference

- Real crash transcript: `scripts/insights/runs/20260711-1302-t6-phase2-campaign.log` (272K, line 1 onward shows the `23505` storm)
- Fixed scraper-worker path that already uses `ON CONFLICT DO NOTHING`: `scraper-worker/src/tasks/precompute-corridor-insights.ts:753` (uses the bulk-insert form) and `:1529` (single-row variant)
- Related: "Never Kill a Running Inference Job by Deploying" (§11) — same crash, different trigger

## 21. Provider Error Messages Often Misdiagnose Concurrency-Related Failures

When an LLM provider returns non-obvious errors during a bulk run (HTTP 429s, "Too many requests", "insufficient_balance", empty content), the obvious reading is usually wrong. Before assuming a model-level problem (rate limit hit, empty output, content moderation), **check what the endpoint actually rate-limits and at what concurrency**.

The easy trap is to read the error message literally:
- HTTP 429 "Too many requests / type: limitation" → assume the account is exhausted
- Empty content under concurrent load → assume the model is broken
- 401/402 on first call → assume the API key is bad

In practice, these error types can have very different root causes:

- **HTTP 429** is the most common rate-limit signal, but its concrete meaning varies by provider. Some providers rate-limit per-account regardless of how many requests your code sends in parallel. Others rate-limit per-concurrent-request above a threshold (e.g., concurrency ≥ 20). The fix differs: account-level 429s mean wait for the window to refresh; per-concurrent 429s mean lower your `--concurrency` flag.
- **Empty content under concurrent load** is often a downstream symptom of 429 (the retry path returns `""` instead of throwing), not a model-output problem. Before assuming the model is broken, check the raw HTTP status on the failed calls.
- **HTTP 401/402 with a `tp-` prefix key** at `api.xiaomimimo.com/v1` is an endpoint-routing problem — the token-plan endpoint is at `token-plan-sgp.xiaomimimo.com/v1`. The key works fine at the right URL. Fix the URL, not the key.

### Pre-flight for any new provider / endpoint combination

Before committing a long-running metered job to a new provider, run a small probe:

1. **Send 5 sequential requests at concurrency=1** to confirm the endpoint, auth, and response shape. If any fails, fix before scaling.
2. **Send 10 parallel requests at concurrency=5, 10, 15, 20** and watch for HTTP 429s. Identify the threshold where the provider starts throttling. Document it.
3. **Check the rate-limit response shape** — does the provider return a `Retry-After` header? An explicit quota exhaustion message? A vague "Too many requests"? The response shape determines whether you should retry with backoff, lower concurrency, or stop the run entirely.
4. **Compare p50 latency at concurrency=1 vs concurrency=20.** A 2×+ latency jump without 429s is a soft throttle — the provider is processing requests but rate-limiting throughput.

### Concrete lessons from the 2026-07-10 T6 backfill (recorded for future provider switches)

| Provider | Concurrency that produces 0 errors | Concurrency that produces 429s | Latency ratio (vs concurrency=1) |
|---|---|---|---|
| DeepSeek `deepseek-v4-flash` | 15 (zero failures across 7,000-cell run) | Unknown; never tested ≥20 | p50 9.4s, p95 17-21s |
| Xiaomi MiMo `xiaomi/mimo-v2.5` (token-plan endpoint) | ≤10 | 20 (624 × 429s observed) | p50 22.6s, p95 35.7s — 2.4× slower than DeepSeek |
| Ollama Cloud `gemma4:31b-cloud` (Pro tier) | 3 (account-wide cap) | N/A — 3 is the hard ceiling | p50 ~7s sustained |

The lesson: **don't diagnose the model from the error message.** The 1844 run produced 2,765 successful MiMo rows AND 624 × 429s simultaneously — meaning some requests succeeded while others throttled. A naive "MiMo is broken" diagnosis would have been wrong; the real diagnosis was "MiMo's token-plan endpoint rate-limits at concurrency ≥ 20."

When switching providers, **also re-test concurrency thresholds**. Don't assume the new provider shares limits with the old one. Each combination of provider + endpoint + key-prefix has its own throttle profile.

---

## 20. Stop Forensics the Moment You Know a Run Is a Write-Off — the User Knows Before You Do

When investigating a "failed" metered-scrape run (failed = rows didn't reach the downstream consumer), there is a natural temptation to keep digging: characterizing the failure pattern, quantifying the credit burn, measuring the 87% match rate of the bridge, designing the recovery chain. **Each of these is informative but expensive in session time.** The user often already knows the run was a write-off before you finish your forensics.

**Signals you are over-investigating a write-off:**

- The user says "this was a massive waste of time and money for me" or "I'm not spending another $100 on this" — **the budget question is closed.** Stop proposing forensic work or recovery paths that cost more.
- The user says "we will just have to trust on the [existing path], but I don't know if we actually got rid of it" — **the user is asking you to verify infrastructure integrity, not build a new pipeline.** Switch from "design a recovery" to "verify the existing path still works."
- The user says "this is correct, but I want to know X" — **the user has already accepted the situation and is asking a follow-up.** Don't relitigate whether the run was a failure.

**The correct stopping point:** Once you have a single piece of evidence that proves the run's output cannot reach the downstream consumer (e.g., the join column is NULL on every row, and the consumer's WHERE clause keys on that column), report that ONE fact and ask the user how they want to proceed. Do not also run the credit-burn analysis, the per-tier failure breakdown, and the bucket-by-bucket diff. That's three more pieces of evidence the user doesn't need to make their decision.

**Real example (2026-06-26):** A ScrapingBee scrape produced 222K rows with `matchedShipId = NULL` on every row. After the first DB query confirmed that fact, the right response was: "The scraper output cannot reach the corridor pipeline. Do you want to (a) drop the rows and fix the scraper, (b) write a one-shot backfill, (c) leave them and trust Playwright?" Instead, the session kept going through hourly-failure analysis, credit-burn quantification, audit-trail examination, name-match rate estimation, and three more diagnostic queries. The user interrupted at minute ~45 with "this was a massive waste of time and money for me." The decision-relevant fact was visible at minute ~5.

**Corollary — also true for inference jobs:** When a long-running LLM precompute has run for an hour and produced suspicious results (0 cells, mismatched counts, drifted category distributions), the temptation is to keep it running "to see what happens." **Stop the job and investigate.** Every minute it runs is a minute of API cost you can't get back. A 1-hour stop-and-investigate cycle is cheaper than a 6-hour "let it finish and see."

**The asymmetry principle applied to investigation:** The marginal value of each additional piece of forensic evidence is small (the decision rarely changes after the first 1-2 findings). The marginal cost of each additional query is real session time and possibly real money. Stop early, surface the decision-relevant facts, ask. Don't build a museum of evidence the user didn't ask for.

**Reference:** See `references/scrapingbee-port-run-2026-06.md` for the full session data — hourly success pattern, credit burn breakdown, the exact wiring gap in the upsert block, the recovery bridge results (195K matched, 846K junctions), and the 5-step chain that took the stranded data to fresh `route_corridors` rows. **The bridge script that rescued the data was `scripts/scraper-service/match-ports-to-itineraries.ts` — load the `port-visit-matching` skill (or its references) to see the full recovery procedure. The 5-minute bridge was the difference between "data is stranded forever" and "data is back in the pipeline" — when in doubt, check if a bridge exists before concluding the data is lost.**

---

## 19. Verify the Join Key on Both Sides Before Trusting a New Scraper to Feed the Pipeline

The 18.x cost-ceiling check is necessary but not sufficient. A scraper can run cheaply *and* produce data that can never reach the downstream consumer because the join key is missing on the producer side. **"It scraped successfully" is not the same as "the pipeline can use it."**

**Real example (2026-06-19 ScrapingBee port-schedule run):**

| Metric | Value |
|--------|-------|
| Snapshots written | 117,284 |
| `port_ship_visits` rows written | 222,816 |
| `matchStatus` after the run | 222,816 × `pending` |
| `matchedShipId` populated | **0** (the column the matcher keys on) |
| Rows that could reach the corridor pipeline | **0** |

The scraper's upsert block was correct (it wrote what CruiseMapper returned) but did not include `matchedShipId` in the INSERT column list. The bridge script (`scripts/scraper-service/match-ports-to-itineraries.ts`) keys on `matchedShipId` and falls back to a `shipName` lookup, so the rows were eventually recoverable — but only by running the bridge explicitly. Without that fallback, the entire 6-day run would have been write-off data.

### Mandatory pre-flight for any new scraper that feeds a multi-step pipeline

1. **Trace the join key.** Open the downstream consumer script (the matcher, the merger, the enricher) and find the WHERE clause that links the scraper's output to its input. That's the column the scraper MUST populate. Read it explicitly; don't infer.

2. **Read the scraper's upsert column list.** The columns named in the `INSERT ... VALUES ...` block are the columns the scraper will ever write. Anything not listed will be NULL forever (or until a separate bridge runs).

3. **Check for a fallback path on the consumer side.** Some consumers fall back from `matchedShipId` to `shipName` (this codebase's `scripts/scraper-service/match-ports-to-itineraries.ts` does this via two chains: exact match against `ships.name`, then `ship_aliases`) or `external_id` to `name` (others). If no fallback exists, the scraper's output is single-use: it works only if the scraper wrote the exact join column. If a fallback exists, the rows are still stranded until the fallback path is run.

    **How to verify a fallback exists for a consumer you haven't read:** search for the join column name in the consumer's source. If the consumer reads from `<column>` AND falls back to `<other_column>` via an `if (!value)` branch or a `?? null` lookup, the fallback is real. If the consumer's WHERE clause or `.find()` directly references the join column with no fallback, the data IS stranded. Don't assume the fallback exists — read the source.

    **Common false-positive in "is data stranded?" diagnostics:** A query like `WHERE matchedShipId IS NOT NULL` returns 0 rows for stranded data — leading to "data is unrecoverable" conclusions. But the consumer may have a fallback path that doesn't require the join column. The check order matters:
    1. Read the consumer's source for the join column
    2. Identify whether the consumer reads `<column>` directly OR falls back to a derived value
    3. If a fallback exists, run the fallback path before declaring the data lost
    4. If no fallback exists, then declare the data stranded

    The two-minute read of the consumer script is the difference between "data is stranded forever" and "data is recoverable in 5 minutes."

4. **Run the bridge BEFORE declaring the run a success.** "Producer correct" + "bridge not run" = "data is stranded." A scraper run report that says "X rows written" without confirming "X rows matchable" is incomplete.

5. **For HTML extractors that use `extract_rules`, expect zero HTML in the audit trail.** ScrapingBee (and similar) returns only the extracted keys at the top level when `extract_rules` is set; the full HTML is not in the response and the `data.html` field is null. If you need ship IDs from the HTML (because they're not in the extracted fields), `extract_rules` won't get you there — fetch raw HTML separately or scrape ship IDs via a different selector.

### The four validation gates for a scraper run report

A scraper run is **not successful** unless all four pass:

1. **Producer-side** — exit code 0, error rate <5%, expected row count reached
2. **Audit trail** — snapshot table populated, raw JSON captured, key columns present
3. **Consumer-side** — join keys populated OR a fallback bridge has run and bridged the rows
4. **Cost** — credits used within budget, failure rate didn't indicate credit exhaustion

In the ScrapingBee example, gates 1, 2, and 4 passed; gate 3 failed silently. The user caught it by asking the "how is it that they are going to be matched?" question before I had verified gate 3 myself.

**Anti-pattern:** Reading the scraper's `INSERT INTO ... VALUES ...` block, seeing the column list, and not cross-referencing against the downstream consumer's join column. The data shape is in front of you; you have to compare it to the consumer shape, not just acknowledge it.

---

## 18. Verify the Cost Ceiling and Budget Burn Rate Before Long-Running Metered Jobs

A scraper or inference job that runs unattended for days on a metered service (ScrapingBee, Ollama Cloud, OpenAI, Anthropic) is a financial liability, not just a technical one. Every minute the job runs without a budget guard is a minute where one bad config can burn real money.

**Real example (2026-06-19 → 2026-06-25, ScrapingBee port schedule scrape):**

| Metric | Value |
|--------|-------|
| Total runtime | 6 days unattended |
| Total credits spent | 587,530 |
| Credits that produced real data (HTTP 200) | 219,460 (37.4%) |
| **Credits wasted on rejected requests (HTTP 401 after credit exhaustion)** | **357,565 (60.8%)** |
| Distinct ports attempted | 2,377 |
| Distinct ports with full success | 695 (29%) |
| Distinct ports with zero success | 1,435 (60%) |

The hourly failure pattern was unmistakable: a clean cliff at `2026-06-24 10:00 UTC` from 99% success to 0% success for 18 hours straight, then a tail-off. The scraper kept grinding for ~18 hours against an account that had run out of credits, burning 5 credits per retry × 3 retries × thousands of requests = tens of thousands of wasted credits.

**Mandatory pre-flight for any long-running metered job:**

1. **Read the budget/cap documentation** for the service BEFORE running. ScrapingBee's per-account credit cap and rate limit are visible in their dashboard. Ollama Cloud has 5-hour tumbling + weekly request windows. OpenAI has per-org spend caps.
2. **Calculate the worst-case burn rate**: `requests_per_hour × credits_per_request × estimated_runtime_hours`. If the number exceeds 50% of your remaining budget, abort and reduce scope.
3. **Set a fail-fast behavior at the HTTP layer**: when the service starts returning 401/402/429 with a "billing" header, the job should pause or alert, not retry with backoff. The retry logic in `scrapingbee-client.ts` retries 3 times on 401 — fine for transient auth glitches, catastrophic for credit exhaustion.
4. **Monitor credit balance mid-run**: the scraper could have checked remaining credits every N requests and aborted when the account dropped below a threshold. This is standard for any long-running paid API integration.
5. **Surface the cost in the run summary**: every long-running metered job should report `credits_spent`, `cost_usd_estimate`, `requests_succeeded`, `requests_failed_by_status` at completion. The scraper DID report credits used — but no human was watching.
6. **Set an alert threshold**: if the failure rate exceeds 50% over any 1-hour window, fire a notification. 18 hours of 100% failure should never happen silently.

**The asymmetry principle applied to cost:** The user said *"I'm not spending another $100 on this"* — this is a HARD CONSTRAINT that overrides any technical argument about data quality. Once the user has set a cost ceiling, do not propose actions that would exceed it without explicit re-authorization. Even a "cheap" diagnostic that might re-trigger the same metered service is off the table until the budget question is re-opened.

**Wasted credits are not refundable.** ScrapingBee and similar services charge per-request regardless of outcome. A 401 response still costs you. The only safe pattern is: verify budget headroom → run with monitoring → abort on budget signals. If the budget is unknown, do not run.

**Why this matters more than correctness bugs:** A wrong scraper config produces wrong data, which is recoverable (re-run with correct config). A blown budget is unrecoverable — you paid real money and got nothing. The asymmetry in recovery cost means the verification protocol should be MORE strict for cost than for correctness.

### State of "the scraper returned successfully" is not the same as "the job succeeded"

A common failure mode: the job's exit code is 0, the run summary says "completed", but the data is unusable for downstream consumption (because the join column isn't populated, because the cost ceiling was blown, because the rate limit was hit halfway through). Always validate the data shape on the consumer side, not just the producer side, before declaring the run a success.

The verification protocol for any scraper/sync job:

1. **Producer-side validation** (the scraper ran without crashes): exit code, row counts, error rate per task
2. **Audit trail validation** (the data is stored): snapshot tables populated, raw JSON captured, key columns present
3. **Consumer-side validation** (the data CAN reach the consumer): join keys populated, indexes match, schema compatible with downstream
4. **Cost validation** (the spend was reasonable): credits used vs expected, failure rate vs budget

**Skipping step 3 was the failure mode in this case. The scraper was producer-correct (2.3) but consumer-broken (3). The user caught it by asking about the join keys before I had verified them.**

## 17. Seasonal/Dormant Data Is Not Garbage — The Dormant-Orphan Trap

Travel data is seasonal.

**The Portland Disambiguation incident (May 2026):** 3,091 `route_corridors` rows were hard-deleted from PG because they had 0 active itineraries. All were seasonal/dormant routes. Their enrichment columns (`avgDailyRate`, `dominantBudget`, `summerCrowding`, `avgMedianAge`, etc.) were permanently lost. FalkorDB retained structural data (clan, familyId, edges) but PG enrichment was gone — re-computation from current data produces different values because the itinerary mix and pricing have changed.

**Pre-deletion mandatory checklist — before ANY bulk DELETE on core tables:**
1. **Blast radius analysis**: Which tables have FK references or FalkorDB edge references to these IDs? Which enrichment columns exist?
2. **Seasonal check**: Do any rows have `itinerary_count > 0` in a past or future season? If yes → dormant, not orphaned.
3. **Enrichment inventory**: List ALL enrichment columns. Estimate recompute cost (API calls, hours, dollars).
4. **FalkorDB sync check**: After PG deletion, FalkorDB nodes become disconnected orphans.
5. **Explicit `--confirm` flag**: Scripts must require `--confirm` or explicit user approval for any bulk DELETE on core tables.

**Decision framework:**

| Condition | Classification | Action |
|-----------|---------------|--------|
| `itinerary_count = 0`, never had itineraries | Truly orphaned | Safe to delete after verification |
| `itinerary_count > 0`, 0 currently active | **Dormant/seasonal** | **DO NOT DELETE** — soft-delete or mark inactive |
| `itinerary_count > 0`, currently active | Active | Normal data |
| Created by a bug (wrong signature, bad match) | Defective | Fix signature, remap — don't delete |

See `references/seasonal-data-pitfall.md` for the full incident analysis and blast radius map.

## 11. Never Kill a Running Inference Job by Deploying

Pushing code to the pipeline-worker branch triggers a Railway redeploy, which sends SIGTERM to the container and kills any in-flight inference. This is the most expensive mistake you can make with inferred assets — not data corruption, but **burned inference time and money with nothing to show for it**.

**Hard rule: CHECK FOR RUNNING JOBS BEFORE PUSHING TO PIPELINE-WORKER.**

```bash
# ALWAYS run this before pushing to pipeline-worker branch:
psql "$STAGING_DB" -c "SELECT id, status, \"jobType\" FROM pipeline_job_runs WHERE status = 'running';"
# If any rows returned → DO NOT PUSH. Wait for the job to complete or cancel it first.
```

**Why this matters more than data corruption:**
- A corrupted `UPDATE` can be rolled back from backup
- A killed inference job means the LLM calls already made are GONE — the results were being written incrementally but the job didn't complete, so partial writes may or may not have committed
- The Ollama API calls cost real money. A 10-hour job killed at hour 2 burned 20% of the budget with 0% of the value.

**Real example (2026-05-23):** A corridor insights job was running (680/117,364 cells completed, ~2 hours in). Two separate pushes to pipeline-worker each triggered a redeploy that killed the job. The second push was for code changes (prerequisite system, progress reporting) that wouldn't have affected the running job's correctness — they were improvements for the NEXT run, not fixes for the current one. Both pushes wasted real inference money. The user: "you just killed the run by deploying, wasting time and money."

**Correct sequence:**
1. Check for running jobs
2. If running → wait for completion, or cancel if the job itself is wrong
3. Push code changes
4. Queue a new job

**Anti-pattern:** Pushing "improvements" to a long-running pipeline while it's executing. The improvement will apply on the next run. The current run doesn't need it mid-flight.

## 12. Verify Before Claiming Readiness — The Detachment Problem

Never say "should work on the next run" or "it should work now" based on reading the code. The session record shows this claim being made multiple times for changes that had TypeScript errors, missing imports, wrong Prisma model names, and missing env vars. Each claim was followed by a failure that cost time or money.

**The detachment cycle that must be broken:**
1. Agent makes a change → claims "it should work" without running it
2. Deploys the change → kills a running inference job
3. Job fails on missing env var or wrong Prisma model name
4. Agent adds the missing var → claims "now it should work"
5. Deploys again → kills the replacement job
6. Discovers another missing import that wasn't copied to the pipeline-worker worktree
7. Repeat until the user intervenes

**Each iteration burns real inference time and money. Each "should work" claim that fails erodes trust.**

**Verification protocol before claiming readiness — every item must pass:**

```bash
# 0. CHECK FOR RUNNING JOBS FIRST — deploy kills active inference
psql "$STAGING_DB" -c "SELECT id, status FROM pipeline_job_runs WHERE status = 'running';"
# IF ANY ROWS RETURNED → DO NOT PUSH. Cancel the job or wait for it to finish.

# 1. TypeScript compiles in PIPELINE-WORKER worktree (not just staging)
cd .worktrees/pipeline-worker && npx tsc --noEmit

# 2. Diff shared directories between branches
diff -rq scripts/insights/ .worktrees/pipeline-worker/scripts/insights/
diff -rq lib/embeddings/ .worktrees/pipeline-worker/lib/embeddings/
diff -rq lib/knowledge-graph/ .worktrees/pipeline-worker/lib/knowledge-graph/

# 3. Dry-run with REAL env vars (validates imports, Prisma names, FalkorDB connection)
OLLAMA_API_KEY=... DATABASE_URL="$STAGING_DB" USE_FALKORDB=true \
  FALKORDB_HOST=... FALKORDB_PASSWORD=... npx tsx scripts/insights/precompute-corridor-insights.ts --dry-run --limit=3

# 4. Guard validation — remove an env var, confirm clear error exit
OLLAMA_API_KEY="" DATABASE_URL="$STAGING_DB" npx tsx scripts/insights/precompute-corridor-insights.ts --dry-run --limit=1
# Should exit with: "Missing required env vars: OLLAMA_API_KEY"

# 5. Both branches pushed and deployed — verify Railway picked up the change
railway logs --service pipeline-worker 2>&1 | tail -5
```

**Real example (2026-05-23):** Over the course of 6 hours, the following cycle repeated:
1. Consolidated profile script fixed on staging → claimed "should work" → pipeline-worker had old grid script → 121K cells computed instead of 2.7K
2. Copied script to pipeline-worker → claimed "should work" → missing `content-embedder.ts` import → would have crashed
3. Copied all imports → claimed "should work" → Prisma model name mismatch (`routeCorridor` vs `route_corridors`) → would have crashed on drift check
4. Fixed Prisma name → pushed → killed running job that had computed 680 cells
5. Pushed again for progress reporting improvements → killed replacement job at 130 cells
Each failure was discovered only by running the code, never by reading it.

## 14. Prerequisite Enforcement for Pipeline Jobs

Long inference jobs depend on upstream data being fresh. When a prerequisite (like FalkorDB sync) hasn't run, the job either fails silently (0 results, exit 0) or produces garbage. The fix is not manual — the pipeline must enforce prerequisites automatically.

**Pattern:** Each job declares prerequisites in the registry. The worker checks whether each prerequisite has completed successfully within a time window before starting the job. If not, it auto-triggers the prerequisite first.

```typescript
// lib/pipeline-jobs/registry.ts
export const JOB_REGISTRY: Record<string, JobDefinition> = {
  precompute_corridor_insights: {
    // ...
    prerequisites: ['falkordb_sync'],  // must have completed within 24h
  },
  falkordb_sync: {
    // no prerequisites — this is a leaf job
  },
};

// pipeline-worker/src/index.ts
async function checkPrerequisites(jobType: string): Promise<void> {
  const def = JOB_REGISTRY[jobType];
  if (!def.prerequisites?.length) return;
  for (const prereq of def.prerequisites) {
    const recent = await prisma.pipeline_job_runs.findFirst({
      where: { jobType: prereq, status: 'completed' },
      orderBy: { completedAt: 'desc' },
    });
    const within24h = recent && Date.now() - recent.completedAt.getTime() < 24 * 3600_000;
    if (!within24h) {
      console.log(`⚠️ Prerequisite '${prereq}' not satisfied. Auto-triggering...`);
      await prisma.pipeline_job_runs.create({ data: { jobType: prereq, status: 'pending' } });
      // Wait for completion before proceeding...
    }
  }
}
```

**Why this matters:** The pipeline-worker was missing FALKORDB_* env vars. The insights job "completed successfully" with 0 corridors because FalkorDB returned nothing. No error, no warning — just empty data. The prerequisite system + startup validation catches this before a single inference call is wasted.

## 14a. Phase Transition Validation in Pipeline Orchestrator

The auto-advance engine chains 47 steps across 10 phases. Between phases, the orchestrator must validate that the previous phase produced plausible results before starting the next. Without this, a zero-result failure in phase 2 cascades silently through phases 3-10, wasting compute and producing garbage data in production.

**Pattern:** After a phase completes, before advancing to the next phase, query baseline counts and compare against stored expectations:

```typescript
// lib/pipeline-jobs/phase-validation.ts
export async function validatePhaseCompletion(
  phase: number,
  runId: string,
  baselines: Record<string, number>
): Promise<{ valid: boolean; reason: string }> {
  switch (phase) {
    case 1: // Port Matching
      const newMatches = await prisma.port_visit_itineraries.count({
        where: { createdAt: { gt: pipelineStart } }
      });
      const unmatched = await prisma.port_ship_visits.count({
        where: { unmatched: true }
      });
      if (newMatches === 0 && unmatched > 0)
        return { valid: false, reason: `0 matches but ${unmatched} visits unmatched` };
      return { valid: true, reason: '' };

    case 2: // Corridor Derivation
      const corridors = await prisma.route_corridors.count();
      if (corridors < baselines.corridors * 0.9)
        return { valid: false, reason: `${corridors} corridors (expected ~${baselines.corridors})` };
      return { valid: true, reason: '' };

    case 3: // FalkorDB Sync
      // Cross-source validation: PG count vs FalkorDB node count within 5%
      // ...

    default:
      return { valid: true, reason: 'Validation not yet implemented' };
  }
}
```

**On validation failure, pause the pipeline (status: `paused`) — do NOT mark it `failed`.** A paused pipeline can be investigated and resumed from the admin UI. A failed pipeline creates urgency but no recourse.

**Baselines are stored at pipeline creation time:**

```typescript
const baselines = {
  corridors: await prisma.route_corridors.count(),
  profiles: await prisma.corridor_profiles.count(),
  cacheRows: await prisma.ai_chat_response_cache.count(),
};
await prisma.pipeline_runs.update({
  where: { id: runId },
  data: { metadata: { baselines } },
});
```

This prevents the scenario where a phase completes with 20% fewer rows than expected and no one notices until production data is wrong.

## 14b. Scraper → Pipeline Auto-Trigger

The pipeline must start automatically when the scraper finishes, not require a human at the keyboard. The callback pattern:

1. Scraper-worker completes `full-data-pipeline.ts`
2. Scraper POSTs to `/api/admin/pipeline-jobs/scraper-callback` with `{ scraperRunId, stats }`
3. API creates a `pipeline_runs` row with `autoAdvance: true` and calls `startPipelineRun(run.id)`
4. Pipeline auto-advances through all 10 phases

**The `autoAdvance` default must be `true`**, not `false`. The 4 historical pipeline runs in the database all have `autoAdvance: false` and all died at phase 1 step 1 — none completed. Manual step-by-step execution does not work for a 47-step pipeline.

**Current state (2026-05-23):** `autoAdvance` defaults to `false` in `app/api/admin/pipeline-runs/route.ts` line 60. The scraper callback endpoint does not exist yet.

## 15. Branch Sync Discipline for Multi-Worktree Projects

When a project has multiple git worktrees (e.g., `staging` + `pipeline-worker`), changes to shared scripts must be applied to BOTH branches. A fix on staging that isn't on pipeline-worker means the production worker runs old code while the developer thinks it's running new code.

**Critical pattern that caused a 97% waste of inference compute:**
- Staging had the consolidated profile script (1 cell/corridor, 2,769 total cells)
- Pipeline-worker still had the old T1/T3/T5 grid script (20 cells/corridor, 121,836 total cells)
- The worker ran the OLD expensive version for hours because no one verified both branches had the same code

**Verification protocol after copying files between worktrees:**
1. `diff` or `md5` the critical scripts on both branches
2. Check for transitive dependencies (new imports, new prompt files, new utility modules)
3. Run `npx tsc --noEmit` in the target worktree — path aliases, Prisma model names, and import paths may differ
4. Verify Prisma model names match the schema in that worktree (`route_corridors` vs `routeCorridor`)

**Real example (2026-05-23):** Copying `precompute-corridor-insights.ts` to the pipeline-worker worktree required also copying `prompts/corridor-profile.ts`, `prompts/dual-emit-schemas.ts`, and `lib/embeddings/content-embedder.ts` — all transitive imports. Missing any of these would crash at runtime. The Prisma model name was `route_corridors` (snake_case) in the schema but the script used `routeCorridor` (camelCase) — a runtime crash on the drift-detection query.

## 16. Data Quality Is the Only Metric That Matters

For applications targeted at professionals, data quality is existential. A travel agent recommending the wrong corridor to a client destroys trust in a way no UI polish can repair. Bad data isn't a minor bug — it's a broken product.

This means:
- **Never treat data recomputation as routine.** Each run costs real inference time and money. "Just re-run it" is the most expensive sentence in the project.
- **The dependency chain is real.** Corridors → FalkorDB sync → insights → profiles → embeddings → cache. A failure at any level cascades downward. Each link must be validated independently, not assumed.
- **Silent success is the worst failure mode.** A pipeline that completes with 0 results and exits 0 is worse than one that crashes — because it's never investigated. Guards that catch drift, missing env vars, and empty results are mandatory, not optional.
- **"Should work on the next run" is never acceptable without verification.** Run `--dry-run --limit=1` with real env vars. Read the last 20 lines of output. Verify the cell count matches expectations. Then, and only then, can you express confidence.
- **Data hierarchy correctness must be verified end-to-end before recompute.** Fixed corridors don't help if the itineraries, port visits, route signatures, or grouping logic upstream are wrong. Validate the full chain, not just the leaf node.

## 13. Informative Progress Reporting for Long-Running Jobs

Long-running inference jobs (30+ minutes) are opaque when the only output is a running counter like `1040/121836 cells (succeeded 1040, failed 0)`. The user has no idea how long it will take, whether it's making progress, or whether anything is wrong.

**Required progress information for any job processing >100 items:**

1. **Startup summary** — total count, concurrency, estimated duration
2. **Per-batch progress** — throughput (items/min), ETA (minutes remaining), last item ID
3. **Final summary** — success count, failure count, total elapsed time, token usage, average latency

```typescript
// ✅ Good — user can see rate and predict completion
console.log(`🚀 Starting: ${cells.length} corridors, concurrency=${args.concurrency}, est ~${estMinutes}min`);
// [PROGRESS] percent=3 label="83/2769 corridors (✓83 ✗0) — 8.2/min, ~33min left"
console.log(`📊 Run complete: 2769/2769 succeeded (100.0%), 0 failed, 32.4min elapsed`);
console.log(`   Tokens: 1,234,567 in / 234,567 out`);
console.log(`   Avg latency: 6.8s`);

// ❌ Bad — no context, no ETA, identical lines for hours
console.log(`1040/121836 cells (succeeded 1040, failed 0)`);
console.log(`1050/121836 cells (succeeded 1050, failed 0)`);
```

**Why this matters:** The user has been managing this system for 4 months across 2,088 commits. When they say "I have no clue what is happening," that's the progress reporting failing them, not the system.