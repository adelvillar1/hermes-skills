---
name: nextjs-dashboard-modernization
description: "Modernize legacy dashboard applications (vanilla JS + server-side rendering) to Next.js + TypeScript + Tremor/Recharts with a maintainable component architecture. Covers monorepo setup, tRPC API consolidation, chart registry pattern, and the specific dependency conflicts that arise with React 18/19 + Tremor + Next.js 15."
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [nextjs, dashboard, modernization, tremor, trpc, typescript]
    related_skills: [init-project-structure, draft-feature-plan]
---

# Next.js Dashboard Modernization

Modernize legacy dashboard applications to a maintainable Next.js + TypeScript stack with component-based chart architecture.

## When to Use

- Legacy dashboard uses vanilla JS + Plotly.js with monolithic files (1,000+ lines)
- Adding a new chart requires touching 4+ files with no clear boundaries
- API has 30+ endpoints where 10-15 would suffice
- No type safety across frontend/backend boundary
- User wants maintainability over speed

## When NOT to Use

- Dashboard is simple (<5 charts, <500 lines total) — overkill
- Team has no React/TypeScript experience — migration cost too high
- Need to ship in <1 week — this is a 3-4 week effort

## Target Stack

| Layer | Technology | Version Notes |
|-------|-----------|---------------|
| Framework | Next.js 15 App Router | Use React 18, not 19 (Tremor v3 peer dep) |
| Language | TypeScript 5.x | Strict mode |
| Styling | Tailwind CSS v3 | v4 has issues with Next.js font system |
| Components | shadcn/ui + Tremor React | Tremor for charts, shadcn for UI primitives |
| State | TanStack Query | Server state caching, loading states |
| API | tRPC or Next.js API Routes | Type-safe RPC, consolidate endpoints |
| Charts | Tremor (standard) + Plotly.js (complex) | Heatmaps, Gantt timelines need Plotly fallback |
| Monorepo | Turborepo | Standard for Next.js + shared packages |

## Critical Dependency Conflicts

### React 19 + Tremor v3
**Problem:** Tremor React v3 requires React `^18.0.0` as a peer dependency. Next.js 15 ships with React 19 by default.

**Fix:** Pin React to 18.3.1 in the app package.json:
```json
"react": "^18.3.1",
"react-dom": "^18.3.1"
```

Install with `--legacy-peer-deps` to bypass the peer dependency conflict:
```bash
npm install @tremor/react --legacy-peer-deps
```

### Tailwind CSS v4 + Next.js
**Problem:** Tailwind v4's `@import "tailwindcss"` syntax fails with Next.js font loading and PostCSS config in ESM projects.

**Fix:** Use Tailwind v3.4.17 with standard directives:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

PostCSS config as CommonJS (`.cjs` extension in ESM projects):
```javascript
// postcss.config.cjs
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### npm Workspaces + Dependency Hoisting
**Problem:** npm workspaces hoists dependencies to root `node_modules/`. Installing in app directory may not create local `node_modules/` entries.

**Fix:** Install workspace dependencies from the ROOT with workspace flag:
```bash
# From monorepo root
cd /path/to/monorepo
npm install tailwindcss@3.4.17 autoprefixer@10.4.21 postcss@8.5.14 -w @beacon/web --save-dev
```

Verify installation by checking root `node_modules/`, not app `node_modules/`:
```bash
ls node_modules/tailwindcss/package.json
```

## Data Processing Backend Pattern

When the legacy dashboard uses Python (FastAPI + Pandas + Plotly) for its data processing, you have two options for connecting it to Next.js:

### Option A: Python HTTP Sidecar (traditional)
Run the Python app as a separate microservice. Simple to keep, but adds: separate deployment, CORS config, service discovery, and double the infrastructure to manage.

### Option B: Python Subprocess Bridge (recommended for single-service deployment)
Call Python processing directly from Next.js via `child_process.execSync()`. Keeps deployment simple — one Railway service handles both Next.js and Python.

#### CRITICAL: Use execFileSync, not execSync

`execSync` with `args.join(" ")` passes arguments through the shell, which **mangles JSON strings in `--params`** (double quotes get interpreted by the shell). Always use `execFileSync` with an args array:

```typescript
// ❌ BROKEN: shell mangles JSON in --params
const stdout = execSync(args.join(" "));  // JSON.stringify(params) gets corrupted

// ✅ CORRECT: no shell involvement
const stdout = execFileSync("python3", [BRIDGE, "--action", action, "--params", JSON.stringify(params)],
  { encoding: "utf-8", timeout: 30000 });
