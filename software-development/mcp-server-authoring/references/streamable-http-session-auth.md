# Streamable HTTP: session, auth, progress (verified SDK 1.30.0, 2026-08-10)

Verified against `@modelcontextprotocol/sdk@1.30.0` while authoring `services/mcp-server`
(the design-tool web app). All type signatures read directly from `node_modules/.../dist/esm/*.d.ts`.

## Package export map (1.30.0)
```json
"."      -> dist/esm/index.d.ts      (everything)
"./server" -> dist/esm/server/index.d.ts
"./types"  -> dist/esm/types.d.ts    (ListToolsRequestSchema, CallToolRequestSchema, ProgressNotificationSchema)
"./client" -> dist/esm/client/index.d.ts
"./validation", "./experimental/*"
```
Import from `@modelcontextprotocol/sdk/server/...` or the root — do NOT rely on a
top-level barrel for every schema; `types.d.ts` holds the request/notification schemas.

## Key type facts
- `Server` (server/index.d.ts) extends `Protocol`; **`connect()` accepts one transport** —
  second connect throws. Hence per-session `{server, transport}` pairs for multi-client.
- `RequestHandlerExtra` (shared/protocol.d.ts) fields: `signal: AbortSignal`,
  `authInfo?: AuthInfo`, `sessionId?: string`, `_meta?`, `requestId`, `requestInfo?`,
  `sendNotification: (n) => Promise<void>`, `sendRequest`, `taskStore?`.
- `AuthInfo` (server/auth/types.d.ts): `{ token, clientId, scopes, expiresAt?, resource?, extra? }`.
  `extra` is `Record<string, unknown>` — the designated place to stash resolved identity.
- Transport wiring: `streamableHttp.js` line ~131 does `const authInfo = req.auth;` and passes
  it into the per-request context, so the node-http `req.auth` property is the injection point.
- `handleRequest(req, res, parsedBody?)` on `StreamableHTTPServerTransport` accepts Node
  `IncomingMessage`/`ServerResponse` directly (no web-standard conversion needed).

## Session mechanics (webStandardStreamableHttp.js)
- `sessionIdGenerator` provided → session mode: session id minted during the `initialize`
  request (`this.sessionId = this.sessionIdGenerator?.()`), returned via `Mcp-Session-Id` header.
- Subsequent requests MUST send `Mcp-Session-Id` (else `validateSession` rejects) and
  `Mcp-Protocol-Version` header.
- Re-initialize on an already-initialized session → 400 `-32600 Invalid Request`.
- `sessionIdGenerator: undefined` → stateless: no session id in responses, no validation,
  and **no server-initiated notifications** (no SSE stream to push over). Use only for
  request/response-only servers.
- `onsessioninitialized(sessionId)` callback fires right after mint — the hook for
  registering the pair in the session map before `handleRequest` returns.

## Progress notification shape
```ts
{ jsonrpc: "2.0", method: "notifications/progress",
  params: { progressToken, progress?, total?, message? } }
```
`progressToken` is required in params and MUST echo the client's `_meta.progressToken`.
`ProgressNotificationSchema` in types.d.ts. Send via `extra.sendNotification(...)` inside a
request handler, or `server.notification(...)` for out-of-band.

**Routing (verified 2026-08-10, cost a debug session):** tool-emitted notifications do NOT go to
the standalone GET stream. `extra.sendNotification` passes `{ relatedRequestId: request.id }`;
`transport.send()` (webStandardStreamableHttp.js) routes `requestId !== undefined` through
`_requestToStreamMapping` to the **per-request POST response stream** (SSE, because
`enableJsonResponse` defaults to false). Only `requestId === undefined` messages (server-initiated
notifications) go to `_standaloneSseStreamId` (the GET stream). Consequences:
- A client that never opens a GET stream still receives tool progress — on the POST body.
- A GET stream with only keepalives is NOT evidence the server is broken.
- Only ONE GET stream per session (`_standaloneSseStreamId` mapping; second GET → 409).

