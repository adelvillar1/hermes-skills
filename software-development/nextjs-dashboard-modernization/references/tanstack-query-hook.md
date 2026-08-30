# TanStack Query Integration for Chart Data

## Hook Structure

```
useChartData({ sessionId, dataPath, params }) → { data, isLoading, isError, error, refetch }
```

## Query Key Convention

```
["chart", dataPath, sessionId, serializedParams]
```

Example: `["chart", "allocation/portfolio", "abc-123", {topN: 5}]`

The `params` object uses referential identity — if you pass a new object each render, use `JSON.stringify(params)` in the dependency array or memoize the params object. The hook's `queryKey` includes the full params object, so TanStack Query's deep comparison handles changes.

## Stale Time Default

5 minutes (300,000ms). Tune lower for dashboards that need near-real-time data, higher for static historical data.

## Prefetch on Tab Hover

Optional enhancement — prefetch chart data when user hovers over a tab, not just on click:

```typescript
onMouseEnter={() => prefetchChart(queryClient, sessionId, path, params)}
```

## Error Recovery

The hook automatically retries once after 1 second. The ChartCard displays a red error banner with the error message. The user can also trigger a manual refetch via a retry button on the error state.

## Cache Invalidation

When the user uploads a new file, invalidate all chart caches for that session:

```typescript
queryClient.invalidateQueries({ queryKey: ["chart", "allocation", sessionId] });
```

Or more aggressively:

```typescript
queryClient.invalidateQueries({ queryKey: ["chart"] });  // invalidates ALL charts
```