```

**Error signature when this happens:** The bridge receives malformed JSON and throws `Expecting property name enclosed in double quotes: line 1 column 2 (char 1)`. If you see this error, check `execSync` vs `execFileSync` first.

For the upload/multipart routes and session API, the same fix applies — use `execFileSync` with a plain args array, never `execSync` with a joined string.

#### Parameter Name Mapping

Frontend camelCase param names must map to Python snake_case:

```typescript
const PARAM_MAP: Record<string, string> = {
  topN: "top_n",
  maxWeeks: "max_weeks",
  startDate: "start_date",
  endDate: "end_date",
  pageSize: "page_size",
  sortBy: "sort_by",
  sortDesc: "sort_desc",
  personId: "person_id",
  minProjects: "min_projects",
  threshold: "threshold",
  search: "search",
};
```

Apply before passing to bridge:
```typescript
const mapped = {}
for (const [k, v] of Object.entries(params)) {
  mapped[PARAM_MAP[k] || k] = v
}
```

#### Architecture

```
Next.js tRPC router
      │
      ▼
bridge.ts (TypeScript wrapper)
      │  child_process.execSync()
      ▼
bridge.py (CLI entry point)
      │
      ├──► AllocationProcessor (Polars)
      │
      ├──► WorkstreamProcessor (Polars)
      │
      └──► SessionStore (file-backed, Parquet on disk)
```

#### bridge.ts — TypeScript wrapper

```typescript
// apps/web/server/bridge.ts
import { execSync } from "child_process";
import fs from "fs";
import path from "path";

const BRIDGE_PATH = path.resolve(process.cwd(), "..", "..", "packages", "data", "bridge.py");

function callBridge(action: string, session?: string, params?: Record<string, unknown>, filepath?: string) {
  const args = ["python3", bridgePath, "--action", action];
  if (session) args.push("--session", session);
  if (params) args.push("--params", JSON.stringify(params));
  if (filepath) args.push("--filepath", filepath);

  const stdout = execSync(args.join(" "), { encoding: "utf-8", timeout: 30000 });
  return JSON.parse(stdout.trim());
}
```

#### bridge.py — Python CLI entry point

Each action is dispatched to a processor method and serialized as JSON to stdout:

```python
# packages/data/bridge.py
def main():
    args = parse_args()
    action = args.action
    if action == "session.create":
        result = handle_session_create(args)
    elif action.startswith("allocation.") or action.startswith("workstream."):
        result = handle_data_query(args)
    elif action.startswith("upload."):
        result = handle_upload(args)
    else:
        result = {"success": False, "error": f"Unknown action: {action}"}
    print(json.dumps(result, default=str))
```

#### Dataset Routing

Not all action prefixes map directly to session data types. Multiple dashboard tabs share the same underlying processor:

```python
allocation_aliases = {"allocation", "workforce", "ops-project", "projects", "people", "trends", "executive"}
session_dataset = "allocation" if dataset in allocation_aliases else dataset
```

All these tabs read from the allocation Excel data:
- `executive.summary` → `AllocationProcessor.get_executive_summary()`
- `trends.rolling-average` → `AllocationProcessor.get_rolling_average()`
- `workforce.summary` → `AllocationProcessor.get_workforce_summary()`

Only `workstream.*` reads from the separate workstream data.

#### Cross-Process Session Persistence

Each `bridge.py` call is a fresh Python process. Sessions must persist to disk:

```python
# File-backed: stores DataFrames as Parquet + meta.json in ~/.beacon/sessions/<uuid>/
class Session:
    @property
    def allocation_path(self) -> Path: return self.path / "allocation.parquet"
    @property
    def workstream_path(self) -> Path: return self.path / "workstream.parquet"

    def set_allocation(self, df: pl.DataFrame, filename: str) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        df.write_parquet(self.allocation_path)
