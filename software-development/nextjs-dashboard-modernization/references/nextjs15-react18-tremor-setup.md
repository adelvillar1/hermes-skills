# Next.js 15 + React 18 + Tremor Setup Guide

> Session: 2026-05-04 — Beacon dashboard modernization
> Problem: Next.js 15 defaults to React 19, Tremor v3 requires React 18

## The Dependency Conflict

```
npm install @tremor/react
# npm error: peer dependency react@"^18.0.0" not satisfied by react@19.0.0
```

## Solution

### 1. Pin React to 18.3.1

```json
// apps/web/package.json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "next": "^15.3.0"
  }
}
```

### 2. Install Tremor with legacy peer deps

```bash
cd apps/web
npm install @tremor/react @heroicons/react @headlessui/react --legacy-peer-deps
```

### 3. Use Tailwind CSS v3 (not v4)

Tailwind v4's `@import "tailwindcss"` syntax breaks Next.js font loading and ESM PostCSS configs.

```bash
# From monorepo ROOT (npm workspaces hoists to root node_modules/)
cd /path/to/monorepo
npm install tailwindcss@3.4.17 autoprefixer@10.4.21 postcss@8.5.14 -w @beacon/web --save-dev
```

Verify:
```bash
ls node_modules/tailwindcss/package.json  # should exist at ROOT
```

### 4. PostCSS config as CommonJS

In ESM projects (`"type": "module"` in package.json), PostCSS config must use `.cjs`:

```javascript
// postcss.config.cjs
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### 5. CSS with standard directives

```css
/* app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 6. TypeScript path aliases

```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

## Verification Steps

```bash
# 1. Build should succeed
cd apps/web
npx next build

# 2. No peer dependency warnings
npm ls @tremor/react

# 3. Tailwind is at root node_modules
ls ../../node_modules/tailwindcss

# 4. Dev server starts
npx next dev --port 3000
```

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Can't resolve 'tailwindcss'` | Tailwind not hoisted to root | Install from root with `-w @beacon/web` |
| `module is not defined in ES module scope` | PostCSS config is `.js` in ESM project | Rename to `.cjs` |
| `useState only works in Client Component` | Missing `"use client"` directive | Add to top of component file |
| `File \| undefined not assignable to File` | Strict TypeScript + FileList API | Add `&& files[0]` guard |

## Working package.json

```json
{
  "name": "@beacon/web",
  "version": "0.1.0",
  "type": "module",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start",
    "lint": "eslint --max-warnings 0",
    "check-types": "tsc --noEmit"
  },
  "dependencies": {
    "@headlessui/react": "^2.2.2",
    "@heroicons/react": "^2.2.0",
    "@tanstack/react-query": "^5.75.0",
    "@tremor/react": "^3.18.7",
    "@trpc/client": "^11.1.0",
    "@trpc/react-query": "^11.1.0",
    "@trpc/server": "^11.1.0",
    "clsx": "^2.1.1",
    "next": "^15.3.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "superjson": "^2.2.6",
    "tailwind-merge": "^3.5.0",
    "zod": "^4.4.3"
  },
  "devDependencies": {
    "@types/node": "^22.15.3",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "autoprefixer": "^10.4.21",
    "eslint": "^9.39.1",
    "postcss": "^8.5.14",
    "tailwindcss": "^3.4.17",
    "typescript": "5.9.2"
  }
}
```
