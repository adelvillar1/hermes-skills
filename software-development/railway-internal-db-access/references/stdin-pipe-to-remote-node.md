# Stdin-Pipe to Remote Node

## When to use

When you need to run a local TypeScript script against Railway's private DB but can't easily base64-encode it (the script is simple, no special characters, or base64 keeps getting mangled by shell layers).

## The pattern

```bash
# Pipe the script content through railway ssh's stdin → node -
cat scripts/my-script.ts | railway ssh --service api --environment production -- node -
```

**Requirements:**
- The script must be self-contained (no local imports outside what's in the app's `node_modules`)
- The script must use a DB driver that exists in the deployed app's `node_modules` (check first: `railway ssh ... -- ls node_modules | grep -i '^postgres$'`)
- The script must not rely on any path resolution (no `__dirname`, no relative imports)

## Why this works

`railway ssh ... -- node -` tells Node.js to read from stdin. The local `cat` feeds the file contents through the SSH pipe. The remote process runs in the app directory (`/app`) where `DATABASE_URL` and the correct `node_modules` exist. No file staging needed.

## Example

```bash
cat scripts/seed-killswitch.ts | railway ssh --service api --environment production -- node -
# Output: Inserted killswitch.terrain_from_map = {"enabled":true}
```

## When NOT to use

- Complex scripts with imports from `@/packages/...` or local paths — use the base64 approach instead
- Scripts needing `tsx` specifically (ESM + TS) — `node -` runs plain JS, so either write `.mjs` or use base64

## Gotchas

- The script is evaluated with the remote Node version, which may differ from your local version. Keep syntax conservative.
- `process.env.DATABASE_URL` is automatically injected by `railway ssh` — don't pass credentials in the script.
