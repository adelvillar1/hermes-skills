# Backend Subagent Verification Workflow (FastAPI + Postgres/Redis)

After a backend subagent completes (or times out), verify the actual running system — not just file existence.

## 1. Static Checks (before booting)

```bash
# Import check with venv Python
.venv/bin/python -c "import sys; sys.path.insert(0,'app'); import admin, platform_config; print('admin routes:', len(admin.router.routes))"

# Route inspection
for r in admin.router.routes: print(' ', r.path)

# Grep gates
grep -c '@app\.' app/admin.py app/platform_config.py  # expect 0
grep -n 'ALLOWED_SORT_COLUMNS' app/admin.py            # injection whitelist present
```

## 2. Boot the App (real local stack)

```bash
# Start data services (remap host ports if conflict)
docker compose -f docker-compose.dev.yml up -d postgres redis
# If host 5432 taken → remap to 5433 in compose ports

# Create a run-dev-api.sh script (env vars + uvicorn) and launch in background
chmod +x backend/run-dev-api.sh
backend/run-dev-api.sh &
# Wait for "Application startup complete"
```

## 3. Mint a Test Token (no password login = SSO apps)

For SSO-only apps, there's no `/api/auth/login`. Mint a JWT using the app's own token logic:

```python
import sys; sys.path.insert(0, 'app')
from auth_sso import create_access_token
token = create_access_token({'user_id': 1, 'school_id': 2, 'role': 'super_admin'})
```

## 4. Endpoint Test Matrix

```bash
# Happy path: super_admin can access platform stats
curl -s -H "Authorization: Bearer ***" http://127.0.0.1:8001/admin/dashboard/stats

# Feature flags (Redis persistence)
curl -s -X PUT -H "Authorization: Bearer ***" -H "Content-Type: application/json" \
  -d '{"api_rate_limiting": "false"}' http://127.0.0.1:8001/admin/config/features
# Verify persistence with a second GET

# No-auth → 401/403
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/admin/dashboard/stats

# Sort injection → safe failure (400 or 200 with default sort, NOT 500)
curl -s "http://127.0.0.1:8001/admin/schools?sort_by=__class__" -H "Authorization: Bearer ***"
```

## 5. Common Gotchas Discovered During Verification

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| `ValueError: password cannot be longer than 72 bytes` | `passlib[bcrypt]` unpinned → pip installs bcrypt 5.0.0, breaks passlib | Pin `bcrypt==4.0.1` in requirements.txt |
| `ResponseValidationError: Input should be a valid list` | `response_model=List[dict]` on endpoint returning a paginated dict | Remove the annotation |
| 403 on platform admin endpoints from base domain | `get_current_user()` subdomain check applied to super_admin | Add `if user.role == "super_admin": return user` before slug check |
| Import succeeds but 0 routes registered | Module-level code error during import (syntax, missing dep) | Check full traceback from import command |

## 6. Idempotency Note

Re-running seed scripts creates duplicate schools/users. Expect counts to increase on re-verify. If a test expects exactly N records, re-seed fresh or adjust expectations.
