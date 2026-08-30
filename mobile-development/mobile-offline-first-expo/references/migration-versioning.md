# SQLite Migration Versioning on Mobile Devices

## The Pitfall

When you modify an existing migration (e.g., changing what Migration 4 creates), devices that already ran the original Migration 4 will **never run the updated version** because `user_version` is already set to 4. The migration runner sees `current_version >= migration_version` and skips.

## Real Example (2026-06-17)

1. Shipped Migration 4: `ALTER TABLE schedule ADD COLUMN signal_bars` + `CREATE TABLE app_kv`
2. User synced, device ran Migration 4, `user_version = 4`
3. Changed Migration 4 to create `signal_history` table instead of `app_kv`
4. Rebuilt and deployed — device has `user_version = 4`, so Migration 4 never runs again
5. `signal_history` table doesn't exist → `getSignalStats()` returns null → no hist accuracy

## Fix

**Never modify a migration that has already shipped.** Always add a new migration number:

```
MIGRATION_004_SIGNAL_BARS (original, unchanged)
MIGRATION_005_SIGNAL_HISTORY (new — creates signal_history table)
```

Update `MIGRATIONS` record and bump the test assertions to expect the new version number.

## Testing Checklist

- [ ] Test `runs migrations when user_version is 0` — asserts all `PRAGMA user_version = N` calls up to latest
- [ ] Test `skips migrations when already current` — sets `user_version` to the latest migration number
- [ ] New migration uses `CREATE TABLE IF NOT EXISTS` for idempotency

## Pattern for Device-Side Aggregation

Instead of server computing aggregated stats and sending pre-computed JSON:

1. Server sends per-game classification rows: `{sport, signal_type, model_correct, is_draw}`
2. Device stores in a table: `signal_history(sport TEXT, signal_type TEXT, model_correct INTEGER, is_draw INTEGER)`
3. Device aggregates with SQL:

```sql
SELECT sport, signal_type,
  COUNT(*) as total,
  SUM(CASE WHEN is_draw = 0 THEN 1 ELSE 0 END) as dir_count,
  SUM(model_correct) as correct
FROM signal_history
GROUP BY sport, signal_type
```

4. UI reads the aggregated result from device SQLite — no server roundtrip needed.

This matches the offline-first pattern: raw data in SQLite, computation on device.