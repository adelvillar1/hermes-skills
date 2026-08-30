"""
Test harness for the response cache middleware — drop-in pytest file.

This is the cleaned, project-agnostic version. The critical thing
you must NOT change is the `_delete_pattern` mock — it must mirror
the real `cache.cache_delete_pattern` (Redis SCAN MATCH glob), NOT
Python `str.startswith`. See pitfall #1 in the parent SKILL.md.

USAGE:
    1. Copy this file to `tests/test_response_cache.py` in your project.
    2. Adjust the import path in `import src.api.middleware.response_cache as rc`
       to match where you put the middleware.
    3. Run: pytest tests/test_response_cache.py -v
    4. Expect 15 tests passing in <1 second.
"""

from __future__ import annotations

import fnmatch
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import response_cache as rc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_cache():
    rc._lru.clear()
    yield
    rc._lru.clear()


@pytest.fixture
def mock_redis():
    """Mock src.services.cache so tests don't need a live Redis.

    CRITICAL: `_delete_pattern` uses fnmatch (Redis SCAN MATCH glob)
    semantics, NOT `str.startswith`. See pitfall #1 in the parent SKILL.md.
    """
    fake_store: dict[str, dict] = {}

    def _get(key):
        return fake_store.get(key)

    def _set(key, value, ttl=300):
        fake_store[key] = value
        return True

    def _delete_pattern(prefix):
        glob = f"{prefix}*"
        keys = [k for k in fake_store if fnmatch.fnmatchcase(k, glob)]
        for k in keys:
            del fake_store[k]
        return len(keys)

    with patch.object(rc.cache_mod, "cache_get", side_effect=_get), \
         patch.object(rc.cache_mod, "cache_set", side_effect=_set), \
         patch.object(rc.cache_mod, "cache_delete_pattern", side_effect=_delete_pattern), \
         patch.object(rc.cache_mod, "get_redis", return_value=MagicMock()):
        yield fake_store


@pytest.fixture
def client(mock_redis):
    """A minimal FastAPI app with the middleware and a few sample routes."""
    app = FastAPI()
    rc.install_response_cache(app)

    @app.get("/api/ratings")
    def ratings():
        return {"ratings": [{"id": "LAD", "rating": 1600}]}

    @app.get("/api/divergence")
    def divergence():
        return {"divergence": [{"team_id": "LAD", "score": 0.05}]}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/admin/clear-cache")
    def clear_cache_endpoint():
        return {"cleared": rc.clear_cache()}

    @app.post("/api/auth/login")
    def login():
        return {"token": "fake"}

    return TestClient(app)


# ---------------------------------------------------------------------------
# Bypass rules
# ---------------------------------------------------------------------------

def test_health_never_cached(client):
    h1 = client.get("/api/health")
    h2 = client.get("/api/health")
    assert h1.headers.get("X-Cache") in (None, "MISS")
    assert h2.headers.get("X-Cache") in (None, "MISS")


def test_writes_never_cached(client):
    r1 = client.post("/api/admin/clear-cache")
    r2 = client.post("/api/admin/clear-cache")
    # Writes must not be X-Cache: HIT-...
    assert r2.headers.get("X-Cache") != "HIT-LRU"
    assert r2.headers.get("X-Cache") != "HIT-REDIS"


def test_auth_paths_never_cached(client):
    """Auth endpoints are user-scoped writes; never cache."""
    # Direct unit test of the bypass predicate
    assert rc._should_bypass("/api/auth/me", "GET") is True
    assert rc._should_bypass("/api/admin/foo", "GET") is True
    assert rc._should_bypass("/api/teams/mlb/LAD/history", "GET") is True
    assert rc._should_bypass("/api/scenarios?sport=mlb", "GET") is True
    assert rc._should_bypass("/api/ratings", "GET") is False
    assert rc._should_bypass("/api/divergence", "GET") is False


# ---------------------------------------------------------------------------
# Cache key normalization
# ---------------------------------------------------------------------------

def test_cache_key_sorted():
    k1 = rc._make_cache_key("GET", "/api/ratings", "sport=mlb&page=1")
    k2 = rc._make_cache_key("GET", "/api/ratings", "page=1&sport=mlb")
    assert k1 == k2


def test_redis_key_namespaced():
    k = rc._make_redis_key("GET", "/api/ratings", "sport=mlb")
    assert k.startswith("resp:GET:/api/ratings")


# ---------------------------------------------------------------------------
# LRU hit / miss
# ---------------------------------------------------------------------------

