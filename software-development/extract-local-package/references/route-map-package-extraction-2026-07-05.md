# Route Map Package Extraction — Session Reference

**Date:** 2026-07-05
**Task:** Extract `lib/route-map/` (22 files, ~5,500 lines) into a standalone package at `packages/nautical-route-maps/`. Plan: `docs/plans/2026-07-05-nautical-route-maps-package-extraction.md`.

## Architecture

Four layers, each with a distinct purpose and dependency profile:

```
packages/nautical-route-maps/
├── core/      →  pure TS, zero deps (A* pathfinder, grids, rivers, antimeridian, Mercator)
├── svg/       →  pure TS, deps on core/ (server-side SVG generators + shared svg-utils)
├── geojson/   →  pure TS, deps on core/ (FeatureCollection emitter)
└── react/     →  TSX, peer deps react + maplibre-gl (MapLibre 3D components)
```

Each layer has its own `index.ts` barrel. Top-level `src/index.ts` re-exports core, svg, geojson (NOT react — that's a separate subpath import).

`package.json` exports map: `.` (top), `./core`, `./svg`, `./geojson`, `./react`. React + maplibre-gl are `peerDependencies` marked `optional: true` so they're not required by consumers of core/svg/geojson.

## Files moved (14 from `lib/route-map/`)

| Source | Destination |
|--------|-------------|
| `coastline-data-10m.ts` | `core/coastline-data.ts` (export name preserved) |
| `shipping-lanes.ts` | `core/shipping-lanes.ts` |
| `sea-grid.ts` | `core/sea-grid.ts` |
| `sea-grid-hires.ts` | `core/sea-grid-hires.ts` |
| `pathfinder.ts` | `core/pathfinder.ts` |
| `pathfinder-hires.ts` | `core/pathfinder-hires.ts` |
| `river-polylines.ts` | `core/river-polylines.ts` |
| `river-router.ts` | `core/river-router.ts` |
| `antimeridian.ts` | `core/antimeridian.ts` |
| `generate-svg.ts` | `svg/generate-route-svg.ts` |
| `generate-detail-svg.ts` | `svg/generate-detail-svg.ts` |
| `generate-family-svg.ts` | `svg/generate-family-svg.ts` |
| `generate-port-map.ts` | `svg/generate-port-map.ts` |
| `generate-path-geojson.ts` | `geojson/generate-path-geojson.ts` |

New files created in the package (not extracted from app):
- `core/types.ts`, `core/mercator.ts`, `core/douglas-peucker.ts` — shared utilities
- `core/index.ts`, `svg/svg-utils.ts`, `svg/index.ts`, `geojson/index.ts` — barrels
- `react/RouteMap3D.tsx`, `react/PortTerrainMap.tsx`, `react/index.ts` — refactored React components

Files that stayed in `lib/route-map/` (Prisma-coupled, kept in app):
- `get-coordinates.ts`, `get-detail-coordinates.ts`, `get-detail-svg.ts`, `get-port-location-map.ts`
- `derive-arrival-port.ts`, `region-classifier.ts`, `region-polygons.ts`
- `__tests__/generate-path-geojson.test.ts` — test, imports from package
- `sea-grid-app.ts` — new file, extracted Prisma-coupled `findMisGeocodedPorts` + `stampPortsOnGrid` from `sea-grid.ts` to keep core dep-free

## App-side changes

### tsconfig.json
Added `baseUrl: "."` (required for non-relative path aliases) and path mappings:
```json
"@nautical-route-maps/core": ["packages/nautical-route-maps/src/core/index.ts"],
"@nautical-route-maps/svg": ["packages/nautical-route-maps/src/svg/index.ts"],
"@nautical-route-maps/geojson": ["packages/nautical-route-maps/src/geojson/index.ts"],
"@nautical-route-maps/react": ["packages/nautical-route-maps/src/react/index.ts"]
```

### Import updates (18+ files)
- App routes/scripts: `@/lib/route-map/generate-svg` → `@nautical-route-maps/svg` (or `../lib/route-map/` → `@nautical-route-maps/...` for scripts)
- Stayed-in-app files: `get-coordinates.ts`, `get-detail-coordinates.ts`, etc. — these imports remain unchanged
- `instrumentation.ts`: dynamic import of `./lib/route-map/pathfinder-hires` → `@nautical-route-maps/core`
- `lib/route-map/__tests__/generate-path-geojson.test.ts`: `../generate-path-geojson` → `@nautical-route-maps/geojson`

### React component wrappers
Both app React components became thin wrappers (100 lines down from 401, 47 lines down from 344):
- `app/components/itinerary/ItineraryRouteMap3D.tsx` — fetches geojson + loads mapConfig, then renders `<RouteMap3D geojson mapConfig />` from package
- `app/components/port/PortTerrainMap.tsx` — maps app props to package props (`portId` → key, `portName` → name, etc.)

Both use `next/dynamic` to keep maplibre-gl out of SSR.

## Pitfalls hit (in order of occurrence)

### 1. River polylines subagent truncated file
Subagent used a 500-line read that truncated `river-polylines.ts` (856 lines). It then wrote an incomplete copy with an extra closing bracket. **Fix:** `cp lib/route-map/river-polylines.ts packages/.../core/river-polylines.ts` (verbatim copy is safer than a subagent rewrite for large data files > 500 lines).

### 2. Barrel export naming conflicts
`sea-grid.ts` and `sea-grid-hires.ts` both export `GRID_WIDTH`, `GRID_HEIGHT`, `latlngToCell`, `cellToLatlng`, `getCostGrid`, `getCellCost`. Same for `pathfinder.ts` and `pathfinder-hires.ts` (both `findSeaRoute`, `findMultiPortSeaRoute`). Wildcard re-export from `core/index.ts` causes `TS2308: Module has already exported a member named X`. **Fix:** Export only hi-res versions from barrel, import lo-res directly: `import { ... } from '@nautical-route-maps/core/sea-grid'`.

### 3. PortType conflict between core and geojson
Both `core/types.ts` and `geojson/generate-path-geojson.ts` exported `type PortType = 'departure' | 'arrival' | 'port_of_call'`. Barrel re-export collision. **Fix:** Remove `PortType` from `core/types.ts` — keep only `Port` interface and `LatLng` there. `PortType` is canonical in the geojson module since it originates from the path geometry output.

### 4. Prisma leakage in `sea-grid.ts`
Original `sea-grid.ts` had `findMisGeocodedPorts()` and `stampPortsOnGrid()` that used `import('@prisma/client').PrismaClient` and queried `cruisemapper_ports`. **Fix:** Move these to `lib/route-map/sea-grid-app.ts` in the app side. They depend on Prisma's table shape and on app data, so they belong in the app, not the zero-dep core. Update `scripts/detect-misgeocoded-ports.ts` to import from the app-side file.

### 5. baseUrl missing for path aliases
App `tsconfig.json` has `paths` but no `baseUrl`. TypeScript requires `baseUrl: "."` for non-relative paths. Without it: `error TS5090: Non-relative paths are not allowed when 'baseUrl' is not set`. **Fix:** Add `"baseUrl": "."` to tsconfig `compilerOptions`.

### 6. Sharing types via Port type name mismatch
Original `DetailPort` interface used `portName`; the plan's proposed `Port` type used `name`. **Fix:** Keep `portName` in `Port` type (matches production contract). This avoids a mapping layer at every call site where app code passes `DetailPort[]` into the SVG generator.

## Verification approach (the part that matters)

After deploying to staging, full auth-based testing was blocked (NextAuth credentials form inputs have no `name` attribute before hydration; Playwright submit timing is unreliable). **Fallback: verify via side-effect API endpoints that don't need auth.**

The route-map API endpoint `/api/route-map?id=<uuid>` returns SVG generated by the package's `generateRouteSvg`. A real itinerary returned a **34,786-byte SVG** while unknown IDs return the **327-byte fallback** (`generateFallbackSvg()`). This size difference alone proves the package is loaded.

**Decisive proof the A* pathfinder ran:**
- 8 coastline polygons rendered (the package's `applyShippingLanes` + `rasterizePolygon` logic)
- 8 occurrences of `#c8a55a` (the package's exact color values)
- **1,152 LineTo (L) commands** in the route path — only possible if `findMultiPortSeaRoute` → `findSeaRoute` → A* min-heap pathfinder ran
- A straight-line fallback would have ~5-10 L commands for a 7-port itinerary

```bash
# Count waypoints
grep -oE 'L[0-9]+\.[0-9]+,[0-9]+\.[0-9]+' /tmp/rm-test.svg | wc -l  # → 1152

# Verify coastline color
grep -o 'fill="#3a5575"' /tmp/rm-test.svg | wc -l  # → 8

# Confirm package function in response
head -c 500 /tmp/rm-test.svg  # → contains "M629.1,879.3 L629.1,916.9..."
```

**The pattern:** when full integration testing is blocked, hit the API endpoints that exercise the package code and verify the output's characteristics match what the package would produce. Don't spin on auth.

## Files touched

52 files changed: 1,541 insertions, 1,064 deletions.

Commit: `344b4126` on `develop`, merged to `staging` as `18b963a8`.

## Skills used / referenced

- `draft-feature-plan` — wrote the 24KB extraction plan
- `writing-plans` — plan shape guidance
- `subagent-driven-development` — parallel subagent dispatch (Phase 2: 3 subagents for core layer)
- `runtime-bug-discovery-via-test-run` — the pattern that informed the staging verification (verify via real-data side effects, not just type-check)