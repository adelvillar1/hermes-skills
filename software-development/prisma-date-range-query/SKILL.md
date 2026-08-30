---
name: prisma-date-range-query
description: Use when building date-range filters in Prisma queries against PostgreSQL DATE columns. Covers the endOfDay UTC trick to prevent off-by-one-day exclusions, and the canonical parameter parsing pattern found in production API routes.
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [prisma, postgresql, date, query, filter, bug-prevention]
  related_skills: [prisma-soft-delete]
---

# Prisma Date Range Query Pattern

## Overview

Filtering records by a date range in Prisma + PostgreSQL seems trivial until your "end date" filter silently excludes the final day's records. The root cause: PostgreSQL's implicit `DATE → TIMESTAMPTZ` cast in non-UTC sessions. The fix: set the end-of-day time in UTC before passing the date to Prisma.

This skill covers the canonical pattern: safe parameter parsing, UTC day boundaries, and the one-line trick that prevents the off-by-one-day bug.

## When to Use

- Building a Prisma query with a date range filter (`startDate` / `endDate` search params)
- Using `@db.Date` on a Prisma model field with PostgreSQL
- Debugging why date-range filters exclude the last day
- Any report or list endpoint with date-range filtering

## The Problem

```typescript
// BAD — excludes records on the endDate
const end = new Date(searchParams.get("endDate"));
where.dateField = { lte: end };
// new Date("2026-04-30") → 2026-04-30T00:00:00.000Z
// PostgreSQL compares: booking_date <= '2026-04-29T20:00:00-04:00'
// April 30th records are excluded!
```

Root cause: `new Date("2026-04-30")` creates midnight-UTC. When Prisma sends this to PostgreSQL in a non-UTC session (common on Railway, Heroku, etc.), the `DATE → TIMESTAMPTZ` implicit cast converts `2026-04-30T00:00:00Z` to the previous day's evening in the session timezone. Records dated on the end date get excluded.

## The Fix

```typescript
const end = new Date(endDate);
end.setUTCHours(23, 59, 59, 999);  // 2026-04-30T23:59:59.999Z
where.dateField = { lte: end };
```

Now PostgreSQL sees `2026-04-30T23:59:59.999Z`, which is >= `2026-04-30T00:00:00` in any timezone.

## Canonical Pattern

```typescript
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(req: NextRequest) {
  // ...auth check...

  const { searchParams } = new URL(req.url);
  const startDate = searchParams.get("startDate");
  const endDate = searchParams.get("endDate");

  const where: Record<string, unknown> = {};

  if (startDate || endDate) {
    where.bookingDate = {};
    if (startDate) {
      const start = new Date(startDate);
      start.setUTCHours(0, 0, 0, 0);
      (where.bookingDate as Record<string, unknown>).gte = start;
    }
    if (endDate) {
      const end = new Date(endDate);
      end.setUTCHours(23, 59, 59, 999);  // CRITICAL: end-of-day UTC
      (where.bookingDate as Record<string, unknown>).lte = end;
    }
  }

  const results = await prisma.booking.findMany({ where });
  return NextResponse.json(results);
}
```

## Key Details

- **`startDate`** → `setUTCHours(0, 0, 0, 0)` — records at the start of the start day are included.
- **`endDate`** → `setUTCHours(23, 59, 59, 999)` — records through the end of the end day are included.
- **Empty object init** (`where.bookingDate = {}`) avoids Prisma type errors when conditionally adding `gte`/`lte`.
- **Always `setUTCHours`**, never `setHours` — the session timezone is unreliable in serverless/containerized environments.

## Reusable Helper

```typescript
function dateFilter(start?: string | null, end?: string | null): Record<string, Date> {
  const filter: Record<string, Date> = {};
  if (start) {
    const s = new Date(start);
    s.setUTCHours(0, 0, 0, 0);
    filter.gte = s;
  }
  if (end) {
    const e = new Date(end);
    e.setUTCHours(23, 59, 59, 999);
    filter.lte = e;
  }
  return filter;
}

// Usage with multiple date fields:
if (startDate || endDate) {
  where.OR = [
    { bookingDate: dateFilter(startDate, endDate) },
    { travelStartDate: dateFilter(startDate, endDate) },
  ];
}
```

## Common Pitfalls

1. **`setHours` vs `setUTCHours`.** `setHours` uses the server's local timezone. In serverless/containerized environments (Railway, Vercel, Heroku), the TZ is unpredictable. Always use UTC.

2. **Direct string construction.** Don't build date strings manually or use template literals in Prisma queries. Always use Date objects — Prisma serializes them properly.

3. **Missing `gte` for startDate.** Without a `gte`, only the `lte` endDate filter is applied — records before startDate are still returned.

4. **`new Date(null)` or `new Date("")`.** These produce `Invalid Date` or unexpected epoch values. Always guard with `if (startDate)` before constructing.

5. **Using this with `@db.Timestamptz`.** If the column is `TIMESTAMPTZ` (not `DATE`), the implicit cast issue doesn't apply, but the pattern is still correct. Safer to use it everywhere for consistency.

## Business Logic: Same-Day Exclusion for Forward-Looking Queries

A common pattern in B2B/apps: "show upcoming sailings/appointments/bookings." Using `gte: today` includes same-day records that are already past from the user's perspective (the ship has sailed, the slot is gone). Use `gte: tomorrow` instead.

```typescript
// WRONG — shows today's already-departed sailings
const where = { departureDate: { gte: getToday() } };

// CORRECT — only shows future departures
const where = { departureDate: { gte: getTomorrow() } };

function getToday(): Date {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
}

function getTomorrow(): Date {
  const today = getToday();
  return new Date(today.getTime() + 24 * 60 * 60 * 1000);
}
```

**Critical distinction — which queries use which boundary:**

| Query purpose | Boundary | Why |
|---|---|---|
| Search results, list views, detail itineraries | `gte: tomorrow` | Same-day records are useless to the user |
| Filter dropdowns (available months, years, regions) | `gte: today` | Showing that something *exists* in the current month/year is informative even if today's specific records are hidden from results |
| Stats/counts (hero numbers, dashboard totals) | `gte: today` or `>= NOW()` | Marketing numbers should count all future including today |
| Similar/recommended itineraries | `gte: tomorrow` | Recommending today's sailing is recommending the past |

**Month filter within same-day-excluded queries:** When a user filters by month, the floor should also be `tomorrow`, not `today`:

```typescript
// Month filter in a search that excludes same-day
const monthStart = new Date(year, month - 1, 1);
const monthEnd = new Date(year, month, 1);
where.departureDate = {
  gte: monthStart > tomorrow ? monthStart : tomorrow,  // not today
  lt: monthEnd,
};
```

## Verification Checklist

- [ ] A record dated on `endDate` appears in results (not excluded)
- [ ] A record dated before `startDate` is excluded
- [ ] A record dated after `endDate` is excluded
- [ ] `startDate` alone (no `endDate`) filters correctly
- [ ] `endDate` alone (no `startDate`) filters correctly
- [ ] Neither parameter returns all records (no date filter applied)
- [ ] Forward-looking queries exclude same-day records (departure/booking dates from today)
- [ ] Filter dropdowns still include today's month/year as available (they show existence, not individual records)
