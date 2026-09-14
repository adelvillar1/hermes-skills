# Modular Refactor Stale API Endpoint References

When a frontend monolith is split into ES modules, the extracted view modules often keep the API URLs they used inside the IIFE. If the backend routes were reorganized during the same refactor — or if the view code is copied from a place that used an old URL convention — the module ends up calling endpoints that do not exist, producing silent 404s.

## The pattern

```js
// ui/js/views/domains.js (extracted from dashboard.js IIFE)
const res = await api('/api/pipeline/domains');   // 404 — route never existed
```

```python
# src/api/routes/admin.py
@router.get("/domains", response_model=List[DomainConfig])   # real route is /api/admin/domains
```

Backend route layout changed (or was always different). The view code was copied without updating the URL, and the `api()` wrapper silently swallows the error, so the UI just shows empty data.

## Why it is silent

- The fetch wrapper has `.catch(() => [])` or similar, turning a 404 into an empty result.
- 404 responses are small and fast, so the page doesn't hang.
- The UI renders its empty state, so the user thinks "no data" rather than "wrong URL."

## Diagnostic recipe

1. **Read the backend route file** for the feature. In FastAPI this is usually `src/api/routes/<area>.py` or `src/api/main.py`. List every route under the relevant prefix.
2. **Read the frontend view file** that calls the API. Search for `api(`, `fetch(`, `axios`, or `Auth.authFetch(`.
3. **Compare the two lists.** Mismatched prefix (`/api/pipeline/*` vs `/api/admin/*`) or missing path segments are the root cause.
4. **Check response shape.** Even after the URL is fixed, the frontend may expect `{ domains: [...] }` while the backend returns `[...]` directly, or it may look for `rows` while the backend returns `row_count`.
5. **Verify with `curl` or `TestClient` against the real backend.** Do not rely on the frontend empty state to tell you the endpoint works.

## The fix

```js
// BEFORE
const res = await api('/api/pipeline/domains');
const data = await res.json();
renderTable(data.domains);

// AFTER
const data = await api('/api/admin/domains');        // correct route
renderTable(data);                                   // backend returns a list directly
```

Also update any sub-endpoints (e.g. `/api/pipeline/corpus/{table}/sample` → `/api/admin/corpus/{table}/sample`).

## Prevention

- When extracting a view module, grep the source for every API call and write down the called path.
- Before the PR is merged, compare that list to the backend router's defined paths.
- Add a regression test that hits the real backend endpoint with `TestClient` and asserts the response shape matches what the view expects.
- If the response shape changes, update both the view and its test in the same commit.

## Real example

ELO Scenario Lab, 2026-06-15: the modular refactor PR extracted `domains.js` and `corpus.js` into `ui/js/views/`. Both still called `/api/pipeline/*`, but the only backend routes were `/api/admin/domains`, `/api/admin/corpus`, and `/api/admin/corpus/{table}/sample`. The admin Domains and Corpus pages showed empty data with 404s in the network tab. The fix updated four files: the two views, the backend `get_domains` handler to cover all 15 sports, and the corresponding `tests/test_api.py` expectation.
