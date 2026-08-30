# Next.js Dev Server Troubleshooting

> Session: 2026-05-04 — Beacon dashboard modernization
> Problem: `next build` passes but `next dev` fails with CSS parse errors and missing `.next/required-server-files.json`

## Symptom: Build Passes, Dev Fails

```bash
npx next build        # ✅ Success
npx next dev          # ❌ Internal Server Error
```

## Root Causes and Fixes

### 1. PostCSS/Tailwind Not in Local node_modules

**Symptom:**
```
Module parse failed: Unexpected character '@' (1:0)
> @tailwind base;
```

**Cause:** npm workspaces hoists dependencies to root. `next dev` sometimes looks for PostCSS plugins in app `node_modules/` before falling back to root.

**Fix:** Ensure Tailwind/PostCSS/Autoprefixer are installed in BOTH root and app:
```bash
# From monorepo root
npm install tailwindcss@3.4.17 autoprefixer@10.4.21 postcss@8.5.14 -w @beacon/web --save-dev

# Verify
ls apps/web/node_modules/tailwindcss/package.json   # should exist
ls node_modules/tailwindcss/package.json             # should also exist
```

### 2. `.next` Cache Corruption

**Symptom:**
```
ENOENT: no such file or directory, open '.next/required-server-files.json'
```

**Cause:** Mixed build artifacts from `next build` (production) and `next dev` (development). The dev server tries to read production build metadata.

**Fix:** Clean cache before switching modes:
```bash
rm -rf .next
npx next dev
```

### 3. Auto-Install Type Dependencies Fails

**Symptom:**
```
ERR_PNPM_FETCH_404  GET https://registry.npmjs.org/@repo%2Feslint-config: Not Found
```

**Cause:** Next.js 15 auto-installs `@types/react` and `@types/node` on first dev start. It uses pnpm internally, which fails on `@repo/*` workspace packages that aren't in npm registry.

**Fix A — Pre-install types:**
```bash
cd apps/web
npm install @types/react @types/node --save-dev
```

**Fix B — Disable auto-install:**
```bash
NEXT_PRIVATE_SKIP_TYPECHECK=1 npx next dev
```

**Fix C — Use npm instead of pnpm for auto-install:**
```bash
# Not directly configurable; Fix A is most reliable
```

### 4. Dev Server Process Management

**Problem:** `next dev` is long-lived. Terminal sessions timeout and kill it.

**Solution — Detached spawn with log monitoring:**
```bash
# Start
cd apps/web && node -e "
const { spawn } = require('child_process');
const fs = require('fs');
const out = fs.openSync('/tmp/next-dev.log', 'w');
const err = fs.openSync('/tmp/next-dev.log', 'a');
const child = spawn('npx', ['next', 'dev', '--port', '3002'], {
  detached: true,
  stdio: ['ignore', out, err]
});
console.log('PID:', child.pid);
child.unref();
"

# Monitor
sleep 6 && cat /tmp/next-dev.log | tail -20

# Health check
curl -s http://localhost:3002/api/trpc/health

# Stop
kill <PID>
```

### 5. ESM/CJS PostCSS Config Conflict

**Symptom:**
```
module is not defined in ES module scope
```

**Cause:** `postcss.config.js` in ESM project (`"type": "module"` in package.json).

**Fix:** Rename to `.cjs`:
```bash
mv postcss.config.js postcss.config.cjs
```

## Diagnostic Checklist

When dev server fails:

1. [ ] `rm -rf .next` — cache corruption?
2. [ ] `ls apps/web/node_modules/tailwindcss` — local deps present?
3. [ ] `cat apps/web/postcss.config.cjs` — correct extension and content?
4. [ ] `cat /tmp/next-dev.log | grep -E "Error|ERR|404"` — specific error?
5. [ ] `curl http://localhost:3000/api/trpc/health` — API routes work?
6. [ ] `npm ls @types/react` — types installed?

## Verification Commands

```bash
# Full clean restart
cd apps/web
rm -rf .next
npx next build        # Verify production build
rm -rf .next
npx next dev --port 3002 > /tmp/next-dev.log 2>&1 &
echo $!  # Note PID
sleep 8
cat /tmp/next-dev.log | tail -10
curl -s http://localhost:3002/
curl -s http://localhost:3002/api/trpc/health
```
