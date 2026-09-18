---
name: async-job-polling-ui
description: "Build the client-side UI affordance for an async server job: a 202-accepted request, a live status indicator, bounded polling, and a snapshot/state resync on completion. Use when wiring a 'Generate X' button whose work finishes later (AI image/3D/mesh generation, video processing, exports, ML inference) and the UI must reflect none → generating → ready/failed."
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [frontend, react, polling, async, api-client, ux, status-indicator]
    related_skills: [cached-artifact-validation, react-form-ux-patterns, client-csrf-token-store]
---

# Async-Job Polling UI

Build the client control for a server job that is **accepted now but finishes later**:
`POST → 202 {status:"generating"}` → poll → `ready` / `failed` → resync state so the
result renders. Common for AI generation (portrait / 3D mesh / landscape), media
processing, exports, and any long-running inference.

## When to Use

- A "Generate / Regenerate / Retry" button triggers a server job that returns 202 and runs detached.
- The UI must show a live status (none → generating → ready / failed) without a websocket push to the acting client.
- Completion is learned by re-fetching a snapshot/entity, not by the POST response.
- The acting client skips its own push notification (author-skip) and relies on the poll; *other* clients learn via the fan-out notice.

## Core Pattern

```
1. POST with raw fetch (NOT the throwing helper) → parse 2xx vs error code.
2. On 202: set a LOCAL status override to "generating" (optimistic, keyed by entity id).
3. While "generating": setInterval poll (e.g. 3s), BOUNDED (e.g. 90s–5min).
4. Each poll re-fetches the snapshot/entity; detect completion; on settle → clear
   interval, set override to ready/failed, call onSettled() to resync.
5. On bound expiry: clear interval and FALL BACK to server-derived status (no infinite spinner).
```

Status model when the snapshot carries the artifact URL but **no explicit status field**:
derive base status from URL presence (`url ? "ready" : "none"`), and let the local
override win while generating. Honor an explicit status field if the server ever adds one.

## Pitfalls (the valuable part)

### 1. Signed/presigned URLs re-sign on every fetch — compare a STABLE identity, not the full URL
Asset URLs backed by object storage (R2/S3 presign, proxy endpoints) get a **fresh
signature on every snapshot fetch**. The query string churns even when the underlying
asset is unchanged. If your poll detects "ready" by `newUrl !== oldUrl`, it fires on
the *first* poll every time (false positive) — or, worse, never stabilizes.

**Fix:** compare a stable identity — the URL **pathname** (which carries the asset id),
not the full URL. The path only changes when a *new* asset is resolved, which is exactly
the "ready" signal.
```ts
function assetIdentity(url: string | null | undefined): string | null {
  if (!url) return null;
  try { return new URL(url).pathname; } catch { return url; }
}
// ready when: fresh.url && assetIdentity(fresh.url) !== basePath
```
Capture `basePath` from the pre-generation URL and **pin it** (do NOT put it in the poll
effect's deps) so resyncs flowing through don't move the goalposts. This is the same
principle as `cached-artifact-validation`: compare the stable identity, not a volatile
representation (there: content hash vs timestamp; here: pathname vs signed URL).

### 2. The shared `post()`/`request()` helper THROWS on non-2xx — you can't check `res.ok`
Many codebases have a central fetch wrapper that throws on any non-2xx so callers don't
decode errors. If a brief/spec shows `const res = await post(...); if (res.ok) {...}`,
that check is **dead code** — `post` never returns a non-ok response, it throws.

**Fix:** for endpoints that must surface a *friendly inline* error (402 premium, 429 cap,
403 role, 400 validation), use **raw `fetch`** with the CSRF header, never throw on HTTP
error, and map the error code to a human reason:
```ts
const res = await fetch(`${API_URL}/...`, { method:"POST", credentials:"include",
  headers: { "Content-Type":"application/json", ...csrfHeader() }, body: JSON.stringify(body) });
if (res.ok) return { ok: true, status: res.status };
let error = `Failed (status ${res.status})`;
try { const code = parseErrorCode(await res.text());
  if (code === "premium_required") error = "…upgrade to generate one.";
  else if (code === "too_many_x") error = "…limit reached — regenerate instead.";
  else if (code) error = code;
} catch { /* keep generic */ }
return { ok: false, status: res.status, error };
```
Match the style of sibling generate-* functions in the same file — don't invent a new shape.

### 3. Key the local status override by entity id — avoid stale-flash on selection change
If the control is reused across a selection (different token/character/scene), a bare
`status` state will flash the *previous* entity's "generating" onto the newly selected one.
Store `{ id, status }` and only apply the override when `override.id === current.id`.

### 4. Bound the poll and fall back — never spin forever
Set `POLL_MAX_MS` matched to the job's real latency (portraits ~90s; Meshy text-to-3d
2–4min → use 300s). On expiry, clear the interval and **drop the override** so the
server-derived status shows through. The job may still land later via the push-notice
resync; the control just stops actively polling. An unbounded spinner is worse than a
control that quietly returns to "none/ready".

