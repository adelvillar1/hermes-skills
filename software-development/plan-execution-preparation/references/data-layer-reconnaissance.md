# Data-Layer Reconnaissance Patterns

> Used when a plan depends on knowing which tables/columns are structured vs plain-text, and which FalkorDB nodes carry which projected properties.

---

## Pattern A: Prisma Schema Inspection (Structured vs Unstructured)

When a Prisma model has both structured and unstructured fields, Prisma client only exposes fields declared in `schema.prisma`. Raw-SQL-only columns exist in Postgres but are invisible to Prisma types.

**Quick check — is a table structured in Prisma?**

1. Open `prisma/schema.prisma`
2. Find the model (e.g., `corridor_insights`, `ship_corridor_insights`, `cruise_line_insights`)
3. Count fields beyond `id`, foreign keys, and `narration`
   - If the only extra fields are `insightType`, `personaId`, `season` → **unstructured** (narration only)
   - If there are typed columns like `archetype String?`, `seasonMode String? @map("season_mode")`, `fitPersonas String[]` → **structured**

**Verification via Prisma client:**

```typescript
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

// If this compiles, the column is in the schema:
const row = await prisma.cruiseLineInsights.findFirst({
  select: { archetype: true, seasonMode: true }
});
```

If a column is missing from Prisma but present in raw SQL (e.g., `fit_verdict` on `corridor_insights`), raw queries are the only path:

```typescript
const result = await prisma.$queryRaw`
  SELECT "fit_verdict", "key_strengths" FROM corridor_insights
  WHERE "insightType" = 'T1_BEST_FIT' LIMIT 1
`;
```

**Remember:** In columns without `@map()`, Prisma stores camelCase names in Postgres. Raw SQL must double-quote them: `"cruiseLineId"`, `"avgDuration"`, `"isCurrent"`. Always verify with:

```sql
SELECT column_name FROM information_schema.columns WHERE table_name = 'corridor_insights';
```

---

## Pattern B: FalkorDB Property Inventory (What Is Actually Projected)

FalkorDB schemas are implicit — properties are created on demand by projection scripts. A node type may have more or fewer properties than the plan assumes.

**Quick check — what properties exist on a node type?**

```bash
# Using the project's FalkorDB client (Node.js)
npx tsx -e "
const { query } = require('./lib/knowledge-graph/falkordb-client');
query(\"MATCH (n:ShipInsight) RETURN keys(n) AS props LIMIT 1\")
  .then(r => console.log(JSON.stringify(r, null, 2)))
  .catch(e => console.error(e.message));
"
```

Or via redis-cli if you have the FalkorDB URL:

```bash
redis-cli -h $FALKORDB_HOST -p $FALKORDB_PORT GRAPH.QUERY cruising-intelligence "MATCH (n:ShipInsight) RETURN keys(n) AS props LIMIT 1"
```

**Key insight types and what to verify:**

| Node type | Expected insight properties | Quick query |
|-----------|----------------------------|-------------|
| `ShipInsight` | `narration`, `computedAt`, `jointFitVerdict`, `reinforcementAxes`, `frictionAxes` | `MATCH (si:ShipInsight) RETURN keys(si) LIMIT 1` |
| `RouteCorridor` | `fitCouples`, `fitLuxury`, `fitBudget`, `fitSolo`, `riskCategories`, `riskSeverity` | `MATCH (rc:RouteCorridor) RETURN keys(rc) LIMIT 1` |
| `Clan` | `fitPersonas`, `fitPercentages`, `riskCategories`, `riskFrequencies`, `dominantSeverity`, `peakMonths`, `topShips`, `shipFitSummary` | `MATCH (c:Clan) RETURN keys(c) LIMIT 1` |
| `CruiseLine` | `insightArchetype`?, `insightSeasonMode`?, `insightDefiningTraits`? | `MATCH (l:CruiseLine) RETURN keys(l) LIMIT 1` |
| `Region` | `fitPersonas`?, `fitPercentages`?, `riskCategories`? | `MATCH (r:Region) RETURN keys(r) LIMIT 1` |

**Common surprise:** `CruiseLine` nodes may NOT have insight properties even if the plan assumes they do. Always verify before writing Cypher that reads `l.insightArchetype`.

---

## Pattern C: Build the PG + FalkorDB Truth Table

After running A and B, always build this table before scoping the plan:

| Data type | Surface | PG table | Structured in Prisma? | FalkorDB node | Properties match? |
|-----------|---------|----------|----------------------|---------------|-------------------|
| T1 corridor fit | Itinerary | `corridor_insights` | No (raw SQL only) | `RouteCorridor` | `fitCouples`, `fitLuxury`, etc. |
| T5 risk flags | Itinerary | `corridor_insights` | No (raw SQL only) | `RouteCorridor` | `riskCategories`, `riskSeverity` |
| T6 ship×corridor fit | Ship | `ship_corridor_insights` | No (raw SQL only) | `ShipInsight` | `narration`, `jointFitVerdict`, etc. |
| T7 line personality | Cruise Line | `cruise_line_insights` | Yes — `archetype`, `seasonMode` | `CruiseLine` | Usually NOT projected; verify |
| Region aggregate | Region | `corridor_family_insights` | Yes — `fitPersonas`, `fitPercentages` | `Clan`/`Region` | `Clan` has; `Region` may not |

This table is the single source of truth for deciding:
- Which surfaces read from PG vs FalkorDB
- Whether a raw SQL query or Prisma client query is needed
- Whether the UI can display structured badges (from FalkorDB properties) or only narration text (from PG)

---

## Pattern D: Row/Node Count Sanity Check

Always verify counts match expectations from the plan or recaps:

```bash
# PostgreSQL count
psql "$STAGING_DB" -t -c "SELECT COUNT(*) FROM ship_corridor_insights WHERE season = 'WINTER_2025';"

# FalkorDB count
redis-cli -h $FALKORDB_HOST -p $FALKORDB_PORT GRAPH.QUERY cruising-intelligence "MATCH (si:ShipInsight) RETURN count(si)"
```

Mismatched counts indicate incomplete projection or stale backfill.
