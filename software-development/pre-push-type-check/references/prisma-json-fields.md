# Prisma JSON Field Handling

## Problem

Prisma `Json?` columns (like `avgWaveHeight`, `monthlyShips`, `exclusivePorts`) return parsed JSON values, not scalars. Attempting to call `.toFixed()`, `.map()`, or arithmetic operators on them fails at runtime even though TypeScript may not catch it (because the Prisma type is `JsonValue` which is `any`-like).

## Common pattern

`avgWaveHeight` on `route_corridors` is `Json?` — actual data is a monthly array like `[1.2, 1.5, 0.8, 1.1, 0.9, ...]`. NOT a single number.

## Fix: extract scalar from JSON

```tsx
// Router side — extract before returning
const extractMax = (val: any): number => {
  if (val == null) return 0;
  if (Array.isArray(val)) return Math.max(0, ...(val as number[]).map(Number));
  return Number(val) || 0;
};

// Component side — compute average
const wh = corridor.avgWaveHeight;
if (!wh) return null;
const val = Array.isArray(wh) 
  ? (wh as number[]).reduce((s, v) => s + v, 0) / wh.length 
  : Number(wh);
if (isNaN(val)) return null;
```

## Other Json fields on route_corridors

- `monthlyShips` — JSON array of ships per month
- `monthlyLines` — JSON array of lines per month  
- `monthlyCapacity` — JSON array of capacity per month
- `exclusivePorts` — JSON array of port names
- `tierDistribution` — JSON object

## Best practice

**Extract scalar values in the tRPC router**, not in the component. Components should receive plain `number`, `string`, `string[]` — never `JsonValue`. This keeps the runtime error surface on the server side where it's caught during development, not in production.
