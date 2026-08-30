# Tremor Chart Component Mapping

## Processor Output → Tremor Input

The Python processors output chart dicts with this generic structure:

```json
{
  "chart_type": "stacked_area",
  "title": "...",
  "x_axis": {"label": "Week", "values": ["2026-01-05", "2026-01-12", ...]},
  "y_axis": {"label": "FTE"},
  "series": [
    {"name": "Project Alpha", "values": [1.0, 0.8, ...]},
    {"name": "Project Beta", "values": [0.5, 0.6, ...]}
  ],
  "metadata": {...}
}
```

Tremor needs flat row arrays:

```typescript
[
  { date: "2026-01-05", "Project Alpha": 1.0, "Project Beta": 0.5 },
  { date: "2026-01-12", "Project Alpha": 0.8, "Project Beta": 0.6 },
]
```

## Component Selection by chart_type

| chart_type | Tremor Component | Fallback | Notes |
|-----------|-----------------|----------|-------|
| `stacked_area` | `AreaChart` | SeriesTable | Best for portfolio FTE |
| `multi_line` | `LineChart` | SeriesTable | Max 6 series recommended |
| `dual_line` | `LineChart` (both series as categories) | SeriesTable | Treat as 2-series line |
| `line` | `LineChart` | SeriesTable | Single series line |
| `bar` | `BarChart` + layout="vertical" | BarTable | Vertical bars |
| `horizontal_bar` | `BarList` | BarTable | Best for rankings |
| `grouped_bar` | `BarChart` + layout="vertical" | BarTable | Uses categories[] + series[] |
| `stacked_bar` | `TremorBarChart` with categories | BarTable | Same as grouped internally |
| `heatmap` | (none) | Custom heatmap table | No Tremor equivalent |
| `histogram` | (none) | Custom histogram bars | No Tremor equivalent |
| `gantt` | (none) | Custom task table | No Tremor equivalent |
| `box_plot` | (none) | Custom stats table | No Tremor equivalent |
| `table` | (none) | Custom data table | No Tremor equivalent |

## Color Palette (10 colors)

```typescript
const colors = ["indigo", "cyan", "amber", "rose", "emerald", "violet", "orange", "teal", "pink", "lime"];
```

Tremor's color system uses named tailwind colors. For >10 categories, colors cycle.

## Animation

Set `showAnimation={false}` in all Tremor components. Data-heavy dashboards stutter with default animations.

## Example: ChartCard render dispatch

```tsx
switch (chartType) {
  case "stacked_area": return <TremorAreaChartView data={d} />;
  case "bar":
  case "horizontal_bar":
  case "grouped_bar":
  case "stacked_bar": return <TremorBarChartView data={d} />;
  case "multi_line":
  case "dual_line":
  case "line": return <TremorLineChartView data={d} />;
  case "heatmap": return <HeatmapFallback data={d} />;
  case "table": return <TableFallback data={d} />;
  case "gantt": return <GanttFallback data={d} />;
  case "box_plot": return <BoxPlotFallback data={d} />;
  case "histogram": return <HistogramFallback data={d} />;
  case "metrics":
  case "summary": return <MetricsView data={d} />;
}
```
