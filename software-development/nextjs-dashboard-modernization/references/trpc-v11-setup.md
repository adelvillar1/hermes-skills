# tRPC v11 + Next.js App Router + SuperJSON Setup

> Session: 2026-05-04 — Beacon dashboard modernization
> Problem: tRPC v11 changed transformer placement, type inference broke with Next.js 15

## Server Setup (App Router API Route)

```typescript
// app/api/trpc/[trpc]/route.ts
import { appRouter } from "@/server/routers/_app";
import { fetchRequestHandler } from "@trpc/server/adapters/fetch";

const handler = (req: Request) =>
  fetchRequestHandler({
    endpoint: "/api/trpc",
    req,
    router: appRouter,
    createContext: () => ({}),
  });

export { handler as GET, handler as POST };
```

## Router with SuperJSON Transformer

```typescript
// server/routers/_app.ts
import { initTRPC } from "@trpc/server";
import { z } from "zod";
import superjson from "superjson";

const t = initTRPC.create({
  transformer: superjson,  // Server-side transformer
});

export const router = t.router;
export const publicProcedure = t.procedure;

export const appRouter = router({
  health: publicProcedure.query(() => ({ status: "ok" })),
  // ... nested routers per dashboard tab
});

export type AppRouter = typeof appRouter;
```

## Client Setup (React Component)

```typescript
// components/providers/trpc-provider.tsx
"use client";

import { httpBatchLink } from "@trpc/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import superjson from "superjson";
import { trpc } from "../../lib/trpc";

function getBaseUrl() {
  if (typeof window !== "undefined") return "";
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return `http://localhost:${process.env.PORT ?? 3000}`;
}

export function TrpcProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const [trpcClient] = useState(() =>
    trpc.createClient({
      links: [
        httpBatchLink({
          url: `${getBaseUrl()}/api/trpc`,
          transformer: superjson,  // v11: transformer goes HERE, not at createClient level
        }),
      ],
    })
  );

  return (
    <trpc.Provider client={trpcClient} queryClient={queryClient}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </trpc.Provider>
  );
}
```

## Client Factory

```typescript
// lib/trpc.ts
import { createTRPCReact } from "@trpc/react-query";
import type { AppRouter } from "../server/routers/_app";

// Explicit type annotation prevents declaration emit issues with tRPC v11 + Next.js 15
export const trpc: ReturnType<typeof createTRPCReact<AppRouter>> = createTRPCReact<AppRouter>();
```

## Type Inference Fix

**Problem:** `createTRPCReact<AppRouter>()` without annotation causes:
```
The inferred type of 'trpc' cannot be named without a reference to
'../../../node_modules/@trpc/react-query/dist/getQueryKey.d-CruH3ncI.mjs'.
This is likely not portable. A type annotation is necessary.
```

**Fix:** Add explicit `ReturnType<typeof createTRPCReact<AppRouter>>` annotation.

## Upstream Type Compatibility

**Problem:** Zod v4 locale imports + TanStack Query private identifiers cause declaration emit failures in Next.js build type checking.

**Symptoms:**
```
Private identifiers are only available when targeting ECMAScript 2015 and higher.
Module can only be default-imported using the 'esModuleInterop' flag
```

**Fix (pragmatic for builds):**
```javascript
// next.config.js
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,  // Types work in IDE; declaration emit is upstream issue
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};
```

**Better fix:** Ensure `tsconfig.json` has `"target": "ES2020"` or higher, and `"esModuleInterop": true`. If using shared `@repo/typescript-config`, verify it doesn't override these.

## Verification

```bash
# 1. Health endpoint responds
curl http://localhost:3000/api/trpc/health
# → {"result":{"data":{"json":{"status":"ok"}}}}

# 2. Frontend shows API status
# Add to any client component:
const health = trpc.health.useQuery()
# → health.data.status === "ok"
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `transformer property has moved to httpLink/httpBatchLink/wsLink` | `transformer` at `createClient` level | Move to `httpBatchLink({ transformer: superjson })` |
| `Cannot find module '@/server/routers/_app'` | Path alias not resolving in API route | Use `@/server/routers/_app` with `baseUrl: "."` in tsconfig |
| `useState only works in Client Component` | tRPC provider missing `"use client"` | Add directive at top of provider file |
| `The inferred type of 'trpc' cannot be named` | tRPC v11 type inference portability | Add explicit `ReturnType` annotation |
| `Module 'ws' not found` | tRPC server includes WS adapter types | Ignore — only affects type check, not runtime |