def test_first_call_miss_second_call_lru_hit(client):
    r1 = client.get("/api/ratings")
    assert r1.headers.get("X-Cache") == "MISS"
    assert r1.headers.get("ETag") is not None
    assert r1.headers.get("Cache-Control") == "private, max-age=60"

    r2 = client.get("/api/ratings")
    assert r2.headers.get("X-Cache") == "HIT-LRU"
    assert r2.headers.get("ETag") == r1.headers.get("ETag")
    assert r2.json() == r1.json()


def test_conditional_get_304_lru(client):
    r1 = client.get("/api/ratings")
    etag = r1.headers["ETag"]

    r2 = client.get("/api/ratings", headers={"If-None-Match": etag})
    assert r2.status_code == 304
    assert r2.headers.get("X-Cache") in ("HIT-LRU-304", "HIT-REDIS-304")
    assert r2.content == b""


def test_conditional_get_200_mismatched_etag(client):
    r1 = client.get("/api/ratings")
    r2 = client.get("/api/ratings", headers={"If-None-Match": 'W/"deadbeef"'})
    assert r2.status_code == 200
    assert r2.json()["ratings"][0]["id"] == "LAD"


# ---------------------------------------------------------------------------
# Redis layer
# ---------------------------------------------------------------------------

def test_redis_hit_promotes_to_lru(client, mock_redis):
    """Cold request populates both LRU and Redis. Wipe LRU; next call hits Redis."""
    app2 = FastAPI()
    rc.install_response_cache(app2)

    @app2.get("/api/big-divergence")
    def big_div():
        return {"divergence": [{"team_id": f"T{i}", "score": i / 100} for i in range(50)]}

    c2 = TestClient(app2)
    r1 = c2.get("/api/big-divergence")
    assert r1.headers.get("X-Cache") == "MISS"
    assert len(rc._lru) == 1
    assert any(k.startswith("resp:") for k in mock_redis)

    rc._lru.clear()
    r2 = c2.get("/api/big-divergence")
    assert r2.headers.get("X-Cache") == "HIT-REDIS"
    assert len(rc._lru) == 1  # promoted back to LRU
    r3 = c2.get("/api/big-divergence")
    assert r3.headers.get("X-Cache") == "HIT-LRU"


def test_conditional_get_304_redis(client, mock_redis):
    """When LRU is cold but Redis is warm and ETag matches, return 304."""
    app2 = FastAPI()
    rc.install_response_cache(app2)

    @app2.get("/api/big")
    def big():
        return {"data": "x" * 1000}

    c2 = TestClient(app2)
    r1 = c2.get("/api/big")
    etag = r1.headers["ETag"]
    rc._lru.clear()
    r2 = c2.get("/api/big", headers={"If-None-Match": etag})
    assert r2.status_code == 304
    assert r2.headers.get("X-Cache") == "HIT-REDIS-304"


def test_clear_cache_wipes_lru_and_redis(client, mock_redis):
    """clear_cache() wipes both stores."""
    app2 = FastAPI()
    rc.install_response_cache(app2)

    @app2.get("/api/big")
    def big():
        return {"data": "x" * 1000}

    c2 = TestClient(app2)
    c2.get("/api/big")
    assert len(rc._lru) == 1
    assert len(mock_redis) == 1

    result = rc.clear_cache()
    assert result["lru_entries_cleared"] == 1
    # resp:* keys deleted — proves fnmatch glob was used
    assert len(mock_redis) == 0
    assert len(rc._lru) == 0

    r = c2.get("/api/big")
    assert r.headers.get("X-Cache") == "MISS"


# ---------------------------------------------------------------------------
# Per-route TTL
# ---------------------------------------------------------------------------

def test_per_route_ttl(client):
    r1 = client.get("/api/ratings")
    r2 = client.get("/api/divergence")
    assert r1.headers.get("Cache-Control") == "private, max-age=60"
    assert r2.headers.get("Cache-Control") == "private, max-age=5"


def test_mark_route_cacheable_override():
    rc._ROUTE_TTLS["/api/custom"] = 42
    rc.mark_route_cacheable("/api/custom", 99)
    assert rc._ttl_for("/api/custom") == 99
    del rc._ROUTE_TTLS["/api/custom"]


def test_small_bodies_not_written_to_redis(client, mock_redis):
    """Bodies < 200 bytes skip Redis (still populate LRU)."""
    client.get("/api/divergence")
    assert len(rc._lru) == 1
    assert len(mock_redis) == 0


def test_large_bodies_written_to_redis(client, mock_redis):
    """Bodies >= 200 bytes are written to Redis."""
    app2 = FastAPI()
    rc.install_response_cache(app2)

    @app2.get("/api/big")
    def big():
        return {"data": "x" * 1000}

    c2 = TestClient(app2)
    c2.get("/api/big")
    assert len(mock_redis) == 1
