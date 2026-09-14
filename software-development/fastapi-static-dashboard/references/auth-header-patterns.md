# Auth Patterns — JWT Cookie Auth + Legacy API Key

The app uses **JWT-based auth with httpOnly cookies** as the primary authentication mechanism. A legacy `X-API-Key` header is supported as a fallback for admin endpoints. The frontend uses an `auth.js` client library that wraps fetch with credential handling and 401 auto-redirect.

## Architecture

```
┌──────────┐   POST /api/auth/login    ┌────────────┐   set-cookie    ┌───────────┐
│ login.js │ ─────────────────────────▶ │ auth.py    │ ──────────────▶ │ httpOnly   │
│ register │   email + password         │ (bcrypt)   │   access_token  │ cookie(JWT)│
└──────────┘                            └────────────┘                  └───────────┘
                                              │                            │
                                              ▼                            ▼
                                        ┌────────────┐            ┌──────────────────┐
                                        │ auth.js    │            │ dependencies.py  │
                                        │ (fetch     │ ◀───────── │ get_current_user  │
                                        │  wrapper)  │  reads     │ require_admin     │
                                        └────────────┘  cookie    └──────────────────┘
```

## Backend: Auth Service (`src/services/auth.py`)

### User model (SQLite)
```sql
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',       -- 'admin' or 'user'
    display_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_login TEXT
);
```

### Key functions
```python
# Password hashing (bcrypt)
hash_password(password: str) -> str
verify_password(plain: str, hashed: str) -> bool

# JWT (PyJWT, HS256)
create_access_token(data: dict, expires_delta: timedelta | None = None) -> str
decode_access_token(token: str) -> dict | None

# User CRUD
create_user(email, password, role="user", display_name=None) -> dict | None
get_user_by_email(email: str) -> dict | None
get_user_by_id(user_id: str) -> dict | None
list_users() -> list[dict]
update_user_role(user_id: str, role: str) -> dict | None
set_user_active(user_id: str, is_active: bool) -> dict | None
delete_user(user_id: str) -> bool

# Admin seeding (startup)
seed_admin_users()  # reads ADMIN_PASSWORD + ADMIN_SEED env vars
```

### JWT cookie settings
```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    max_age=settings.JWT_EXPIRATION_HOURS * 3600,
    samesite="lax",
)
```

## Backend: Dependencies (`src/api/dependencies.py`)

### `get_current_user` — validates JWT cookie
```python
async def get_current_user(access_token: str | None = Cookie(default=None)):
    if not access_token:
        raise HTTPException(401, "Not authenticated")
    payload = decode_access_token(access_token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    user = get_user_by_id(payload.get("sub"))
    if not user or not user.get("is_active"):
        raise HTTPException(401, "User not found or inactive")
    return user  # {"id", "email", "role", "display_name", "is_active", ...}
```

### `require_admin` — dual auth (JWT cookie OR legacy API key)
```python
async def require_admin(
    access_token: str | None = Cookie(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    # Try legacy API key first
    if x_api_key and API_KEY:
        if x_api_key == API_KEY:
            return {"id": "legacy-api-key", "email": "admin@legacy", "role": "admin"}
        raise HTTPException(401, "Invalid API key")
    # Fall through to JWT
    user = await get_current_user(access_token)
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user
```

### Route protection patterns
```python
# Any authenticated user
@router.get("/api/ratings")
async def get_ratings(user=Depends(get_current_user)): ...

# Admin only (JWT cookie OR legacy API key)
@router.get("/api/admin/domains")
async def admin_domains(admin=Depends(require_admin)): ...

# Public (no auth)
@router.post("/api/auth/login")
@router.post("/api/auth/register")
@router.get("/")  # landing page
```

## Backend: Auth Routes (`src/api/routes/auth.py`)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/auth/login` | Public | Email + password → JWT cookie |
| `POST /api/auth/register` | Public | Create account (role defaults to `user`) |
| `GET /api/auth/me` | JWT | Returns current user info |
| `POST /api/auth/logout` | JWT | Clears cookie, redirects to `/` |

