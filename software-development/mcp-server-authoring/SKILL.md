---
name: mcp-server-authoring
description: Author MCP servers with the SDK - tools, transports, zod.
---

# MCP Server Authoring

Build MCP servers that expose an application's operations as tools. This covers the server side (the `@modelcontextprotocol/sdk`); for the the harness *client* side (connecting `mcp_servers` in config) see the `native-mcp` skill.

## When to use
- Creating a new `apps/<name>` MCP workspace (e.g. an agent-accessible ops server over an existing REST API)
- Adding tools to an existing MCP server
- Debugging `registerTool` type errors or SDK/zod incompatibilities

## Architecture: thin client over existing REST
The most maintainable shape is a pure REST client — no DB access, no response re-validation:
- The host app's API stays the validator of record; the MCP server just translates tool calls → HTTP requests.
- Preserve server-authoritative contracts: mutations still go through the app's normal routes (audit logging, validation, versioning all live there).
- Map API error bodies (`{ error: string }`) to a typed error hierarchy (401/403/404/409/500) so tools can surface failure strings without crashing the server.

## Tool definitions as data (testable without the SDK)
Define tools as a plain array of `{ name, title, description, input (zod), call(client, input) }`, then wire them in a loop. This lets unit tests assert route/method/body mapping with a stubbed client — no MCP SDK runtime needed in tests.

```ts
export const toolDefs: ToolDef[] = [ { name: "admin_health", ..., input: z.object({}), call: (c) => c.request({ path: "/admin/health" }) }, ... ];
export function registerTools(server: McpServer, client: ApiClient): void {
  for (const def of toolDefs) {
    server.registerTool(def.name, { title: def.title, description: def.description, inputSchema: def.input },
      async (input: unknown) => textContent(await def.call(client, input)));
  }
}
```

## `registerTool` signature (SDK 1.30.x) — verified
```ts
server.registerTool(name: string, config: { title?: string; description?: string; inputSchema?: AnySchema }, cb: ToolCallback): RegisteredTool
```
- **3 arguments** — name, config object, callback. Passing 4 args (schema as a separate 3rd arg) is the deprecated `tool()` style → `TS2554: Expected 3 arguments, but got 4`.
- The callback receives the **parsed input object directly** — NOT wrapped in `{ input }`.
- `inputSchema` accepts a single zod schema (`AnySchema`), not a raw shape — use `z.object({...})`, not `{ field: z.string() }`.

## PITFALL: dual zod instances break `inputSchema` typing
`@modelcontextprotocol/sdk@1.30.0` declares `zod ^3.25 || ^4.0`, but its `zod-compat` module imports the **v4-only subpaths** `zod/v3` and `zod/v4/core` — so the SDK's `AnySchema` types (`z3.ZodTypeAny | z4.$ZodType`) come from a zod **v4** instance. If your workspace pins an older zod (e.g. `3.23.8`), npm installs a separate nested zod under the SDK, and a schema from your old instance fails assignment:
```
TS2322: Type 'ZodTypeAny' is not assignable to type 'AnySchema | ZodRawShapeCompat | undefined'
```
**Fix (verified 2026-08-09 on the D&D VTT project, monorepo):** the MCP workspace must use `zod@^4.0.0` so its schemas are v4 types matching the SDK's instance. Other workspaces can stay on v3 (`^3.25.0`); the two majors coexist cleanly in one lockfile. Do NOT bother aligning everyone to `^3.25.0` to "dedupe" — the SDK's v4-subpath imports mean npm keeps a v4 nested copy regardless, and a v3 schema will never satisfy `AnySchema`. Verify with `node -e "console.log(require('./node_modules/zod/package.json').version)"` + check `apps/<mcp>/node_modules/zod` resolves to 4.x, then `npm run typecheck --workspace apps/<mcp>` must pass. (Full incident + check commands: `references/sdk-registertool-and-zod.md`.)

## Role-filtered `tools/list` on the low-level `Server` (SDK 1.30 — verified)
When tools must be advertised per-role (admin-only tools hidden from regular clients), the high-level
`McpServer.registerTool` can't filter — drop to the low-level `Server` +
`server.setRequestHandler(ListToolsRequestSchema, ...)`:

