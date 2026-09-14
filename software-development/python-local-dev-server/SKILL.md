---
name: python-local-dev-server
description: "Start, restart, and troubleshoot local Python development servers (FastAPI/Flask/Django). Covers dependency installation, port conflict resolution, zombie process cleanup, and health verification."
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [python, fastapi, uvicorn, flask, django, local-dev, server, port-conflict]
    related_skills: [project-warmup, debug-issue]
---

# Python Local Development Server

Start, restart, and troubleshoot local Python development servers. Covers the full flow from cloned repo to running server, with emphasis on port conflicts and zombie process cleanup — the most common friction points.

## When to Use

- User says "start the server", "run the app", "launch locally", or "resume this project"
- A Python project needs to be brought up after clone, pull, or long idle period
- `python run.py` or `uvicorn` fails with "address already in use"
- A background process from a previous session is still holding a port

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server (use python3 on macOS/Linux)
python3 run.py
# OR for explicit port
python3 run.py --port 8001
# OR direct uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Port Conflict Resolution

### Diagnose: Is something already listening?

```bash
# macOS
lsof -i :<PORT> | grep LISTEN

# Linux
ss -tlnp | grep :<PORT>
# OR
netstat -tlnp | grep :<PORT>
```

### Kill the zombie process

```bash
# Get PID from lsof output, then kill
kill <PID>

# If stubborn
kill -9 <PID>
```

### Common zombie sources

| Source | How it happens | Prevention |
|--------|-------------|------------|
| Previous background session | `terminal(background=true)` process wasn't fully terminated | Always `kill` old PIDs before starting new background sessions |
| Docker container | `docker run -p 8000:8000` still running | `docker ps` → `docker stop <container>` |
| Another project | Different repo using same default port | Use `--port` flag to pick a free port |
| IDE debug server | VS Code / PyCharm running a debug session | Check IDE's running configurations panel |

### Picking an alternative port

If 8000 and 8001 are both taken, scan for an open port:

```bash
# Find next available port starting from 8002
for port in $(seq 8002 8010); do
  if ! lsof -i :$port >/dev/null 2>&1; then
    echo "Port $port is free"
    break
  fi
done
```

## Background Process Handling (Terminal Tool)

When using the terminal tool's `background=true` for long-lived servers:

### The zombie problem

Python processes started via `terminal(background=true)` may not fully release their port when the session ends, especially if the process was started with shell backgrounding (`&`) inside the command. The terminal tool spawns a shell, which spawns Python, and the shell may exit while Python keeps running.

### Safe pattern

```bash
# BAD: shell backgrounding creates a detached process the tool can't track
python3 run.py --port 8001 &

# GOOD: let the terminal tool handle backgrounding directly
# Use terminal(background=true) with the command directly, no &
```

### Verification after background start

```bash
# 1. Check process is running
ps aux | grep "run.py\|uvicorn"

# 2. Check port is bound
lsof -i :8001 | grep LISTEN

# 3. Health check
curl -s http://localhost:8001/health || curl -s http://localhost:8001/
```

### Cleanup before restart

Always run this before starting a new background server session:

```bash
# Kill any existing Python process on the target port
PID=$(lsof -t -i :8001)
if [ -n "$PID" ]; then
  kill $PID
  sleep 1
  # Verify it's gone
  lsof -i :8001 | grep LISTEN || echo "Port 8001 is now free"
fi
```

## Health Verification

After the server starts, verify it's actually serving:

```bash
# FastAPI default — root may 404, try docs or a known endpoint
curl -s http://localhost:8001/docs
curl -s http://localhost:8001/health
curl -s http://localhost:8001/

# For non-FastAPI (Flask/Django), root usually works
curl -s http://localhost:8001/ | head -c 200
```

## Common Pitfalls

### 1. `python` vs `python3`

On macOS and many Linux distros, `python` may not exist or may point to Python 2. Always use `python3` unless the project explicitly uses a virtual environment or `pyenv` shim.

```bash
# Check which python
which python3
python3 --version
```

### 2. pip dependency conflicts

If `pip install -r requirements.txt` shows dependency resolver warnings, the project may have incompatible version pins. Common with `starlette`/`fastapi` version drift:

```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
```

**Fix:** Usually safe to ignore if the install completed. If the server fails to start with import errors, reinstall the conflicting package explicitly:

```bash
pip install --force-reinstall starlette==0.48.0
```

### 3. Kaleido/Plotly export hangs on first run

The `kaleido` package (used by Plotly for PNG/SVG export) may hang or crash on first initialization. If the server starts but chart export fails:

```bash
# Pre-warm kaleido by running a minimal plot export once
python3 -c "import plotly.graph_objects as go; fig = go.Figure(); fig.write_image('/tmp/test.png')"
```

### 4. Background process output buffering with `terminal(background=true)`

When starting a Python server via the terminal tool's `background=true`, output may appear empty in polls because:
- The process hasn't flushed stdout yet (Python buffers by default)
- The shell wrapper redirects output in a way the tool can't capture
- The process exited immediately but the shell wrapper is still running

