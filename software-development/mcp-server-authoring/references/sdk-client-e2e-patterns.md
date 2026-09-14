# SDK client-side E2E patterns (verified SDK 1.30.0, 2026-08-10 the design-tool web app)

Driving a Streamable-HTTP MCP server from the SDK Client in a standalone E2E script
(`e2e.mjs` style, no the harness config changes). All signatures read from
`node_modules/@modelcontextprotocol/sdk/dist/esm/{client,shared}/*.d.ts`.

## Transport construction (bearer-only servers)
```js
new StreamableHTTPClientTransport(new URL("http://localhost:8787/mcp"), {
  requestInit: { headers: { authorization: `Bearer ${token}` } },
});
```
`requestInit.headers` is enough for a zero-trust bearer server — no `authProvider`, no OAuth.
Per-token clients: build one transport per token (headers differ), each with its own `Client`.

## PITFALL: `onprogress` belongs in the THIRD arg of `callTool`
```js
client.callTool(
  { name: "generate_frames", arguments: {...}, _meta: { progressToken: "e2e-gen-1" } },
  undefined,                       // resultSchema (optional)
  { onprogress: (p) => seenProgress.push(p) }   // RequestOptions — NOT inside params
);
```
- Signature: `callTool(params, resultSchema?, options?: RequestOptions)`.
- `RequestOptions.onprogress` (shared/protocol.d.ts) is where progress notifications are delivered.
- Putting `onprogress` inside `params` is silently ignored → **0 notifications** while the call
  itself completes fine. Real failure observed: server emitted progress correctly (server log clean),
  client reported `0 notifications`. `_meta.progressToken` correctly stays in params.
- **The client OVERWRITES `_meta.progressToken` with its internal messageId** (a small integer)
  when `onprogress` is provided (protocol.js `request()`: `_meta.progressToken = messageId`, and
  `_progressHandlers.set(messageId, onprogress)`). So:
  - Never assert on a literal token value in e2e — the echoed token will be an integer, not your string.
  - When debugging server logs, expect the echoed progressToken to be that integer; a custom string
    token only survives when `onprogress` is NOT set (e.g. raw-curl probes pass their own literal).
  - Client-side lookup is `_progressHandlers.get(Number(notification.params.progressToken))` —
    token types are normalized to numbers on both ends.

## PITFALL: client default request timeout is 60s — long SSE tools abort
`DEFAULT_REQUEST_TIMEOUT_MSEC = 60000` (shared/protocol.d.ts). A generate/review tool that
legitimately runs 30–120s is aborted client-side at 60s unless the request passes a longer timeout
in the options arg. Symptom from the server side: `tool invocation` logged but NO `upstream_call`
completion line — the stream was still alive when the client gave up. Set the client timeout to
~300s for real-LLM tools (the server's own ~120s upstream timeout is a separate knob). Pair it with
`resetTimeoutOnProgress: true` in the same options object — the SDK then refreshes the per-request
deadline on every progress notification (protocol.js `_onprogress` checks
`timeoutInfo.resetTimeoutOnProgress`), so a slow-but-alive stream with progress keeps going.
Confirmed option names on SDK 1.30: `{ timeout: 300_000, resetTimeoutOnProgress: true, onprogress }`.

## Assertion patterns that worked
- Tools-list role filtering: `listTools()` → assert admin tools absent/present by token role.
- Tool errors (402 paywall, 429): the SDK surfaces the result with `isError` — parse
  `res.content[0].text` as JSON and assert on the payload (`{error, status}`), NOT on a thrown
  exception.
- Garbage token: `client.connect()` rejects; the transport wraps the server's 401 JSON in an
  `Error`/`UnauthorizedError`. Assert `/401|Unauthorized|invalid bearer/i` on the message.
- Slow-tool batching: skip real generation with an env flag (`MCP_E2E_SKIP_GENERATE=1`) so the
  fast assertion suite runs without burning LLM calls.
- LLM-backed steps (generate/review): retry ONCE on failure before asserting — the upstream LLM
  provider fails transiently (a review call observed failing at ~96s, passing on retry). Assert the
  tool's own error message is surfaced (e.g. `{error, status}` in content text) so a real upstream
  failure is distinguishable from a swallowed/generic error. With the server fixed to propagate
  `error` events (see streamable-http-session-auth.md), a second consecutive failure is a genuine
  bug worth failing the suite on.

## Script hygiene
- Tokens via env (`MCP_E2E_ADMIN_TOKEN`, `MCP_E2E_FREE_TOKEN`), never hardcoded — the script is a
  committed dev artifact reusable for Phase-4 prod E2E.
- Lifecycle: `client.connect(transport)` → run asserts → `client.close()` per token, so session
  state doesn't leak between role checks.
