---
name: prisma-nested-orderby
description: Sort Prisma query results by related entity fields (nested orderBy) and dynamic sort direction. Covers the relational sort syntax, dynamic direction handling, and common pitfalls when sorting by foreign key relationships.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [prisma, postgresql, sorting, orderby, relations, nested-query]
    related_skills: [prisma-date-range-query, react-url-synced-filters]
---

# Prisma Nested orderBy Pattern

## Overview

Prisma supports sorting by fields on related models via nested `orderBy` syntax. This is essential when a list view needs sorting by a parent/related entity's attribute — e.g., sorting itineraries by cruise line name, or bookings by customer tier.

This skill covers the syntax, dynamic direction (asc/desc from user input), and the common pitfall of trying to sort by a relation without traversing through it.

## When to Use

- Sorting a list by a parent entity's name (itineraries → cruise line name)
- Sorting by a related lookup table's display order (products → category displayOrder)
- User-facing sort controls that need ascending/descending toggle
- Any API endpoint where `sortBy` and `sortOrder` are query parameters

## The Syntax

### Basic Nested Sort (Static)

```typescript
// Sort itineraries by their ship's cruise line name
const itineraries = await prisma.ship_itineraries.findMany({
  orderBy: {
    ship: {
      cruiseLine: {
        name: 'asc',
      },
    },
  },
});
```

### Dynamic Direction (From User Input)

```typescript
// API input: sortBy='cruiseLine', sortOrder='desc'
function buildOrderBy(sortBy: string, sortOrder: 'asc' | 'desc') {
  const dir = sortOrder;

  switch (sortBy) {
    case 'departure':
      return { departureDate: dir };
    case 'price':
      return { startingPrice: dir };
    case 'duration':
      return { duration: dir };
    case 'cruiseLine':
      // Nested: itinerary → ship → cruiseLine → name
      return { ship: { cruiseLine: { name: dir } } };
    default:
      return { departureDate: 'asc' };
  }
}

const itineraries = await prisma.ship_itineraries.findMany({
  orderBy: buildOrderBy(input.sortBy, input.sortOrder),
});
```

**Key**: Pass `sortOrder` as a separate parameter from `sortBy`. The frontend toggles direction without changing the selected field, and the backend applies the direction dynamically to whichever field is selected.

## Zod Schema for API Input

```typescript
import { z } from 'zod';

const searchInput = z.object({
  sortBy: z.enum(['departure', 'price', 'duration', 'cruiseLine']).default('departure'),
  sortOrder: z.enum(['asc', 'desc']).default('asc'),
});
```

**Note**: Always accept `sortOrder` as a separate parameter, not hardcoded. This lets the frontend toggle ascending/descending without changing the `sortBy` field.

## Frontend: Sort UI with Direction Toggle

```tsx
<div className="flex items-center gap-2">
  <select
    value={sortBy}
    onChange={(e) => { setSortBy(e.target.value as SortBy); setOffset(0); }}
  >
    <option value="departure">Departure Date</option>
    <option value="duration">Duration</option>
    <option value="cruiseLine">Cruise Line</option>
  </select>
  <button
    onClick={() => { setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc')); setOffset(0); }}
    title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
  >
    {sortOrder === 'asc' ? '↑' : '↓'}
  </button>
</div>
```

## Common Pitfalls

### Forgetting the Relation Path

```typescript
// ❌ WRONG — Prisma throws: "Unknown field `cruiseLineName`"
orderBy: { cruiseLineName: 'asc' }

// ✅ RIGHT — traverse the relation
orderBy: { ship: { cruiseLine: { name: 'asc' } } }
```

### Sorting by Non-Scalar Relations

```typescript
// ❌ WRONG — can't sort by a relation itself, only scalar fields
orderBy: { ship: { cruiseLine: 'asc' } }

// ✅ RIGHT — must specify a scalar field on the related model
orderBy: { ship: { cruiseLine: { name: 'asc' } } }
```

### Missing Include/Select

Nested `orderBy` does NOT require `include` or `select` — it works purely on the relation path. However, if you also need the related data in the response, you must include it separately:

```typescript
// Sorting by cruise line name AND returning cruise line data
const itineraries = await prisma.ship_itineraries.findMany({
  orderBy: { ship: { cruiseLine: { name: 'asc' } } },
  include: {
    ship: {
      include: {
        cruiseLine: { select: { id: true, name: true, tier: true } },
      },
    },
  },
});
```

### Performance: No Index on Related Field

Nested sorting can be slow if the related field isn't indexed. PostgreSQL must join and sort:

```sql
-- Generated SQL (simplified)
SELECT i.* FROM ship_itineraries i
JOIN ships s ON i.ship_id = s.id
JOIN cruise_lines cl ON s.cruise_line_id = cl.id
ORDER BY cl.name ASC;
```

**Fix**: Add an index on the related sort field:

```prisma
model cruise_lines {
  id   String @id
  name String
  // Add index for sorting
  @@index([name])
}
```

Or create a composite index if the sort is always paired with a filter:

```prisma
// If you always filter by region + sort by cruise line
@@index([regionId, shipId]) // on ship_itineraries
```

## Multi-Level Nested Sort

Prisma supports arbitrary nesting depth (as long as the relations exist):

```typescript
// Sort by: itinerary → ship → cruise line → region → displayOrder
orderBy: {
  ship: {
    cruiseLine: {
      region: {
        displayOrder: 'asc',
      },
    },
  },
},
```

## Combining with Pagination

Always apply `orderBy` BEFORE `skip`/`take` — Prisma handles this correctly, but the ordering determines which rows are in each page:

```typescript
const page = await prisma.ship_itineraries.findMany({
  where: { status: 'active' },
  orderBy: { ship: { cruiseLine: { name: 'asc' } } },
  skip: (pageNumber - 1) * pageSize,
  take: pageSize,
});
```

## Verification Checklist

- [ ] Sorting by related field returns correctly ordered results
- [ ] Ascending and descending both work
- [ ] Results are stable (consistent order for ties)
- [ ] Pagination doesn't scramble order between pages
- [ ] Query performance is acceptable (< 200ms for 10K rows)
- [ ] Related field has a database index if sorting is frequent
