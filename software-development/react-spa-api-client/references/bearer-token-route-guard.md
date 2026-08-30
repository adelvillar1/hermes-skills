# Bearer-token SPA route guard (localStorage token, FastAPI/JWT)

The main SKILL.md covers HttpOnly **cookie** sessions. Some stacks (FastAPI +
JWT, many SaaS scaffolds) put the token in `localStorage` and attach it as
`Authorization: Bearer <token>` — no cookies, no CSRF. The route-guard shape
is the same but with two extra failure modes.

## The guard: validate the token, don't just check presence

`localStorage.getItem('authToken')` is **not** an auth check — a stale or
forged token passes it. Validate against `/api/auth/me` before rendering:

```jsx
export function RequireAuth({ children }) {
  const [status, setStatus] = useState('checking') // checking | ok | denied
  useEffect(() => {
    let cancelled = false
    async function check() {
      const token = getToken()
      if (!token) { if (!cancelled) setStatus('denied'); return }
      try {
        const res = await fetch('/api/auth/me')
        if (cancelled) return
        if (res.ok) setStatus('ok')
        else { localStorage.removeItem('authToken'); setStatus('denied') }
      } catch {
        // Network blip — be lenient; page fetches will surface real errors
        if (!cancelled) setStatus('ok')
      }
    }
    check()
    return () => { cancelled = true }
  }, [])
  if (status === 'checking') return <Loader />
  if (status === 'denied') return <Navigate to="/" replace />
  return children
}
```

Wrap EVERY protected route with it (`/dashboard`, `/admin`, `/speed-entry`,
`/platform`, …) — a route that renders without the guard is an auth hole even
when the API 401s, because the page shell loads and just shows dead fetches.

## Wire the token onto every fetch — but don't recurse

A global wrapper is the least invasive way to cover screens that use raw
`fetch()`:

```js
const originalFetch = window.fetch.bind(window)   // capture FIRST
const authFetch = (input, init) => {
  const token = getToken()
  if (token) {
    init = init || {}
    init.headers = { ...(init.headers || {}), Authorization: `Bearer ${token}` }
  }
  return originalFetch(input, init)
}
window.fetch = authFetch
```

If you call `fetch(...)` inside `authFetch` instead of `originalFetch`, the
wrapper calls itself → `RangeError: Maximum call stack size exceeded` and a
blank app. Pre-login requests (`/api/auth/providers`) must stay tokenless —
only attach when a token exists.

## Login page: skip to dashboard when already authenticated

If the token is valid, the login page should redirect immediately instead of
showing the form (otherwise the guard bounces users back and forth):

```js
if (getToken()) {
  fetch('/api/auth/me').then(r => {
    if (r.ok) navigate('/dashboard')
    else localStorage.removeItem('authToken')
  }).catch(() => { /* stay on login */ })
}
```

## Role-aware nav

The nav should reflect the authenticated role, not show the same links to
everyone. Fetch `/api/auth/me` once (you already do for the avatar initials) and
branch:

```jsx
const isPlatformAdmin = role === 'super_admin'
const links = isPlatformAdmin
  ? [{ to: '/platform', label: 'Platform Admin' }, ...SCHOOL_LINKS]
  : SCHOOL_LINKS
```

Verify BOTH directions in the browser: elevated role sees + can navigate the
link; normal user does not see it.

## Pitfalls

- **Pydantic 422 `detail` is a list of objects.** Rendering it in a toast
  crashes React (`Minified React error #31`, blank screen). Guard with
  `typeof error?.detail === 'string' ? error.detail : fallback`.
- **Frontend camelCase vs backend snake_case** is the usual cause of those
  422s — the backend schema is the source of truth for request keys.
- **`/auth/me` returning 200 with `role: 'super_admin'`** — use `role` from the
  response, not from the login response body (login often omits it at top level).
- Browsers cache 301s aggressively: after fixing an nginx route conflict,
  stale browsers can still show the broken page until a `?cachebust=` reload.
