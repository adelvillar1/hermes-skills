# ScrapingBee Port-Schedule Run — 2026-06-19 → 2026-06-25

Session-specific detail for the failure pattern described in §19 of the SKILL.md (verify join keys on both sides before trusting a new scraper). Captures exact numbers, the hourly cliff pattern, and the bridge script that recovered the stranded rows.

## What ran

- **Scraper**: `scraper-worker/src/scrapers/scrapingbee-port-schedules.ts`
- **Mode**: Bulk backfill of `port_ship_visits` for 2,377 ports × 24 months
- **Duration**: 2026-06-19 15:00 UTC → 2026-06-25 04:00 UTC (≈6 days unattended)
- **Queue order**: ports sorted by `visitCount DESC` (highest-value first)
- **Cost cap**: hit zero credits at 2026-06-24 10:00 UTC; kept retrying for ~18 hours

## Hourly success pattern (the cliff)

| Window | Status |
|--------|--------|
| 2026-06-19 15:00 → 2026-06-24 09:00 | **99% HTTP 200** (~90,449 successful snapshots) |
| 2026-06-19 15:00 | 1,608 HTTP 400 (transient config error at run-start, fixed within an hour) |
| 2026-06-24 10:00 | **93 OK, 3,117 HTTP 401** — the cliff |
| 2026-06-24 11:00 → 2026-06-25 04:00 | **0% OK, 100% HTTP 401** for ~18 hours straight |
| 2026-06-25 04:00 | 157 HTTP 401, then run terminates |

The 2026-06-24 10:00 UTC cliff is the diagnostic signature of credit exhaustion on ScrapingBee. The retry logic in `scrapingbee-client.ts` retries 3 times on 401, multiplying wasted credits 5× per rejected request.

## Cost breakdown

| Metric | Value |
|--------|-------|
| Total credits spent | 587,530 |
| Credits on HTTP 200 | 219,460 (37.4%) |
| Credits on HTTP 401 (post-exhaustion) | 357,565 (60.8%) |
| Credits on HTTP 400 (initial config error) | ~8,840 |
| Distinct ports fully successful | 695 (29%) |
| Distinct ports fully failed | 1,435 (60%) — all `visitCount < ~35` |
| Distinct ports partially successful | 247 (10%) |

The 1,435 fully-failed ports are concentrated in `visitCount < ~35` because the queue is sorted by `visitCount DESC` and credits ran out partway through — *not* because the small ports are unreachable, but because they were processed last and the budget was empty.

## The wiring gap (why the data was stranded)

The scraper's upsert block at `scrapingbee-port-schedules.ts` lines 147-161 writes:

```ts
data: {
  portName, portSlug, cruiseMapperId, cruiseMapperPortUrl,
  shipName, visitDate, arrivalTime, departureTime,
  matchStatus: 'pending', source: 'scrapingbee'
}
```

It does **not** write `matchedShipId`. The downstream bridge (`scripts/scraper-service/match-ports-to-itineraries.ts`) keys on `matchedShipId` and falls back to `shipName` lookup against the `ships` and `ship_aliases` tables. So the rows were recoverable by running the bridge — but until the bridge ran, all 222K rows were stranded with `matchStatus='pending'`.

The HTML audit trail is also empty: `raw_html` is NULL on all 117,284 snapshots. ScrapingBee with `extract_rules` returns only the extracted keys; `data.html` is not in the response. There is no ship ID data anywhere in the snapshots — backfill by re-parsing HTML would require a re-scrape.

## The recovery bridge (what worked)

```bash
# 1. Dry-run first — verifies match rate without writes
DATABASE_URL="<staging>" npx tsx scripts/scraper-service/match-ports-to-itineraries.ts --dry-run --verbose

# 2. Live run — populates matchedShipId + writes port_visit_itineraries junctions
DATABASE_URL="<staging>" npx tsx scripts/scraper-service/match-ports-to-itineraries.ts
```

Match results on the 222,816 ScrapingBee rows:

| Outcome | Distinct ship names | Rows | % |
|---|---|---|---|
| Exact name match against `ships.name` | 597 | 191,070 | 85.8% |
| Match via `ship_aliases` | 93 | 21,665 | 9.7% |
| Unmatched | 494 | 10,081 | 4.5% |
| **Total** | **1,184** | **222,816** | **100%** |

The 4.5% unmatched bucket includes river ships (`amanubia`, `amadeus riva`) that may not be in the `ships` table, plus parser artifacts where CruiseMapper extracted a port name as the ship (`albany ny`, `arriving in amsterdam holland`).

## Full chain that recovered the data

| Step | Script | Outcome |
|------|--------|---------|
| 1 | `match-ports-to-itineraries.ts` (dry-run) | 195,212 of 224,353 pending visits would resolve |
| 2 | `match-ports-to-itineraries.ts` (live) | 195,212 → `matched`, 846,117 junction rows inserted in 256s |
| 3 | `refresh-mv-itinerary-port-visits.ts` | MV refreshed in 68.5s (2.17M rows, was 1.33M) |
| 4 | `compute-route-corridors.ts --dry-run` | 5,961 missing-sig itineraries, 0 changed corridors |
| 5 | `compute-route-corridors.ts` (live) | 842 sigs computed, 342 corridors upserted, 894 regionId sync, 8s total |

## Takeaway

A 6-day, 587K-credit run produced zero rows that reached the corridor pipeline until the bridge was run. The bridge was 5 minutes of work; the run was 6 days. The asymmetry is what §19 is about: producer-correct ≠ consumer-correct, and the consumer-side check is the one most often skipped.
