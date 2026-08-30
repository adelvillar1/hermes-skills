---
name: react-spa-api-client
description: "Wire a React SPA to a session-cookie REST API."
version: 1.0.0
metadata:
  hermes:
    tags: [react, vite, typescript, api-client, auth, spa, fetch]
    related_skills: [hono-drizzle-zod-api, cross-origin-spa-auth, develop-verify-commit-loop]
---

# React SPA ↔ Session-Cookie REST API

Build the frontend half of a monorepo where a Vite React SPA talks to a same-origin REST API (Hono/Express/etc.) that authenticates with an HttpOnly session cookie. Covers the typed fetch client, the auth context + protected-route trio, and the workflow for migrating a localStorage-backed prototype to live API calls.

Sibling skill: `hono-drizzle-zod-api` is the server half of this stack (routes, multipart field-mapping, migrations). Load both when working across the boundary. For cross-origin deployments (separate subdomains), load `cross-origin-spa-auth` instead — the cookie/CSRF topology changes. For **Bearer-token stacks** (JWT in `localStorage`, no cookies — FastAPI/JWT scaffolds), see `references/bearer-token-route-guard.md`: the same route-guard trio but with token validation via `/auth/me`, the global fetch-wrapper recursion trap, and role-aware nav.

## When to Load

- Building the first frontend client for a session-cookie API.
- Migrating a localStorage/in-memory prototype dashboard to live API calls.
- Adding login/logout, an auth context, or protected/admin routes to a React SPA.
- Writing a typed `fetch` wrapper (error handling, FormData uploads, 204s).

## The typed client (single chokepoint)

Every request flows through one `request<T>()` wrapper. Copy `templates/typed-api-client.ts` and adapt. Non-negotiables:

