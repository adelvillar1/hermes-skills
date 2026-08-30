# TanStack Query v5 Migration

This project uses `@tanstack/react-query` v5 (^5.90.21). The v4 option `keepPreviousData` was removed.

## Wrong (v4 — subagent pattern)

```tsx
const { data } = trpc.analytics.getData.useQuery(
  { regionId },
  { keepPreviousData: true }
);
```

This produces `No overload matches this call` type errors.

## Correct (v5)

```tsx
import { keepPreviousData } from '@tanstack/react-query';

const { data } = trpc.analytics.getData.useQuery(
  { regionId },
  { placeholderData: keepPreviousData }
);
```

## Detection

Search for `keepPreviousData: true` in any new component file — it's a reliable indicator of v4 API usage.
