---
name: api-performance-optimization
description: "Use when optimizing HTTP API page-load or response latency for a production service. Covers the full loop: baseline measurement (cold + warm p50/p95), infrastructure layer targeting (HTTP response cache, GZip, ETag/304, Redis backing), per-route TTL decisions, bypass rules for writes/auth, production measurement after deploy, and reading the numbers without misattributing RTT. Applies to FastAPI / Starlette / any ASGI or WSGI framework; the cache middleware pattern generalizes."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [performance, optimization, api, caching, etag, gzip, measurement, baseline, fastapi]
    related_skills: [draft-feature-plan, project-warmup, write-session-recap, browser-automation, api-performance-baseline, fastapi-response-cache, legacy-iife-to-es-modules]
---

# API Performance Optimization

Repeatable recipe for cutting HTTP API latency end-to-end. Defense-in-depth: cache the response, compress the body, negotiate with the client via ETag, then optionally split the bundle on the frontend.

## When to Use

- A page is slow to load and the bottleneck is API call latency (not frontend render).
- Multiple views fan out to the same handful of read endpoints.
- The service has Redis (or any shared cache) available for cross-process cache.
- The service is behind a reverse proxy / CDN and the response body is large.
- Production traffic is on, so changes must be measurable and reversible.

## When NOT to Use

- The bottleneck is frontend JS execution or DOM size → use a frontend perf skill.
- The bottleneck is database query cost → optimize the SQL, not the API layer.
- You don't have a way to measure the win in production (no auth token, no URL, no observability) → set that up first, this skill is measurement-driven.

## The Loop (always run it)

```
1. Pre-deploy:  perf_baseline.py <base_url> <token> before
2. Ship change (cache middleware / GZip / etc.)
3. Push to main, wait for deploy
4. Post-deploy: perf_baseline.py <base_url> <token> after
5. Diff the JSONs. Report actual numbers. Do not paraphrase the harness.
```

If the step "wait for deploy" is unclear, probe with a small authenticated call and look for a marker you can correlate to your change (X-Cache header, a new Content-Encoding, a debug header). Don't guess.

## Five Phases, Independently Shippable

Layered defenses. Each is a separate PR so you can measure the win per phase and bail on any that don't pay off.

### Phase 1 — HTTP response cache middleware (highest impact, lowest risk)

* **Storage:** in-process LRU (per-worker) backed by Redis (cross-process). The LRU is the read-through accelerator; Redis is the write-through source of truth.
* **Cache key:** `f"{method}:{path}:{sorted_query_string}"`. Sort the query string so `?sport=mlb&page=1` and `?page=1&sport=mlb` produce the same key.
* **TTL:** per-route table. Sport-scoped read endpoints that change at most once a day tolerate 30-60s. Volatile aggregations (scenarios, divergence) tolerate 5-10s. Default to 5s for anything you can't classify.
* **Bypass rules (MUST be explicit):** non-GET methods, paths matching `_NEVER_CACHE_PATH_PREFIXES` (e.g. `/api/auth/`, `/api/admin/`, `/api/teams/{id}/history` for per-team), the `/api/health` endpoint, responses that set `X-No-Cache: 1`.
* **ETag:** SHA1 of the response body, prefixed `W/"`. Return `ETag` and `Cache-Control: private, max-age=N` on cached responses. Return `304 Not Modified` (empty body) on matching `If-None-Match`.
* **Cache-Control: private, max-age=N** (not `public`) even if responses are sport-scoped — keeps intermediaries from caching user-bearing data by accident.

### Phase 2 — Redis backing

Wrap your response cache's `cache_set`/`cache_get` to write through to Redis. Reuse the existing `cache.cache_set` / `cache.cache_get` if your service already has a Redis layer (it should, for sessions / MC / market odds). Skip Redis writes for bodies < 200 bytes (overhead > savings).

Namespacing: use a distinct prefix (`resp:*`) so a `cache_delete_pattern('resp:*')` only flushes response cache, not `mc:*` or `ratings:*` keys.

### Phase 3 — GZip middleware

`app.add_middleware(GZipMiddleware, minimum_size=500)`. One line. Compresses responses ≥ 500 bytes when the client sends `Accept-Encoding: gzip` (every browser does).