## Raw-curl progress probe (isolate server vs client)
When an e2e client reports 0 progress, prove the server with curl BEFORE touching client code:
```sh
ADMIN=dc_live_...; BASE=http://localhost:8787/mcp
# 1. initialize — session id comes back in the RESPONSE HEADER, not the body
SID=$(curl -s -i -X POST $BASE -H "Authorization: Bearer $ADMIN" \
  -H "content-type: application/json" -H "accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-probe","version":"0"}}}' \
  | grep -i '^mcp-session-id:' | tr -d '\r' | cut -d' ' -f2)
# 2. initialized notification (202) — Accept header is REQUIRED or you get 406
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE -H "Authorization: Bearer $ADMIN" \
  -H "content-type: application/json" -H "accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SID" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
# 3. open the GET stream (optional here — progress rides the POST response anyway)
# 4. tools/call with a literal progressToken; the PROGRESS EVENTS ARE IN THIS RESPONSE
curl -s -X POST $BASE -H "Authorization: Bearer $ADMIN" \
  -H "content-type: application/json" -H "accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_frames","arguments":{...},"_meta":{"progressToken":"probe-1"}}}' \
  --max-time 130 -o /tmp/mcp-call.json
grep -c '"method":"notifications/progress"' /tmp/mcp-call.json   # expect >0
```
The POST response is an SSE stream: `event: message` frames carrying progress notifications and the
final result. Keepalive comments (`: keepalive`) appear on the GET stream every 15s
(`DEFAULT_SSE_KEEP_ALIVE_MS`). If this probe shows progress events, the server is correct and the
bug is client-side (onprogress placement, timeout, or token matching — see sdk-client-e2e-patterns.md).

## Zero-trust bearer pattern (the design-tool web app MCP)
1. HTTP layer: parse `Authorization: Bearer <key>`; no header → 401 JSON immediately
   (before transport). Malformed → 401.
2. Resolve identity by calling upstream `GET /api/auth/me` with the bearer; cache
   `{userId, role}` keyed by token sha256, TTL ~60s. Upstream is the validator of record —
   the MCP service never re-derives authz.
3. `req.auth = { token, clientId: "designcanvas-mcp", scopes: [], extra: { userId, role } }`.
4. `tools/list`: filter admin-only tools by `extra.authInfo.extra.role === "admin"`.
5. `tools/call`: dispatch to the tool, pass `extra.signal` + token down; upstream re-checks
   paywall/kill-switch/ownership on every call (402/403/409 surface as tool errors).

## Rate limiting (in-memory, single instance)
- Per-token token bucket: refill/sec + burst capacity, keyed by token hash.
- Global in-flight semaphore for long-running tools (each SSE call holds a connection
  30–120s; unbounded concurrency exhausts the upstream pool). TryAcquire → 429-style tool
  error when saturated, release in `finally`.
- Opportunistic prune of stale buckets (`pruneBuckets`) so the map doesn't grow unbounded
  as tokens are minted/revoked.

## zod-4 `.default({})` trap
`z.object({ name: z.string() }).default({})` → TS error; the default must satisfy the
schema. Use `z.object({ name: z.string().optional() })` + handler fallback. Empty tools:
`z.object({})` with no `.default`.

## Upstream SSE client (translation core)
- POST with `Accept: text/event-stream`; check `content-type` FIRST — non-SSE response =
  guard failure (401/402/403/429) as plain JSON, throw typed `UpstreamError(status, body)`.
- Read loop: `getReader()` + `TextDecoder({stream:true})`, split blocks on blank line
  (handle both `\n\n` and `\r\n\r\n`; a block may end with one or the other).
- Per block: parse `event:` (default `message`) + `data:` lines (JSON.parse, fallback to
  `{raw}` on parse failure). `event === "done"` → capture payload; `event === "error"` → capture
  payload into `errorEvent` (upstream's own failure message, e.g. LLM/provider error — `lib/sse.ts`
  `createSseResponse` emits it before closing when the handler throws); everything else → sink.
- **If the stream ends without `done`, throw with the captured `errorEvent` payload if present**
  (`UpstreamError(502, errorEvent, "upstream stream error")`) — NOT a generic "SSE stream ended
  without done payload". A transient upstream LLM failure otherwise reads as a transport bug.
- **Log `upstream_stream_open` at stream-open (status 200)**, not just at completion — long
  30–120s streams otherwise log nothing until they finish, and look "stuck" when a client aborts
  early.
- Abort: own timeout controller (~120s) + forward `extra.signal`; map `AbortError` to a
  clean 504 tool error, never a crash. Detach the external listener in `finally`.
