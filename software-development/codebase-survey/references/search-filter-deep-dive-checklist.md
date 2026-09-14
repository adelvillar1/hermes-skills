# Search & Filter Deep Dive Checklist

Systematic investigation of a search/filter feature in a full-stack application. Use when the user asks for a "deep dive of the X page and its filtering" or "how does the Y search work?"

## Precondition

Project context loaded (CLAUDE.md, schema, recaps). The user names a specific page/feature, not the whole app.

## Steps

### 1. Find the page entry point

```bash
find app -type f -name "*.tsx" | xargs grep -l "<PageName\|pageName\|route.*slug" | head -10
```

Look for:
- Route file (`app/<route>/page.tsx` or `pages/<route>.tsx`)
- Whether it's a server or client component
- Feature flag gating (`isHarborEnabled()`, `isFeatureFlag()`)
- Whether multiple variants exist (legacy vs. modern UI)

**Key question:** Is there more than one implementation? Common pattern: `/sailings` (new) and `/app/itineraries` (legacy) both render the same feature with different components.

### 2. Read the frontend search component

Read the main client component that handles filter state and results display.

Map:
- **Filter dimensions** — what can the user filter by? (region, date, price, text search, etc.)
- **State management** — useState, URL params, query string synchronization
- **UI components** — sliders, checkboxes, pills, dropdowns, chips for active filters
- **Pagination** — offset-based, cursor-based, or load-more
- **Empty state** — what happens when no results match?
- **Sort options** — what orderings are available?
- **View modes** — grid, list, map, toggle?
- **Similar/recommended results** — does the page show "similar" or "recommended" items?

### 3. Trace the API call

Find the tRPC/GraphQL/REST call that fetches search results.

```bash
grep -rn "trpc.*search\|trpc.*filter\|trpc.*find" app/<route>/ --include="*.tsx"
```

Note:
- Procedure name and router
- Input parameters (what filters are sent to the server?)
- Output shape (what does the server return?)
- Whether it's a `useQuery` (read) or `useMutation` (write)
- Caching strategy (`staleTime`, `enabled`, `refetch`)

### 4. Read the backend search procedure

Read the router file that implements the search endpoint.

Map:
- **Input schema** — Zod/Pydantic validation, what fields are optional vs. required
- **Where clause construction** — how filters are combined (AND, OR, nested)
- **Base filters** — always-applied filters (e.g., `status = 'active'`, `departureDate >= tomorrow`)
- **Special filters** — anything non-standard:
  - Graph database lookups (FalkorDB, Neo4j)
  - Materialized view queries (`$queryRaw` on MVs)
  - Full-text search (Elasticsearch, pgvector, trigram)
  - Geospatial filters
- **Order by** — sort logic, default ordering
- **Pagination** — limit/offset, cursor, or page-based
- **Enrichment** — does the endpoint attach metadata (scores, reasons, similarity) from the graph?

### 5. Read the data layer

For each non-standard filter, trace to its data source:

| Filter type | Where to look |
|-------------|--------------|
| Materialized view | `prisma/migrations/*_create_*_view/migration.sql` |
| Graph database | `lib/knowledge-graph/*.ts`, `server/routers/*.ts` |
| Full-text search | `prisma/migrations/*_search_indexes/migration.sql` |
| Enum/constants | `lib/constants/*.ts` |
| Pipeline jobs | `lib/pipeline-jobs/registry.ts`, `lib/pipeline-jobs/monthly-corridor-phases.ts` |

### 6. Check for dynamic/cascading filters

Does the UI update available filter options based on current selections?

```bash
grep -rn "getDynamicFilterOptions\|getFilterOptions\|availableOptions\|cascading" app/ server/ --include="*.ts" --include="*.tsx"
```

If yes, read the dynamic options procedure. Note how it builds the base `where` clause from current filters and excludes the dimension being computed.

### 7. Compare variants (if multiple implementations exist)

When the codebase has two+ implementations of the same feature (e.g., `SailingsSearch` vs `HarborItinerariesContent`), create a comparison table:

| Feature | Variant A | Variant B |
|---------|-----------|-----------|
| Pagination | Offset (Previous/Next) | Load-more |
| Tier filter | ✅ Button pills | ❌ Not exposed |
| Profile filter | ✅ 7 personas | ❌ Not exposed |
| View toggle | Route / Ship | Route only |
| Port of call | ✅ URL param | ❌ Not exposed |
| Similar results | ✅ FalkorDB strip | ❌ Not shown |

This reveals feature drift and helps the user decide which variant to maintain.

### 8. Synthesize findings

Structure the report:

1. **Architecture overview** — routes, components, data flow
2. **Filter dimensions** — table of all filters with their data sources
3. **Backend logic** — how the `where` clause is built, special patterns (graph filtering, MV queries)
4. **Data layer** — MV definitions, graph queries, indexes
5. **Integration points** — how graph DB and relational DB work together
6. **Feature comparison** — if multiple variants exist
7. **Potential issues** — silent failures, stale data, performance risks, missing error handling

## Common patterns to watch for

### Graph → Relational bridge
```typescript
// FalkorDB returns ship IDs, Prisma filters by those IDs
const shipIds = await falkorDBService.getShipIdsForProfile('profile:families');
where.ship = { id: { in: shipIds } };
```
**Pitfall:** If FalkorDB fails, `shipIds` becomes `undefined` and the filter is silently skipped. Check error handling.

### Materialized view for search
```sql
-- Pre-computed join with calculated fields
CREATE MATERIALIZED VIEW itinerary_port_visits AS ...;
CREATE INDEX idx_ipv_port_name_trgm ON itinerary_port_visits USING gin (port_name gin_trgm_ops);
```
**Pitfall:** MV must be refreshed after data changes. Check pipeline job registration.

### Similarity search via graph edges
```typescript
const similarShips = await falkorDBService.findSimilarShips(shipId, { limit: 20 });
// Re-rank PG results by graph similarity score
```
**Pitfall:** Enrichment data (similarity scores, match reasons) may be discarded. Verify the response includes them.

### Dynamic filter options
```typescript
// Given current filters, what values are still possible?
const availableMonths = await getDynamicFilterOptions({ regionId, cruiseLineId, year });
```
**Pitfall:** The base `where` clause must exclude the dimension being computed, or the filter will self-restrict.

## Output format

Use markdown tables and bullet lists. Include:
- File paths and line numbers for key code sections
- SQL snippets for MV definitions
- Cypher snippets for graph queries
- Architecture diagrams (ASCII or text description)
- Comparison tables for variants

Do NOT paste raw file contents — synthesize. The report should be readable in 5-10 minutes.
