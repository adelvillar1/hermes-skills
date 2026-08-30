---
name: fastapi-response-cache
description: "Add a Starlette/FastAPI HTTP response cache middleware for sport- or tenant-scoped read endpoints. Caches full response bodies with LRU (in-process) + Redis (cross-process) backing, ETag/If-None-Match 304 conditional GET, and per-route TTLs. Use this skill when a FastAPI app's GET endpoints recompute the same data on every navigation (no Cache-Control, no ETag, no Content-Encoding), when a single page fans out to 4-6 endpoints and each takes 300ms-4s, when building admin/dashboard APIs that re-render on every view change, or when you want a 5-50x latency win without changing the routes themselves. Includes a drop-in ~340-line middleware and a 15-test pytest harness — do not write your own when this template exists. Pairs with api-performance-baseline (measure first) and api-performance-optimization (the orchestration). Avoid for user-scoped data, write endpoints, or any response that varies per-token."
version: 1.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [fastapi, starlette, middleware, caching, redis, etag, performance, http-cache, response-cache]
    related_skills: [api-performance-baseline, materialized-view-dashboard-optimization, fastapi-static-dashboard, draft-feature-plan]
---

# FastAPI Response Cache Middleware

A drop-in Starlette `BaseHTTPMiddleware` that caches HTTP responses in two tiers — an in-process LRU (no network, <1ms hits) backed by Redis (cross-process, survives deploys) — with ETag/If-None-Match 304 conditional GET support and per-route TTLs. Designed for sport-, tenant-, or league-scoped read endpoints that are currently re-executing the full SQL+Python pipeline on every navigation.

## Why this exists

A typical dashboard fans out to 4-6 GET endpoints in parallel. If none of them cache, every navigation re-runs the same queries. The Today view in ELO Scenario Lab measured (2026-06-11):

| Endpoint | Warm p95 | Body size |
|---|---|---|
| `/api/schedule/mlb` | **4,181ms** | 1,101KB |
| `/api/scenarios` | 655ms | 291KB |
| `/api/divergence` | 564ms | 8KB |
| `/api/ratings` | 539ms | 21KB |

No `ETag`, no `Cache-Control`, no `Content-Encoding`. The page load = sum of those p95s because `Promise.all` doesn't help when each call is a full cold run. After this middleware: every warm call returns in <30ms (LRU) or <200ms (Redis), the browser sends `If-None-Match` and gets 304, and Today view load drops to ~100ms.

## When to Use

- **Sport/league/tenant-scoped read endpoints** returning the same data for every authenticated user
- **Endpoints that are slow but stable** — pipeline runs at 2AM, ratings update after games, no per-request variation
- **Dashboard / admin pages** that hit the same 4-6 endpoints on every render
- **Public API endpoints** with no auth or only API-key auth (no per-user cache keying needed)
- **You measured first** with `api-performance-baseline` and confirmed warm ≈ cold (the smoking gun)

## Don't Use For

- **User-scoped data** (per-account dashboards, personalized feeds) — wrong shape; would need a per-user key dimension
- **Endpoints with per-request variation** (timestamps, request IDs, request-derived headers) — the cache key needs to capture every varying input
- **Write endpoints** (POST/PUT/PATCH/DELETE) — bypass rule below handles this but the value of caching writes is zero
- **Streaming responses** (SSE, websockets, large file downloads) — the body-collection pattern in this middleware assumes finite, fully-buffered bodies
- **Endpoints that are already fast** (<20ms) — adding a cache layer costs more in latency variance than it saves
- **Replacing a fine-grained cache** (per-row, per-entity) — this is HTTP-level; for query-level caching, see `materialized-view-dashboard-optimization`

## The Middleware Shape

`src/api/middleware/response_cache.py` (~340 lines). Five pieces:

