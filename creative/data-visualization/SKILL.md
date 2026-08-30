---
name: data-visualization
description: Design clear, accessible, and actionable data visualizations.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Data, Charts, Dashboards, Accessibility]
---

# Data Visualization

Design clear, accessible, and impactful charts, dashboards, and infographics.

## When to use

- Build dashboards or analytics interfaces.
- Show trends, relationships, distributions, or comparisons.
- Present geographic or part-to-whole data.

## Core principles

- Data-first: understand the data structure before choosing a visual.
- Visual encoding: position is most accurate, then length, then angle/area, then color.
- Accessibility: never rely on color alone; add labels, tooltips, text alternatives, and keyboard navigation.

## Choose a chart

- Comparison: bar or column chart.
- Trend over time: line or area chart.
- Part-to-whole: stacked bar, treemap, or pie (sparingly).
- Distribution: histogram or box plot.
- Relationship: scatter or bubble chart.
- Geographic: map or choropleth.

## Match question to chart

- "How much?" → Bar.
- "Over time?" → Line.
- "Parts of a whole?" → Stacked bar / treemap.
- "How related?" → Scatter / bubble.
- "Where?" → Map.
- "How distributed?" → Histogram / box plot.

## Tools

- Custom: D3.js.
- Easier React/Vanilla: Chart.js, Recharts, Victory.
- BI: Tableau, Power BI.
- Infographics: Figma, Illustrator.

## Implementation pattern (D3.js)

Create an `svg` with `viewBox`, bind data with `.data(data).join("rect")`, and use scales like `d3.scaleLinear`.

## Design guidelines

- Color: use colorbrewer2.org, limit categories to 5-7, use sequential scales for continuous data.
- Typography: 12-14px labels, 16-18px titles, tabular figures, 4.5:1 minimum contrast.
- Interactions: hover for details, click to filter, 300-500ms transitions, provide undo/reset.
- Responsive: use `viewBox`, adjust ticks at breakpoints, ensure 44px touch targets, plan mobile layouts.

## Best practices

- Remove chart junk.
- Keep scales consistent.
- Label clearly and provide context.
- Support exploration with tooltips, filtering, drill-down, and legends.
- Verify accessibility: contrast, color independence, text labels, alt text.
