# REST Chart Data API Pattern

When tRPC's GET input format with superjson transformer causes 400/500 errors (common with tRPC v11 + Next.js 15 + superjson), an alternative pattern is to serve chart data through direct REST API routes that call the Python bridge directly.

## When to Use This Pattern

- tRPC GET queries fail with "Invalid input" or "Expecting property name" for complex input objects
- The tRPC v11 + superjson GET input format is fighting you
- You want simpler curl/fetch-able endpoints for debugging

## Architecture

```
ChartCard (React) ──► /api/data/:dataset/:chart?sessionId=xxx&topN=5 ──► bridge.py ──► Python processor
```

## Implementation

### Route definition

```typescript
// apps/web/app/api/data/[dataset]/[chart]/route.ts
import { NextRequest, NextResponse } from "next/server";
import { execFileSync } from "child_process";

const BRIDGE = path.resolve(process.cwd(), "..", "packages", "data", "bridge.py");

// Route map: maps URL path segments to bridge actions
const CHART_ROUTES: Record<string, Record<string, string>> = {
  allocation: {
    portfolio: "allocation.portfolio",
    byDepartment: "allocation.by-department",
    heatmap: "allocation.heatmap",
    distribution: "allocation.distribution",
    riskSummary: "allocation.risk-summary",
    // ... etc
  },
  executive: {
    summary: "executive.summary",
    deptHealth: "executive.dept-health",
  },
  // ... etc for all datasets
};

export async function GET(request: NextRequest, { params }: { params: Promise<{ dataset: string; chart: string }> }) {
  const { dataset, chart } = await params;
  const action = CHART_ROUTES[dataset]?.[chart];
  if (!action) return NextResponse.json({ error: "Unknown chart" }, { status: 404 });

  const sessionId = request.nextUrl.searchParams.get("sessionId");
  if (!sessionId) return NextResponse.json({ error: "sessionId required" }, { status: 400 });

  // Build query params with camelCase→snake_case mapping
  const queryParams: Record<string, unknown> = {};
  const PARAM_MAP = { topN: "top_n", maxWeeks: "max_weeks", startDate: "start_date", /* ... */ };
  for (const [key, value] of request.nextUrl.searchParams.entries()) {
    if (key === "sessionId") continue;
    const mappedKey = PARAM_MAP[key] || key;
    // Auto-convert numbers and booleans
    if (!isNaN(Number(value)) && value !== "") queryParams[mappedKey] = Number(value);
    else if (value === "true" || value === "false") queryParams[mappedKey] = value === "true";
    else queryParams[mappedKey] = value;
  }

  const stdout = execFileSync("python3", [BRIDGE, "--action", action, "--session", sessionId, "--params", JSON.stringify(queryParams)],
    { encoding: "utf-8", timeout: 30000 });
  const result = JSON.parse(stdout.trim());
  if (!result.success) return NextResponse.json({ error: result.error }, { status: 500 });
  return NextResponse.json(result.data);
}
```

### Frontend consumption

```tsx
// ChartCard fetches directly from REST API
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  const qp = new URLSearchParams({ sessionId });
  qp.set("topN", "10");
  qp.set("startDate", "2026-01-01");
  
  fetch(`/api/data/allocation/portfolio?${qp.toString()}`)
    .then(r => r.json())
    .then(d => { setData(d); setLoading(false); })
    .catch(e => { setError(e.message); setLoading(false); });
}, [sessionId]);
```

## Advantages vs tRPC

| | REST Data API | tRPC |
|---|---|---|
| URL clarity | `GET /api/data/allocation/portfolio?sessionId=xxx` | Opaque `?input=%7B%22json%22%3A...%7D` |
| Debugability | Works in curl/browser directly | Must encode superjson payload |
| Error messages | Raw JSON from bridge | Wrapped in tRPC error format |
| Type safety | Manual (no Zod) | Automatic |
| Method support | GET only | GET + POST + streaming |
| Batch queries | No | Yes |

**Tradeoff**: You lose tRPC's automatic type inference. Use REST when you value debuggability and simplicity over full type safety for chart data fetching.

## When to Combine Both

Keep tRPC for:
- Mutations (upload, delete session)
- Simple queries (health check)
- Server-side rendering where type inference matters

Use REST for:
- All chart data fetching (GET requests from browser)
- Debugging/development
- cURL-based integration testing