## Backend: Admin User Management (`src/api/routes/admin.py`)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/admin/users` | `require_admin` | List all users (strips password hashes) |
| `PATCH /api/admin/users/{id}/role` | `require_admin` | Change role (`admin` ↔ `user`) |
| `PATCH /api/admin/users/{id}/active` | `require_admin` | Enable/disable account |
| `DELETE /api/admin/users/{id}` | `require_admin` | Delete user (can't delete self) |

## Frontend: `ui/js/auth.js`

```javascript
const Auth = {
  async login(email, password) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email, password})
    });
    if (!res.ok) throw new Error((await res.json()).detail);
    const user = await res.json();
    this.user = user;
    return user;
  },

  async fetchWithAuth(url, opts = {}) {
    // Cookies are sent automatically with same-origin requests
    const res = await fetch(url, { ...opts, credentials: 'same-origin' });
    if (res.status === 401) {
      window.location.href = '/login.html';
      return;
    }
    return res;
  },

  isAdmin() { return this.user?.role === 'admin'; }
};
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | Recommended | auto-generated | HS256 signing key. Set for consistency across restarts. |
| `JWT_EXPIRATION_HOURS` | No | `168` (7 days) | Token lifetime |
| `ADMIN_PASSWORD` | Yes (first deploy) | — | Seeds `adelvillar@gmail.com` as admin on startup |
| `ADMIN_SEED` | No | — | Comma-separated `email:password` pairs for additional admins |
| `ADMIN_API_KEY` | No | — | Legacy API key for `X-API-Key` header fallback |

## Startup Seeding

```python
# Called in FastAPI startup event
def seed_admin_users():
    # 1. If ADMIN_PASSWORD is set and no admin exists with that email, create one
    # 2. Parse ADMIN_SEED for additional email:password pairs
    # 3. Idempotent — does NOT overwrite existing passwords
    # 4. App refuses to start if ADMIN_PASSWORD is missing and no admins exist
```

## TestClient Cookie Pitfall (Critical)

**Problem:** When multiple auth fixtures (admin, user) share the same `TestClient` instance, setting a cookie on one fixture silently overwrites the cookie on the other.

```python
# conftest.py — THE WRONG WAY
@pytest.fixture
def auth_client(client):      # 'client' is shared TestClient
    token = create_access_token({"sub": admin_id, "role": "admin"})
    client.cookies.set("access_token", token)  # sets on SHARED client
    return client

@pytest.fixture
def user_client(client):      # SAME shared TestClient
    token = create_access_token({"sub": user_id, "role": "user"})
    client.cookies.set("access_token", token)  # OVERWRITES admin cookie!
    return client
```

**Symptom:** Tests pass individually but fail when run together. `auth_client` requests resolve as `user@test.com` instead of `admin@test.com`, causing mysterious 403s on admin endpoints.

**Root cause:** `client.cookies.set("access_token", ...)` is a single-valued dict. The last `set()` wins. When `test_update_user_role` calls `user_client.get("/api/auth/me")` to get the user ID, it overwrites the admin cookie. The subsequent `auth_client.patch(...)` sends the user's token, gets 403.

**Fix:** In tests that need IDs from other users, query the database directly instead of making API calls through a different fixture:

```python
# THE RIGHT WAY — direct DB query, no cookie collision
def test_update_user_role(self, auth_client):
    from src.services.auth import get_user_by_email
    user = get_user_by_email("user@test.com")
    user_id = user["id"]
    r = auth_client.patch(f"/api/admin/users/{user_id}/role", json={"role": "admin"})
    assert r.status_code == 200
```

**Rule:** Never use one fixture's client to make API calls that set cookies when another fixture's client is also in scope. Use direct DB/service calls to get IDs and state.

## Legacy API Key Pattern (Deprecated)

For backward compatibility during migration, `require_admin` accepts either a JWT cookie or an `X-API-Key` header:

```python
# Still works:
curl -H "X-API-Key: dev-key" http://localhost:8000/api/admin/domains
```

The legacy path is tried first if `x_api_key` is provided AND `ADMIN_API_KEY` is configured. If a wrong key is provided, it rejects immediately (401). If no key is provided, it falls through to JWT validation.

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **TestClient cookie overwrite** | Tests pass individually but 403 in suite; `require_admin` sees wrong user | Use direct DB queries for user IDs; never swap cookies between fixtures |
| Missing JWT cookie | 401 "Not authenticated" | Login first; cookie is set via `response.set_cookie()` |
| Expired JWT | 401 "Invalid or expired token" | Set `JWT_EXPIRATION_HOURS` appropriately; re-login |
| User deactivated | 401 "User not found or inactive" | `get_current_user` checks `is_active` on every request |
| Role field empty in JWT payload | 403 "Admin access required" | Ensure `create_access_token` includes `role` in payload |
| CORS not configured for credentials | Browser blocks cookie set on cross-origin | `CORSMiddleware` with `allow_credentials=True` |
| `JWT_SECRET` changes between restarts | All existing tokens become invalid | Set `JWT_SECRET` env var for consistency |
| Admin self-delete | Server error or orphaned session | Backend rejects: "Cannot delete your own account" |
| Invalid role value in PATCH | 422 Validation Error | Validate against `Literal["admin", "user"]` |