**Symptoms:** `process(action="poll")` shows "running" but `process(action="log")` shows 0 lines. `lsof` shows the port is NOT actually bound.

**Fix:** Redirect output to a file explicitly and use a simple command (no shell backgrounding with `&`):

```bash
# BAD: shell backgrounding inside the command
python3 run.py --port 8001 > /tmp/server.log 2>&1 &

# GOOD: let the terminal tool handle backgrounding, redirect to file
python3 run.py --port 8001 > /tmp/server.log 2>&1
```

Then verify by reading the file:
```bash
cat /tmp/server.log
tail -f /tmp/server.log
```

Or skip the terminal tool entirely and use a direct background process with health checks:
```bash
# Start and immediately verify
python3 run.py --port 8001 > /tmp/server.log 2>&1 &
sleep 2
cat /tmp/server.log
lsof -i :8001 | grep LISTEN
```

### 5. `.python-version` file mismatch

If the project has a `.python-version` file (e.g., for `pyenv`), ensure the specified version is installed:

```bash
cat .python-version
pyenv install -s $(cat .python-version)
```

### 6. FastAPI `StaticFiles` mounted at `/` intercepts API routes

When using `app.mount("/", StaticFiles(...))` in FastAPI, the static file handler catches ALL routes including `/api/*` unless the API routes are registered **before** the mount, or the mount uses a more specific path.

**Symptoms:** API endpoints return 404 or serve the static index.html instead of JSON. The browser shows the SPA instead of OpenAPI docs at `/docs`.

**Fix:** Register API routes and `@app.get()` endpoints **before** the `StaticFiles` mount:

```python
# CORRECT: API routes first
app.include_router(api_router, prefix="/api")
app.get("/api/health")(...)  # Also before mount

# THEN mount static files
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
```

If static files must be at `/` and API routes at `/api/`, ensure no `@app.get("/")` or `@app.get("/{path}")` catch-all is registered before the mount — it will shadow `StaticFiles`.

### 7. `terminal(background=true)` falsely detects long-lived processes

The terminal tool's heuristic may flag `pip install` or `pytest` as "long-lived server processes" and refuse to run them in foreground. This happens because the tool pattern-matches on keywords like `uvicorn`, `fastapi`, or `--reload` anywhere in the command string.

**Symptoms:** `terminal` returns: "This foreground command appears to start a long-lived server/watch process. Run it with background=true..." even for one-shot commands like `pip install fastapi uvicorn`.

**Fix:** Use `execute_code` with `subprocess.run(..., capture_output=True)` instead of `terminal` for commands that the tool misidentifies. Or append a non-matching suffix like `2>&1 | tail -5` to break the heuristic (fragile).

```python
# Use execute_code for pip installs when terminal misidentifies
import subprocess
result = subprocess.run(
    ['pip', 'install', 'fastapi', 'uvicorn'],
    capture_output=True, text=True
)
print(result.stdout[-1000:])
```

### 8. Uvicorn subprocess can't find project modules (even with `pip install -e .`)

After `pip install -e .`, uvicorn may still fail with `ModuleNotFoundError: No module named 'src'` because uvicorn spawns a subprocess that doesn't inherit the working directory's Python path context.

**Symptoms:** `python3 -c "from src.api.main import app; print('OK')"` works, but `python3 -m uvicorn src.api.main:app` fails. `./run.sh` with `PYTHONPATH` set may also fail depending on the shell environment.

**Fix — wrapper script:**

```bash
#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${DIR}:${PYTHONPATH}"
cd "${DIR}"
python3 -m uvicorn src.api.main:app --reload --port 8000
```

**Fix — if wrapper still fails:** The local uvicorn subprocess spawning model is fragile across different shell environments. **Use Docker instead** for a deterministic environment:

```bash
# Build and run with Docker
docker build -t myapp .
docker run -d -p 8000:8000 myapp
```

This is the pattern used in production (Railway, Fly, etc.). The container's `WORKDIR` + `ENV PYTHONPATH` guarantee `src` is findable.

### 9. `uvicorn --reload` (or a stale background process) returns old code while direct Python tests pass

Uvicorn's file watcher may miss edits, or a background `uvicorn` process may keep running an older version of an imported module. Directly importing the module in a fresh Python interpreter shows the new behavior; the HTTP endpoint still returns the old response shape.

**Symptoms:**
- `python3 -c "from src.services.x import y; y()"` produces the updated output.
- `curl http://localhost:8000/endpoint` returns stale data or the old payload schema.
- `lsof -i :8000` shows a Python process that started before your edit.

**Fix — restart the server, not just rely on reload:**