Expect 4-10x size reduction on JSON; the more repetitive the schema, the bigger the win. Test it explicitly with an `Accept-Encoding: gzip` curl; verify `Content-Encoding: gzip` and that the decodable JSON is unchanged.

### Phase 4 — Frontend lazy view loading

For SPAs that dynamic-import every view module on first paint: split the 8 critical-path modules (auth, config, state, dom, api, format, dom-refs, hash) from the 13 view modules. Lazy-load views on route activation. Drop the `?cb=Date.now()` cache buster on view imports (it's load-bearing only on the critical path that must always re-execute).

Expected: first-paint JS drops 60-70%. View switches drop to ~10ms warm.

### Phase 5 — Streaming render + `requestIdleCallback`

For pages that `await` 4-5 API calls in parallel before showing anything: render the page shell + skeleton placeholders in <100ms before any data resolves. Defer non-critical sections (trending, alerts) to `requestIdleCallback` with a Safari < 17.4 fallback (`setTimeout(fn, 0)`).

This is the cold-cache UX fix — even if data takes 4s to arrive, the user sees structure immediately.

## Pitfalls (read these before shipping)

### "Redis unavailable" usually means the app can't resolve the injected Redis hostname

Managed platforms (Railway, Render, Fly.io, etc.) typically inject `REDIS_URL` with a **private/internal hostname** that only resolves inside their network. In some container configurations this hostname fails to resolve (`nodename nor servname provided, or not known`), even though Redis itself is healthy.

**Fix:** make your Redis initializer try the primary `REDIS_URL` first, then fall back to the platform's public proxy URL (e.g. Railway's `REDIS_PUBLIC_URL`) with a short `socket_connect_timeout`. Log which URL succeeded/failed. The public proxy is slightly slower but reliable; the private hostname is faster when it works. Add a `/admin/redis-check` endpoint exposing `connected`, `client_host`, and `dbsize` so future debugging is one curl away.

Example shape:
```python
for key in ("REDIS_URL", "REDIS_PUBLIC_URL"):
    url = os.environ.get(key)
    if not url:
        continue
    try:
        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=5)
        client.ping()
        logger.info("Redis connected via %s", key)
        return client
    except Exception as exc:
        logger.warning("Redis connection failed for %s: %s", key, exc)
logger.warning("Redis unavailable — cache disabled")
return None
```

### Don't trust the harness's p95 number at face value if the harness is geographically far from the server

The end-to-end RTT between the harness and the server is *part of* the wall-clock time. A 200ms warm p95 measured from a US-East harness to a Railway US-Central app is dominated by RTT, not by server work. The real win is bigger than the harness shows.

**Verify:** add a direct probe that confirms `X-Cache: HIT-LRU` on warm calls. If the server is returning from cache in <1ms, the 200ms is just RTT — the user on a same-region browser will see <50ms.

### Cold-cache "first call" times can be slower than warm times

The very first call to a cold endpoint incurs the full SQL/Python pipeline cost. That's the true baseline. The 4,000ms you see on call 1 is the work, not a bug. Phase 1 (cache) makes that work happen once per TTL window, not once per request.

### `startswith` is not glob

If you mock `cache_delete_pattern` in tests, do NOT use `str.startswith(prefix)`. The real Redis function does `SCAN MATCH {prefix}*` (glob). Use `fnmatch.fnmatchcase(k, f"{prefix}*")` in your mock. This bit me in production code once — the keys were right, the mock was wrong, and `clear_cache` silently no-oped in tests.

### ETag should be `W/"<hash>"` (weak), not `"<hash>"` (strong)

The body is semantically equivalent across caching windows, so weak ETag is correct. It also avoids 304s being rejected by clients that require byte-for-byte equality.

### Bodies < 200 bytes shouldn't hit Redis

A 50-byte JSON + the Redis SET/GET round-trip + serialization = more CPU/network than just serving the response. Skip Redis for tiny bodies. The LRU still caches them; only the cross-process layer is skipped.

### The cache middleware MUST be installed AFTER CORS