```

**Use the environment variable `BEACON_SESSIONS_DIR`** to override the sessions directory (useful for Railway ephemeral filesystem vs bind mount).

#### Bridge Action Map

The bridge maps ~45 actions to Python processor methods. Key pattern — one argparser, one JSON response:

| Action | Processor Method | Notes |
|--------|-----------------|-------|
| `allocation.portfolio` | `get_portfolio_weekly_fte(date_cutoff, top_n)` | TimeSeriesBuilder, top N groups |
| `allocation.heatmap` | `get_department_heatmap(date_cutoff, max_weeks)` | Pivot to z_values matrix |
| `allocation.distribution` | `get_allocation_distribution()` | Returns raw values array |
| `workstream.timeline` | `get_task_timeline(top_n)` | Gantt-format data |
| `executive.summary` | `get_executive_summary()` | Composite metrics |

### Pitfalls

1. **Session lost between calls** — Each bridge call is a subprocess. Use file-backed storage (Parquet), not in-memory dicts. If sessions disappear, check `~/.beacon/sessions/` exists and is writable.
2. **Polars write_excel engine** — Requires `fastexcel` or `xlsxwriter`. Install with `pip install fastexcel openpyxl xlsxwriter`.
3. **Build passing ≠ bridge working** — The production build includes the tRPC router but doesn't test the Python bridge. Verify with `npm run dev` + actual API calls, not just `next build`.
4. **Session cleanup** — Parquet files accumulate. Add a cron or Railway restart hook to clear `~/.beacon/sessions/`. Sessions older than 24h should be purged.
5. **Large file uploads** — Bridge reads the full Excel into memory. For files >50MB, consider chunked processing. Current max: 10MB per the legacy config.
6. **Deployment Python dependency** — Railway nixpacks must have `polars`, `fastexcel`, `python-dateutil`. Add to `requirements.txt` or `pyproject.toml` in the data package.

## TanStack Query Integration

After the REST API layer is in place, add TanStack Query (v5) as the data-fetching layer for all chart cards:

### Custom Hook

```typescript
// lib/use-chart-data.ts
import { useQuery, useQueryClient } from "@tanstack/react-query";

export function useChartData<T = Record<string, unknown>>({
  sessionId, dataPath, params = {},
  staleTime = 5 * 60 * 1000, // 5 min cache
  enabled = true,
}) {
  return useQuery<T, Error>({
    queryKey: ["chart", dataPath, sessionId, params],
    queryFn: async () => {
      const qp = new URLSearchParams({ sessionId });
      for (const [k, v] of Object.entries(params)) qp.set(k, String(v));
      const res = await fetch(`/api/data/${dataPath}?${qp.toString()}`);
      if (!res.ok) throw new Error(`[${res.status}] ${dataPath}`);
      return res.json();
    },
    staleTime,
    retry: 1, // one retry on transient failure
    retryDelay: 1000,
    enabled,
  });
}
```

### Prefetch for Tab Switching

```typescript
export function prefetchChart(
  queryClient: ReturnType<typeof useQueryClient>,
  sessionId: string, dataPath: string, params?: Record<string, unknown>
) {
  const qp = new URLSearchParams({ sessionId });
  for (const [k, v] of Object.entries(params ?? {})) qp.set(k, String(v));
  queryClient.prefetchQuery({
    queryKey: ["chart", dataPath, sessionId, params],
    queryFn: () => fetch(`/api/data/${dataPath}?${qp.toString()}`).then(r => r.json()),
    staleTime: 5 * 60 * 1000,
  });
}
```

Wire into the tab navigation to prefetch adjacent tabs on click:

```typescript
const handleTabSwitch = useCallback((tabId: string) => {
  setActiveTab(tabId);
  // Prefetch adjacent tabs for instant rendering
  const idx = TABS.findIndex((t) => t.id === tabId);
  [TABS[idx - 1], TABS[idx + 1]]
    .filter(Boolean)
    .forEach((tab) => {
      const cards = getCardsForTab(tab.id, filterParams);
      cards.slice(0, 3).forEach((card) =>
        prefetchChart(queryClient, sessionId, card.path, card.extra)
      );
    });
}, [sessionId, filterParams, queryClient]);
```

## Tremor Chart Component Mapping

The chart data model from the Python processors outputs structured dicts that need to be mapped to Tremor's component API:

### Data Shape Mapping

| Tremor Component | Our Chart Type | Data Requirements | Notes |
|-----------------|----------------|-------------------|-------|
| `AreaChart` | `stacked_area` | `{date, series1, series2...}` | Convert `x_axis.values` + `series[].values` to category data array |
| `BarChart` | `bar`, `stacked_bar`, `grouped_bar` | `{category, series1, series2...}` | `categories[]` for grouped, `data` for simple |
| `LineChart` | `line`, `multi_line`, `dual_line` | `{date, series1, series2...}` | Max 6 categories recommended |
| `BarList` | `horizontal_bar` | `[{name, value}]` | Sort descending, max 25 items |
| `DonutChart` | (fallback for bar) | `[{name, value}]` | Use when BarList gets too many items |

### Category Data Converter

```typescript
// Converts processor format to Tremor's flat row format
function toCategoryData(
  xVals: string[],
  series: Array<{ name: string; values: number[] }>
): Record<string, string | number>[] {
  return xVals.map((label, i) => {
    const row: Record<string, string | number> = { date: label };
    for (const s of series) row[s.name] = s.values[i] ?? 0;
    return row;
  });
}
```

### Tremor Component Usage

```tsx
import { AreaChart, BarChart, LineChart, BarList, DonutChart } from "@tremor/react";

