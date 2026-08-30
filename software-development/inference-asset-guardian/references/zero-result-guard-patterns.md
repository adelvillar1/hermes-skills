# Zero-Result Guard Implementation Patterns

This reference contains concrete TypeScript implementation patterns for the zero-result guards described in the main SKILL.md (sections 6, 12, 14a).

## Pattern 1: Count guard at pipeline entry

```typescript
const corridors = await fetchCorridors();
if (corridors.length === 0) {
  // If delta said there are corridors to process but we got 0, that's a bug
  const pgCount = await prisma.route_corridors.count();
  if (deltaIds.length > 0) {
    throw new Error(
      `Delta found ${deltaIds.length} corridors needing profiles, but FalkorDB returned 0.\n` +
      `PG has ${pgCount} corridors. FalkorDB may be out of sync.\n` +
      `Run the falkordb_sync pipeline job first, then retry.`
    );
  }
  // Legitimate empty state — nothing to do
  console.log('No corridors need profiles. Exiting.');
  process.exit(0);
}
```

## Pattern 2: Baseline comparison

```typescript
const resultCount = await processData();
const baseline = await getRecentBaseline(); // e.g., last run's count

if (resultCount === 0 && baseline > 100) {
  throw new Error(
    `Expected ~${baseline} results based on last run, got 0. Likely upstream failure.`
  );
}
```

## Pattern 3: Minimum threshold

```typescript
const ports = await fetchPorts();
// We always have at least 1,000 active ports. Less is a data problem.
if (ports.length < 1000) {
  throw new Error(
    `Only ${ports.length} ports returned — expected at least 1,000. Possible DB connection issue.`
  );
}
```

## Pattern 4: Cross-source validation

```typescript
const pgCount = await prisma.route_corridors.count();
const falkorCount = await falkorDB.getNodeCount('RouteCorridor');
const drift = Math.abs(pgCount - falkorCount) / pgCount;

if (drift > 0.05) { // more than 5% mismatch
  console.error(
    `⚠️ Drift detected: PG has ${pgCount} corridors, FalkorDB has ${falkorCount}. ` +
    `Run falkordb_sync before processing.`
  );
  process.exit(1);
}
```

## Pattern 5: Dep-hash NULL detection after topology rebuild

When the topology (corridors, families, clans) is rebuilt, `dep_hashes.full_hash` gets set to NULL for all existing corridors. The delta detection logic (`getChangedCorridorIds`) compares `full_hash IS DISTINCT FROM MD5(...)` — NULL is always distinct, so ALL corridors get flagged as changed, triggering a full recomputation worth $144K+.

```typescript
// After any topology rebuild, re-seed dep hashes BEFORE running insight jobs
await prisma.$executeRaw`
  UPDATE corridor_dep_hashes dh
  SET full_hash = MD5(COALESCE(CAST(rc.signature AS TEXT), '') || '|' || /* all columns */)
  FROM route_corridors rc
  WHERE dh.corridor_id = rc.id;
`;
// THEN verify no NULL hashes remain
const nullHashes = await prisma.$queryRaw`
  SELECT COUNT(*) as count FROM corridor_dep_hashes WHERE full_hash IS NULL
`;
if (nullHashes[0].count > 0) {
  throw new Error(`${nullHashes[0].count} corridors have NULL dep hashes. Re-seed before running insights.`);
}
```

## Pattern 6: Prisma model name mismatch (silent undefined)

When a Prisma query uses a model name that doesn't match the schema, it doesn't throw a TypeScript error or a runtime error — it returns `undefined`.

```typescript
// ❌ Silent undefined — no error, just wrong results
const count = await prisma.routeCorridor.count(); // undefined.count → crash... or 0 if coerced
const corridors = await prisma.routeCorridor.findMany(); // undefined.findMany → crash

// ✅ Correct — matches schema @map convention
const count = await prisma.route_corridors.count();
const corridors = await prisma.route_corridors.findMany();

// Guard: verify model exists at runtime
const modelNames = Object.keys(prisma).filter(k => !k.startsWith('_'));
if (!modelNames.includes('route_corridors')) {
  throw new Error(`Prisma model 'route_corridors' not found. Available: ${modelNames.join(', ')}`);
}
```