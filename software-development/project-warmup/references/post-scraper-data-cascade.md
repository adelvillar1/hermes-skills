# Post-Scraper Data Cascade

After a monthly scraper run completes (new port visits, itineraries, or ships), data must cascade through PG corridors → enriched aggregates → LLM insights → FalkorDB graph → production sync. The full sequence is ~6-12 hours depending on LLM phase duration.

## Dependency Graph (Simplified)

```
Scraper finishes
  │
  ▼
Match Port Visits (5-30 min)
  │
  ├──→ SVG Mini-Maps (5-30 min) — can run in parallel
  ├──→ SVG Detail Maps (10-60 min)
  │
  ▼
Route Corridors (2-5 min)
  │
  ▼
Region Reclass (2-5 min) → Corridor Clans (5-8 min) → Corridor Enrichment (10-20 min)
  │
  ▼
Corridor Families (2-5 min) → Clan Aggregates (<1 min) → Family Topology (2-5 min)
  │
  ▼
FalkorDB Sync (30-45 min)  ← first time graph has new data
  │
  ▼
─── LLM INSIGHT PHASE (hours, largest time cost) ───
  │
  ├── T1/T3/T5 Precompute (corridor_insights, ~704K cells)
  ├── T2 Upgrade Insights (corridor_upgrade_insights, hours)
  ├── T4 Family Insights (corridor_family_insights, 30-90 min)
  ├── T6 Ship-Corridor Insights (ship_corridor_insights, hours)
  └── T7 Cruise Line Insights (cruise_line_insights, 15-30 min)
  │
  ▼
Aggregate Clan Insights (<2 min) → Aggregate Region Insights (<1 min)
  │
  ▼
Project to FalkorDB (2-5 min, 9 Cypher passes)
  ├── T1/T5 CorridorInsight nodes
  ├── T6 ShipInsight nodes
  ├── T7 CruiseLineInsight nodes
  ├── RegionInsight nodes
  ├── BEST_FOR edges (Clan→GuestProfile)
  ├── DOMINATES_IN edges (CruiseLine→Clan)
  ├── SERVES_CLAN edges (Ship→Clan)
  └── SIMILAR_CLAN edges
  │
  ▼
Narrative Precomputation (9 Ollama jobs, ~15 min total)
  ├── Report Card, Fleet Age, Service Quality, Cruise Line
  ├── Region, Regional Value, Best Of, Clan, Ship
  │
  ▼
AI Cache Prewarm (v2 templates → v3 corridors → v4 Ollama synthesis, ~5h)
  │
  ▼
Redis Flush → Re-warm → PG Sync to Production → FalkorDB Replication → Production Redis Warm
```

## Orchestrated Alternative

Instead of running each step individually from the admin pipeline UI, the `graph_intelligence_refresh` job orchestrates:
- Refresh route_clans
- Aggregate clan insights (force)
- Aggregate region insights (force)
- Project all seasons to FalkorDB
- Replicate to production

Run this after T1-T7 insights have been precomputed.

## Critical Path

The critical path (blocking chain) is the sequence where each step depends on the prior one:

1. **Scraper → Match Port Visits** — nothing can progress until matching is done
2. **Route Corridors → Enrich → Families → Sync to FalkorDB** — linear chain
3. **FalkorDB Sync → Insight Precompute** — insights read from FalkorDB corridors
4. **T1-T7 → Aggregate → Project to FalkorDB** — aggregation depends on raw insights
5. **Project → Sync to Production** — production can't be updated until projections are complete

Non-critical paths (can run in parallel):
- SVG map generation (mini + detail + port location)
- Ship image import
- Port country codes
- Most narrative jobs (read from PG, not FalkorDB)

## Key Tables Written Per Phase

| Phase | Tables written | Rows (approx) |
|-------|---------------|---------------|
| Match visits | `port_visit_itineraries` | 300K+ |
| Route Corridors | `route_corridors` | ~16K |
| Corridor Enrichment | `route_corridors` (updated) | ~16K |
| Corridor Families | `corridor_families` | ~2,360 |
| Clan Aggregates | `route_clans` | ~57 |
| Family Topology | `corridor_family_topology` | ~2,360 |
| T1/T3/T5 Insights | `corridor_insights` | ~704K |
| T2 Insights | `corridor_upgrade_insights` | varies |
| T4 Insights | `corridor_family_insights` (family rows) | varies |
| T6 Insights | `ship_corridor_insights` | varies |
| T7 Insights | `cruise_line_insights` | ~588 |
| Clan Aggregation | `corridor_family_insights` (clan rows) | 228 |
| Region Aggregation | `corridor_family_insights` (region rows) | 96 |

## FalkorDB Graph Nodes/Edges After Full Cascade

| Entity | Type | Count |
|--------|------|-------|
| RouteCorridor nodes | Node | ~16K |
| Ship nodes | Node | ~687 |
| CruiseLine nodes | Node | ~49 |
| Region nodes | Node | 24 |
| Clan nodes | Node | 57 |
| Port nodes | Node | ~5,000 |
| GuestProfile nodes | Node | 5 |
| CorridorInsight nodes | T1/T5 | ~160K |
| ShipInsight nodes | T6 | varies |
| CruiseLineInsight nodes | T7 | ~1,440 |
| RegionInsight nodes | Node | ~96 |
| SAILS_CORRIDOR edges | Ship→Corridor | varies |
| HAS_INSIGHT edges | →Insight | varies |
| BEST_FOR edges | Clan→GuestProfile | ~57 |
| DOMINATES_IN edges | CruiseLine→Clan | ~218 |
| SERVES_CLAN edges | Ship→Clan | varies |
| SIMILAR_CLAN edges | Clan→Clan | varies |

## Repository Layout

Pipeline jobs: `lib/pipeline-jobs/registry.ts` (879 lines, 40+ jobs)
Scraper-worker tasks: `scraper-worker/src/tasks/` (10+ task files)
Pipeline orchestrator: `scripts/graph-intelligence-refresh.ts`
Post-pipeline sequence guide: see plan `2026-05-01-scraper-dashboard-and-pipeline-seq.md`

## Common Gotchas

- **FalkorDB sync must complete before insight precomputation** — corridor insights read from graph, not PG directly
- **T1/T5 run first** (they're the foundation), then T2/T4, then T6, then T7 last
- **Insight aggregation must wait** until all T-rows for the current cycle are populated — partial data produces stale clan/region aggregates
- **Project to FalkorDB must run after aggregation** — projection reads from `corridor_family_insights` which aggregation writes
- **Ollama rate limits**: 5-hour tumbling window + weekly cap on Pro/Max tiers. The Max tier (c=10) was upgraded for the initial backfill — if downgraded to Pro (c=3), insight precomputation takes ~3x longer
- **Ollama model choice matters**: `nemotron-3-super:cloud` has better JSON throughput than `gemma4:31b-cloud` for insight generation. Check `CLAUDE.local.md` for current model config