- **SDK 1.30 has NO `zodToJsonSchema` util** (verified: `grep -rl zodToJsonSchema dist/esm` is empty).
  Use `toJsonSchemaCompat(schema, { strictUnions: true, pipeStrategy: "input" })` from
  `@modelcontextprotocol/sdk/server/zod-json-schema-compat.js` — it accepts zod **v4** schemas AND
  `.default()`-wrapped objects (mcp.js uses it internally for registerTool). Importable via the
  package export map (`server/zod-json-schema-compat`).
- Build the tool registry as data (`ToolDef[]` with `input: z.ZodTypeAny`), filter by
  `extra.authInfo.extra.role` at request time, map to `{ name, description, inputSchema }`.
- `CallToolRequestSchema` handler: find the def, zod-parse `request.params.arguments`, build a
  `ToolCtx` (upstream client, token, identity, `extra.signal`, progress sender), return
  `{ content: [{ type: "text", text }], isError }`.

## PITFALL: SDK client `callTool` — `onprogress` lives in the THIRD arg, not params
`client.callTool(params, resultSchema?, options?)` — progress notifications only arrive if you pass
`{ onprogress: (p) => ... }` as the third `options` arg (`RequestOptions` in shared/protocol.d.ts).
Putting `onprogress` INSIDE the `params` object is silently ignored → **0 notifications received**
while the call completes fine (hit 2026-08-10 on the design-tool web app e2e; server-side
`extra.sendNotification` wiring was already correct). `_meta: { progressToken }` correctly stays in
params. Also: `StreamableHTTPClientTransport` takes `requestInit: { headers: { authorization: "Bearer …" } }`
for token auth (no authProvider/OAuth needed for raw bearer).

## PITFALL: SDK client default request timeout is 60s — long-running tools abort
`DEFAULT_REQUEST_TIMEOUT_MSEC = 60000` in shared/protocol.d.ts. An SSE-backed tool that legitimately
runs 30–120s (generation, review) will be aborted CLIENT-side at 60s unless you pass a longer
per-request timeout in the `options` arg — the server stream is still alive and logs show no
`upstream_call` completion. E2E scripts driving real LLM tools MUST set e.g.
`{ timeout: 300_000 }` (verify the exact option name in your SDK version's `RequestOptions` — older
builds expose `requestTimeout`). The server's own ~120s upstream timeout is a separate knob.

## Transports
- **stdio**: `new StdioServerTransport()` — for local dev and `mcp_servers` stdio config. Log to stderr, never stdout (protocol owns it).
- **HTTP (streamable)**: `StreamableHTTPServerTransport` on a bare `node:http` server — no framework needed. `/healthz` → 200 (Railway healthcheck); `/mcp` handles GET (SSE stream), POST (JSON-RPC), DELETE (session teardown).

### Multi-client session model (verified SDK 1.30.0)
`Server.connect()` accepts ONE transport — connecting a second throws `Already connected`. So multi-client hosting = **one Server + one transport per client session**, registered in a `Map<sessionId, {server, transport}>`:
- Create the pair on first contact (POST with `initialize`, no `Mcp-Session-Id` header); the transport's `sessionIdGenerator: () => randomUUID()` mints the session during initialize and it's returned in the `Mcp-Session-Id` header.
- Subsequent requests carry `Mcp-Session-Id` → look up the pair, call `transport.handleRequest(req, res)` on the stored instance.
- DELETE request → `transport.close()`, drop from the map (the SDK does NOT auto-clean; sessions also linger until process restart).
- Session mode is what makes **progress notifications work** — but see the routing correction below: tool-emitted notifications ride the per-request POST response stream, NOT the standalone GET stream. Stateless mode (`sessionIdGenerator: undefined`) can't push server-initiated notifications at all.
- Per-request tool handlers get `extra.sessionId` — use it to build per-session context if needed.

