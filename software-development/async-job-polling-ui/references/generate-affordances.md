# "Generate X" affordances (portrait / landscape / character-mesh / token-mesh)

Session-specific detail for the `async-job-polling-ui` skill, drawn from building a production app
DM-only token 3D-model UI (P4 of the Meshy text-to-3d plan, 2026-07-22).

## The four affordances (same skeleton)

| Component | Job | Gate | Poll bound | Detects ready via |
|---|---|---|---|---|
| `CharacterMeshGenerate.tsx` | character 3D mini | `ai_character_mesh` (player tier) | 300s | `getCharacter(id).meshStatus` ready/failed |
| `LandscapeGenerate.tsx` | scene terrain | `ai_landscape` (DM tier) | 90s | snapshot `landscapeStatus` (explicit field) |
| portrait control | character portrait | `ai_portrait` | 90s | `getCharacter(id).portraitStatus` |
| `TokenMeshGenerate.tsx` (NEW) | token 3D model | `ai_landscape` (DM tier) + DM role | 300s | **snapshot token `meshUrl` pathname change** |

Characters and landscapes have an explicit status field the client can poll. **Tokens do
not** — the scene snapshot `TokenState` carries only `meshUrl` (no `meshStatus`). That
asymmetry is what forced the local-override + pathname-comparison design.

## api.ts contract (the throwing-helper trap)

`request()` throws on any non-2xx; `post()` wraps it. So the brief's
`const res = await post(...); if (res.ok)` is dead — `post` never returns non-ok. All
`generate*` functions therefore use **raw fetch** and never throw on HTTP error:
`generatePortrait`, `generateMesh`, `generateLandscape`, and the new `generateTokenMesh`.
They return `{ ok, status, error? }` and map server error codes to friendly strings:
`premium_required`, `too_many_*`, `feature_disabled`. CSRF goes via `csrfHeader()`
(double-submit; `request()` keeps the in-memory token in sync from response bodies).

`generateTokenMesh(tokenId, description)` → `POST /tokens/:id/generate-mesh`,
body `{ description }`. Server: DM-only + `requireFeature("ai_landscape")`,
`MAX_TOKEN_MESHES_PER_ACCOUNT` (default 30), returns `202 { meshStatus: "generating" }`.
Error codes: 402 `premium_required`, 429 `too_many_token_meshes`, 403 DM-only /
`feature_disabled`, 400 missing/overlong (>600 char) description, 404.

## Why pathname comparison (the signed-URL trap)

`resolveAssetUrl` (apps/api/src/storage.ts) returns an **R2 presigned URL (3600s)** or a
proxy `/assets/:id` URL. Presign re-signs on every snapshot fetch → the query string
churns. `TokenMeshGenerate` captures `basePath = new URL(token.meshUrl).pathname` before
generation and compares each poll's fresh token `meshUrl` pathname against it. A changed
path == a new asset resolved == ready. `basePath` is deliberately NOT in the poll effect's
deps so resyncs don't move it.

## Status model in TokenMeshGenerate

```ts
const baseStatus = token.meshUrl ? "ready" : "none";   // snapshot has URL only
const status = (override?.id === token.id ? override.status : null) ?? baseStatus;
```
202 → `setOverride({ id, status: "generating" })`. Poll `getSceneState(sceneId)` every 3s,
bounded 300s; on pathname change → `setOverride(ready)` + `onSettled()` (Tabletop calls
`resyncScene()`). On bound expiry → `setOverride(null)` (falls back to baseStatus). The
`token_mesh_status` push notice toasts *other* clients (author-skip in `usePresence`);
the acting DM learns via this poll.

## Mount point + gating

Mounted in the DM "Edit token" modal (`Tabletop.tsx`), which is itself gated
`{isDm && selectedToken && ...}`. The component also early-returns `null` unless
`isDm && meshyConfigured`. There is **no config endpoint** exposing whether `MESHY_API_KEY`
is set (only `/health`), so Tabletop passes `meshyConfigured={true}` with a TODO to thread
a real server flag (e.g. on `/auth/me`). Token meshes have no parametric stub, so an
unconfigured server must hide the control (unlike characters, which fall back to the
parametric builder).

## Verification used

`npm run typecheck` (5 workspaces) + `npm test` (159 tests). Commit specific files only —
a concurrent P5 subagent was writing `meshy.test.ts` in the same repo; `git add <files>`
avoided sweeping it in.
