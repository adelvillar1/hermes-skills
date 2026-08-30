---
name: runtime-bug-discovery-via-test-run
description: |
  After implementing a scraper, ETL job, or any feature that touches the database,
  run it against real data immediately as part of the deliverable. This catches
  constraint violations, timeout issues, and silent partial-success states that
  no amount of plan-level review or type-checking can anticipate.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [testing, scraper, etl, database, runtime-verification, validation]
---

# Runtime Bug Discovery via Test Run

## The principle

Type-checking (`tsc --noEmit`), unit tests, and grep-verifiable ACs are **structural verification** — they confirm the code compiles, the tests pass, and the right symbols exist. They do **not** catch:

- **Database constraint violations** the plan didn't anticipate (e.g., a unique constraint spanning fields the plan didn't account for)
- **Transaction timeout / scale issues** that only appear with realistic data volumes (e.g., 100+ rows × per-row round-trips exceeds a 5s default timeout)
- **Silent partial-success states** where the scraper reports success but data didn't land (e.g., a transaction commits the snapshot but the per-row inserts all fail and are swallowed)
- **Data shape mismatches** between what the source actually returns and what the parser expects (e.g., a table column shifted by one position)

These bugs only surface when the code runs against real data. **The test run is not a final polish step — it is part of the deliverable.**

## When to use

After implementing any of:
- A scraper (port schedules, ship itineraries, product listings, etc.)
- An ETL job that writes to the database
- A migration that transforms existing data
- A feature that integrates with an external API and persists results

The cost of a test run is 2-5 minutes. The cost of shipping a broken implementation that fails silently in production is the next deploy cycle + user reports.

## How to run a test against real data

### Step 1: Pick a representative target

Choose the target that will most likely expose bugs:
- **Highest-value entity** — top port by visit count, top ship by capacity, most-used user
- **Highest-traffic edge case** — the entity with the most records to write (tests scale limits)
- **Mixed-source data** — entity that already has rows from a different source (tests unique constraints that span sources)

If the scraper has a `lastScrapedBefore` filter, pick an entity whose `lastScrapedAt` is before that threshold. If no such entity exists naturally, **backdate one row's timestamp** to put it in scope:

```sql
UPDATE cruisemapper_ports
SET "lastScrapedAt" = '2026-06-14 10:00:00+00'::timestamptz
WHERE "portSlug" = 'nassau';
```

This is a deliberate test setup, not a production data change. Restore the real timestamp after the test.

### Step 2: Run the scraper with `dryRun: false`

Do not run dry-run first — dry-run skips the upsert path, which is where the constraint violations live. Run live with a small scope (1 port, 1 ship, 1 user) to keep the blast radius contained.

```bash
DATABASE_URL="postgresql://..." FIRECRAWL_URL="..." \
  npx tsx scraper-worker/src/tests/run-my-scraper.ts
```

### Step 3: Verify the DB state

After the run completes, query the destination tables directly:

```sql
-- Did the visits actually land?
SELECT count(*) FROM port_ship_visits
WHERE "portSlug" = 'nassau' AND source = 'firecrawl';

-- Did the snapshot land?
SELECT count(*) FROM port_schedule_snapshots
WHERE "portSlug" = 'nassau' AND source = 'firecrawl';

-- Are the timestamps updated?
SELECT "portSlug", "lastScrapedAt" FROM cruisemapper_ports
WHERE "portSlug" = 'nassau';
```

If `visits_landed = 0` but the scraper reported success → silent partial-success bug (the transaction committed the snapshot but the per-row inserts were swallowed).

### Step 4: Check the scraper logs for error patterns

```bash
# Look for transaction timeouts
grep "Transaction already closed" /tmp/scraper-run.log

# Look for unique constraint violations
grep "Unique constraint failed" /tmp/scraper-run.log

# Look for silent upsert failures
grep "ERROR" /tmp/scraper-run.log | grep -v "expected"
```

### Step 5: Restore test-setup data

```sql
-- Restore the real lastScrapedAt
UPDATE cruisemapper_ports
SET "lastScrapedAt" = '<original-timestamp>'::timestamptz
WHERE "portSlug" = 'nassau';
```

## Expected finding rate

From observed sessions: **1-2 bugs per scraper implementation.** Common bugs found:

| Bug | Symptom | Fix |
|-----|---------|-----|
| Unique constraint spans sources | `Unique constraint failed on (cruiseMapperId, shipName, visitDate)` after first run | Switch from `deleteMany`+`create` to `upsert` |
| Transaction timeout | `Transaction already closed: timeout 5000ms` after 100+ upserts | Pass `{ timeout: 30000 }` to `$transaction` |
| Silent snapshot-only commit | Snapshots stored but 0 visits inserted | Check transaction boundary — diff engine may be running outside the transaction |
| Stale `lastScrapedAt` | Scraper updates timestamp even when visits failed | Move `lastScrapedAt` update to after the upsert succeeds, not at the start of the month |

## Anti-pattern: dry-run only

Running `dryRun: true` first and treating success as "implementation done" is a common failure mode. Dry-run skips:
- Database writes (the source of most constraint bugs)
- Transaction boundary behavior (the source of timeout bugs)
- Side effects on `lastScrapedAt`, snapshot storage, diff computation

**Rule:** dry-run is for initial smoke-testing the scrape flow (does the network call work, does the parser produce reasonable output). Live run is for validating the persistence layer. Both are needed.

## Real example: Firecrawl scraper integration (2026-07-05)

Plan had 14 grep-verifiable ACs, all passed. Type-check passed with 0 errors in the Firecrawl files. Implementation appeared complete.

Live test against Nassau (highest-value port, 6,075 visitCount claim, 3,361 existing DB visits — mixed Playwright + ScrapingBee sources):