### PITFALL: where progress notifications actually go (SDK 1.30 verified 2026-08-10)
`extra.sendNotification(...)` inside a tool handler passes `{ relatedRequestId: request.id }` to
`transport.send()` (shared/protocol.js ~326). In `webStandardStreamableHttp.js` `send()`:
- `requestId !== undefined` → routes via `_requestToStreamMapping` to the **dedicated per-request
  SSE stream** — i.e. the POST response stream of that `tools/call`. With `enableJsonResponse`
  defaulting to **false**, every POST request becomes an SSE response, so progress events are
  interleaved with the final result on the POST response body.
- Only messages with `requestId === undefined` (server-initiated, out-of-band) go to the standalone
  GET stream (`_standaloneSseStreamId`).
So: **a client that never opens a GET stream still receives tool progress** (it arrives on the POST
response), and a GET stream will appear "empty" of progress while the POST body carries all of it.
Debug with the raw-curl probe in `references/streamable-http-session-auth.md` before touching client
code — the server is often already correct.

### Bearer auth threading: `req.auth` → `extra.authInfo` (zero-trust pattern)
Set `(req as any).auth = { token, clientId, scopes, extra }` BEFORE `transport.handleRequest(req, res)`; the SDK passes it through to every request handler as `extra.authInfo` (type `AuthInfo` from `server/auth/types.d.ts`: `{token, clientId, scopes, expiresAt?, resource?, extra?}`). This is the clean way to inject an API-key identity without per-request globals:
- Validate the bearer at the HTTP layer (extract header, look up identity, 401 on missing/bad) — reject before the transport ever sees it.
- Stash the resolved identity (`{userId, role}`) in `authInfo.extra` so `tools/call` handlers can read `extra.authInfo.extra.role` for role-filtered behavior.
- `extra.signal` is an AbortSignal for client disconnect — wire it to upstream `AbortController`s so long calls die when the client leaves.

### Long-running tools: upstream SSE → MCP `notifications/progress`
For tools backed by an upstream SSE stream (30–120s generation):
- POST upstream with `Accept: text/event-stream`; read the stream with `getReader()` + `TextDecoder`, splitting on blank-line separators (support both `\n\n` and `\r\n\r\n`).
- **Distinguish guard failures from streams by content-type**: if the response is not `text/event-stream`, the upstream answered plain JSON (401/402/403/429) before streaming — parse and surface as a clean tool error, don't try to read SSE.
- Capture the terminal `done` event's payload; every other event → `extra.sendNotification` with `{ jsonrpc: "2.0", method: "notifications/progress", params: { progressToken, progress?, total?, message? } }`, where `progressToken` comes from the client's request `_meta.progressToken` when supplied.
- **PITFALL: upstream `error` events get swallowed behind a generic 502.** Upstream SSE routes
  (e.g. `lib/sse.ts` `createSseResponse`) emit `event: error` + `{error: "..."}` then close when the
  handler throws (LLM failure, provider timeout). If the client only treats `done` as terminal and
  otherwise throws `"SSE stream ended without done payload"`, the real failure message is lost and
  a transient LLM error reads as a transport bug. Capture `event === "error"` payloads into a
  variable and, when the stream ends without `done`, throw `UpstreamError(502, errorEvent)` with the
  captured payload — surface the upstream's own message. (Real case 2026-08-10: review tool returned
  generic 502 at ~96s; the actual upstream error was a transient review-LLM failure.)
- **Log `upstream_stream_open` the moment an SSE stream opens** (status 200), not just on
  completion/failure. Otherwise a legitimate 30–120s stream shows zero log lines and reads as
  "stuck" when the client aborts at its 60s default.
- Abort upstream on `extra.signal` (client disconnect) and on a hard timeout (~120s matches prod SSE heartbeat behavior); translate `AbortError` into a clean 504-style tool error, never a crash.

## PITFALL: log the in-flight limiter's CAPACITY, not its live active count
In-flight limiters expose the *current* active count (correctly 0 at startup); logging
`maxInflight: <activeCount>` at startup prints `maxInflight: 0` and looks like the cap was never
configured. Expose a `get capacity()` on the limiter and log that. (Hit 2026-08-10 on the design-tool web app:
startup log said `maxInflight: 0` with a configured cap of 8.)

