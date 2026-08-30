# Docker Caching Pitfalls — Stale Code in Containers

When code changes don't appear in the running container, the build cache is serving old layers. This reference covers the diagnosis and fix.

## Symptom

- API endpoints return old data counts (e.g., 8 teams instead of 34)
- New fields missing from JSON responses
- UI shows old behavior despite code changes committed
- `docker-compose up` starts instantly (no build step)

## Root Cause

Docker layer caching. If `COPY src/ ./src/` hasn't changed (from Docker's perspective), it reuses the cached layer with old code.

Common triggers:
- `docker-compose up` without `--build`
- Dockerfile hasn't changed, so Docker skips the `COPY` layer
- `.dockerignore` excludes files that changed
- Build context doesn't include the modified files

## Diagnosis

```bash
# Check if container has new code
docker exec <container> cat src/api/routes/ratings.py | head -5

# Check image build time
docker images | grep myapp

# Check if compose is using cached build
docker-compose up -d  # Should show "Building app" if rebuilding
```

## Fix

**Always use `--build` when code changes:**

```bash
docker-compose down
docker-compose up -d --build
```

**Force no-cache if cache is poisoned:**

```bash
docker-compose down
docker build --no-cache -t myapp .
docker-compose up -d
```

**Verify after rebuild:**

```bash
# Check the running container has new code
curl -s http://localhost:8080/api/ratings | python3 -m json.tool | grep -c '"id"'
# Should match expected count
```

## Faster Alternative: `docker cp` for Runtime Data Changes

When only **runtime data** changes (corpus DB, cache files, config JSON), you can skip the full rebuild:

```bash
# Copy corpus DB to running container (30x faster than rebuild)
docker cp .forecast/corpus.db myapp-container:/app/.forecast/corpus.db

# Restart the container to pick up the new file
docker restart myapp-container
```

**When to use rebuild vs cp:**

| Change type | Action | Time |
|-------------|--------|------|
| Source code (Python, HTML, JS) | `docker compose build app` + `up -d` | ~30s |
| Static files only (HTML, CSS, JS) | `docker compose build app` + `up -d` | ~30s |
| **Runtime data only** (corpus DB, cache) | `docker cp` + `docker restart` | **~2s** |
| Dependencies (pyproject.toml, requirements) | `docker compose build --no-cache` | ~120s |

**Important:** `docker cp` goes to the container name, not the service name. Find the actual container name:
```bash
docker ps --filter name=app --format "{{.Names}}"
# Often: elo-scenario-lab-app-1
```

**Verification after cp:**
```bash
# Check the count in the running container
docker exec <container> python3 -c "
import sqlite3
c = sqlite3.connect('/app/.forecast/corpus.db')
print(c.execute('SELECT COUNT(*) FROM evidence_items').fetchone()[0])
c.close()
"
```

## Prevention

1. **Always use `--build`** when any source file changes:
   ```bash
   docker-compose down && docker-compose up -d --build
   ```

2. **Use `docker cp`** for runtime data changes (corpus DB, caches) to avoid unnecessary rebuilds.

3. **Use `.dockerignore`** to exclude cache dirs but NOT source dirs:
   ```
   .cache/
   .forecast/
   .git/
   __pycache__/
   *.pyc
   ```

3. **Version your images** for reproducibility:
   ```bash
   docker build -t myapp:$(git rev-parse --short HEAD) .
   ```

4. **Multi-stage builds** for cleaner cache invalidation:
   ```dockerfile
   # Stage 1: Dependencies (rarely changes)
   FROM python:3.13-slim as deps
   COPY pyproject.toml ./
   RUN pip install -e ".[dev]"
   
   # Stage 2: Application (changes often)
   FROM deps as app
   COPY src/ ./src/
   COPY ui/ ./ui/
   ```

## Related

- `templates/docker-compose.yml` — Docker Compose with nginx reverse proxy
- `references/data-pipeline-integration.md` — Docker volume mounts for persistent corpus
