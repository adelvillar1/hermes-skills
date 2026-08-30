# Cursor-Based Pagination Envelope (PaginatedResponse)

A reusable pattern for adding cursor-based pagination to a bilateral-bridge API.
Covers the Python contract, the TS Zod schema, the cursor encode/decode utility,
repository pagination methods, FastAPI dependency injection, and TanStack Query
integration with backward-compatible hook shapes.

## 1. The Envelope Contract

### Python (`src/contract/paginated_response.py`)

```python
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    items: list[T]
    next_cursor: str | None = Field(alias="nextCursor", default=None)
    has_more: bool = Field(alias="hasMore", default=False)
    total_estimate: int | None = Field(alias="totalEstimate", default=None)
```

Usage as `response_model`: `PaginatedResponse[InstrumentContract]`

### TypeScript (`types/paginated-response.ts`)

```typescript
import { z } from 'zod';

export function PaginatedResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    items: z.array(itemSchema),
    nextCursor: z.string().min(1).nullable(),
    hasMore: z.boolean(),
    totalEstimate: z.number().int().nonnegative().nullable(),
  }).strict();
}

export type PaginatedResponse<T> = {
  items: T[];
  nextCursor: string | null;
  hasMore: boolean;
  totalEstimate: number | null;
};
```

## 2. Cursor Utility

Cursors are base64url-encoded JSON objects encoding the sort key(s) of the last
item in a page. base64url avoids `+`, `/`, `=` — all URL-unsafe.

```python
import base64, json
from collections.abc import Mapping

class InvalidCursorError(Exception):
    """Raised when a cursor string cannot be decoded."""

def encode_cursor(key_values: Mapping[str, str | int | float | None]) -> str:
    raw = json.dumps(key_values, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")

def decode_cursor(cursor: str) -> dict:
    try:
        padded = cursor + "=" * (4 - len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        decoded = json.loads(raw)
    except Exception:
        raise InvalidCursorError(f"Invalid cursor: {cursor[:20]}...")
    if not isinstance(decoded, dict):
        raise InvalidCursorError("Cursor must decode to a JSON object")
    return decoded
```

**Key points:**
- Use `Mapping` (not `dict`) for the `encode_cursor` param type to satisfy
  Pyright's invariant type parameter checking — `dict[str, str]` is NOT
  assignable to `dict[str, str | int | float | None]` due to invariance.
- Strip `=` padding on encode, restore on decode.
- `InvalidCursorError` → HTTP 400 via exception handler (client error, not 500).

### Composite Cursors

For non-unique sort keys (e.g., `made_at` when batch predictions share a
timestamp), use a composite cursor to guarantee stable ordering:

```python
stmt = stmt.where(
    (Prediction.made_at < last_made_at)
    | (
        (Prediction.made_at == last_made_at)
        & (Prediction.prediction_id < last_pred_id)
    )
)
```

Encode both keys in the cursor:
```python
next_cursor = encode_cursor({
    "made_at": items[-1].made_at,
    "prediction_id": items[-1].prediction_id,
})
```

## 3. FastAPI Pagination Dependency

```python
from dataclasses import dataclass
from fastapi import Query

@dataclass
class PaginationParams:
    limit: int
    cursor: str | None
    include_total: bool

def get_pagination(
    limit: int = Query(default=50, ge=1, le=500),
    cursor: str | None = Query(default=None),
    include_total: bool = Query(default=False, alias="includeTotal"),
) -> PaginationParams:
    return PaginationParams(limit=limit, cursor=cursor, include_total=include_total)
```

**Ruff N803:** The param must be `include_total` (snake_case), not `includeTotal`.
The `alias="includeTotal"` makes FastAPI accept `?includeTotal=true` from the wire.

### Invalid Cursor → HTTP 400

```python
@app.exception_handler(InvalidCursorError)
async def invalid_cursor_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
```

## 4. Repository Pattern

```python
async def list_paginated(
    session: AsyncSession,
    *,
    limit: int = 50,
    cursor: str | None = None,
    include_total: bool = False,
) -> tuple[list[Model], str | None, int | None]:
    stmt = select(Model)

    if cursor is not None:
        decoded = decode_cursor(cursor)
        last_id = decoded.get("model_id")
        if last_id is not None:
            stmt = stmt.where(Model.model_id > last_id)

    stmt = stmt.order_by(Model.model_id.asc()).limit(limit)
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    has_more = len(items) == limit
    next_cursor = encode_cursor({"model_id": items[-1].model_id}) if has_more and items else None

    total_estimate = None
    if include_total:
        count_stmt = select(func.count()).select_from(Model)
        total_estimate = (await session.execute(count_stmt)).scalar_one()

    return items, next_cursor, total_estimate
```

**`has_more` detection:** `len(items) == limit`. If the DB returns exactly `limit`
rows, there MIGHT be more. The next cursor is the sort key of the LAST item. If
the next page returns fewer than `limit`, there are no more — `has_more` is
False and `next_cursor` is null.

## 5. TanStack Query Integration (backward-compatible)

The key insight: keep the existing `{ data, loading, error }` hook interface so
consuming screens don't need changes. List endpoints use `useInfiniteQuery` and
flatten the pages into a single `T[]`:

```typescript
import { useInfiniteQuery } from '@tanstack/react-query';

export function useInstruments(params?: { sector?: string }): HookState<Instrument[]> {
  const query = useInfiniteQuery({
    queryKey: ['instruments', params?.sector],
    queryFn: ({ pageParam, signal }) =>
      api.getInstruments({ sector: params?.sector, limit: 50, cursor: pageParam }, signal),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: !USE_MOCK,
  });

  return {
    data: query.data ? query.data.pages.flatMap((p) => p.items) : null,
    loading: query.isLoading,
    error: query.isError ? toError(query.error) : null,
  };
}
```

**`exactOptionalPropertyTypes` note:** If `exactOptionalPropertyTypes: true` is
set in tsconfig, client function signatures need `{ cursor?: string | undefined }`
(not just `{ cursor?: string }`) because `pageParam` from TanStack Query is
`string | undefined`.

### QueryClientProvider setup

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,      // 30s before refetch on focus
      gcTime: 5 * 60_000,     // 5m before garbage-collected
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

createRoot(rootEl).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);
```

## 6. Migrating Existing Bare-Array Endpoints

When converting an endpoint from returning `T[]` to `PaginatedResponse[T]`,
existing tests that assert `resp.json() == []` or `len(data) == N` will break.
Update them to use `data["items"]` instead of `data`:

```python
# Before (bare array)
assert resp.json() == []
assert len(data) == 30

# After (paginated envelope)
assert resp.json()["items"] == []
assert len(data["items"]) == 30
```

Add new tests for pagination behavior:
- Multi-page fetch with no overlap between page 1 and page 2
- Invalid cursor returns HTTP 400 (not 500)
- `includeTotal=true` returns a `totalEstimate` integer
