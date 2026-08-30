# Component-Library Adoption Intake (variant of design-reference-intake)

When the question is "is this component/visual library useful for OUR APPS" (not "improve our skills"), the deliverable changes: a **USE-CASES.md committed into the locally cloned repo** + a Mnemosyne pointer — not skill edits. Proven 2026-08-23 against MengTo/threeui (MIT, 100 React shader/WebGL/CSS components, cloned to ~/Projects/threeui, full `npm run build` verified).

## Workflow

1. **Clone and verify the build before analyzing.** `git clone --depth 1`, `npm install`, run the repo's own full build. A catalog you can't build is a different recommendation.
2. **Extract the REAL catalog programmatically, not from the README.** Component inventories usually live in a data file (threeui: `src/data/shaders.tsx`, 412KB). Fetch it raw, regex out `id`/`label`/`category`/`runtime`/`description` per entry, and group by category. The README's "50 components" claim hid 102 route entries across 8 categories — the grouped table is what makes per-project mapping fast.
3. **Check the install surface.** Look for an npm package + subpath imports (`exports` map in package.json) vs copy-source-only, and whether per-component subpaths keep bundles small (threeui: `@designcodeio/threeui/components/<Name>`).
4. **Map to every active project, not just the obvious one.** Rows = use case | components | where in the app | effort (XS/S/M). Include a "skip / reference-only" verdict where fit is poor (threeui's r128–r165 canvases vs simcityclone's r185 scene graph) — an honest no-fit row is as valuable as the picks.
5. **End each project section with a priority pick** and close the doc with a suggested first sprint (2–3 components, ~2h). The doc is written for a future session with zero context.
6. **Record cross-cutting caveats once:** Three.js version aliasing (`"three128": "npm:three@0.128.0"`) means catalog components are self-contained canvases — never wire into a host app's existing scene graph; full-HTML components need runtime assets copied to `public/` (or `sourceUrl`/`assetBaseUrl` overrides); one active WebGL canvas per page; lazy-load + `prefers-reduced-motion`.
7. **Mnemosyne pointer** (global, ~0.75): repo URL, license, clone path, USE-CASES.md path, first-sprint pick.

## Pitfalls

- **NODE_ENV=production in the ambient shell makes `npm install` silently skip devDependencies** ("added 2 packages" for a repo with react+vite+typescript devDeps). Fix: `npm install --include=dev`. Symptom: missing `node_modules/.bin/vite` etc. on first build attempt.
- Batch the independent fetches (README + raw catalog file) in one turn; the catalog regex pass runs locally in execute_code.
- Three.js version soup inside a catalog is normal (r128–r165 via npm aliases). It only matters when mixing into a host scene graph — isolated canvases are safe.