**Run 1** → 0 visits inserted, 1 port failed. Errors: `Unique constraint failed on (cruiseMapperId, shipName, visitDate)`. Bug: `deleteMany` only removed Firecrawl-sourced visits, then `.create()` collided with Playwright rows.

**Fix:** Switch to `upsert()` with the 3-field unique key. Re-run.

**Run 2** → 77 visits inserted in first month, then `Transaction already closed: timeout 5000ms`. Bug: Prisma's default 5s transaction timeout exceeded by 77 upsert round-trips.

**Fix:** Pass `{ timeout: 30000 }` to `$transaction`. Re-run.

**Run 3** → 2,693 visits inserted across 24 months, 0 errors. Final state verified in DB.

Without the test run, both bugs would have shipped silently. The implementation would have compiled, the type-check would have passed, the grep ACs would have all been green — and the first production deploy would have inserted 0 visits.

## When to skip this step

Skip if:
- The implementation is pure logic with no database writes
- The implementation is a UI change with no backend persistence
- The destination table is ephemeral / test-only
- You already ran a live test in the last 30 minutes on the same code path

Do not skip if:
- The plan mentions `$transaction`, `$queryRaw`, `$executeRaw`, or any upsert/insert
- The implementation touches a table with a unique constraint
- The scraper is expected to process >50 records per run

## When full integration testing is blocked: verify via side-effect API endpoints

A common real-world scenario: you've deployed the change, but you can't run a full integration test because:
- The page requires authentication (NextAuth credentials form, OAuth flow, SSO redirect)
- The test data hasn't been seeded
- The visual UI is in a browser-only state (no curl equivalent)
- Login timing is unreliable in headless Playwright

**The pattern:** find a non-auth API endpoint that exercises the package's code, call it with a known-good input, and verify the output contains characteristics only the package could produce. This proves the code path runs without requiring the full integration test.

Example from the nautical-route-maps package extraction (2026-07-05): the package contained an A* sea route pathfinder. After deploying to staging, the NextAuth login flow was unreliable in headless Playwright (form inputs have no `name` attribute before hydration; click+submit timing varies). The workaround:

1. Hit `/api/route-map?id=<real-itinerary-uuid>` — an endpoint that returns SVG via the package's `generateRouteSvg`
2. A real itinerary returned a **34,786-byte SVG** with **1,152 LineTo (L) commands** in the route path
3. Unknown IDs return a **327-byte fallback** SVG from the package's `generateFallbackSvg()`
4. 1,152 L commands is only possible if `findMultiPortSeaRoute` → `findSeaRoute` → A* min-heap pathfinder ran
5. A straight-line fallback would have produced ~5-10 L commands for a 7-port itinerary
6. Combined with the package's exact color codes (`#c8a55a`, `#3a5575`) appearing in the output, the deploy is verified

```bash
# Count waypoints (proof A* pathfinder ran)
grep -oE 'L[0-9]+\.[0-9]+,[0-9]+\.[0-9]+' /tmp/rm-test.svg | wc -l  # → 1152

# Verify package-specific colors
grep -o 'fill="#3a5575"' /tmp/rm-test.svg | wc -l  # → 8 (coastline polygons)

# Compare response sizes (real vs fallback)
curl -s "https://staging/api/route-map?id=<real-uuid>" | wc -c  # → 34786
curl -s "https://staging/api/route-map?id=<unknown>" | wc -c   # → 327
```

Generalizable checks after deploying any package extraction or library change:

1. **Compare response sizes** — real-package-output vs fallback. Size delta proves the non-fallback code path ran.
2. **Count output markers specific to the package's algorithms** — waypoint count, color hex codes, specific element counts, timing characteristics (e.g., A* runs in <500ms for cached data, much longer for fresh runs; a suspiciously fast response may indicate fallback)
3. **Check `page error` and `console error` counts** on unauthenticated landing pages — zero errors means the chunked bundle includes the package without import resolution failures
4. **Time the response** — fast response for cached data, slow for fresh compute. If a request that should take 2s returns in 50ms, something's wrong (likely returning fallback).

Full auth-based testing is still needed eventually, but side-effect verification gives confidence the deploy worked before you spend time debugging auth. Don't spin on login when a non-auth endpoint can prove the package is live.

## After finding a bug: extend the test, don't just fix it

The bugs this skill is designed to catch are **the exact kind of bugs that will reappear** the next time someone touches the same code path — either because the constraint wasn't documented, the timeout default isn't memorable, or the data shape is non-obvious. Fixing the bug without locking it in is leaving a trap for the next session.

After fixing a runtime bug, add a regression assertion to your existing test script or create one. The assertion should reproduce the scenario that triggered the bug:

| Bug found | Regression to add |
|-----------|-------------------|
| Unique constraint spans sources | Test against an entity with rows from a different source; assert `count(visits WHERE source = 'firecrawl') > 0` after the run |
| Transaction timeout at N rows | Add a comment in the test that the target has N+ visits and the timeout is 30s; if N drops, future readers will know why 30s was chosen |
| Silent snapshot-only commit | Assert `count(snapshots) === count(months_scraped)` AND `count(visits) > 0` — the bug was snapshots land but visits don't, so check both |
| Parser column shift | Add a row-count assertion to the test: `parsed.length === expected_count_from_cruisemapper_page` |

The test script at `scraper-worker/src/tests/firecrawl-selfhost-test.ts` already has the right shape — it compares parsed counts to DB counts after a real run. Use that pattern, or extend the `run-firecrawl-port-scraper.ts` runner to do a post-run DB assertion automatically.

**Rule:** A bug found at runtime without a corresponding test assertion is half-fixed. The next agent who refactors the scraper will reintroduce it.