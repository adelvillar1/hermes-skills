# Seasonal/Dormant Data Pitfall

## The Trap

When a data cleanup script encounters rows with `itinerary_count > 0` but zero *currently active* itineraries, it's tempting to classify them as "orphaned" and delete them. This is almost always wrong for seasonal travel data.

Cruise itineraries are seasonal — Caribbean routes peak in winter, Alaska routes in summer, Mediterranean routes in spring/fall. A corridor with `itinerary_count = 27` but 0 currently active itineraries is **dormant**, not orphaned. It will reactivate when the next season's itineraries are loaded.

## The Blast Radius

Deleting a `route_corridors` row cascades through 16+ tables:

1. `route_corridors` (the corridor itself)
2. `route_signature_map` (old→new signature mapping)
3. `route_map_svgs` (SVG visualizations)
4. `corridor_dep_hashes` (delta detection hashes)
5. `corridor_profiles` (insight narratives)
6. `corridor_upgrade_insights` (upsell data)
6. `corridor_seasonal_profiles` (seasonal breakdowns)
8. `corridor_line_presence` (cruise line presence per corridor)
9. `route_clans` (clan aggregation — if the corridor was a type specimen)
10. FalkorDB: `RouteCorridor` nodes
11. FalkorDB: `CORRIDOR_IN_CLAN`, `CORRIDOR_IN_REGION` edges
12. FalkorDB: `CorridorInsight` nodes (if projected)
13. `content_embeddings` (vector search rows keyed by corridor)
14. AI Chat response cache (keyed by corridor signature)

Each enrichment column (`avgDailyRate`, `dominantBudget`, `summerCrowding`, `avgMedianAge`, etc.) is expensive to recompute and context-dependent — the itinerary mix, ship configurations, and pricing data change over time, so recomputing from current data produces *different values* from the originals.

## Real Example: Portland Disambiguation (May 2026)

When Portland OR was disambiguated from Portland ME, 3,091 route corridors were hard-deleted from PG because they had 0 "active" itineraries. All enrichment columns were permanently lost. FalkorDB retained the nodes with structural data (clan, familyId, edges) but PG-level enrichment was gone.

**What should have happened:** 
- Mark corridors as `status = 'dormant'` or `isActive = false` (soft-delete)
- Preserve all enrichment columns
- When next-season itineraries activate the corridor, reset `isActive = true`

**The fix applied:** Added hard rules to CLAUDE.md prohibiting bulk DELETE on core tables without blast-radius analysis and explicit approval. Enrichment columns are now treated as irreplaceable assets, not caches.

## Decision Framework

| Condition | Classification | Action |
|-----------|---------------|--------|
| `itinerary_count = 0` AND no itineraries ever existed | Truly orphaned | Safe to delete after verification |
| `itinerary_count > 0` but 0 currently active | Dormant/seasonal | **DO NOT DELETE** — soft-delete or mark inactive |
| `itinerary_count > 0` AND currently active | Active | Normal data, no action needed |
| Created by a bug (wrong signature, bad port match) | Defective | Fix the signature, then remap — don't delete the row |

## Pre-Deletion Checklist (mandatory before any bulk DELETE on core tables)

1. **Blast radius analysis**: Which tables have FK references to this table? Which FalkorDB node types reference these IDs? Which enrichment columns exist and what would it cost to recompute them?
2. **Seasonal check**: Do any of these rows have `itinerary_count > 0` in a past or future season? If yes, they're dormant, not orphaned.
3. **Enrichment inventory**: List ALL enrichment columns on the target table and any related tables. Estimate recompute cost (API calls, hours, dollars).
4. **FalkorDB sync check**: Which FalkorDB node types and edge types reference these IDs? After PG deletion, these nodes become orphans in the graph.
5. **Explicit `--confirm` flag**: The script must require `--confirm` or explicit user approval. No silent bulk deletion.

See `docs/PORTLAND-DISAMBIGUATION-POSTMORTEM.md` for the full incident analysis.