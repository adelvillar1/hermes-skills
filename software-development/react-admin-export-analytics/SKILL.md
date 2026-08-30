---
name: react-admin-export-analytics
description: Use when adding CSV export or charts to a React admin UI.
---

# React Admin Console — Export & Analytics

Class-level patterns for bolting **client-side CSV export** and **recharts analytics** onto an
existing React + shadcn/ui + Tailwind admin console (Vite or Next.js). These features recur across
admin surfaces (Members/Orders/Deliveries exports, Overview dashboards); reuse the drop-in helper
and the theming recipe instead of re-deriving them.

## When to use
- Adding an "Export CSV" button to a table/list tab.
- Adding dashboard charts (sales trend, growth) or summary stat cards to an Overview page.
- Any client-side download or recharts chart inside a shadcn/Tailwind themed app.

## 1. Client-side CSV export

Use the drop-in helper in `templates/csv.ts` — copy it to `src/lib/csv.ts` verbatim. It provides:
- `toCsv(headers, rows)` — RFC 4180 escaping (quotes fields containing `,` `"` `\n` `\r`, doubles
  embedded quotes), CRLF line endings.
- `downloadCsv(filename, csv)` — prepends a UTF-8 BOM (`\uFEFF`) so Excel opens accented/unicode
  text correctly, builds a Blob, triggers a click, revokes the object URL.

Wire an Export button next to the existing table controls:

```tsx
<Button variant="outline" onClick={() => {
  const csv = toCsv(
    ['name', 'phone', 'active', 'joined_at'],
    filtered.map(m => [m.name, m.phone ?? '', m.active ? 'yes' : 'no', m.joinedAt.slice(0, 10)]),
  )
  downloadCsv('members.csv', csv)
}}>
  <Download className="mr-2 h-4 w-4" /> Export
</Button>
```

### Pitfalls
- **Export the FILTERED rows, not the raw list.** Users expect Export to match what's on screen.
  Pass the same `filtered` array the table renders; honor any active search/status/event filter.
- **Coerce everything to strings.** `toCsv` takes `string[][]`. Numbers via `String(n)`,
  cents→dollars via `(cents / 100).toFixed(2)`, booleans to `'yes'/'no'`, dates via
  `.slice(0, 10)` for `YYYY-MM-DD`, nullables via `?? ''`.
- **Disable the button when there's nothing to export** (`disabled={!rows || rows.length === 0}`)
  for month-scoped lists that may be empty.
- **Name the file after the scope** (`deliveries-${month}.csv`) when the data is period-bound.
- The BOM is intentional — do not strip it; Excel needs it for UTF-8.

## 2. recharts + shadcn/Tailwind theming

recharts is usually already a dep in these consoles. The trap is hardcoding colors that clash with
the theme. Use the app's CSS variables via `hsl(var(--*))`:

```tsx
<ResponsiveContainer width="100%" height={200}>
  <BarChart data={salesByMonth}>
    <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-muted-foreground/20" />
    <XAxis dataKey="month" tick={{ fill: 'currentColor', fontSize: 12 }} className="text-muted-foreground" />
    <YAxis tick={{ fill: 'currentColor', fontSize: 12 }} className="text-muted-foreground" tickFormatter={v => `$${v}`} />
    <RechartsTooltip
      formatter={(value: number) => [`$${value.toFixed(2)}`, 'Sales']}
      contentStyle={{
        backgroundColor: 'hsl(var(--card))',
        border: '1px solid hsl(var(--border))',
        borderRadius: '8px',
        color: 'hsl(var(--foreground))',
      }}
    />
    <Bar dataKey="dollars" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
  </BarChart>
</ResponsiveContainer>
```

Rules:
- Series fills/strokes: `hsl(var(--primary))` (or `--chart-1..5` if the theme defines them).
- Axis ticks: `tick={{ fill: 'currentColor', fontSize: 12 }}` + `className="text-muted-foreground"`.
- Grid: `stroke="currentColor"` + `className="text-muted-foreground/20"`.
- Tooltip: style `contentStyle` with `hsl(var(--card))` / `hsl(var(--border))` /
  `hsl(var(--foreground))` so it matches dark/light theme. Import as `Tooltip as RechartsTooltip`
  to avoid clashing with shadcn's `Tooltip`.
- Always wrap charts in `<ResponsiveContainer width="100%" height={N}>` — recharts needs an
  explicit-sized parent.
- For counts use `allowDecimals={false}` on the YAxis; for money add a `tickFormatter`.
- `LineChart`/`Line type="monotone"` for cumulative/growth series; `BarChart`/`Bar` for per-period totals.

## 3. Overview analytics computations

Compute last-N-months buckets with `date-fns` (`subMonths`, `format`), then reduce the
already-loaded lists client-side — no new API call needed when the Overview already fetches the
collections:

```ts
const months = Array.from({ length: 6 }, (_, i) => {
  const d = subMonths(new Date(), 5 - i)
  return { key: format(d, 'yyyy-MM'), label: format(d, 'MMM') }
})
const salesByMonth = months.map(({ key, label }) => ({
  month: label,
  dollars: orders.filter(o => o.paid && o.createdAt.slice(0, 7) === key)
                 .reduce((s, o) => s + o.totalCents, 0) / 100,
}))
```

- Month bucketing on ISO timestamps: compare `createdAt.slice(0, 7) === 'YYYY-MM'`.
- Cumulative growth: `members.filter(m => m.joinedAt.slice(0, 7) <= key).length`.
- Add small stat cards (this-month vs last-month with ↑/↓ delta, status counts) using the existing
  `Card`/`CardContent` + `fmtMoney` helpers rather than inventing new markup.

## Verification
Run the project build (`npm run build` / `tsc -b && vite build`). Unused-import TS errors are the
common failure when adding recharts/date-fns imports incrementally — add all imports up front.