```bash
# 1. Find every process on the port
lsof -i :8000

# 2. Kill them all
kill <PID1> <PID2>

# 3. Start fresh from the project root with the venv
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Then verify the *HTTP* shape, not just the import:

```bash
curl -s http://localhost:8000/api/endpoint | python3 -m json.tool | head -20
```

When using the terminal tool's `background=true`, always run the cleanup step before starting a new background session. Do not trust `--reload` to pick up every change during a long debugging loop.

### 9. `pytest` runs against the wrong Python — venv vs system Python split

A common macOS dev gotcha: a project has a `.venv/` with the project's dependencies installed via `pip install -e ".[dev]"`, but the global `pytest` in `$PATH` (often from a different Python install) takes precedence over the venv's pytest. Tests "pass" because they run against the system Python, which may have transitive deps from other projects, while the venv itself is missing packages the production deploy will use.

**Symptoms:**
- `pytest -q` shows "461 passed" but `python -c "import bcrypt; print(bcrypt.__version__")` inside the venv raises `ModuleNotFoundError`
- `which pytest` points to `/Library/Frameworks/Python.framework/Versions/3.13/bin/pytest` (system) instead of `.venv/bin/pytest`
- Production deploy fails with a missing dep that the local venv was supposed to have

**The trap:**
```bash
$ which python python3 pytest
/Users/<you>/Projects/foo/.venv/bin/python
/Users/<you>/Projects/foo/.venv/bin/python3
/Library/Frameworks/Python.framework/Versions/3.13/bin/pytest     # ← system Python!

$ head -1 $(which pytest)
#!/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13   # ← not the venv
```

**Fix — three options, in order of preference:**

1. **Use the venv's pytest explicitly:** `source .venv/bin/activate && pytest -q`. The activate prepends `.venv/bin` to PATH so `pytest`, `python`, and `pip` all resolve to the venv.
2. **Use `python -m pytest` from the venv:** `python -m pytest -q` always uses the venv's pytest because the venv's `python` is the entry point.
3. **Recreate the venv from a clean pyproject.toml:** If the venv's deps have drifted, `rm -rf .venv && uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"` rebuilds deterministically.

**Verification — confirm tests and the venv see the same package set:**
```bash
$ source .venv/bin/activate && python -c "import bcrypt, pydantic; print('ok')"
# If this fails, the venv is missing a dep that the system pytest has.
# Either re-install or recognize that pytest is running against a different interpreter.
```

**Why this is dangerous for deploys:** The Railway Dockerfile does `pip install -e ".[dev]"` from `pyproject.toml`. If the venv (which mirrors the Dockerfile) is missing a dep that pytest relied on from system Python, the deploy will fail. **Always verify the venv itself can run the tests**, not just the system pytest.

**Real example (2026-06-01):** Local venv was missing `email-validator` (a transitive of `pydantic[email]`) and `bcrypt`. System Python 3.13 had both from other projects. `pytest -q` showed 461 passed because it ran against system Python. The push to `main` triggered a Railway deploy which did a clean `pip install` from `pyproject.toml` — neither dep was declared, so the app crashed at import time with `ImportError: email-validator is not installed`. Fix: declare the deps in `pyproject.toml`, then rebuild the venv and re-run tests to confirm.

**Variant: `.venv` on the wrong Python (uv projects).** A subtler failure mode on uv-managed projects: `.venv/` was created before the project bumped to a new Python version (e.g., `pyproject.toml` requires `python = ">=3.13"` but the venv is on system Python 3.10). Running `pytest` from the broken venv silently collects 0 tests — exit code 0, no output — masking the fact that nothing is actually being tested. Documentation drift in `CLAUDE.md` and `STATE-SNAPSHOT.md` "test counts" can persist for weeks because no one notices pytest is collecting nothing.

**Symptoms:**
- `uv run pytest --co -q` collects 980 tests
- `pytest --co -q` (from the broken venv) collects 0 tests
- Both exit 0; the broken one just silently does nothing
- The venv's `python -c "import sys; print(sys.version)"` shows 3.10.x

**Fix — use uv to enforce the right Python:**
```bash
# Option A: always run tests via uv (recommended)
uv run pytest -q              # uses pyproject.toml's required Python
uv run pytest --co -q         # collection only — fast, no execution

# Option B: recreate the venv on the right Python
rm -rf .venv
uv venv --python 3.13
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest -q                     # now runs against 3.13
```

**Why the silent-zero-tests is dangerous for doc drift:** If you trust doc-stated test counts (e.g., "1,083 tests passing") without running the suite, you can update `STATE-SNAPSHOT.md` to a number that's been wrong for weeks. Always run `uv run pytest --co -q` before writing a test count into a doc — the collection step is fast and reveals the real number, including any pytest collection errors that the broken venv would hide.

## Workflow: Resume a Cloned Python Project

```bash
# 1. Navigate to project
cd /path/to/project

# 2. Check Python version
cat .python-version 2>/dev/null || python3 --version

# 3. Install / update dependencies
pip install -r requirements.txt

# 4. Free the target port
PORT=8001
PID=$(lsof -t -i :$PORT 2>/dev/null)
[ -n "$PID" ] && kill $PID && sleep 1

# 5. Start server in background
# (Use terminal tool with background=true)
python3 run.py --port $PORT

# 6. Verify
sleep 2
curl -s http://localhost:$PORT/ | head -c 100
curl -s http://localhost:$PORT/docs | head -c 100
```

## References

- `references/port-conflict-cleanup.md` — Detailed lsof/netstat patterns, cross-platform port scanning, and zombie process identification.
