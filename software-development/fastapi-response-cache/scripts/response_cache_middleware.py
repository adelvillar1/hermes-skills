"""
Response cache middleware — drop-in template for FastAPI / Starlette.

This is the cleaned, project-agnostic version of the middleware. Replace
`src.services.cache` with your project's cache module (anything exposing
`cache_get`, `cache_set`, `cache_delete_pattern`, and `get_redis` that
returns `None` when unavailable — see the Redis primitives section below).

USAGE:
    from src.api.middleware.response_cache import install_response_cache
    install_response_cache(app)   # call AFTER CORS, BEFORE include_router

KEY DESIGN POINTS (see the parent SKILL.md for the full writeup):

* Two-tier storage: in-process LRU (default 1024 entries) + Redis (when
  REDIS_URL is set). LRU is the fast path; Redis is the source of truth
  for cross-process consistency.

* Cache key: f"{METHOD}:{path}?{sorted_query_string}" — sort the query
  string so re-ordered query params collide.

* ETag = SHA1 of the response body. 304 on If-None-Match with empty body.

* Bypass rules: non-GET, /api/auth/, /api/admin/, /api/pipeline/,
  /api/teams/{id}/history, /api/health. Extend the
  `_NEVER_CACHE_PATH_PREFIXES` tuple for your project.

* Bodies < 200 bytes skip Redis (tiny responses don't benefit from
  cross-process caching).

* Returns X-Cache: MISS / HIT-LRU / HIT-REDIS / HIT-LRU-304 / HIT-REDIS-304
  for log-driven verification that the cache is hitting.

REDIS PRIMITIVES YOU NEED:
    cache.cache_get(key)         -> Any | None   (None on miss / Redis down)
    cache.cache_set(key, val, ttl) -> bool
    cache.cache_delete_pattern(prefix) -> int   (uses Redis SCAN MATCH glob)
    cache.get_redis()            -> Redis | None

If your project doesn't have a Redis layer yet, see
`scripts/redis_cache_adapter.py` for a minimal standalone implementation.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Replace with your project's cache module.
from src.services import cache as cache_mod  # noqa: F401  (template)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config — customize per project
# ---------------------------------------------------------------------------

DEFAULT_TTL_SECONDS = 5

# Per-route TTL overrides. Paths are matched exactly (no wildcards).
# Add your hot read endpoints here.
_ROUTE_TTLS: dict[str, int] = {
    "/api/ratings": 60,
    "/api/teams": 60,
    "/api/divergence": 5,
    "/api/schedule/mlb": 5,
    "/api/schedule/nfl": 5,
    "/api/schedule/nba": 5,
    "/api/schedule/nhl": 5,
    "/api/schedule/mls": 5,
    "/api/playoffs/mlb": 30,
    "/api/playoffs/nfl": 30,
    "/api/playoffs/nba": 30,
    "/api/playoffs/nhl": 30,
    "/api/playoffs/mls": 30,
}

# Paths we never cache. Matched by `path.startswith(prefix)`.
_NEVER_CACHE_PATH_PREFIXES: tuple[str, ...] = (
    "/api/auth/",
    "/api/admin/",
    "/api/pipeline/",
    "/api/calibration/",
    "/api/teams/",          # /api/teams/{sport}/{id}/history is per-team
    "/api/scenarios",       # heavy + volatile
    "/api/market-odds",
    "/api/health",
)

# Body size threshold for writing to Redis. Smaller bodies stay in LRU only.
_REDIS_WRITE_MIN_BYTES = 200

# LRU capacity.
_LRU_MAXSIZE = 1024


# ---------------------------------------------------------------------------
# In-process LRU
# ---------------------------------------------------------------------------

class _LRU(OrderedDict):
    """OrderedDict-based LRU. Bounded by `maxsize` entries."""

    def __init__(self, maxsize: int = 1024) -> None:
        super().__init__()
        self._maxsize = maxsize

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        if key not in self:
            return default
        self.move_to_end(key)
        return super().get(key, default)

    def put(self, key: str, value: Any) -> None:
        if key in self:
            self.move_to_end(key)
            super().__setitem__(key, value)
            return
        super().__setitem__(key, value)
        if len(self) > self._maxsize:
            self.popitem(last=False)


_lru = _LRU(maxsize=_LRU_MAXSIZE)


def clear_cache() -> dict[str, int]:
    """Clear both the in-process LRU and any Redis response-cache keys.

    Returns counts for observability. Wire this to your `/admin/clear-cache`
    endpoint.
    """
    lru_count = len(_lru)
    _lru.clear()
    redis_count = 0
    try:
        redis_count = cache_mod.cache_delete_pattern("resp:*")
    except Exception as exc:
        logger.warning("Redis response-cache delete failed: %s", exc)
    return {"lru_entries_cleared": lru_count, "redis_keys_cleared": redis_count}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _should_bypass(path: str, method: str) -> bool:
    if method != "GET":
        return True
    if path in ("/api/health", "/", ""):
        return True
    for prefix in _NEVER_CACHE_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _ttl_for(path: str) -> int:
    if path in _ROUTE_TTLS:
        return _ROUTE_TTLS[path]
    return DEFAULT_TTL_SECONDS


def _normalize_query(qs: str) -> str:
    if not qs:
        return ""
    pairs: list[tuple[str, str]] = []
    for part in qs.split("&"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            pairs.append((k, v))
        else:
            pairs.append((part, ""))
    pairs.sort()
    return "&".join(f"{k}={v}" for k, v in pairs)


def _make_cache_key(method: str, path: str, qs: str) -> str:
    return f"{method}:{path}?{_normalize_query(qs)}"


def _make_redis_key(method: str, path: str, qs: str) -> str:
    """Namespaced Redis key. The `resp:` prefix lets us invalidate
    `resp:*` without colliding with `mc:*` or `ratings:*` keys written
    by other code paths.
    """
    return f"resp:{_make_cache_key(method, path, qs)}"


def _etag_of(body: bytes) -> str:
    return 'W/"' + hashlib.sha1(body).hexdigest()[:20] + '"'


def _build_hit_headers(entry: dict[str, Any], x_cache: str) -> dict[str, str]:
    return {
        "ETag": entry["etag"],
        "Cache-Control": f"private, max-age={entry['max_age']}",
        "X-Cache": x_cache,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """HTTP response cache for GET endpoints."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        method = request.method
        path = request.url.path
        qs = request.url.query

        if _should_bypass(path, method):
            return await call_next(request)

        cache_key = _make_cache_key(method, path, qs)
        redis_key = _make_redis_key(method, path, qs)

        # Conditional GET — fast 304 path on LRU hit
        if_none_match = request.headers.get("if-none-match")
        if if_none_match:
            cached = _lru.get(cache_key)
            if cached is not None and cached["etag"] == if_none_match:
                return Response(status_code=304, headers={
                    "ETag": cached["etag"],
                    "Cache-Control": f"private, max-age={cached['max_age']}",
                    "X-Cache": "HIT-LRU-304",
                })
            # LRU miss but client sent ETag — try Redis
            if cached is None:
                redis_hit = cache_mod.cache_get(redis_key)
                if redis_hit and redis_hit.get("etag") == if_none_match:
                    return Response(status_code=304, headers={
                        "ETag": redis_hit["etag"],
                        "Cache-Control": f"private, max-age={redis_hit.get('max_age', DEFAULT_TTL_SECONDS)}",
                        "X-Cache": "HIT-REDIS-304",
                    })

        # LRU full-body hit
        cached = _lru.get(cache_key)
        if cached is not None and cached["expires_at"] > time.time():
            return Response(
                content=cached["body"],
                status_code=cached["status"],
                headers=_build_hit_headers(cached, "HIT-LRU"),
            )

        # Redis full-body hit
        if cached is None:
            redis_hit = cache_mod.cache_get(redis_key)
            if redis_hit and redis_hit.get("expires_at", 0) > time.time():
                _lru.put(cache_key, redis_hit)  # promote to LRU
                return Response(
                    content=redis_hit["body"],
                    status_code=redis_hit["status"],
                    headers=_build_hit_headers(redis_hit, "HIT-REDIS"),
                )

        # Cache miss — call the route
        response = await call_next(request)

        if 200 <= response.status_code < 300:
            if hasattr(response, "body") and isinstance(response.body, bytes):
                body = response.body
            else:
                # Streaming path (Starlette's body_iterator is a runtime
                # attribute not in the type stubs).
                body = b""
                iterator = getattr(response, "body_iterator", None)
                if iterator is not None:
                    async for chunk in iterator:
                        body += chunk if isinstance(chunk, bytes) else chunk.encode()

            max_age = _ttl_for(path)
            etag = _etag_of(body)
            entry = {
                "body": body,
                "status": response.status_code,
                "etag": etag,
                "max_age": max_age,
                "expires_at": time.time() + max_age,
            }

            _lru.put(cache_key, entry)

            if len(body) >= _REDIS_WRITE_MIN_BYTES:
                try:
                    cache_mod.cache_set(redis_key, entry, ttl=max_age)
                except Exception as exc:
                    logger.debug("Redis resp-set failed for %s: %s", redis_key, exc)

            headers = dict(response.headers)
            headers["ETag"] = etag
            headers["Cache-Control"] = f"private, max-age={max_age}"
            headers["X-Cache"] = "MISS"
            headers.pop("content-length", None)

            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )

        return response


def mark_route_cacheable(path: str, max_age: int) -> None:
    """Override the TTL for a specific path. Call from a route module
    at import time, e.g.:

        from src.api.middleware.response_cache import mark_route_cacheable
        mark_route_cacheable("/api/scenarios", 10)
    """
    _ROUTE_TTLS[path] = max_age


def install_response_cache(app: FastAPI) -> None:
    """Idempotent install. Safe to call multiple times."""
    app.add_middleware(ResponseCacheMiddleware)
    logger.info("ResponseCacheMiddleware installed (LRU maxsize=%d)", _LRU_MAXSIZE)