// Stacked area chart
<AreaChart
  className="h-64"
  data={chartData}
  index="date"
  categories={categories}  // series names
  colors={["indigo", "cyan", "amber", "rose"]}
  valueFormatter={(v) => v.toFixed(2)}
  yAxisWidth={50}
  showLegend={categories.length > 1}
  showAnimation={false}
/>

// Horizontal bar list
<BarList
  data={items.map(i => ({ name: i.label, value: i.count }))}
  className="h-64"
  valueFormatter={(v) => v.toFixed(2)}
/>
```

### Limitations — Tremor cannot render these, use fallback table renderers:

- Heatmaps (z_values matrix)
- Histograms (raw value arrays)
- Gantt timelines (task start/end data)
- Box plots (quartile statistics)

## CSV Export Pattern

Leverage the bridge's existing `export.csv.*` actions:

```typescript
// app/api/export/[dataset]/route.ts
export async function GET(request: NextRequest, { params }: { params: Promise<{ dataset: string }> }) {
  const { dataset } = await params;
  const sessionId = request.nextUrl.searchParams.get("sessionId");

  const stdout = execFileSync("python3",
    [BRIDGE, "--action", `export.csv.${dataset}`, "--session", sessionId, "--params", "{}"],
    { encoding: "utf-8", timeout: 60000 });
  const result = JSON.parse(stdout.trim());

  return new NextResponse(result.csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="beacon_${dataset}_${sessionId.slice(0, 8)}.csv"`,
    },
  });
}
```

Add trigger buttons in the dashboard header:

```tsx
<button onClick={() => window.open(`/api/export/allocation?sessionId=${sid}`, "_blank")}>
  CSV (Allocation)
</button>
```

### Future Export Candidates

- **Excel workbook** — Bridge already has `export.excel` action. Serve as downloadable .xlsx.
- **Immersive HTML** — Generate self-contained HTML with embedded chart data for offline viewing. Bridge would need a Jinja template + data serialization step.

## Chart Registry Pattern
Replace N `load*Chart()` functions with a single registry:

```typescript
// lib/chart-registry.ts
const chartRegistry = {
  'allocation-portfolio': { processor: 'portfolio', method: 'getWeeklyFte' },
  'risk-heatmap': { processor: 'risk', method: 'getDepartmentHeatmap' },
  // ... 30+ charts
} as const

export type ChartId = keyof typeof chartRegistry
```

### Processor Split Pattern
Split monolithic processor into focused classes:

```
packages/data/src/processors/
  portfolio-processor.ts    # Portfolio, dept, project views
  risk-processor.ts         # Heatmaps, over-allocation, distribution
  workforce-processor.ts    # Employee types, headcount, unassigned
  project-processor.ts      # Staffing curves, team sizes, matrix
  people-processor.ts       # Timelines, workload, busiest
  trend-processor.ts        # Rolling averages, WoW, utilization
```

Each processor <300 lines, single responsibility.

### API Consolidation Pattern
Replace 51 endpoints with ~15 tRPC procedures:

```typescript
// server/routers/charts.ts
export const chartRouter = router({
  get: publicProcedure
    .input(z.object({ chartId: z.string(), filters: filterSchema }))
    .query(({ input }) => {
      const { processor, method } = chartRegistry[input.chartId]
      return processors[processor][method](input.filters)
    }),
  
  upload: publicProcedure
    .input(z.object({ type: z.enum(['allocation', 'workstream']), file: z.any() }))
    .mutation(({ input }) => uploadHandler.process(input)),
    
  export: publicProcedure
    .input(z.object({ format: z.enum(['csv', 'excel', 'html']), filters: filterSchema }))
    .mutation(({ input }) => exportHandler.generate(input)),
})
```

## Component Architecture

```
components/
  layout/
    dashboard-shell.tsx      # Tabs, filter bar, container
    header.tsx               # Logo, session indicator
    filter-bar.tsx           # Date range, top-N, department picker
  charts/
    chart-card.tsx           # Reusable chart container with export button
    chart-registry.tsx       # Maps chartId to component
  upload/
    upload-zone.tsx          # Drag-and-drop with progress
  data-table/
    data-table.tsx           # TanStack Table wrapper
```

## Migration Checklist

- [ ] Scaffold Turborepo with Next.js 15 + React 18
- [ ] Install Tremor with `--legacy-peer-deps`
- [ ] Configure Tailwind v3 with `.cjs` PostCSS config
- [ ] Set up tRPC with chart registry router
- [ ] Split monolithic processor into 6+ focused classes
- [ ] Build DashboardShell with 11 tabs
- [ ] Implement chart components (Tremor standard, Plotly fallback)
- [ ] Add TanStack Query for server state
- [ ] Re-implement exports (CSV, Excel, HTML)
- [ ] Add Playwright E2E tests
- [ ] Validate data accuracy against legacy app

## Pitfalls

1. **Don't use React 19 with Tremor v3** — peer dependency conflict, charts won't render
2. **Don't use Tailwind v4 with Next.js font system** — `@import "tailwindcss"` breaks `next/font`
3. **Don't install workspace deps from app directory** — npm hoists to root, use `npm install -w <workspace>` from root
4. **Don't try to migrate all charts at once** — start with 3-4 core charts, validate, then expand
5. **Don't add new features during migration** — strict 1:1 parity until cutover
6. **tRPC v11 transformer location** — `transformer` moved from `createClient()` to `httpBatchLink()` options. Putting it at client level throws: `TypeError: The transformer property has moved to httpLink/httpBatchLink/wsLink`
7. **Next.js dev server auto-install types** — `next dev` auto-installs `@types/react` and `@types/node` via pnpm. In Turborepo with `@repo/*` workspace packages, this fails with `ERR_PNPM_FETCH_404` because pnpm tries to resolve `@repo/eslint-config` from npm registry. Fix: pre-install types manually or disable auto-install with `NEXT_PRIVATE_SKIP_TYPECHECK=1`
8. **Build passing ≠ dev working** — Production build and dev server use different compilation paths. Always verify both. If build passes but dev fails, check: (a) PostCSS/Tailwind local node_modules, (b) `.next` cache corruption, (c) auto-install type dependencies
9. **Dev server process management** — `next dev` is long-lived. Use detached spawn with log files for health monitoring, not foreground terminal sessions that get killed on timeout.
10. **Stale lockfile after scaffold** — `create-turbo` generates a `package-lock.json` with React 19 resolutions, but Tremor requires React 18. Running `npm install` on the scaffold won't re-resolve if the lockfile is already present — you must `rm package-lock.json && npm install` to regenerate it. Symptom in Railway CI: `npm error code EUSAGE` / `npm ci` fails because lockfile's `@types/react@19.x` doesn't satisfy package.json's `@types/react@18.x`.
11. **Railway TOML format for nixpacks** — Railway's `railway.toml` uses standard TOML, NOT JSON. Do not use arrays of objects for `[nixpacks]` plan config: `plan = [{ "providers": ["node", "python"] }]` is invalid TOML. Instead, set `NIXPACKS_META=python` as an env var, and install Python deps in the `startCommand`:
    ```toml
    [service]
    startCommand = "pip install -r packages/data/requirements.txt -q && pip install -e packages/data/ -q && cd apps/web && npx next start --port $PORT"
    ```
    Error signature: `parse failure, failed to parse railway.toml: toml: line 7 (last key "nixpacks.plan"): expected '.' or '=', but got ':' instead`
12. **Railway health check timing** — If `startCommand` installs Python deps first (pip install), the build + install can take 60-90s before the Next.js server is ready. Make sure `healthcheckTimeout` in `railway.toml` is ≥300s to avoid premature restart loops.
13. **Railway GitHub auto-deploy triggers** — Once a service is linked to a GitHub repo, every push to the tracked branch triggers a new build. There's no way to disable this per-push in the free tier — push knowing a build will start.

## Reference Files

- `references/nextjs15-react18-tremor-setup.md` — Step-by-step dependency resolution
- `references/trpc-v11-setup.md` — tRPC v11 + Next.js App Router + superjson configuration
- `references/python-subprocess-bridge.md` — Full Python subprocess bridge architecture and rationale
- `references/polars-api-pitfalls.md` — Polars v1.40+ API traps when porting from Pandas
- `references/chart-registry-pattern.ts` — Full chart registry implementation
- `references/processor-split-example.py` — Before/after processor split
- `references/dev-server-troubleshooting.md` — Next.js dev server failure modes and fixes
- `references/rest-chart-data-api.md` — REST data API pattern as tRPC fallback for chart data
- `references/multipart-upload-bridge-pattern.md` — Excel file upload through Next.js to Python bridge
- `references/tanstack-query-hook.md` — TanStack Query hook for chart data fetching with caching and prefetch
- `references/tremor-chart-mapping.md` — Tremor component mapping for processor chart data shapes
