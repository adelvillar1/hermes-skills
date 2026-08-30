# Inspect the App's SQLite Database on the iOS Simulator

When an offline-first Expo app has sync or migration issues, inspect the device's SQLite database directly from the Mac's terminal. This bypasses the app's UI and reveals the exact schema state, row counts, and column definitions.

## Find the database file

The simulator stores app data in a container whose UUID changes on each install. Find it dynamically:

```bash
DEVICE_ID=E621FA7C-581F-4395-B81D-9ADC4E1AA70E
BUNDLE_ID=com.eloscenariolab.app

CONTAINER=$(xcrun simctl get_app_container "$DEVICE_ID" "$BUNDLE_ID" data)
DB="$CONTAINER/Documents/SQLite/elo_offline.db"
```

If `get_app_container` returns empty (app not installed or path varies), search:

```bash
find ~/Library/Developer/CoreSimulator/Devices/$DEVICE_ID/data/Containers/Data/Application \
  -name "elo_offline.db" 2>/dev/null | head -1
```

## Diagnostic queries

### Schema state

```bash
# Migration version
sqlite3 "$DB" "PRAGMA user_version;"

# Table list
sqlite3 "$DB" ".tables"

# Column definitions (verify migration 2 columns exist)
sqlite3 "$DB" "PRAGMA table_info(schedule);"

# Check specific table exists
sqlite3 "$DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='team_details';"
```

### Row counts (verify sync actually wrote data)

```bash
sqlite3 "$DB" "SELECT 'schedule', COUNT(*) FROM schedule
               UNION ALL SELECT 'ratings', COUNT(*) FROM ratings
               UNION ALL SELECT 'team_details', COUNT(*) FROM team_details
               UNION ALL SELECT 'playoff_odds', COUNT(*) FROM playoff_odds
               UNION ALL SELECT 'team_history', COUNT(*) FROM team_history;"
```

### Sync metadata

```bash
sqlite3 "$DB" "SELECT * FROM sync_meta;"
```

## When to use this

| Symptom | What to check |
|---------|---------------|
| Sync "succeeds" but screens are empty | Row counts — did ingest actually write rows? |
| `table X has no column named Y` at sync time | `PRAGMA table_info(X)` — did migration 2 add the column? |
| Migration "ran" but schema is incomplete | `PRAGMA user_version` — is it the expected version? |
| App boots but crashes on specific screen | Table exists? Column names match ingest SQL? |
| Need to verify column names match between migration and ingest | Compare `PRAGMA table_info` output with INSERT column list in `offline.ts` |

## Reset the database (for clean QA)

```bash
# Uninstall clears the entire app container including the DB
xcrun simctl uninstall "$DEVICE_ID" "$BUNDLE_ID"

# Reinstall with fresh DB
xcrun simctl install "$DEVICE_ID" path/to/App.app
```

Alternatively, clear just the tables without uninstalling:

```bash
sqlite3 "$DB" "DELETE FROM schedule; DELETE FROM ratings; DELETE FROM team_details; DELETE FROM sync_meta; PRAGMA user_version = 0;"
```