## PITFALL: zod-4 `.default({})` on a required-field object fails typecheck
`z.object({ name: z.string() }).default({})` errors — zod's default value must satisfy the schema, and `{}` lacks `name`. The fix is to make fields optional: `z.object({ name: z.string().optional() })` and fall back in the handler. Empty-arg tools: `z.object({})` alone (no `.default`). (Applies to any zod-4 project, not just MCP; hit while authoring the the design-tool web app tool registry.)

## Tests to write
1. Client: bearer header sent, query serialization (null/undefined skipped), JSON body, each status → correct error class, network failure → generic error.
2. Tool defs: exactly the planned tool names; each maps to the right route/method/body; `id` stripped from update/revoke bodies; input validation rejects bad values.
3. `tools/list` handshake returns exactly the registered tools (E2E or script).

## Env shape (thin server)
- `API_URL` (base), `ADMIN_TOKEN`/equivalent (bearer), `PORT` (null → stdio, set → HTTP), `LOG_LEVEL`. Fail fast at startup if the token is missing.
- Rate-limit knobs via env (e.g. `RATE_LIMIT_REQS` 60/min, `RATE_LIMIT_BURST` 20) so prod tuning needs no rebuild.
- **Standalone service package hygiene:** a `services/<name>/` package living inside a larger repo needs root `.gitignore` entries
  (`/services/*/node_modules/`, `/services/*/dist/`) or `git status` floods with the dependency tree — add them in the same commit that adds the package. Keep the package OUT of the root pnpm workspace (own `pnpm-workspace.yaml`) so its SDK/zod versions can't collide with the app's.

## PITFALL: session-cookie API's CSRF guard blocks mutating MCP tools
If the wrapped REST API protects session mutations with a double-submit CSRF guard (cookie + `x-csrf-token` header), every MCP POST/PATCH/DELETE fails `403 csrf_invalid` — the MCP server has no cookie session. Exempt machine auth at the API's CSRF guard, but ONLY for a **valid configured bearer token**:
- Export a constant-time check from the auth module (`isAdminBearer(req)` comparing `Authorization: Bearer <token>` against `ADMIN_API_TOKEN` via `timingSafeEqual`).
- In the CSRF guard: `if (isAdminBearer(req)) return;` — skip the double-submit check.
- **Never** exempt on `header.startsWith("Bearer ")` alone — a garbage bearer + valid session cookie would bypass CSRF entirely (real regression, caught in review on the D&D VTT project 2026-08-09).
- Add unit tests: valid-token-exempt, garbage-token-still-403, token-unset-still-403, GET/EXEMPT_PATHS unaffected.

## E2E proof without wiring the harness config
A the harness `mcp_servers` stdio entry is just an SDK Client over `StdioClientTransport`. Prove the whole server with a script that does the same (no config changes, no restart):
```ts
const client = new Client({ name: "e2e", version: "0.1.0" });
await client.connect(new StdioClientTransport({ command: "npx", args: ["tsx", "src/index.ts"], cwd: MCP_ROOT, env: { DNDVTT_API_URL, DNDVTT_ADMIN_TOKEN } }));
const tools = await client.listTools();                 // assert exact tool count/names
const res = await client.callTool({ name: "...", arguments: {...} });
```
Checks: handshake succeeds, `tools/list` returns exactly the expected tools, health works, then a real create → update → delete round-trip, and verify the **audit trail in the DB** (actor = service account, soft-delete fields). Evidence → `docs/e2e-review/<date>-<feature>.md`.

## Related
- `native-mcp` — the harness client-side config for connecting to this server.
- `subagent-implementation-recovery` — subagents generating large new workspaces often die mid-generation; recover by writing the files yourself.
- Reference: `references/sdk-registertool-and-zod.md` — verified SDK signatures, the zod incident, check commands.
- Reference: `references/streamable-http-session-auth.md` — multi-client session model, `req.auth`→`extra.authInfo` bearer threading, SSE→progress translation, rate limiting (all verified on SDK 1.30.0 while building the the design-tool web app MCP service).
- Reference: `references/sdk-client-e2e-patterns.md` — SDK Client E2E: bearer transport construction, `onprogress` in callTool's 3rd arg (not params), 60s default client timeout vs long SSE tools, assertion patterns.