### 5. Use a ref for the settle callback so the interval doesn't re-subscribe
If `onSettled` is in the poll effect's deps and the parent re-creates it each render, the
interval tears down and rebuilds constantly. Mirror it into a ref
(`onSettledRef.current = onSettled`) and call `onSettledRef.current()`, keeping the effect
deps to `[status, entity.id, scopeId]`.

### 6. Reset transient draft/error state when the entity changes
A description textarea and inline error belong to the selected entity. Clear them in an
effect on `[entity.id]` so switching selections doesn't carry over a stale draft or error.

### 7. Determinate progress: the entity PROP is stale during generation — capture the poll response
Once the server sends live progress (`progress: 0–100` + a `phase` string) alongside
status, the naive move is to render the bar from the entity prop (`character.meshProgress`).
But the prop is **stale for the whole generation**: the parent only refetches/resyncs on
*settle* (ready/failed), and the push notice (if any) usually just toasts — it does not
refetch. So a prop-driven bar sits frozen at 0% for the entire 2–4 minutes.

**Fix:** capture the freshest progress from each poll response into local state, keyed by
entity id (mirror the `{id, status}` override pattern of pitfall #3), and prefer it over
the prop:
```ts
const [live, setLive] = useState<{ id: string; progress: number | null; phase: Phase | null } | null>(null);
// inside the poll .then (before the settle check):
setLive({ id: entity.id, progress: fresh.progress ?? null, phase: fresh.phase ?? null });
// at render:
const cur = live && live.id === entity.id ? live : null;
const progress = cur?.progress ?? entity.progress ?? null; // live wins, prop is the fallback
const pct = progress ?? 0;                                  // aria-valuenow + fill width
```
Reset `live` in the `[entity.id]` effect (pitfall #6). Render with
`role="progressbar"` + `aria-valuenow/min/max`, a phase label mapped from the raw phase
(e.g. `preview→"Sculpting"`, `refine→"Texturing"`, `download→"Finalizing"`, else
`"Generating"`), the numeric `%` when present, and a `transition: width …s` on the fill to
smooth the 3s poll steps (honor `prefers-reduced-motion`). Parse the progress fields in the
API layer (`asNumber(...) ?? null`, snake_case fallback) — never read raw response keys in
the component.

### 4b. Measure the job before you set the bound — a bound below real latency strands the user

A 90s bound on a job that actually takes 100–165s is worse than no bound: the poll expires
mid-generation, the override is dropped, and the control falls back to the server-derived state
(`none`), so the user is told the thing they just asked for does not exist WHILE it is being built.
Worse, they will press Generate again.

**Set the bound from a MEASURED end-to-end run, not from the shape of the work.** Real case: an
interview-guide generator was assumed to take ~30s; measured through the server it took **165s**
(and 100s when run directly, so the server path was slower too). The bound went 90s → 240s. Then
re-check it after ANY change that alters provider or parallelism — the same build ran >240s while
its provider calls were still serial, and got 2.5x faster once they were parallelised.

Corollary: if the work behind the button is a per-item loop, PARALLELISE it before widening the
bound. A wider bound hides the real problem; concurrency fixes it.

## Visibility / gating

Generation is usually gated server-side (role + premium feature). The client control should
*hide itself* when the viewer lacks the role/feature or the backend capability is absent
(e.g. no API key configured) — but **never hide the resulting artifact**: display is ungated,
so a premium user's generated asset renders on a free viewer's board. If there's no config
endpoint to tell the client whether the backend is configured, accept a prop and default it
on with a TODO to thread a real server flag; the server rejects with a clear error anyway.

## Verification

- Typecheck clean; existing tests pass.
- Non-privileged viewer / unconfigured backend → component renders `null` (early return before any JSX).
- Manually confirm: 202 flips UI to "Generating…", poll detects ready via **pathname change**, resync renders the asset, and the bound stops the spinner.

## Reference

See `references/generate-affordances.md` for the concrete implementation
(`api.ts` raw-fetch contract, the `TokenMeshGenerate`/`LandscapeGenerate`/`CharacterMeshGenerate`
structure, poll bounds per job type, and the `meshUrl`-only snapshot that forced the
local-override + pathname-comparison design).