1. **Bypass rules** — never cache non-GET, never cache `/api/auth/`, `/api/admin/`, `/api/pipeline/`, `/api/teams/{id}/history`, `/api/health`, etc. List-driven, easy to extend.
2. **Cache key** — `f"{METHOD}:{path}?{sorted_query_string}"`. Sort the query string so `?sport=mlb&page=1` and `?page=1&sport=mlb` collide.
3. **ETag** — SHA1 of the response body, returned on every cached response. Client sends `If-None-Match`; matching ETag returns 304 with empty body.
4. **Two-tier storage** — LRU first (1024 entries, maxsize configurable), Redis second (shared across workers). On miss: LRU → Redis → route. On write: LRU + Redis (fire-and-forget for Redis).
5. **`X-Cache` debug header** — `MISS` / `HIT-LRU` / `HIT-REDIS` / `HIT-LRU-304` / `HIT-REDIS-304`. Lets you grep Railway logs to verify the cache is hitting.

## Per-Route TTL Configuration

Default 5s. Override per-path via a dict in the middleware:

```python
_ROUTE_TTLS: dict[str, int] = {
    "/api/ratings": 60,           # pipeline runs at 2AM — 60s is safe
    "/api/teams": 60,
    "/api/divergence": 5,         # may shift with new MC data
    "/api/schedule/mlb": 5,       # ditto
    "/api/playoffs/mlb": 30,      # changes after re-simulate
}
```

Or call `mark_route_cacheable("/api/foo", 30)` at import time from a route module. The TTL is also returned as `Cache-Control: private, max-age=N` so the browser caches for the same window.

**TTL design principle:** the longest TTL you can defend is `time_between_data_updates / 2`. If your pipeline runs at 2AM, a 12-hour TTL is theoretically fine. In practice, 60s for slow-changing and 5s for hot-changing data gives you the win without any staleness complaints.

## Install

```python
# src/api/main.py
from fastapi.middleware.cors import CORSMiddleware
from src.api.middleware.response_cache import install_response_cache

app = FastAPI(...)
app.add_middleware(CORSMiddleware, ...)  # CORS first
install_response_cache(app)              # Cache second
app.include_router(...)                   # Routes last

# Important: `Cache-Control: private` (not public). Although responses
# are sport-scoped (same for every user), `private` keeps intermediaries
# from caching user-bearing data by accident if you ever extend the bypass
# list to allow per-user routes.
```

## Body Collection Pattern

The middleware sits between Starlette's routing and the FastAPI route handler. To cache the body, you must read it from the `Response` object before returning — and FastAPI's `JSONResponse` already has `.body` as bytes:

```python
if hasattr(response, "body") and isinstance(response.body, bytes):
    body = response.body
else:
    # Streaming path (rare for FastAPI route handlers)
    body = b""
    iterator = getattr(response, "body_iterator", None)
    if iterator is not None:
        async for chunk in iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode()
```

The `body_iterator` access is a known false-positive in Pyright — it's a runtime attribute on Starlette's `Response` but not in the type stubs. `getattr` with a default suppresses the warning.

## Skip Redis for Small Bodies

Bodies < 200 bytes skip the Redis write. Tiny responses (a 70-byte `{status: "ok"}`) don't benefit from cross-process caching and burn Redis cycles on every write. The in-process LRU still gets them.

```python
if len(body) >= 200:
    try:
        cache_mod.cache_set(redis_key, entry, ttl=max_age)
    except Exception as exc:
        logger.debug("Redis resp-set failed for %s: %s", redis_key, exc)
```

## Test Harness Pattern (15 tests, 0.3s)

Mock `src.services.cache` so tests don't need a live Redis. The mock **must use glob matching, not `str.startswith`** — see Pitfall #1 below.

```python
@pytest.fixture
def mock_redis():
    fake_store: dict[str, dict] = {}
    def _get(key): return fake_store.get(key)
    def _set(key, value, ttl=300):
        fake_store[key] = value
        return True
    def _delete_pattern(prefix):
        # The real cache.cache_delete_pattern appends '*' and uses
        # Redis SCAN MATCH (glob). Mimic that with fnmatch.
        import fnmatch
        glob = f"{prefix}*"
        keys = [k for k in fake_store if fnmatch.fnmatchcase(k, glob)]
        for k in keys: del fake_store[k]
        return len(keys)
    with patch.object(rc.cache_mod, "cache_get", side_effect=_get), \
         patch.object(rc.cache_mod, "cache_set", side_effect=_set), \
         patch.object(rc.cache_mod, "cache_delete_pattern", side_effect=_delete_pattern), \
         patch.object(rc.cache_mod, "get_redis", return_value=MagicMock()):
        yield fake_store
```

