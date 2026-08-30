---
name: extract-local-package
description: "Extract a coherent set of files from an application directory into a local package (or package subdirectory) and fix internal imports so the new package is self-contained. Covers copy decisions, import rewriting, deduplicating shared helpers, and verification."
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [refactoring, monorepo, packages, typescript, imports, code-relocation]
    related_skills: ["refactor-safely", "review-changes"]
    changelog: "v1.0.0 — initial skill covering copy-extract-and-rewrite-imports workflow, including the common pitfall of duplicated MinHeap/simplifyPath helpers that should be replaced by a shared package helper. v1.1.0 — added pitfalls from route-map extraction (2026-07-05): barrel-export naming conflicts when lo-res and hi-res variants share export names, Prisma leakage back to app for cross-tier helpers, baseUrl requirement for path aliases, the verify-via-side-effect pattern when full integration testing is blocked, and a session reference at references/route-map-package-extraction-2026-07-05.md. v1.2.0 — added pitfalls #11–12 from post-extraction test breakage (2026-07-06): vitest doesn't read tsconfig paths (needs vitest.config.ts with resolve.alias), stale vi.mock() paths after module relocation."
---

# Extract Files into a Local Package

Move a coherent, self-contained slice of code from an application directory into a local package (or a package subdirectory such as `packages/<name>/src/core`) and fix all imports so the package is internally consistent and the rest of the app can import it cleanly.

## When to Use

- The user says "copy the X files into the Y package core"
- Extracting a feature slice (e.g., route-map generation, SVG generation, pathfinding) into a reusable package
- Preparing a package for publication or for monorepo reuse
- Splitting a large app into packages without changing behavior

## Trigger Phrases

- "copy ... files into ... package"
- "extract ... into the package"
- "move these files to the package"
- "package up ..."

## Workflow

### 1. Read the source files before copying

Read the files the user names (or files implied by the task). Identify:
- The module's public exports
- Internal imports between the files
- Imports from outside the slice (e.g., Prisma, external packages, unrelated app modules)
- Inline helpers that duplicate functionality already in the destination package (e.g., `simplifyPath`, `perpendicularDistance`, `MinHeap`)

### 2. Identify the destination layout

- Determine the package root and the target subdirectory (often `src/core`).
- Check whether the package already has shared helpers that can replace inline helpers from the source files.
- If a source file's name is too specific to the app, rename it to fit the package vocabulary (e.g., `coastline-data-10m.ts` → `coastline-data.ts`) while preserving the exported symbol name if external code depends on it.

### 3. Copy the files

Use `cp` or `write_file` to place the files in the destination. Preserve the original files in the app directory unless the user explicitly asks to delete them.

### 4. Rewrite internal imports to be relative within the package

Update all `import` statements that cross the package boundary to use relative paths inside the package:
- `./coastline-data-10m` → `./coastline-data` (if renamed)
- Any inline helper (e.g., `simplifyPath`, `perpendicularDistance`) that already exists in the package should be imported from the package helper instead of being duplicated.
- Imports from outside the slice (e.g., Prisma) should be left as-is unless the package has a different contract.

### 5. Deduplicate helpers

Common duplicate helpers found in pathfinding/geometry code:
- `MinHeap` — often implemented inline in multiple pathfinder files. Keep one implementation per package.
- `simplifyPath` / `perpendicularDistance` — often inline when the package already has `douglas-peucker.ts` with `simplifyLatLngPath` and `douglasPeucker`.
- Replace inline implementations with the package's shared helper and add the corresponding `import`.

**Pitfall:** Two pathfinder files (`pathfinder.ts` and `pathfinder-hires.ts`) copied from the same app often contain identical `MinHeap` and `simplifyPath` implementations. If the package already has `douglas-peucker.ts`, delete the inline helpers and use `simplifyLatLngPath` from `./douglas-peucker` in both files.

### 6. Decide whether the extracted component should stay Tailwind-or-styled

If the package is consumed by multiple apps (or by an app without the same Tailwind tokens), replace app-specific classes and CSS variables with inline styles or a plain CSS module so the component renders correctly outside the original app. Examples:
- `bg-paper`, `border-line-2`, `text-mute`, `font-display` → inline `style` objects with hex values, or a prop-driven className.
- `var(--bg-body)`, `var(--text-muted)` → explicit colors or CSS custom props passed from the parent.

Keep the markup/structure identical; only replace styling tokens that don't exist in the package's consumer. If the package is private and the consumer shares the same Tailwind config, leaving Tailwind classes is fine, but verify that the package's `tsc` build doesn't depend on Tailwind at compile time.

