# Python Subprocess Bridge Architecture

Pattern for calling Python data processing from Next.js tRPC via subprocess.

## Why not a separate HTTP service?

| Concern | Subprocess Bridge | HTTP Sidecar |
|---------|------------------|--------------|
| Deployment complexity | Single Railway service | Two services, env sync |
| Latency | ~200ms per call (Python startup) | ~5ms per call (keep-alive) |
| Session persistence | File-backed (Parquet) | In-memory (Redis or RAM) |
| CORS / auth | None needed | Must configure |
| Railway cost | Single instance | Double |

**Choose bridge** when deployment simplicity matters more than sub-50ms response times, and when Excel uploads (not real-time streaming) dominate the workload.

## Architecture Diagram

```
┌─────────────┐     child_process.execSync()     ┌─────────────────┐
│  Next.js 15  │ ──────────────────────────────────▶  Python CLI    │
│  tRPC Router │                                     bridge.py      │
│              │ ◀─────────────────────────────────  (fresh process) │
│  bridge.ts   │     JSON to stdout                                    │
└─────────────┘                                   └────────┬────────┘
                                                           │
                                              ┌────────────┴────────────┐
                                              │                         │
                                   ┌──────────▼──────────┐   ┌─────────▼─────────┐
                                   │  AllocationProcessor│   │ WorkstreamProcessor│
                                   │  (Polars, 25 charts)│   │ (Polars, 7 charts)│
                                   └──────────┬──────────┘   └─────────┬─────────┘
                                              │                        │
                                              └──────────┬─────────────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │  File Session Store  │
                                              │  (~/.beacon/sessions/)│
                                              └─────────────────────┘
```

## Key Design Decisions

### 0. Use execFileSync, NEVER execSync with joined args

**This is the most common failure mode.** When you pass JSON params through the shell:

```typescript
// ❌ BROKEN — execSync joins args into a shell command
const args = ["python3", bridge, "--params", JSON.stringify({top_n: 5})];
execSync(args.join(" "));  // Shell mangles double quotes, JSON becomes unparseable

// ✅ CORRECT — execFileSync passes args directly to the kernel
execFileSync("python3", [bridge, "--params", JSON.stringify({top_n: 5})],
  { encoding: "utf-8", timeout: 30000 });
```

**Symptom of the bug:** bridge.py receives `--params` value as `{top_n: 5}` (missing quotes) and JSON.parse fails with `"Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"`.

### 0.1 Parameter Name Mapping

Bridge expects snake_case params (`top_n`, `start_date`), but frontend/API uses camelCase (`topN`, `startDate`). Map them:

```typescript
const PARAM_MAP: Record<string, string> = {
  topN: "top_n", maxWeeks: "max_weeks", startDate: "start_date",
  endDate: "end_date", pageSize: "page_size", sortBy: "sort_by",
  sortDesc: "sort_desc", personId: "person_id", minProjects: "min_projects",
};
```

### 2. File-backed sessions, not in-memory
Each bridge call is a fresh Python process. In-memory dicts are lost. Use Polars `write_parquet()` to persist DataFrames, with a `meta.json` for session metadata.

**Session directory layout:**
```
~/.beacon/sessions/<session-uuid>/
├── allocation.parquet    # Polars DataFrame
├── workstream.parquet    # Polars DataFrame
└── meta.json             # { session_id, created_at, filenames }
```

### 3. Dataset routing abstraction
Not all action prefixes map 1:1 to session data types:

```python
ALLOCATION_ALIASES = {"allocation", "workforce", "ops-project", "projects", "people", "trends", "executive"}
ALLOCATION_ALIASES = {"allocation", "workforce", "ops-project", "projects", "people", "trends", "executive"}
```

7 dashboard tabs read from the allocation data; only 1 tab reads from workstream data.

## File Layout

```
packages/data/
├── src/processors/
│   ├── __init__.py          # Package exports
│   ├── config.py            # Column maps, constants
│   ├── session_store.py     # File-backed session persistence
│   ├── timeseries.py        # Date-ranged → daily/weekly FTE engine
│   ├── allocation.py        # 25 chart methods
│   └── workstream.py        # 7 chart methods
├── bridge.py                # CLI entry point (403 lines)
├── test_smoke.py            # Direct processor tests
├── test_bridge.py           # Full bridge end-to-end tests
└── pyproject.toml
```

```
apps/web/server/
├── bridge.ts                # TypeScript wrapper
└── routers/_app.ts          # Rewired tRPC router
```

## Testing Checklist

- [ ] `python3 test_smoke.py` — direct processor tests pass
- [ ] `python3 test_bridge.py` — 20+ CLI actions end-to-end
- [ ] `next build` succeeds (verifies TypeScript side compiles)
- [ ] Upload Excel → query chart data loop works (manual: upload file, check session persists)
- [ ] Cross-process session: create session → upload in call 1 → query in call 2

## Railway Deployment Requirements

- Python 3.9+ with: `polars`, `fastexcel`, `python-dateutil`, `xlsxwriter`
- `BEACON_SESSIONS_DIR` env var pointing to a writable directory
- nixpacks must auto-detect `pyproject.toml` in `packages/data/`

### nixpacks.toml (if needed):
```toml
[phases.install]
cmds = ["pip install -e packages/data/"]
```