Test categories to cover (the canonical set):

1. **Bypass** — non-GET, `/api/health`, `/api/auth/*`, `/api/admin/*` all return without `X-Cache` header
2. **LRU hit** — second call returns `X-Cache: HIT-LRU`, identical ETag, identical body
3. **Redis hit promotes to LRU** — clear LRU between calls, second call shows `X-Cache: HIT-REDIS`, third call shows `HIT-LRU`
4. **304 LRU** — `If-None-Match` with LRU-cached ETag returns 304 with empty body
5. **304 Redis** — same, with LRU cleared
6. **Cache-Control header** — `private, max-age=60` for ratings, `private, max-age=5` for divergence
7. **clear_cache()** — wipes both LRU and Redis (`resp:*` keys), `cache_delete_pattern` is called with the right prefix
8. **Per-route TTL override** — `mark_route_cacheable()` updates the dict
9. **Small bodies skip Redis** — body < 200 bytes doesn't write to fake_store
10. **Cache key normalization** — sorted query string (e.g. `?a=1&b=2` ≡ `?b=2&a=1`)

Use `TestClient(app)` (FastAPI's, not httpx directly) — it handles ASGI middleware stack lifecycle correctly.

## Common Pitfalls

### 1. `cache_delete_pattern` uses Redis glob, not Python `str.startswith`

**This is the #1 trap.** The Redis-backed `cache.cache_delete_pattern` in `src/services/cache.py` appends `*` to the prefix and uses Redis `SCAN MATCH` (a glob). Python's `str.startswith` does NOT honor `*` — `'resp:foo'.startswith('resp:*')` is `False`.

```python
# ❌ Looks right, silently broken — every cache-delete misses
def _delete_pattern(prefix):
    keys = [k for k in store if k.startswith(prefix)]
    ...

# ✅ Mirrors Redis SCAN MATCH semantics
def _delete_pattern(prefix):
    import fnmatch
    glob = f"{prefix}*"
    keys = [k for k in store if fnmatch.fnmatchcase(k, glob)]
    ...
```

**Symptom:** `clear_cache()` returns `{redis_keys_cleared: 0}` even when the store has matching keys. The data layer is fine; only the test mock or your own delete helper is wrong. Always confirm by printing the matched-key count from your delete function.

### 2. `body_iterator` is a Pyright false positive

Starlette's `Response` has `body_iterator` as a runtime attribute (set after `render()` is called), but the type stubs don't expose it. Pyright flags it. Use `getattr(response, "body_iterator", None)` to silence the warning without runtime risk.

### 3. Caching user-scoped data leaks across users

If a cached endpoint returns data that varies per user, the ETag will collide and one user could see another's response. **Audit every cached endpoint** before adding it to the safe list:

- Is the response sport/league/tenant-scoped (same for every user)? → Safe to cache
- Does it include `user.email`, `user.role`, or per-account data? → Add to bypass list
- Does it depend on `request.headers` (other than auth)? → Add to bypass list

The default `Cache-Control: private` (not `public`) is a defense-in-depth: it tells intermediaries not to cache, even if the cache key is correct.

### 4. `Content-Length` must be removed when you rebuild the body

When the middleware reads `response.body` and re-wraps it in a new `Response`, the original `Content-Length` header may be wrong (especially if you used GZip middleware elsewhere). Always `headers.pop("content-length", None)` before re-wrapping, or downstream CDNs will reject the response.

### 5. "Redis unavailable" often means the injected Redis hostname doesn't resolve

Managed platforms (Railway, Render, etc.) inject `REDIS_URL` with a private/internal hostname. In some container configs this fails to resolve (`nodename nor servname provided, or not known`) while Redis itself is healthy. Build a fallback to the platform's public proxy URL (e.g. `REDIS_PUBLIC_URL`) with `socket_connect_timeout=5`, log which URL succeeded/failed, and add an admin diagnostic endpoint (`/admin/redis-check`) returning `connected`, `client_host`, and `dbsize`.

### 6. Redis LRU eviction interacts badly with this cache

If your `redis.conf` has `maxmemory-policy allkeys-lru` (or similar), the OS can evict cache entries from under you. The middleware will silently miss and re-run the route. For predictable behavior, run Redis in `noeviction` mode OR use a separate Redis instance for response caching with `allkeys-lru` and accept the variance.

### 7. Cache-Control: `public` vs `private`

Use `private` (not `public`) for auth-gated APIs. Even when responses are sport-scoped (identical for every user), the response was generated on behalf of an authenticated request — `public` invites CDN caching that may or may not respect the auth context. `private` keeps the cache in the LRU/Redis layer you control.

### 8. Don't cache the auth probe

The `/api/auth/me` endpoint returns the current user — varies per token. It's covered by the `/api/auth/` prefix in the bypass list. If you write a custom auth probe, add it to the bypass set explicitly.

### 9. Static assets (.js/.css/.html) must bypass the cache entirely

**This is the most common production cache bug.** The response cache middleware processes ALL GET requests that aren't in `_NEVER_CACHE_PATH_PREFIXES`. Static files served via `StaticFiles` (`.js`, `.css`, `.html`) pass right through the bypass check. The middleware caches them with ETags, and when you push updated JS, the browser sends the old ETag and gets `304 Not Modified` — serving stale JS **forever**.

**Symptom:** You push a JS fix to production. Users do a hard refresh (Cmd+Shift+R) and STILL see the old behavior. The browser's DevTools Network tab shows `304 Not Modified` for the JS files. The fix works locally (where the LRU cache was flushed on restart) but not in production (where Redis still has the old ETag).

**Real example (2026-06-16):** Signal bars descriptions were added to `signalBars.js`. The file was deployed to Railway. But the response cache middleware had already cached the old `signalBars.js` with an ETag. Every browser request with `If-None-Match: <old-etag>` got `304 Not Modified` back. The descriptions never reached users. Debugging this wasted 3+ cycles before someone checked the `X-Cache` header on the static file response.

**Fix — two layers:**

1. **Bypass static assets in the middleware:**
```python
def _should_bypass(path: str, method: str) -> bool:
    if method != "GET":
        return True
    if path in ("/api/health", "/", ""):
        return True
    # Never cache static assets
    if path.endswith(".js") or path.endswith(".css") or path.endswith(".html"):
        return True
    for prefix in _NEVER_CACHE_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False
```

2. **Add `Cache-Control: no-cache, must-revalidate` to static file responses** via a `StaticFiles` subclass so the browser always revalidates:
```python
class _NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        resp = await super().get_response(path, scope)
        if path.endswith((".js", ".css", ".html")):
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        return resp

app.mount("/", _NoCacheStaticFiles(directory="ui", html=True), name="ui")
```

3. **Bump the script tag version** as a one-time cache-buster for already-cached browsers:
```html
<!-- Before: <script src="/js/dashboard.js"></script> -->
<script src="/js/dashboard.js?v=2"></script>
```

**Why `?cb=Date.now()` on dynamic imports isn't enough:** the dynamic `import('/js/lib/foo.js?cb=Date.now())` in `dashboard.js` handles module-level cache-busting. But `dashboard.js` itself is loaded via a plain `<script src="/js/dashboard.js">` tag with no cache-buster. If the browser cached the OLD `dashboard.js` (which doesn't have the new import), no amount of cache-busting inside the new `dashboard.js` matters — the browser never fetches it.

**Diagnostic heuristic:** When a JS fix works locally but not in production after deploy, check `X-Cache` headers on the static file response. If it says `HIT-LRU-304` or `HIT-REDIS-304`, the response cache is serving stale JS.

### 10. ETag 304 check must verify cache entry hasn't expired

**This is the most insidious bug in this middleware.** The conditional GET path (lines ~259-277 in the template) checks `If-None-Match` and returns `304 Not Modified` when the client's ETag matches the cached entry. But if the code only checks `if cached is not None` and skips the expiration check, the middleware will return `304` for **expired** cache entries — serving stale data indefinitely.

**Symptom:** Data exists in the database (verified by direct DB queries), but the UI shows stale results. The `304` response is invisible in logs because it's a "success" status code — no error, no traceback, just stale data. This can waste hours of debugging on the data pipeline when the real problem is the HTTP cache layer.

**Real-world example (2026-06-16):** The accuracy page showed games with "—" in market odds columns even though odds had been copied to production PostgreSQL and verified to match. The entire data pipeline was correct — the cache was serving a response computed before the odds data existed, and the ETag check never let it refresh.

**Fix:** Every ETag-match check in the 304 path must also verify `cached["expires_at"] > time.time()`:

```python
# ❌ Bug: returns 304 for expired entries
if cached is not None:
    if cached["etag"] == if_none_match:
        return Response(status_code=304, ...)