### 7. Verify the package compiles

Run the package's type checker on the moved files:
- For TypeScript: `npx tsc --noEmit <list of moved files>` or the package's `tsc` command.
- If the package has a build script, run it.
- Fix any import errors, duplicate identifiers, or missing symbols before reporting success.
- If the component uses React types, ensure `@types/react` or a `react` peerDependency is declared and the package's tsconfig includes JSX.

## Safety Checks

- [ ] Source files read before copy
- [ ] Internal imports rewritten to relative package paths
- [ ] External imports (Prisma, app-specific modules) reviewed for correctness
- [ ] Duplicated helpers deduplicated against package helpers
- [ ] App-specific Tailwind / CSS tokens replaced with portable styles if the package will be consumed by other apps
- [ ] Type checker passes on the moved files
- [ ] Original files preserved unless user asked to delete them

## Common Pitfalls

1. **Forgetting to rename an import when the file was renamed.** If `coastline-data-10m.ts` becomes `coastline-data.ts`, every file that imports it must change from `./coastline-data-10m` to `./coastline-data`.
2. **Leaving duplicated helpers behind.** Two copied files often contain identical `MinHeap` or `simplifyPath` implementations. The package will fail with "Duplicate identifier" or compile errors unless one is removed.
3. **Replacing an inline helper without adding the import.** If you delete `simplifyPath` and start calling `simplifyLatLngPath`, add `import { simplifyLatLngPath } from './douglas-peucker'` first.
4. **Leaving app-styled markup in a package component.** If the package component uses `bg-paper`, `text-mute`, `var(--bg-body)`, or `className` tokens that only exist in the source app, it will render unstyled in another consumer. Either keep the component style-agnostic (plain markup with optional `className` prop) or replace those tokens with portable inline styles/CSS modules during extraction.
5. **Not running type-check after the move.** The package may have stricter settings than the app; verify with `tsc --noEmit`.
6. **Barrel export naming collisions between lo-res and hi-res variants.** When extracting a codebase with paired variants (e.g., `sea-grid.ts` 360×180 + `sea-grid-hires.ts` 1080×540, or `pathfinder.ts` lo-res + `pathfinder-hires.ts` hi-res), both files export the same names (`GRID_WIDTH`, `getCostGrid`, `findSeaRoute`, etc.). A wildcard re-export from `core/index.ts` triggers `TS2308: Module has already exported a member named X`. **Fix:** export only one variant from the barrel (the one consumers actually need — usually hi-res); expose the other via a direct subpath import: `import { ... } from '@nautical-route-maps/core/sea-grid'`. Or, if both are genuinely needed at the barrel level, rename one variant's exports with a suffix (`GRID_WIDTH_HIRES`, `findSeaRouteLowRes`) — but this is rarely worth it.
7. **Type collision when the same primitive type is defined in multiple modules.** Example: `type PortType` defined in both `core/types.ts` and `geojson/generate-path-geojson.ts` triggers the same `TS2308` error from a barrel re-export. **Fix:** keep the canonical definition in the module where it originates (the one that *creates* the type) and remove the duplicate from the other. The consumer re-exports the canonical version.
8. **Prisma/database leakage into a zero-dep package.** When extracting modules, check for `import('@prisma/client')` dynamic imports or direct DB calls hidden inside helper functions. A pathfinder module that takes `prisma: PrismaClient` as an argument and queries a DB table can't ship as a zero-dependency package. **Fix:** move the Prisma-coupled functions to an app-side file (e.g., `lib/sea-grid-app.ts`), rewrite them to take generic inputs (the package's pure helpers + raw data), or accept an injected data source. Update the script callers to point at the app-side file. Verify with `grep -r 'prisma\|@/lib\|next/' <package>/src/<core|svg|geojson>/` — must be zero matches.
9. **Missing `baseUrl` in app tsconfig.** When the app uses `paths` without `baseUrl`, TypeScript rejects non-relative alias values with `TS5090: Non-relative paths are not allowed when 'baseUrl' is not set`. **Fix:** add `"baseUrl": "."` to `compilerOptions` before any `@org/pkg/*` path mappings.
10. **Subagent truncates large data files.** When dispatching a subagent to copy a file > 500 lines, the agent's default `read_file` view often truncates. The subagent then writes an incomplete copy. **Fix:** for large data files (auto-generated lookup tables, river polylines, coastline polygons), use `cp <src> <dest>` in the controller session instead of dispatching a subagent to copy. Verify line counts match: `wc -l <src> <dest>`.