- `credentials: 'include'` on every request — the session cookie is HttpOnly, so this is the *only* auth mechanism. There is no token to store or attach.
- **Never set `Content-Type` when the body is `FormData`** — the browser must generate the multipart boundary. Detect with `body instanceof FormData` and omit the header.
- `204` → return `undefined` (don't call `res.json()` — it throws on an empty body).
- Non-2xx → parse `{error}` from the body and throw a typed `ApiError(status, message)` so callers can `toast.error(errorMessage(err))` uniformly.
- Group endpoints by resource (`api.members.list()`, `api.events.create(...)`) and export response types from the same file — the client file is the frontend's contract.

Multipart uploads: append fields as strings, booleans as `'true'/'false'`, and the `File` under the field name the server expects. If the server uses a snake_case→camelCase `fieldMap` (see `hono-drizzle-zod-api` pitfall #1), you may send camelCase directly — it passes through unmapped. Nested arrays/objects (e.g. a per-event `wines` lineup) can't be appended per-row: if the route reads the field through a JSON-parse helper (e.g. `parseWinesField`), send it as a single JSON-stringified form field — `fd.append('wines', JSON.stringify(data.wines))` — while the JSON body path sends the native array. Read the route's parse helper before choosing the encoding; the same logical field has two wire forms depending on content type.

## Pitfalls

### 1. `erasableSyntaxOnly` forbids constructor parameter properties
New Vite React-TS templates (TS 5.8+) enable `"erasableSyntaxOnly": true`, which rejects `constructor(public status: number, ...)` with a confusing TS error. Declare the field separately:
```ts
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}
```

### 2. Read the actual route handlers before writing client types
Do not derive response types from the old client-side types or from the DB schema alone — the route handler decides the real shape. Watch for:
- **Inconsistent derived-field naming**: one route may return `has_photo` (snake_case) while a sibling returns `hasPhoto`. Mirror exactly what each handler emits.
- **Server-computed joins**: admin list endpoints often return `memberName`/`memberType` alongside the row — the client type must include them (they're absent from the DB type).
- **Aggregate/360 endpoints**: profile-style routes (`GET /members/:id/profile`) compose several collections in one response. Type them as intersections over the base row types — `orders: (Order & { items: OrderItem[] })[]`, `signups: (Signup & { event: { id: string; title: string; date: string } | null })[]` — so the consuming sheet/page gets full typing without duplicating row fields.
- **The task spec itself can misstate the wire shape.** A plan doc or ticket may name fields that don't exist (e.g. spec said `wineName`/`quantity` while the drizzle schema and handler emit `wine`/`qty`). The route handler + DB schema are the source of truth; the spec is only a hint. Verify before writing types — a wrong field name here compiles fine and only breaks at runtime.
- **Stub endpoints and anti-enumeration shapes.** Partially-implemented routes can return something entirely different from the spec — e.g. a forgot-password route answering `{ message }` (deliberately identical whether or not the email is registered) or a reset-password route answering 501 until its token table exists. When a task spec dictates the client types for such endpoints, type per spec but read the handler and report the actual response/stub status back — downstream UI work must know "typed" ≠ "implemented server-side."
- **Response fields every handler emits are required, not optional.** If every route returning a shape includes `wines: EventWine[]` (list, detail, create, update), type it required on the response interface; reserve optional for fields some endpoint genuinely omits. Optional-where-always-present forces `?? []` boilerplate on every consumer and hides the invariant.
- **Money in cents**: the wire is integer cents; keep UI forms in dollars and convert at the client edge (`dollarsToCents` on submit, `fmtMoney(cents)` for display). Never let float dollars reach the API.

### 3. Auth context needs a `loading` state, not just `user`
`user: AuthUser | null` alone can't distinguish "not logged in" from "still checking the session" — a `ProtectedRoute` that only checks `user` will flash a redirect to `/login` on every hard refresh of `/admin`. Always model three states: `loading` (spinner), `null` (redirect), `user` (render). Call `GET /auth/me` once on mount inside a `cancelled`-guarded effect.

### 4. Logout is fire-and-forget
`api.auth.logout().catch(() => undefined)` then clear local state — a failed server call must never strand the user "logged in" client-side. The cookie's Max-Age handles expiry regardless.

### 5. Page-load fetches need a timeout + a retryable error state, not just loading/success
A bare `fetch` has **no default timeout** — a stalled request (serverless/Railway cold start, a proxy that accepts the socket but never responds, a hung upstream) will neither resolve nor reject, so a component that only models `loading`/`success`/`empty` sits on its "Loading…" spinner **forever**. This reads to the user as a broken page even though the code is "correct." Symptom reported as *"the page is stuck on loading and the data never shows."*

Model **four** terminal states for any fetch that gates page content, and add a watchdog:
```tsx
const [data, setData] = useState<T[] | null>(null)   // null = still loading
const [failed, setFailed] = useState(false)
const [attempt, setAttempt] = useState(0)            // bump to retry

useEffect(() => {
  let alive = true
  setData(null); setFailed(false)
  const timer = setTimeout(() => { if (alive) setFailed(true) }, 12000)  // watchdog
  api.things.list()
    .then(d => { if (!alive) return; clearTimeout(timer); setFailed(false); setData(d) })
    .catch(() => { if (!alive) return; clearTimeout(timer); setFailed(true) })
  return () => { alive = false; clearTimeout(timer) }
}, [attempt])

// render: failed → "couldn't load" + <button onClick={() => setAttempt(a => a + 1)}>Try again</button>
//         data === null → "Loading…"
//         data.length === 0 → genuine empty state
//         else → the content
```
- The `alive`/`cancelled` guard prevents a late response (arriving after the watchdog fired or after unmount) from clobbering the error state — clear the timer on settle AND on cleanup.
- Keying the effect on `attempt` gives a real retry that re-runs the whole fetch (reset to loading first), rather than a stale re-render.
- Keep the timeout generous (10–15s) so a legitimate cold start isn't mistaken for failure, but finite so the page always reaches *some* terminal state.
- This is distinct from pitfall #3 (auth `loading`): that one is about the session check flashing a redirect; this one is about *content* fetches hanging. Both are "model the in-flight state explicitly" — apply the same discipline to any fetch whose result gates what the user sees.

## Auth context + protected route

`templates/auth-context.tsx` has the provider (`user`, `loading`, `login`, `logout`). The route guard:

```tsx
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <FullScreenSpinner />          // state 1: checking session
  if (!user) return <Navigate to="/login" replace />  // state 2: anonymous → login
  if (user.role !== 'admin') return <Unauthorized />  // state 3: signed-in non-admin
  return <>{children}</>
}
```

Routes: `/login` (public), `/admin` (wrapped in `ProtectedRoute`), and — when migrating — a `<Navigate to="/admin" replace />` at the old path so bookmarks/deep links survive.

## Detail panels (360 views)

Record-detail sheets (click a table row → right-side Sheet with the member's full profile) are the main consumer of aggregate endpoints. Copy `templates/detail-sheet.tsx`. The load-bearing conventions:

- Parent owns exactly one piece of state — `selectedId: string | null` — and the sheet derives `open={!!id}` from it. No separate `open` boolean to drift out of sync; the clickable cell is a plain `<button onClick={() => setSelectedId(m.id)}>` with a hover affordance.
- The fetch effect is keyed on the id: reset local state when it goes null, and guard with a `cancelled` flag so a fast close doesn't toast a stale error or write one record's data over the next record's.
- Radix `SheetContent` requires an accessible title — render `<SheetTitle className="sr-only">` while the profile is still loading.
- Keep the header fixed and scroll only the body (`flex-1 overflow-y-auto` on the body container, header outside it). Wide panels: `sm:max-w-2xl`.
- Mirror the dashboard's existing status→badge-tone vocabulary (e.g. the page's `STATUS_TONES` map) instead of inventing new colors — the new view should read as native. Light badge backgrounds (amber, stone-400) need `text-stone-950` for contrast.
- Derive the stat strip (lifetime spend, counts of confirmed/delivered rows) client-side from the fetched collections — no extra endpoint.
- Mutations inside the sheet (e.g. saving staff notes) toast on success and call an `onSaved` prop so the parent list refreshes too.

## Migration workflow: localStorage → live API

1. **Survey the API first.** Read every route file to confirm methods, paths, request content-type (JSON vs multipart), and exact response shapes. The shared Zod schemas tell you request bodies; only the handlers tell you responses.
2. **Write the client + types** mirroring real shapes (pitfall #2). Reuse the API's own vocabulary (status enums, cents).
3. **Rewrite the page component-by-component**, replacing store hooks with per-tab `useEffect` fetches + a `refresh` callback after mutations. Keep the visual design; only the data layer changes. Add `sonner`/toast feedback on every mutation (success + `errorMessage(err)` on failure).
4. **Delete the old store and its types file** in the same change, and grep for stragglers (`rg 'club-store|types/club' src/`). Leaving them invites half-migrated imports.
5. **Add the backward-compat redirect** for the old route path.
6. **Verify end-to-end** (below) — a green `tsc`/`vite build` proves types, not behavior.

## Verification

```bash
npm run build                        # tsc -b catches erasableSyntaxOnly etc.
# Spin up throwaway Postgres + the API with a seeded admin:
docker run --rm -d --name pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=app -p 55432:5432 postgres:16
DATABASE_URL=postgres://postgres:test@localhost:55432/app \
  ADMIN_EMAIL=test@test.com ADMIN_BOOTSTRAP_PASSWORD=testpass123 PORT=3000 node api/dist/index.js &
# Cookie-jar smoke test of the exact payloads the client sends:
curl -s -c /tmp/cj.txt -X POST localhost:3000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"test@test.com","password":"testpass123"}'
curl -s -b /tmp/cj.txt localhost:3000/api/members
curl -s -b /tmp/cj.txt -X POST localhost:3000/api/events -F title=X -F date=2026-08-15 -F isSpecial=true
```
Then drive the real flow in a browser: load `/login`, sign in, confirm the dashboard renders live rows, and check the console for errors. Multipart endpoints especially — curl `-F` and browser `FormData` both hit the server's `parseBody()` path, so test at least one upload-bearing payload.

## Templates
- `templates/typed-api-client.ts` — request wrapper, `ApiError`, endpoint-group skeleton, money/date formatters. Copy and fill in endpoints.
- `templates/auth-context.tsx` — `AuthProvider` + `useAuth` with the three-state session check.
- `templates/detail-sheet.tsx` — controlled record-detail Sheet: fetch-on-open with cancelled guard, sr-only title while loading, fixed header + scrollable body, status-tone badges.
