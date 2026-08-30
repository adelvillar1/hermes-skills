# Prisma JSON handoff typing recipe

Session: 2026-07-08 — implementing `scraper-worker/src/lib/scrape-handoff-writer.ts` for `monthly_scrape_handoffs`.

## Problem

Prisma generated `Json` fields do not accept `Record<string, unknown>` or plain `null` in TypeScript input types. Errors included:

```
Type 'null' is not assignable to type 'NullableJsonNullValueInput | InputJsonValue | undefined'.
Type 'Record<string, unknown>' is not assignable to type 'NullableJsonNullValueInput | InputJsonValue | undefined'.
```

## Working pattern

Use the generated Prisma JSON types and the `Prisma.JsonNull` sentinel.

```typescript
import { Prisma } from '@prisma/client';

function safeSummaryJson(
  summary?: ScrapeHandoffSummary,
): Prisma.InputJsonValue | undefined {
  if (!summary) return undefined;
  return summary as Prisma.InputJsonValue;
}

function readinessToJson(
  readiness: ScrapeReadiness,
): Prisma.InputJsonValue {
  return { ...readiness } as Prisma.InputJsonValue;
}
```

In the `update` block, clear a JSON field by assigning `Prisma.JsonNull` instead of `null`:

```typescript
update: {
  summary: Prisma.JsonNull,
  readiness: Prisma.JsonNull,
  // ...
}
```

## Why `Record<string, unknown>` fails

Prisma's `InputJsonValue` is a recursive union:

```typescript
type InputJsonValue =
  | string
  | number
  | boolean
  | { toJSON?: unknown }
  | { [key: string]: InputJsonValue }
  | InputJsonValue[]
  | null;
```

The object branch requires an index signature `{ [key: string]: InputJsonValue }`, which a `Record<string, unknown>` does not satisfy because `unknown` is not assignable to `InputJsonValue`. Casting the whole value to `Prisma.InputJsonValue` is the accepted pattern.

## Other gotchas from this session

- Run `npx prisma generate` in the worker package before type-checking. The root-generated client may not be the one the worker imports.
- If the worker package has its own `node_modules/@prisma/client`, either symlink it to the root copy or generate separately inside the package.
- Do not import contract files from outside the worker's `tsconfig rootDir`. Duplicate constants locally.

## Related code

- `scraper-worker/src/lib/scrape-handoff-writer.ts`
- `lib/pipeline-jobs/scrape-handoff.ts` (shared contract, used by non-worker packages)
- `prisma/schema.prisma` — `monthly_scrape_handoffs` model
