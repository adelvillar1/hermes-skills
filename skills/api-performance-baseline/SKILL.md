---
name: api-performance-baseline
description: "Measure an HTTP API's per-endpoint latency, body size, and caching headers before optimizing anything. Use this skill FIRST whenever the user reports a slow API, says 'the app is sluggish', 'pages take 5-10s', 'the dashboard is slow', 'make it faster', 'reduce latency', 'why is the API slow', wants to add a response cache, wants to add GZip middleware, or starts any work that includes the words 'performance', 'faster', 'optimize', 'speed up', or 'latency'. Captures cold + warm p50/p95 in one shot, plus the four headers that reveal whether the server is already doing any of the work (ETag, Cache-Control, Content-Encoding, X-Cache). Produces a JSON file that can be diffed after the optimization to prove the win. Pairs with api-performance-optimization (orchestration) and fastapi-response-cache (the middleware); load all three together when starting perf work — do not write a custom baseline harness when this one already exists."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [performance, api, latency, baseline, measurement, caching, etag, gzip, optimization]
    related_skills: [draft-feature-plan, python-local-dev-server, subagent-driven-development, python-debugpy]
---

# API Performance Baseline

Measure first, optimize second. Before adding a response cache, GZip middleware, or refactoring an endpoint, you need to know the **actual** current numbers. Without a baseline, "we made it faster" is unfalsifiable and the user's intuition about which endpoint is the worst is almost always wrong.

This skill is the **measurement layer** that pairs with any "make the API faster" work. It produces a single JSON file that the user can diff before/after to prove the optimization landed.

## When to Use

- User reports slow API calls, slow page loads, or "the dashboard takes 5-10 seconds"
- User says "performance", "faster", "optimize", "speed up", "reduce latency"
- Starting a plan that adds response caching, GZip, or HTTP/2 push
- Verifying a Railway deploy didn't regress latency
- Before/after a `mc-simulate` or `pipeline` run that touches the API
- Auditing a third-party API before integrating it

**Skip if** the user is asking about a one-off slow request (just `curl -w "%{time_total}"` is enough) or the change is purely functional with no perf angle.

## The Pattern: One Script, One JSON, Two Numbers Per Endpoint

The script captures three things per endpoint that other timing tools miss:

1. **Cold + warm p50/p95** — proves whether the server is already caching anything. If warm_p95 ≈ cold, the server is recomputing on every call. If warm_p95 << cold, there's already a cache.
2. **The four caching headers** — `ETag`, `Cache-Control`, `Content-Encoding`, `X-Cache` — reveal in one glance whether ETag, HTTP cache, GZip, or a custom middleware is in play. **No-op optimizations happen because people skip this step.**
3. **A conditional GET probe** — sends `If-None-Match` with the cold ETag and reports the 304 status. Proves whether the ETag is real or decorative.

A typical output looks like:

```
GET  /api/ratings?sport=mlb              cold=470ms  warm_p50=501ms  warm_p95=539ms  size=21KB  ETag=no  CC=-                cond=-
GET  /api/schedule/mlb?days_ahead=5      cold=3506ms warm_p50=4022ms warm_p95=4181ms size=1101KB ETag=no CC=-                cond=-
```

The user can now **see** the worst offender (schedule, 4.2s, 1.1MB) and prioritize accordingly. Without this output, "the dashboard is slow" produces vague plans.

## The Harness

`scripts/perf_baseline.py` in this skill's directory. Stdlib only (`urllib`, `statistics`, `json`) — no `requests` or `httpx` dependency. Takes `<base_url> <token> [label]` and writes `/tmp/perf_<label>.json`.

Re-run it with the same label to overwrite. Diff with `jq` or `diff /tmp/perf_before.json /tmp/perf_after.json` to show the win.

### What the script does, step by step

For each endpoint in the ENDPOINTS list:

1. **Cold call** — captures wall-clock time, status, body size, all response headers.
2. **N=10 warm calls in a tight loop** — captures each time, computes p50/p95/max/mean.
3. **Conditional GET** — if the cold call returned an ETag, re-fetches with `If-None-Match` and reports the status (200 if the body changed, 304 if it matched, 404 if the ETag is ignored).

Default N=10 is enough to expose a cache hit (warm drops to <5ms) and stable enough to compute a p95 without burning minutes. For load tests, bump to 50 or 100.

### How to extend the ENDPOINTS list

Edit the `ENDPOINTS` constant in the script. Add one tuple per hot endpoint:

```python
ENDPOINTS: list[tuple[str, str]] = [
    ("GET", "/api/ratings?sport=mlb"),
    ("GET", "/api/scenarios?sport=mlb&days_ahead=5"),
    # ... whatever the frontend fans out to
]
```

For a frontend-driven audit, **read the actual `api()` calls in the view modules** (`grep -r "api('/api" ui/js/views/`) — don't guess which endpoints matter. The slowest one in the user's mind is rarely the slowest on the server.

