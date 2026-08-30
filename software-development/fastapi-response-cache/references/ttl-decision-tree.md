# TTL Decision Tree

How to pick the right `max-age` (seconds) for a cached endpoint.

## Quick decision rule

```
max-age = time_between_data_updates / 2
```

If your data updates every 2 hours (e.g. nightly pipeline at 2AM), `max-age=3600` is safe. If data shifts every minute (e.g. live game odds), `max-age=30` is generous.

## By data class

| Data class | Update cadence | Recommended TTL | Why |
|---|---|---|---|
| **Pipeline-derived** (ratings, MC simulations) | Once daily (2AM) | 3600s (1h) | No user expects to see "this morning's stale data" within an hour of a fresh run |
| **Daily aggregation** (yesterday's accuracy, today's games) | Once daily (after midnight) | 1800s (30m) | Some users run their own daily check, then check again before bed |
| **Live data** (current odds, in-progress game state) | Real-time (seconds) | 5–10s | Stale data here is actively misleading |
| **Volatile derived** (divergence, scenario, playoff odds) | Every pipeline run | 5–30s | May shift with new injury reports or MC re-simulation |
| **Reference data** (sport list, team list, sport→id map) | Almost never | 86400s (24h) | The data is static; even an hour is conservative |
| **User-specific** (per-team history) | N/A | **0 (bypass)** | Wrong shape — needs a per-user cache key dimension |
| **Static page content** (HTML, JS, CSS) | Per deploy | 3600s + content-hash in URL | Standard HTTP cache pattern; separate from API |

## When to break the rule

- **Debugging window** — when first shipping, use 5s for everything. Promote to longer TTLs after confirming no false-positive staleness complaints.
- **High write contention** — if a route does heavy writes that invalidates the cache, lower the TTL OR use `cache_delete_pattern` to flush on writes.
- **Multiple deploys per day** — a 24h TTL may outlive a deploy; use shorter TTLs if you deploy hot.

## The right question to ask

"**What is the maximum age of data the user is willing to see?**" If they want fresh-by-the-second, you have a different problem (websockets, SSE). If they're OK with 5-minutes-stale, `max-age=300` is fine. If they expect nightly freshness, `max-age=3600` is fine.

## Per-route examples (from the ELO Scenario Lab plan)

```python
_ROUTE_TTLS = {
    # Slow-changing reference data
    "/api/ratings": 60,            # ratings update after games (~minutes apart)
    "/api/teams": 60,              # same
    "/api/playoffs/mlb": 30,       # changes after re-simulate

    # Volatile derived data
    "/api/divergence": 5,          # may shift with new MC data
    "/api/schedule/mlb": 5,        # live game schedule
    "/api/schedule/nfl": 5,
    "/api/schedule/nba": 5,
    "/api/schedule/nhl": 5,
    "/api/schedule/mls": 5,

    # Bypassed (not in the cache table at all)
    # /api/teams/{sport}/{id}/history   — per-team
    # /api/scenarios                      — heavy + volatile
    # /api/auth/*                         — user-scoped
    # /api/admin/*                        — state-changing
}
```

## Why "private" not "public" with these TTLs

`Cache-Control: public, max-age=60` would let a CDN cache the response for 60s. That's correct only if the response is *truly* the same for every user. For a sport-scoped API, the response is the same for every user — but the response was generated on behalf of an authenticated request. Using `private` keeps the cache in your LRU/Redis layer (where you can `clear_cache()` on deploy) and out of any CDN tier that might cache across users or across deploys.