# ✅ Correct: expired entries fall through to the route handler
if cached is not None and cached["expires_at"] > time.time():
    if cached["etag"] == if_none_match:
        return Response(status_code=304, ...)
```

Apply the same fix to **both** the LRU and Redis 304 paths. The full-body cache hit path (lines ~280-286) already checks `expires_at` — it's only the ETag revalidation paths that tend to skip it.

**Diagnostic heuristic:** When data exists in the DB but the UI shows stale results, check the HTTP response cache layer FIRST. Look for `304 Not Modified` in server logs, or check `X-Cache` headers. If the client keeps getting 304s, the cache entry is expired but the ETag check isn't enforcing the TTL.

### 11. Middleware order matters

Install `ResponseCacheMiddleware` AFTER `CORSMiddleware` but BEFORE route mounting. Starlette runs middleware in reverse-registration order (last added = outermost). The cache needs to see the final response (after CORS) but before the route handler.

```python
app.add_middleware(CORSMiddleware, ...)        # 1st added = innermost
install_response_cache(app)                    # 2nd added = wraps CORS
app.include_router(...)                         # 3rd = deepest
```

### 12. Pydantic response model strips undeclared fields — endpoint returns 422

When you add a new field to the service that builds a sync payload (e.g., a `signal_history` list of per-game classification rows), FastAPI validates the response against the Pydantic model and returns **`422 Unprocessable Entity`** if the dict has keys not declared on the model. The endpoint fails entirely — not just the affected rows.

**Symptom:** A user logs in and sync fails with 422. The mobile app can't get data. Server logs show `response_model=MobileSyncPayload Validation error: ... extra fields not permitted` or similar.

**Fix:** Keep the backend Pydantic model and the service's returned dict in **exact** sync. After adding a new field to `build_sync_payload()`, also add the field to `MobileSyncPayload`. Create a typed item model if the field is a list of structured objects:

```python
class SignalHistoryRow(BaseModel):
    sport: str
    signal_type: str
    model_correct: int
    is_draw: int = 0

