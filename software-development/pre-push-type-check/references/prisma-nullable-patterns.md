# Prisma Nullable Field Patterns

## Root cause of most build failures

Prisma marks optional fields as `String?` / `Int?` → the generated Prisma Client types are `string | null` / `number | null`. Subagents writing custom TypeScript interfaces nearly always declare these as `string` / `number` (non-nullable), which causes `Type 'string | null' is not assignable to type 'string'` errors.

## Common nullable fields by table

### cruise_line_insights
- archetype: `String?` → `string | null`
- seasonMode: `String?` → `string | null`  (but Prisma field is actually non-null)
- clienteleFlex: `String?` → `string | null`
- personaId: `String?` → `string | null`

### cruise_lines
- tier: `String` (NON-nullable — safe)
- description, logoUrl, website: all nullable

### route_corridors
- avgDailyRate: `Float?` → `number | null`
- avgDuration: `Float?` → `number | null`
- peakMonth: `Int?` → `number | null`
- summerTemp, winterTemp, springTemp, fallTemp: `Float?` → `number | null`
- summerRainDays, winterRainDays, etc: `Float?` → `number | null`
- summerCrowding, winterCrowding: `Float?` → `number | null` (springCrowding/fallCrowding DO NOT EXIST)
- avgWaveHeight: `Json?` → not a scalar (see prisma-json-fields.md)
- clan: `String?` → `string | null`

### cruise_line_inclusions
- beverages, gratuities, wifi, specialtyDining, excursions: `String` (non-nullable) but values are STRING ENUMS: "included" / "partial" / "not_included"
- butlerService, minibarIncluded, laundry: `Boolean` (non-nullable)

### corridor_insights
- corridorId, insightType, season: non-nullable
- structured columns (riskCategories, severity, advisorAction, disqualifiers): DO NOT EXIST on corridor_insights model — only on aggregated models like route_clans

## Fix strategies (preferred order)

1. **Remove custom interfaces entirely** — let TypeScript infer from tRPC's return type:
   ```
   // BAD: custom interface that will drift
   interface MyRow { archetype: string; ... }
   
   // GOOD: inference
   const { data } = trpc.analytics.getData.useQuery();
   data.map(d => d.archetype) // TS infers string | null correctly
   ```

2. **Use `type Row = typeof data[number]`** — derives from actual hook return type

3. **Use `any` in function parameters** for helper functions that receive tRPC-returned data

4. **Match nullable exactly** as a last resort if custom interface is unavoidable

## Null guard patterns

```tsx
// Indexing with nullable value
const color = archetype ? COLORS[archetype] : DEFAULT;

// Filtering on nullable field
data.filter(d => d.archetype != null && d.archetype === selected);

// Displaying nullable field
{d.archetype ?? 'Unknown'}
```
