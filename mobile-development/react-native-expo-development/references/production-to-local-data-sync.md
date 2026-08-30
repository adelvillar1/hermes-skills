# Production-to-Local SQLite Data Sync

When developing a mobile app locally, the local SQLite corpus often has thin or stale data compared to production PostgreSQL. This causes misleading UI symptoms: missing leagues in filter pills, empty schedule pages, null MC histogram data. Syncing production data into local SQLite gives data parity for offline mobile dev.

## When to use

- Mobile screens show fewer leagues/teams than production (e.g., Schedule page only shows MLB/NBA/NHL pills when production has 10+ sports)
- MC histogram and confidence interval fields are null locally but present in production
- You need realistic data volumes to QA mobile sync ingestion and UI rendering

## The script pattern

```python
#!/usr/bin/env python3
"""Pull production PostgreSQL data into local SQLite for mobile dev parity."""
import sqlite3
import pg8000

PG = dict(
    host="<public-proxy-host>",
    port=<proxy-port>,
    database="railway",
    user="postgres",
    password="<password>",
    timeout=60,
)

LOCAL_DB = ".forecast/corpus.db"

# Tables to sync, in dependency order (parents first)
SYNC_TABLES = [
    "evidence_packets",
    "evidence_items",
    "packet_items",
    "market_odds_history",
    "mc_game_dist",
    "mc_team_season",
    "mc_calibration",
    "scraper_jobs",
]

# Skip user data tables (local dev auth)
SKIP_TABLES = ["users", "user_favorites"]

BATCH_SIZE = 500

def get_pg_columns(pg_cur, table):
    pg_cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    return [r[0] for r in pg_cur.fetchall()]

def get_sqlite_columns(sl_cur, table):
    sl_cur.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in sl_cur.fetchall()]

def ensure_columns(sl_cur, table, pg_cols, sqlite_cols):
    """ALTER TABLE to add any PG columns missing from SQLite."""
    for col in pg_cols:
        if col not in sqlite_cols:
            print(f"  ALTER TABLE {table} ADD COLUMN {col}")
            sl_cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} REAL")
    return pg_cols

def sync_table(pg_cur, sl_cur, table, dry_run=False):
    pg_cols = get_pg_columns(pg_cur, table)
    sqlite_cols = get_sqlite_columns(sl_cur, table)
    cols = ensure_columns(sl_cur, table, pg_cols, sqlite_cols)

    col_list = ", ".join(cols)
    placeholders = ", ".join(["?"] * len(cols))

    pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = pg_cur.fetchone()[0]
    print(f"\n[{table}] {total:,} rows from production")

    if dry_run:
        return total

    sl_cur.execute(f"DELETE FROM {table}")
    print(f"  cleared {sl_cur.rowcount:,} local rows")

    pg_cur.execute(f"SELECT {col_list} FROM {table}")
    batch = []
    for row in pg_cur:
        batch.append(tuple(row))
        if len(batch) >= BATCH_SIZE:
            sl_cur.executemany(
                f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})",
                batch,
            )
            batch = []
    if batch:
        sl_cur.executemany(
            f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})",
            batch,
        )
    print(f"  inserted {total:,} rows")
    return total
```

## Schema drift handling

Local SQLite schema may lag behind production PostgreSQL. The `ensure_columns()` function ALTERs missing columns before inserting. This handles the common case where production has added columns (e.g., `simulated_at`, `iterations`, `mean_total_rating_delta` on `mc_game_dist`) that local SQLite doesn't have yet.

**Important:** the ALTER TABLE assumes `REAL` type for missing columns. If a column is TEXT or INTEGER, adjust the type per-column or infer from `information_schema.columns.data_type`.

## Verification after sync

After syncing, verify the mobile sync endpoint returns expected data:

```bash
# Register a test user and get a JWT
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@test.com","password":"testpass123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Check sport counts in sync payload
curl -s "http://localhost:8000/api/mobile/sync" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
sched = data.get('schedule', [])
ratings = data.get('ratings', [])
print(f'Schedule: {len(sched)} games')
print(f'Ratings: {len(ratings)} teams')
sports = {}
for g in sched:
    sports[g.get('sport','?')] = sports.get(g.get('sport','?'),0)+1
for k,v in sorted(sports.items(), key=lambda x:-x[1]):
    print(f'  {k}: {v}')
"
```

## Pitfalls

### Schedule shows fewer leagues than Ratings

This is expected behavior, not a sync problem. Schedule entries only exist for leagues with upcoming games (in-season). Football leagues between matchdays have `game_results` and `power_ratings` but no `schedule` entries. The Today screen derives pills from both schedule + ratings, so it shows all sports. The Schedule screen derives pills from schedule data only, so it shows only in-season leagues.

### MC game dist is empty even after sync

If `mc_game_dist` was empty locally and you synced, verify the table actually has rows:

```bash
sqlite3 .forecast/corpus.db "SELECT sport, COUNT(*) FROM mc_game_dist GROUP BY sport"
```

If still empty, the sync script may have failed silently on this table due to schema drift. Check that all production columns exist locally before the INSERT runs.

### pg8000 not installed in the right Python

The script uses system Python (not the venv). Install with `pip3 install pg8000` for the system Python, or adjust the script to use the venv's Python. The `execute_code` sandbox may use a different Python than the terminal — run sync scripts from the terminal.