11. **Vitest doesn't read `tsconfig.json` path aliases — tests silently fail to load.** After extracting code into a package and updating app imports to `@org/pkg/*` aliases, `vitest run` fails with `Failed to load url @org/pkg/... Does the file exist?`. **Root cause:** vitest/vite does NOT read `tsconfig.json` `paths` — `tsc --noEmit` passes (it reads tsconfig), but vitest resolves bare imports through its own module resolution and can't find the alias. **Fix:** create `vitest.config.ts` with explicit `resolve.alias` entries mirroring the tsconfig paths:
    ```ts
    import { defineConfig } from 'vitest/config';
    import { resolve } from 'path';
    export default defineConfig({
      resolve: {
        alias: {
          '@': resolve(__dirname),
          '@org/pkg/core': resolve(__dirname, 'packages/pkg/src/core/index.ts'),
          '@org/pkg/svg': resolve(__dirname, 'packages/pkg/src/svg/index.ts'),
          // ... one per subpath export
        },
      },
      test: {
        include: ['**/__tests__/**/*.test.ts'],
        exclude: ['node_modules/**', '.worktrees/**', '.next/**'],
      },
    });
    ```
    Also scope `test.include` to `**/__tests__/**/*.test.ts` and exclude `.worktrees/` + `.next/` — without a config, vitest scans everything and picks up Playwright specs, tsx scripts, and duplicate files in worktrees/standalone builds. **Verification:** run `npx vitest run --outputFile=/tmp/vitest.json` and parse the JSON — `success: true` and `numFailedTestSuites: 0`. Don't trust the recap claim; re-run the tests.

12. **Stale `vi.mock()` paths after extraction.** When a test mocks a module by relative path (e.g., `vi.mock('../pathfinder-hires', ...)`) and that module is moved to a package, the mock target breaks silently. The test file's import statement was updated to `@org/pkg/geojson`, but the mock still points at the old relative path — vitest either throws "module not found" or the mock doesn't intercept the right module. **Fix:** update the mock path to resolve to the same module ID the package code imports. If `generate-path-geojson.ts` (now in the package) imports `from '../core/pathfinder-hires'`, the mock must target the package's internal file: `vi.mock('../../../packages/pkg/src/core/pathfinder-hires', ...)`. The path is relative to the test file's location, pointing at the actual source file inside the package.

## Verification Checklist

- [ ] All copied files are in the target package directory
- [ ] Internal imports are relative within the package
- [ ] No duplicate `MinHeap`, `simplifyPath`, or similar helpers remain
- [ ] `tsc --noEmit` passes on the moved files
- [ ] Original files remain intact (unless deletion was requested)
- [ ] `grep -r 'prisma\|@/lib\|next/' <package>/src/core/ <package>/src/svg/ <package>/src/geojson/` returns 0 results (proves zero app coupling in non-React layers)
- [ ] If the package has barrel re-exports, no naming collisions in `core/index.ts` (TS2308 errors)

## After extraction: verify via side-effects, not just type-check

Type-check passing means the code *compiles*. It does not mean the package *works* end-to-end. When you deploy and full integration testing is blocked (auth gates, missing test data, opaque visual surfaces), fall back to **verify via side-effect API endpoints**.

The pattern: find a non-auth API endpoint that exercises the package's code, call it with a known-good input, and verify the output contains characteristics only the package could produce.

Example from the route-map extraction: hitting `/api/route-map?id=<real-itinerary-uuid>` returned a 34,786-byte SVG with **1,152 LineTo (L) commands** in the route path. A straight-line fallback would have produced ~5-10 L commands. The 1,152 number is only achievable if `findMultiPortSeaRoute` → `findSeaRoute` → A* min-heap pathfinder ran in the package. Combined with the presence of `#c8a55a` (package's exact gold color) and `#3a5575` (package's coastline color), this proves the package is loaded and running.

Quick checks after deploying a package extraction:
1. Compare response sizes: real-package-output vs fallback (size delta proves the non-fallback code path ran)
2. Count output markers specific to the package's algorithms (waypoint count, color hex codes, specific element counts)
3. Time the response: A* pathfinder runs in <500ms for cached data, much longer for fresh runs — a suspiciously fast response may indicate fallback
4. Check `page error` and `console error` counts on unauthenticated landing pages — zero errors means the chunked bundle includes the package without import resolution failures

Full auth-based testing is still needed, but the side-effect verification gives confidence the deploy worked before you spend time debugging auth.
