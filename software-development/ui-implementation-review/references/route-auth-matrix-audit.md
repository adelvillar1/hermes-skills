# Route-by-Route Auth Matrix Audit Reference

Concrete workplan for step 7b of `ui-implementation-review` — auditing every state-changing route in a multi-route service for missing auth or missing role checks. Use when a project has grown past 10 routes and may have inconsistent `requireSession()` / `requireAuth()` / `requirePlatformAdmin()` / `isDmOfCampaign()` coverage.

## When to use

Trigger: any **full-app review** where the project has:
- A `routes/`, `controllers/`, or `views/` directory with 10+ endpoint files
- Multiple authorization layers (session, role, platform admin)
- A history of feature-by-feature additions where auth may have been bolted on per route instead of globally

## The 5-step audit recipe

### Step 1 — Inventory all routes

```bash
# Node/Express/Fastify/Hono
grep -rhE '(app|router)\.(get|post|patch|delete|put)\(' apps/api/src/routes/ \
  | sort > /tmp/all-routes.txt

# Python/Flask/FastAPI
grep -rnE '@app\.(get|post|patch|delete|put)\(' apps/api/src/

# Rails
grep -rnE '^\s*(get|post|patch|delete|put)\s' config/routes.rb app/controllers/

# Next.js route handlers
find apps/web/app/api -name "route.ts" -exec grep -lE 'export async function (GET|POST|PATCH|DELETE)' {} \;
```

For each route, capture:
- HTTP method
- Path (with `:param` notation)
- Whether reads (GET) or mutates (POST/PATCH/DELETE/PUT)

### Step 2 — Inventory all auth middleware calls

```bash
# Per project, replace these with the project's actual auth middleware names
grep -rnE 'requireSession\(|requireAuth\(|requirePlatformAdmin\(|isDmOfCampaign\(|isOwner\(' \
  apps/api/src/routes/
```

For each call, capture:
- File:line
- Which route(s) it's inside

### Step 3 — Compute the coverage matrix

`mutating_routes - auth_routes = missing_auth_routes`

In practice:

```bash
# Routes that mutate state
grep -rhE 'app\.(post|patch|delete|put)\(' apps/api/src/routes/ \
  | sed -E 's/.*app\.[a-z]+\("([^"]+)".*/\1/' | sort -u > /tmp/mutating.txt

# Routes that check auth (rough heuristic: routes whose file imports session.ts)
for f in apps/api/src/routes/*.ts; do
  if grep -qE "requireSession|requireAuth|requirePlatformAdmin" "$f"; then
    echo "$f"
  fi
done
# Then manually cross-reference to find the gap
```

### Step 4 — Live verify each gap

For every gap route, hit it with no cookie / no auth header and confirm:

```bash
# Should be 401 (Unauthorized) — anything else is a bug
curl -sS -X <METHOD> https://staging.example.com<path>/<fake-uuid> -w '\nHTTP %{http_code}\n'
```

For destructive routes specifically:

```bash
# This should NEVER return 204/200. Should always be 401.
curl -sS -X DELETE https://staging.example.com/saved-encounters/00000000-0000-0000-0000-000000000000 -w '\nHTTP %{http_code}\n'
```

### Step 5 — Report with reproduction recipe

For each gap, the report line is:

```markdown
### 🔴 B<N>. <METHOD> <PATH> accepts unauthenticated requests 🛡️

**File:** apps/api/src/routes/<file>.ts:<line>
**Verify:**
\`\`\`bash
$ curl -sS -X <METHOD> https://staging.example.com<path>/<fake-id> -w '\\nHTTP %{http_code}\\n'
HTTP <observed>
\`\`\`
**Fix:** Add requireSession() at the top of the handler; for destructive
or scope-limited routes load the row first, then add the role check
(e.g., isDmOfCampaign(campaignId, accountId)).
```

## Real failure — the D&D VTT project 2026-07-18

5 routes in one audit found without auth:

| Route | Method | Expected | Live observed |
|---|---|---|---|
| `/saved-encounters/:id` | DELETE | 401 | **204** (silent success!) |
| `/content/:id` | GET | 401 / 200 | 404 (no row, no auth — but auth missing too) |
| `/content/:id` | PATCH | 401 | 404 (no auth) |
| `/content/:id` | DELETE | 401 | 404 (no auth) |
| `/content/:id/duplicate` | POST | 401 | 404 (no auth) |

All 5 patched in a single PR by adding `requireSession()` + the appropriate role check.

## Common false-positives to avoid

- **Public read endpoints** — `GET /health`, `GET /content/search` (when search is intentionally public). Verify the project intends them public before flagging.
- **Internal service tokens** — endpoints gated by `X-Internal-Token` header (e.g., `/content/import`) are not the same as missing auth; they're a different trust boundary.
- **Import-script endpoints** — `POST /content/import` gated by `CONTENT_IMPORT_KEY` is correct, not a bug.

## Cite this if you referenced the recipe

```
Per ui-implementation-review §7b + references/route-auth-matrix-audit.md
```