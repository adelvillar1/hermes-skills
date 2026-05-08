# Project Infrastructure Inventory — Check Before Writing Scripts

This is a checklist of existing infrastructure that must be consulted before
writing any new script or tool for this project. The user has built these
systems deliberately — reinventing them wastes sessions and causes frustration.

## Pipeline Jobs (`lib/pipeline-jobs/registry.ts`)

The project has a full job system with 30+ registered jobs. Before writing
any new data-generation, enrichment, prewarming, or batch-operation script,
check whether a job already exists here.

Key jobs include:
- `svg_mini_maps` → `scripts/prewarm-route-maps.ts`
- `svg_detail_maps` → `scripts/prewarm-route-maps.ts --detail`
- `port_location_maps` → `scripts/prewarm-port-location-maps.ts`
- `route_corridors` → `scripts/compute-route-corridors.ts`
- `precompute_corridor_insights` → `scripts/insights/precompute-corridor-insights.ts`
- And 25+ more

Each job definition includes:
- Script path(s)
- CLI flags (`--force`, `--dry-run`, `--limit`, `--concurrency`, etc.)
- Category, estimated duration

The admin UI at `/app/admin/pipeline` exposes these jobs with a form UI.
All jobs run on the Railway server via `child_process.spawn` — NOT locally.

**If a job exists for the task, use it. Fix its script if needed. Do not write
a new script.**

## Technical Documentation (`TECHNICAL-DOCUMENTATION.md`)

Section §26 covers the Admin Pipeline Jobs architecture in detail.
Also §23 covers SVG Route Map Persistence. Read relevant sections before
working on infrastructure tasks.

## Route Map Infrastructure Summary

| Component | Path | Used by |
|-----------|------|---------|
| Mini-map generation | `lib/route-map/generate-svg.ts` | API, prewarm, pipeline |
| Detail map generation | `lib/route-map/generate-detail-svg.ts` | API, prewarm, pipeline |
| Coordinate fetching | `lib/route-map/get-coordinates.ts` | Both generators |
| Detail coordinates | `lib/route-map/get-detail-coordinates.ts` | Detail generator |
| Sea pathfinder (hi-res) | `lib/route-map/pathfinder-hires.ts` | Both generators |
| Sea pathfinder (low-res) | `lib/route-map/pathfinder.ts` | Fallback chain |
| River router | `lib/route-map/river-router.ts` | Both generators |
| Antimeridian handling | `lib/route-map/antimeridian.ts` | Both generators |
| Coastline data | `lib/route-map/coastline-data-10m.ts` | Both generators |
| Pipeline prewarm script | `scripts/prewarm-route-maps.ts` | svg_mini_maps, svg_detail_maps |
| Admin prewarm endpoint | `app/api/admin/prewarm-platform/route.ts` | Direct API |
| Route map API | `app/api/route-map/route.ts` | On-demand generation |
| Route map detail API | `app/api/route-map/detail/route.ts` | On-demand detail |
| Port map generator | `lib/route-map/generate-port-map.ts` | Port location maps |
| DB table | `route_map_svgs` (PK: routeSignature) | All mini/detail maps |

## Mini-Map Dimensions

Correct: 400×250. This must be consistent across ALL surfaces:
- `generate-svg.ts` default params
- `generateFallbackSvg` defaults
- `app/api/route-map/route.ts` call site
- `app/api/admin/prewarm-platform/route.ts` call site (line 96)
- `scripts/prewarm-route-maps.ts` call site (line 125)

If any of these drifts, the card rendering breaks.

## Coordinate Fetching

Uses `port_visit_itineraries` join table (canonical N-N relationship), NOT the
old `port_ship_visits.matchedShipId` + date range heuristic. The join table
covers ~99% of active itineraries vs ~6% for the old path.