CORS short-circuits OPTIONS preflights. If you install response-cache first, the X-Cache / ETag headers you set may not make it through the CORS pass. Reverse the order in your `main.py`.

### Be ruthlessly honest about bypass rules

A cache that serves a 5-minute-stale `/api/auth/me` is a security incident. Audit each cached endpoint for user-scoping. Default to bypass for anything that returns user data, anything that takes a body or POSTs, and anything behind `/api/admin/`.

### The `_should_bypass` check must run BEFORE the cache key

Otherwise you generate keys for `/api/auth/login` (which then never get hit again, but pollute the LRU). Cheap fix; expensive if you forget.

## Per-Route TTL Heuristics

| Endpoint type | TTL | Rationale |
|---|---|---|
| ELO ratings (per-sport, post-pipeline) | 60s | Pipeline runs at 2AM; ratings don't change mid-day |
| Team lists (all teams, sport-scoped) | 60s | Same as ratings |
| Upcoming schedule with win probabilities | 5-10s | Could shift with new injury data |
| Scenario aggregations (per-game) | 5s | Volatile; depends on injury state — consider bypassing entirely |
| Divergence (current vs MC projected) | 5s | Changes when new MC sim runs |
| Playoff odds | 30s | MC output, recomputed on `mc-simulate` |
| Per-team history | BYPASS | Varies by team; not cacheable as a single key |
| Auth / admin / pipeline | BYPASS | User-scoped or write side-effects |

## Verification

After each phase:

1. **Cold-path ETag + Cache-Control headers** present: `curl -i <url>` shows `ETag: W/"..."` and `Cache-Control: private, max-age=N`.
2. **Warm path** uses cache: `X-Cache: HIT-LRU` (or `HIT-REDIS` on cross-process hit) on second call within TTL.
3. **304 path**: third call with `If-None-Match: <etag>` returns 304 with empty body and `X-Cache: HIT-LRU-304`.
4. **Write endpoints** never show `X-Cache: HIT-*` — verify with a POST.
5. **GZip**: `curl -H "Accept-Encoding: gzip" -i <url>` shows `Content-Encoding: gzip` and the body is 3-10x smaller.
6. **Tests** for the middleware cover: bypass rules, LRU hit/miss, Redis hit, 304 LRU+Redis paths, per-route TTL, clear_cache() wiping both stores.
7. **Pytest** total count increases by N (where N = new tests) and remains 0 fail.

After deploy, re-run the harness and diff. Don't paraphrase — paste the diff.

## Test Patterns

For the response-cache middleware specifically:

```python
# Fixture: a mock Redis with proper glob semantics (NOT startswith)
def _delete_pattern(prefix):
    glob = f"{prefix}*"
    keys = [k for k in fake_store if fnmatch.fnmatchcase(k, glob)]
    for k in keys: del fake_store[k]
    return len(keys)

# Test 304 returns empty body
def test_conditional_get_304(client):
    r1 = client.get("/api/ratings")
    r2 = client.get("/api/ratings", headers={"If-None-Match": r1.headers["ETag"]})
    assert r2.status_code == 304
    assert r2.content == b""
    assert r2.headers.get("X-Cache") == "HIT-LRU-304"

# Test bodies below Redis threshold still go to LRU
def test_small_bodies_skip_redis(client, mock_redis):
    client.get("/api/tiny")  # returns ~70 bytes
    assert len(rc._lru) == 1
    assert len(mock_redis) == 0  # didn't make it to Redis
```

## Linked Artifacts

- `scripts/perf_baseline.py` — measurement harness; reusable across projects
- `src/api/middleware/response_cache.py` — reference implementation
- `docs/plans/2026-06-11-frontend-and-api-perf.md` — full plan from a real session
- `references/response-cache-recipe.md` — deep-dive implementation notes for Phases 1-3
- `references/frontend-lazy-view-loader.md` — deep-dive for Phase 4 (router.js pattern, ?cb=Date.now() boundary, test seam)

## When You're Done

Write a session recap with:
- Before/after p50/p95 for every endpoint measured
- The list of new cache keys / TTLs introduced
- Any endpoint deliberately excluded from caching and why
- Verification commands the user can re-run