### How to find a token

Most production APIs are auth-gated. Three options in order of preference:

1. **Existing test user** — check the seed file or `python -m src.cli` for a test seed.
2. **Public register endpoint** — most modern apps have one. Use a real-looking email (`perf.test@your-domain.com` — `.local`/`.test` are often rejected by email validators).
3. **Admin API key / legacy X-API-Key** — check `CLAUDE.local.md` or the `ADMIN_API_KEY` env var.

Save the token in `PERF_TOKEN` env var, pass via `argv[2]`, or paste inline. Tokens don't expire in minutes; reuse them.

## Interpreting the Output

### What "warm" should look like

| Pattern | What it means | Action |
|---|---|---|
| `warm_p95 << cold` (e.g. 5ms vs 500ms) | Server is caching. Don't add a duplicate layer. | Leave alone. |
| `warm_p95 ≈ cold` (e.g. 480ms vs 500ms) | No server-side cache. Big optimization opportunity. | Add response cache middleware. |
| `warm_p95 > cold` (e.g. 600ms vs 500ms) | Cold cache was a fluke; warm is the real number. | Plan around warm, not cold. |
| High variance (e.g. min=200ms, max=2000ms) | Network jitter, GC pause, or DB connection contention. | Run more iterations; check Railway metrics. |

### What the headers tell you in 5 seconds

| Header set | What it means |
|---|---|
| `ETag: "abc..."` present, `If-None-Match` returns 304 | Real HTTP cache. Respect it in the client. |
| `ETag` present, conditional GET returns 200 | Decorative ETag. Server doesn't actually implement 304 logic. Strip the header or fix the handler. |
| `Cache-Control: max-age=N` | Client/browser cache hint. Pair with an ETag for revalidation. |
| `Content-Encoding: gzip` | GZip middleware in place. Check size column — if all bodies are <10KB, GZip is wasted CPU. |
| None of the above | Greenfield. The plan needs all four: ETag, Cache-Control, Content-Encoding, and the response-cache middleware. |

## Workflow: Using the Baseline in a Plan

The `draft-feature-plan` skill is the right next step after the baseline. The baseline output becomes the **acceptance criteria** for the optimization plan:

> **Phase 1 (Response Cache)**: p95 cold→warm drops ≥10x for `/api/schedule/mlb` (4181ms → <400ms). Verified by re-running `perf_baseline.py` against the optimized server.

The `Acceptance criteria` section of the plan should name specific numbers, not "the API gets faster". **Specific numbers are verifiable; adjectives aren't.**

## Pitfalls

- **Measuring the wrong thing**: don't measure `/api/health` and call it a perf baseline. Health is 200 OK with 0 work — it'll always be <50ms. Measure the endpoints the user actually hits.
- **Confusing auth latency with endpoint latency**: the 401 round-trip is ~50ms. If you forget to pass a token, you'll measure the auth middleware, not the endpoint.
- **Cold-call variance on the first call**: the first call may include JIT, connection pool warmup, or DNS resolution. The harness already handles this (1 cold + 10 warm), but if you see `cold < warm_p50`, suspect the cold measurement and run again.
- **Production vs local measurements diverge**: production has the database, Redis, and 1+ dynos. Local dev with SQLite will be 10-100x faster for the first call but will NOT show caching wins (in-process LRU behaves differently). **Always measure production for the before/after diff**; use local for "is my code even being hit" debugging.
- **GZip makes the size column misleading**: a 1101KB endpoint might gzipped-serve at 200KB. The harness doesn't auto-decompress; the `Content-Encoding` header tells you whether the body is compressed. Divide body size by Content-Encoding multiplier to estimate wire size.
- **ETag on dynamic data is dangerous**: if the endpoint returns user-specific data, ETag collisions across users leak data. Verify each cached endpoint is sport/league-scoped, not user-scoped, before adding ETag.
- **Caching the wrong thing**: a `Cache-Control: max-age=60` on `/api/playoffs/mlb` is fine (refreshes nightly). The same on `/api/teams/{id}/history` would hide freshly-updated history. Audit per-endpoint TTLs.

## Verification

After running the baseline, the deliverable is:

1. **`/tmp/perf_<label>.json`** — the raw data, suitable for diffing.
2. **A 1-paragraph diagnosis** — which endpoint is the worst, what the headers reveal, what the optimization should target.
3. **A specific number to beat** — the worst p95 becomes the "after" target. "Reduce /api/schedule/mlb warm_p95 from 4181ms to <400ms" is a real criterion.

Re-run the harness with the same label after each optimization PR. If the JSON diff shows no improvement, the PR didn't move the needle — investigate, don't merge.

## Files in This Skill

- `scripts/perf_baseline.py` — the harness, stdlib only
