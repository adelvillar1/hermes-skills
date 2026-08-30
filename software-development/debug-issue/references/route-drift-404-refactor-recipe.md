# Route-Drift 404 After Refactor — Reproduction Recipe

> ELO Scenario Lab example: 2026-06-15 hotfix for Domains/Corpus views returning 404.

## Symptom

Dashboard **Domains** and **Corpus** admin views show "Failed to load domains: 404" / "Failed to load corpus: 404".

## Root cause

The frontend view modules (`ui/js/views/domains.js`, `ui/js/views/corpus.js`) were extracted during the modular frontend refactor. They still called `/api/pipeline/domains`, `/api/pipeline/corpus`, and `/api/pipeline/corpus/{table}/sample`. The backend had placed those endpoints under `src/api/routes/admin.py` with router prefix `/admin`, so the true paths were `/api/admin/domains`, `/api/admin/corpus`, and `/api/admin/corpus/{table}/sample`.

## Detection commands

```bash
# Find all API URLs in the affected view modules
grep -nE "api\('/api/" ui/js/views/*.js

# Confirm backend routers and their prefixes
grep -nE "APIRouter\(prefix|router\.(get|post|put|delete)\(" src/api/routes/*.py

# Confirm how routers are mounted in main.py
grep -nE "include_router|prefix=" src/api/main.py

# Compare frontend calls against actual mounted routes
python3 - <<'PY'
import ast, re, pathlib
from collections import defaultdict

frontend = {}
for f in pathlib.Path('ui/js/views').glob('*.js'):
    for line in f.read_text().splitlines():
        m = re.search(r"api\('(/api/[^']+)'", line)
        if m:
            frontend.setdefault(f.name, []).append(m.group(1))

backend = []
for f in pathlib.Path('src/api/routes').glob('*.py'):
    text = f.read_text()
    prefix_match = re.search(r'APIRouter\(prefix="([^"]+)"', text)
    prefix = prefix_match.group(1) if prefix_match else ''
    for method, path in re.findall(r'@router\.(get|post|put|delete)\("([^"]+)"', text):
        backend.append((f.name, prefix + path))

print("== Frontend calls ==")
for view, urls in sorted(frontend.items()):
    for u in urls:
        print(f"{view}: {u}")
print("\n== Backend routes ==")
for route_file, route in sorted(backend):
    print(f"{route_file}: {route}")
PY
```

## Verification via TestClient

Run from the project root with the venv active:

```python
import os
os.environ.pop("DATABASE_URL", None)
os.environ["JWT_SECRET"] = "test-secret-key-for-pytest-that-is-long-enough"
os.environ["ADMIN_PASSWORD"] = "testadmin123"

from fastapi.testclient import TestClient
from src.api.main import app
from src.services.auth import create_access_token, get_user_by_email, create_user
from src.services.corpus import ensure_mc_tables, ensure_users_table, ensure_user_favorites_table

ensure_mc_tables(); ensure_users_table(); ensure_user_favorites_table()
user = get_user_by_email("admin@test.com")
if not user:
    create_user(email="admin@test.com", password="<test-password>", role="admin", display_name="Test Admin")
    user = get_user_by_email("admin@test.com")

token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
c = TestClient(app)
c.cookies.set("access_token", token)

print("domains", c.get("/api/admin/domains").status_code, len(c.get("/api/admin/domains").json()))
print("corpus", c.get("/api/admin/corpus").status_code, c.get("/api/admin/corpus").json())
print("sample", c.get("/api/admin/corpus/evidence_items/sample?limit=2").status_code)
```

## Response-shape gotchas

The backend returned the list **directly**, not wrapped in `{domains: [...]}` or `{tables: [...]}`. The frontend had to adapt:

- `domains` → `[{sport, config}, ...]` (use `config.name`/`config.slug`, `config.starter_sources`, `config.key_state_fields`)
- `corpus` → `[{name, row_count}, ...]` (not `rows`, `size_human`, `updated_at`)
- `sample` → `{table, columns, rows, total_rows}`

## Data-coverage gotcha: endpoint returns fewer entities than the canonical list

After the 404 was fixed, `/api/admin/domains` returned only **5** sports because it read on-disk domain packs for American sports only. The canonical `VALID_SPORTS` in `src/constants.py` lists **15** sports. The fix:

1. Iterate `VALID_SPORTS` instead of a hardcoded American list.
2. Use on-disk packs when present; synthesize a minimal config for football leagues (and any missing sport) from `HOME_FIELD_ADVANTAGE`, `SPORT_K_FACTORS`, and per-sport source/engine maps.
3. Normalize on-disk configs so every row has readable `name`, `source`, `engine`, and `status`.
4. Order results logically (American sports first, then football leagues).
5. Update the test assertion from `len == 5` to `len == 15` and verify all football keys are present.

## Fix summary

1. Update URLs from `/api/pipeline/*` to `/api/admin/*`.
2. Adapt frontend to the actual backend response shape.
3. Verify the backend returns the full canonical entity set; synthesize missing entries when necessary.
4. Run `pytest` and `pnpm run test` to ensure no regressions.
