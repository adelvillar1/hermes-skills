# Cross-Platform Native Binaries on Railway

## The Trap

When `package.json` pins platform-specific binaries, Railway's Linux build daemon fails with `EBADPLATFORM`.

```json
// BAD: pins darwin-only binaries
"dependencies": {
  "@esbuild/darwin-arm64": "^0.21.5",
  "@rollup/rollup-darwin-arm64": "^4.62.4",
  "@img/sharp-darwin-arm64": "^0.35.3"
}
```

Error:
```
npm error EBADPLATFORM: Unsupported platform for @esbuild/darwin-arm64@0.21.5: 
wanted {"os":"darwin","cpu":"arm64"} (current: {"os":"linux","cpu":"x64"})
```

## The Fix

Two working variants — pick based on how the binary is used:

**Variant A — replace platform-specific packages with parent packages** (best when the
parent is already a direct dep or transitively present; the parent's own
optionalDependencies pull the right binary per platform):

```json
// GOOD: parent packages with optionalDependencies for all platforms
"dependencies": {
  "esbuild": "^0.21.5",
  "rollup": "^4.62.4",
  "sharp": "^0.35.3"
}
```

**Variant B — move the platform binaries to `optionalDependencies`** (best when you
cannot drop the explicit packages, e.g. the root build needs them and you don't want
to rely on the parent's transitive resolution). npm skips them on non-matching
platforms and still installs them locally:

```json
// GOOD: same packages, but optional → Linux skips, macOS installs
"dependencies": {
  "@vitejs/plugin-react": "^4.3.1",
  "canvas": "^3.2.3",
  "serve": "14.2.3",
  "sharp": "^0.35.3"
},
"optionalDependencies": {
  "@esbuild/darwin-arm64": "^0.21.5",
  "@img/sharp-darwin-arm64": "^0.35.3",
  "@img/sharp-libvips-darwin-arm64": "^1.3.2",
  "@rollup/rollup-darwin-arm64": "^4.62.4"
}
```

Then regenerate the lockfile (`npm install --package-lock-only --ignore-scripts`) so
the entries carry `"optional": true` — the committed lockfile is what the builder
reads.

## `railway up` vs GitHub auto-deploy — why one fails and the other doesn't

A **GitHub-triggered Railway deploy builds from a clean snapshot** of the repo, so a
lockfile with darwin entries is never materialized against a local tree. A
**`railway up` uploads the LOCAL working tree** (including a populated `node_modules`
with platform binaries), so the builder's `npm install` re-validates every entry
against Linux/x64 and EBADPLATFORM surfaces. Same package.json + lockfile, different
result depending on the deploy path. If a GitHub deploy succeeded but `railway up`
fails with EBADPLATFORM, the fix is in the dependency declaration, not the deploy
method.

## `.npmrc` — empty `omit=` is invalid in npm 10

An empty `omit=` (used historically to "override a global omit=dev") is **rejected by
npm 10** with `npm warn invalid config Must be one or more of: dev, optional, peer`.
The invalid config breaks optional-dep filtering and can itself contribute to the
platform check misfiring. Don't try to statically override a global `omit=dev` with
`omit=` — rely on npm's default (omit nothing) and, if the build env forces it,
inject `--include=dev --include=optional` on the CLI instead. Minimal safe `.npmrc`:

```ini
fund=false
audit=false
```

## The Lockfile Trap

A macOS-generated `package-lock.json` pins darwin-arm64 entries. Railway's railpack copies any lockfile in, causing EBADPLATFORM even if you fixed `package.json`.

**Solution**: Don't commit `package-lock.json` for repos with native binaries. Add to `.npmrc`:
```ini
package-lock=false
include=dev
include=optional
fund=false
audit=false
```

## `package-lock=false` — Why

Railpack's build step copies any lockfile present in the build context. With native binaries, this pins the darwin-only entries. `package-lock=false` tells npm to ignore the lockfile entirely, letting each environment generate its own from `package.json` semver ranges.

## Global `omit=dev` Override

A global npm config (`~/.npmrc` or `/etc/npmrc`) may set `omit = ["dev"]`, which strips devDependencies (typescript, vitest, etc.) from `node_modules`. Railway build daemon needs devDependencies to compile.

**Fix**: Add `include=dev` to project `.npmrc` to override the global config.

## Verification

After fixing, the Railway build log should show:
- No `EBADPLATFORM` errors
- `✓ Compiled successfully` (or equivalent)
- All services report `SUCCESS` via `railway service list --environment production --json`

## Historical

the D&D VTT project terrain-from-map deploy (2026-08-06): 3 failed builds (EBADPLATFORM). Root `package.json` pinned `@esbuild/darwin-arm64`, `@rollup/rollup-darwin-arm64`, `@img/sharp-darwin-arm64`. Fixed by:
1. Replacing platform deps with parent packages
2. Removing `package-lock.json` from git
3. Adding `package-lock=false` + `include=dev` + `include=optional` to `.npmrc`

the D&D VTT project dice-results deploy, same day (second occurrence): `railway up` to staging
failed both services at `npm install` with the same EBADPLATFORM, while the GitHub
auto-deploy minutes earlier had succeeded. The repo had since grown darwin binaries
back into `dependencies` (commit `89339af`). Resolved with **Variant B**: moved the
four binaries to `optionalDependencies`, dropped the invalid empty `omit=` from
`.npmrc`, regenerated the lockfile (entries now `"optional": true`). Lesson: the
deployment method determines whether the failure surfaces — GitHub clean-snapshot
builds masked it; `railway up` exposes it.
