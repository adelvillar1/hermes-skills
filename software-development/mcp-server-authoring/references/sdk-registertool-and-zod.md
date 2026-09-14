# MCP SDK 1.30.0 — verified signatures, zod dual-instance incident (2026-08-09)

Verified against `@modelcontextprotocol/sdk@1.30.0` installed in the the D&D VTT project monorepo
(`node_modules/@modelcontextprotocol/sdk/dist/esm/server/mcp.d.ts`).

## `registerTool` signature (the API to use)

```ts
registerTool<OutputArgs, InputArgs>(name: string, config: {
    title?: string;
    description?: string;
    inputSchema?: AnySchema;   // a SINGLE zod schema (z.object({...})), not a raw shape
    outputSchema?: AnySchema;
    annotations?: ToolAnnotations;
    _meta?: Record<string, unknown>;
}, cb: ToolCallback<InputArgs>): RegisteredTool
```

- Exactly **3 arguments**. The old `tool(name, description, paramsSchema, cb)` / `tool(name, paramsSchema, annotations, cb)` overloads are `@deprecated` — passing 4 args to `registerTool` gives `TS2554: Expected 3 arguments, but got 4`.
- The callback receives the **parsed input object directly** (the output of the zod `inputSchema`), NOT `{ input }`-wrapped.
- `inputSchema` wants `AnySchema` = `z3.ZodTypeAny | z4.$ZodType` (from `server/zod-compat.d.ts`), so it accepts one full schema. Do NOT pass a raw object of field schemas (that's `ZodRawShapeCompat`, a different union branch that will reject a standalone `ZodType`).

## The dual-zod pitfall (why inputSchema rejects your schemas)

**Root cause observed:** SDK 1.30.0 declares `"zod": "^3.25 || ^4.0"` in its dependencies. When the
workspace pins an older zod (this project used `3.23.8` at root for packages/shared + apps/api),
npm installs a **nested** zod under the SDK:

```
node_modules/zod/package.json                                    → 3.23.8   (your schemas)
node_modules/@modelcontextprotocol/sdk/node_modules/zod/package.json → 4.4.3  (SDK's AnySchema)
```

`AnySchema = z3.ZodTypeAny | z4.$ZodType` — the SDK's `z3`/`z4` import their own installed zod
instance. A `z.ZodTypeAny` from YOUR `3.23.8` instance is a *different nominal type* from the
SDK's `z3.ZodTypeAny` (v3.25+) or `z4.$ZodType` (v4), so it fails assignment:

```
src/tools.ts(133,57): error TS2322: Type 'ZodTypeAny' is not assignable to type
'AnySchema | ZodRawShapeCompat | undefined'.
  Type 'ZodTypeAny' is not assignable to type 'ZodRawShapeCompat'.
    Index signature for type 'string' is missing in type 'ZodType<any, ZodTypeDef, any>'.
```

The error message is misleading — it points at `ZodRawShapeCompat` but the real cause is the
zod major-version/instance mismatch, not the schema shape.

**Fix direction (VERIFIED 2026-08-09, do not trust the ^3.25-dedupe myth):** the SDK's
`zod-compat` imports the **v4-only subpaths** `zod/v3` and `zod/v4/core`, so the SDK's
`AnySchema` types come from a zod **v4** instance no matter what v3 version you align to.
Bumping the workspace to `^3.25.0` alone does NOT dedupe — npm keeps a nested v4 under the
SDK (`node_modules/@modelcontextprotocol/sdk/node_modules/zod` stayed 4.4.3 even after root
zod became 3.25.76). The MCP workspace must use `zod@^4.0.0` so your schemas are v4 types
matching the SDK's instance:

```json
"dependencies": { "zod": "^4.0.0" }
```

Other workspaces (api/gateway/shared) can stay on `^3.25.0` — the two majors coexist in one
lockfile (root zod 3.25.76 for apps, nested 4.4.3 under apps/mcp + SDK). Verified green:
`npm run typecheck --workspace apps/mcp` passed with this arrangement.

Confirm resolution:
```bash
node -e "console.log(require('./apps/mcp/node_modules/zod/package.json').version)"  # 4.x
env -u NODE_ENV npm run typecheck --workspace apps/mcp   # exit 0
```

**Related the D&D VTT project incident (same session):** a wrong "skip CSRF for any Bearer header" guess
was caught by review — the exemption must check `isAdminBearer(req)` (constant-time compare
against the *configured* `ADMIN_API_TOKEN`), NOT `auth.startsWith("Bearer ")`. A garbage
bearer + valid session cookie must never bypass the CSRF double-submit check. Add unit tests
for valid-exempt / garbage-not-exempt / unset-token-not-exempt.

## Other verified facts

- `StreamableHTTPServerTransport` exists at `server/streamableHttp.js`; v1 pattern that works:
  one transport + `createServer(async (req, res) => transport.handleRequest(req, res, req.headers))`.
  Session bookkeeping can be deferred (`sessionIdGenerator: undefined`).
- `StdioServerTransport` at `server/stdio.js`; log to stderr, protocol owns stdout.
- Tool responses must be `{ content: [{ type: "text", text: string }] }`.
- SDK types come from `dist/esm/` — grepping `mcp.d.ts` for `registerTool` / `AnySchema` is the
  fast way to confirm signatures before writing code.
