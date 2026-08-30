#!/usr/bin/env python3
"""
perf_baseline.py — measure API latency for the hot endpoints a UI fans out to.

Records cold + warm p50/p95 + cache-hit headers + conditional-GET behavior
to a JSON file, for before/after diffs.

Usage:
    python perf_baseline.py [BASE_URL] [TOKEN] [LABEL]
    python perf_baseline.py https://prod-url eyJ... before
    python perf_baseline.py https://prod-url eyJ... after

Defaults:
    BASE_URL = https://distinguished-energy-production-e3d0.up.railway.app
    TOKEN    = (read from $PERF_TOKEN env var)
    OUT      = /tmp/perf_<label>.json (label auto-derived from BASE_URL host)

Add your endpoints to the ENDPOINTS list at the top. The harness issues:
  - 1 cold call (Cache-Control / ETag headers captured)
  - 10 warm calls (p50/p95 across them)
  - 1 conditional GET with If-None-Match: <cold-ETag> (if ETag was set)

Then prints a per-endpoint cold-vs-warm-p95 comparison table.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

# === CONFIGURE THIS LIST PER PROJECT ===
# Endpoints the slowest view fans out to. Sport-scoped to whichever
# sport has the most data; pick the one users open first.
ENDPOINTS: list[tuple[str, str]] = [
    ("GET", "/api/ratings?sport=mlb"),
    ("GET", "/api/scenarios?sport=mlb&days_ahead=5"),
    ("GET", "/api/divergence?sport=mlb"),
    ("GET", "/api/schedule/mlb?days_ahead=5"),
    ("GET", "/api/playoffs/mlb"),
    ("GET", "/api/teams?sport=mlb"),
]

# Number of warm calls per endpoint (after the 1 cold call).
N_WARM = 10


def _request(url: str, method: str, token: str, headers: dict[str, str] | None = None) -> tuple[float, int, int, dict[str, str]]:
    """Returns (time_total_seconds, status_code, body_size_bytes, response_headers)."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            elapsed = time.perf_counter() - t0
            return elapsed, resp.status, len(body), dict(resp.headers)
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - t0
        try:
            body = e.read()
        except Exception:
            body = b""
        return elapsed, e.code, len(body), dict(e.headers) if e.headers else {}


def _label_for(base_url: str) -> str:
    if "railway" in base_url:
        return "prod"
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return "local"
    return base_url.replace("https://", "").replace("http://", "").split("/")[0]


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def main(argv: list[str]) -> int:
    base_url = argv[1] if len(argv) > 1 else os.environ.get(
        "PERF_BASE_URL",
        "https://distinguished-energy-production-e3d0.up.railway.app",
    ).rstrip("/")
    token = (
        argv[2]
        if len(argv) > 2
        else os.environ.get("PERF_TOKEN", "")
    )
    if not token:
        print("ERROR: provide a token via argv[2] or PERF_TOKEN env var", file=sys.stderr)
        return 2

    label = argv[3] if len(argv) > 3 else _label_for(base_url)
    out_path = f"/tmp/perf_{label}.json"

    print(f"Perf baseline → {out_path}")
    print(f"  base_url: {base_url}")
    print(f"  warm N  : {N_WARM} per endpoint")
    print()

    results: dict[str, Any] = {
        "meta": {
            "base_url": base_url,
            "label": label,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "n_warm": N_WARM,
            "endpoints": [ep[1] for ep in ENDPOINTS],
        },
        "endpoints": {},
    }

    for method, path in ENDPOINTS:
        url = base_url + path
        # Cold call
        cold_t, cold_status, cold_size, cold_headers = _request(url, method, token)
        cold_etag = cold_headers.get("ETag") or cold_headers.get("etag")
        cold_cache = cold_headers.get("Cache-Control") or cold_headers.get("cache-control")
        cold_enc = cold_headers.get("Content-Encoding") or cold_headers.get("content-encoding")
        cold_x_cache = cold_headers.get("X-Cache") or cold_headers.get("x-cache")

        # Warm calls
        warm_times: list[float] = []
        warm_statuses: list[int] = []
        warm_sizes: list[int] = []
        for _ in range(N_WARM):
            t, s, sz, _h = _request(url, method, token)
            warm_times.append(t)
            warm_statuses.append(s)
            warm_sizes.append(sz)

        # Conditional GET
        cond_status = cond_size = None
        if cold_etag:
            _t, cond_status, cond_size, _h = _request(
                url, method, token, headers={"If-None-Match": cold_etag}
            )

        ep_result = {
            "cold": {
                "time_s": round(cold_t, 4),
                "status": cold_status,
                "body_bytes": cold_size,
                "etag": cold_etag,
                "cache_control": cold_cache,
                "content_encoding": cold_enc,
                "x_cache": cold_x_cache,
            },
            "warm": {
                "times_s": [round(t, 4) for t in warm_times],
                "p50_s": round(_percentile(warm_times, 50), 4),
                "p95_s": round(_percentile(warm_times, 95), 4),
                "max_s": round(max(warm_times), 4),
                "min_s": round(min(warm_times), 4),
                "mean_s": round(statistics.mean(warm_times), 4),
                "statuses": warm_statuses,
                "body_bytes": warm_sizes[-1],
            },
            "conditional_get": {
                "status": cond_status,
                "body_bytes": cond_size,
            } if cold_etag else None,
        }
        results["endpoints"][path] = ep_result

        warm_p50 = ep_result["warm"]["p50_s"] * 1000
        warm_p95 = ep_result["warm"]["p95_s"] * 1000
        cold_ms = cold_t * 1000
        print(
            f"  {method:4s} {path:50s} cold={cold_ms:7.1f}ms  "
            f"warm_p50={warm_p50:6.1f}ms  warm_p95={warm_p95:6.1f}ms  "
            f"size={cold_size/1024:6.1f}KB  ETag={'yes' if cold_etag else ' no'}  "
            f"CC={cold_cache or '-':20s}  cond={cond_status or '-'}"
        )

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {out_path}")
    print("\nQuick comparison (cold vs warm_p95 in ms):")
    for path, ep in results["endpoints"].items():
        cold = ep["cold"]["time_s"] * 1000
        warm95 = ep["warm"]["p95_s"] * 1000
        speedup = cold / warm95 if warm95 > 0 else 0
        print(f"  {path:50s}  {cold:7.1f} → {warm95:7.1f}  ({speedup:.1f}x faster warm)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