class MobileSyncPayload(BaseModel):
    favorites: list[MobileFavorite]
    schedule: list[MobileScheduleGame]
    ratings: list[MobileRating]
    team_details: list[MobileTeamDetail]
    playoff_odds: list[MobilePlayoffOdds]
    team_history: list[MobileTeamHistoryGame]
    signal_history: list[SignalHistoryRow] = []   # new field
    truncated: bool
    generated_at: str
```

**Verification:** after changing the payload shape, `curl /api/mobile/sync | jq 'keys'` and confirm the new key is present. Do not rely on the service's internal dict alone.

### 13. The fix-iteration loop: when the cache layer is innocent, look upstream

This is a process lesson, not a code pattern. The response cache middleware gets blamed for many production "data is stale" bugs. It is often the culprit — but not always. When the user reports "I still see the old data after the fix":

1. **Check the cache layer first** — `curl -I <URL>` and look for `X-Cache: HIT-*` headers. If MISS, the cache is correctly missing. The fix never reached the server.
2. **Check the server process** — are you sure the deployed container has the new code? `git log origin/main` and `git rev-parse HEAD` should match the commit you pushed.
3. **Check the data pipeline** — does the source data exist? Run the same query the route handler runs, directly against the DB.
4. **Check the response model** — did you add a new field? Pydantic 422 silently breaks the whole endpoint (see pitfall #12).
5. **Check the client code** — is the client using the new field? Or is the Zod schema rejecting it? Or is the device SQLite query wrong?

The pattern: after the third "the cache is stale" fix that didn't work, stop assuming the cache is the problem. The bug has moved on.

## Files in This Skill

- `scripts/response_cache_middleware.py` — drop-in copy-paste template, ready to drop into `src/api/middleware/response_cache.py`
- `scripts/test_response_cache.py` — 15-test pytest harness, run after copy-paste
- `references/ttl-decision-tree.md` — when to use 5s vs 30s vs 60s vs longer for a given endpoint

## Adding New Route Families Later

When you add a new authenticated route family (e.g., `/api/mobile/`, `/api/user/`, `/api/notifications/`), audit it for user-scoping **before** the first deploy. If any endpoint in the family returns data that varies per user or accepts mutations, add the family prefix to the bypass list in the middleware.

**Pattern:** keep a single `never_cache_prefixes` tuple and extend it when a new route family lands:

```python
_NEVER_CACHE_PATH_PREFIXES: tuple[str, ...] = (
    "/api/auth/",
    "/api/admin/",
    "/api/mobile/",   # user favorites, sync, device-scoped
    "/api/user/",
    "/api/health",
    ...
)
```

**Regression test:** add a test that calls the new endpoint twice with two different users (or once authenticated and once unauthenticated) and asserts the second response is not the cached first response. A cached auth endpoint usually manifests as a 200 for an unauthenticated request or User A seeing User B's data.

### Pitfall: a new route is cached by accident and leaks across users

**Symptom:** `GET /api/mobile/favorites` returns 200 with User A's favorites even when called with no token, or User B sees User A's favorites. Another common example: `GET /api/mobile/sync` returning a cached authenticated payload to an unauthenticated client.
**Root cause:** the response cache key is `METHOD:path:query` and does **not** include the user. A prior authenticated request cached the response, and a later unauthenticated or different-user request hit the same key.
**Fix:** add the route family prefix (e.g., `/api/mobile/`) to `_NEVER_CACHE_PATH_PREFIXES`, clear the cache, and add a regression test.

### Pitfall: cache middleware order causes the bypass to be ignored

If you register a new router **before** `install_response_cache(app)`, but the middleware is mounted after route inclusion, Starlette may still route through the cache. Always mount the cache middleware **after** CORS but **before** route inclusion, and verify with the `X-Cache` header on a request to the new family — you should see **no** `X-Cache` header at all (bypassed requests don't set it).

### Pitfall: test fixtures share a cache and mask cache leakage

`TestClient` instances created from the same `app` share the same ASGI app and therefore the same in-process LRU. If a test uses one `TestClient` to seed data and another to assert isolation, the cache is shared across both. This is actually what you want for catching cache-key leaks, but it can look like a bug when it's really the cache doing its job. Always run the regression test both with the cache enabled and with the route bypassed to confirm the root cause.

app.add_middleware(GZipMiddleware, minimum_size=500)
```

Pairs naturally — the cache stores compressed bodies in Redis (smaller bytes, fewer network hops), and the browser decompresses on receipt. Together: cache + GZip = 5-10x latency win for the typical dashboard.

## Files in This Skill

- `scripts/response_cache_middleware.py` — drop-in copy-paste template, ready to drop into `src/api/middleware/response_cache.py`
- `scripts/test_response_cache.py` — 15-test pytest harness, run after copy-paste
- `references/ttl-decision-tree.md` — when to use 5s vs 30s vs 60s vs longer for a given endpoint
