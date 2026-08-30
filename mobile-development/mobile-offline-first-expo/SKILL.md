---
name: mobile-offline-first-expo
description: "Build offline-first React Native/Expo apps with a sync API: SQLite source of truth, TanStack Query for network only, Zustand for UI state, JWT in expo-secure-store."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mobile, expo, react-native, offline-first, sqlite, tanstack-query, zustand]
    related_skills: [subagent-driven-development, react-native-expo-development]
---

# Offline-First Expo Mobile App

## When to use

Use this skill when building a React Native / Expo mobile client that:
- Needs to work offline after an initial sync
- Has an existing backend API (FastAPI, REST, etc.) you do not want to reimplement
- Reuses backend user accounts via JWT
- Targets iOS/Android simulators or internal builds first, App Store later

## Core architecture

| Concern | Tool | Rule |
|---------|------|------|
| Offline source of truth | `expo-sqlite` relational DB | UI reads from SQLite, never from TanStack Query cache |
| Network fetches | TanStack Query (`@tanstack/react-query`) | Only for HTTP lifecycle (loading, error, retry). Do NOT persist TanStack cache to SQLite. |
| UI state | Zustand | Theme, selected tab, form state only. Never put synced data in Zustand. |
| Auth token | `expo-secure-store` | Store JWT here. Never in `AsyncStorage` or plain state. |
| Sync orchestration | Custom `SyncProvider` | Foreground sync with a minimum interval (e.g., 5 minutes) + manual refresh. |
| Failed writes | SQLite mutation outbox | Queue failed mutations and replay on next successful sync. |

## File layout (inside `mobile/apps/<app>/src/`)

```
src/
  api/client.ts      # typed fetch wrapper + JWT attachment
  db/offline.ts      # SQLite schema, migrations, CRUD, outbox
  db/migrations.ts   # SQL migrations keyed by PRAGMA user_version
  store/auth.ts      # Zustand login/logout UI state
  store/sync.ts      # TanStack Query client + SyncOrchestrator + performSync()
  hooks/useOfflineData.ts   # UI hooks that read SQLite
  types/api.ts       # Zod schemas mirroring backend Pydantic
```

## Sync lifecycle

1. **Login** stores JWT in `expo-secure-store` via `api/client.ts`.
2. **`SyncProvider`** mounts and calls `performSync()`:
   - `GET /api/mobile/sync`
   - Validate with Zod
   - Write to SQLite in a single `withTransactionAsync` (clear-and-insert)
   - Flush mutation outbox
3. **Foreground guard**: only auto-sync if last successful sync is older than 5 minutes (or manual pull-to-refresh).
4. **Conflict rule**: server wins. On sync, local SQLite tables are replaced by server payload.
5. **Logout** clears secure-store, SQLite, and TanStack Query cache; calls `POST /api/auth/logout`.

## Pitfalls

### 1. UI hooks read SQLite once on mount and never refresh after sync

`useEffect` with an empty dependency array loads SQLite on first render. After `performSync()` writes new data, the screen still shows old data until unmount.

**Fix**: pass a `refresh` key into every offline hook and increment it after sync:

```tsx
// src/hooks/useOfflineData.ts
export function useSchedule(refresh = 0) {
  const [data, setData] = useState<MobileScheduleGame[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    getSchedule().then((rows) => {
      if (!cancelled) { setData(rows); setLoading(false); }
    });
    return () => { cancelled = true; };
  }, [refresh]);
  return { data, loading };
}
```

```tsx
// src/screens/TodayFeed.tsx
const [refreshKey, setRefreshKey] = useState(0);
const { data: schedule } = useSchedule(refreshKey);

const handleRefresh = useCallback(async () => {
  await performSync();
  setRefreshKey(k => k + 1);
}, []);
```

See [`references/refresh-key-hook-pattern.md`](references/refresh-key-hook-pattern.md) for the full snippet.

### 2. `performSync()` swallows errors; caller cannot show them

If `performSync()` has its own `try/catch`, a manual refresh button cannot surface the error. Either remove the inner catch (let the caller handle) or return a result object `{ ok, error }`.

### 3. Auth login navigation runs before state updates

Zustand `login()` is async. Calling it and then immediately checking `isLoggedIn` from `useAuthStore.getState()` is the reliable pattern, but reading the hook value on the same render is not:

```tsx
const { login, isLoggedIn } = useAuthStore();
await login(email, password);
// isLoggedIn here is stale if read from the hook destructuring
```

**Fix**:

```tsx
await login(email, password);
if (useAuthStore.getState().isLoggedIn) {
  navigation.navigate('TodayFeed');
}
```

### 4. Storing JWT in AsyncStorage or Zustand

Never. Use `expo-secure-store`. On iOS it uses Keychain; on Android, Keystore-backed EncryptedSharedPreferences.

### 5. Using TanStack Query cache as offline source of truth

TanStack Query cache is in-memory and expires. It is not a durable offline database. Always treat `expo-sqlite` as the single source of truth for synced data.

### 6. Login does not automatically sync data

If the sync orchestrator runs on app mount, the user is usually logged out, so it skips. After login succeeds, nothing tells the data layer to sync again.

**Fix:** trigger `performSync()` immediately after a successful login, before dismissing the modal:

```tsx
const handleLogin = async () => {
  clearError();
  await login(email.trim(), password);
  if (useAuthStore.getState().isLoggedIn) {
    try { await performSync(); } catch { /* performSync logs internally */ }
    navigation.goBack();
  }
};
```

### 7. Sync orchestrator tries to sync while logged out

A foreground sync that fires before login will hit `401`, clear the token, and update the "last sync" timestamp. The next app-state change then skips because the interval hasn't elapsed.

**Fix:** check auth inside `maybeSync()` and subscribe to the auth store so a fresh login forces a sync:

```ts
const unsubscribe = useAuthStore.subscribe((state) => {
  if (state.isLoggedIn && !wasLoggedInRef.current) {
    wasLoggedInRef.current = true;
    maybeSync(true);
  }
});
```

### 8. UI `??` fallback fails on empty strings

Backend payloads often return `home_team_name: ""` instead of `null`. The nullish coalescing operator `??` does not treat an empty string as missing, so the UI renders `@`.

**Fix:** use logical OR fallback and fall through to the team ID:

```tsx
<Text>
  {game.away_team_name || game.away_team_id || 'Away'} @ {game.home_team_name || game.home_team_id || 'Home'}
</Text>
```

### 9. SQLite transaction wrapper is unstable on some Expo builds

`db.withTransactionAsync()` can throw `finalizeAsync` failures when many prepared statements run inside the transaction, causing the entire sync to abort.

**Fix:** use explicit `BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK` via `db.execAsync()` and `INSERT OR REPLACE` per row so a single bad row never rolls back everything. See `references/mobile-sync-deduplication.md`.

### 10. The sync payload is too thin to render rich offline cards

If the backend `/api/mobile/sync` only returns raw schedule rows (team IDs, names, date), the mobile UI has no probabilities, confidence, narrative, or market edge to show. The user gets a list of team names instead of game cards.

**Fix:** make the mobile sync service run the same enrichment pipeline the web schedule view uses — win probability computation, Monte Carlo alignment, market-odds de-vigging, and narrative generation. Store all of it in the SQLite `schedule` table. The UI then reads from SQLite and can show rich cards without any further network calls.

See [`references/rich-mobile-sync-payload.md`](references/rich-mobile-sync-payload.md) for the exact field contract used in this project.

### 11. Migrations add columns that the initial CREATE already includes

If a new migration uses `ALTER TABLE schedule ADD COLUMN x` while the initial `CREATE TABLE` already defines `x`, fresh installs will apply migration 1, then migration 2 will fail with `duplicate column name`.

**Fix:** keep the initial schema at the version it had when first released, and put *only* new columns in the migration. Existing installs get the column added; fresh installs run the migration too, successfully.

### 12. Backend FastAPI response model strips undeclared fields

Even if the sync service builds a rich dict with probabilities, narratives, and player stats, FastAPI will drop every key not declared on the response model. The mobile client then sees a thin payload and the SQLite table cannot populate its rich columns.

**Fix:** keep the backend Pydantic model (`MobileScheduleGame` / `MobileSyncPayload`) in exact sync with the SQLite table schema and the service's returned fields. After adding new service fields, always update the Pydantic model before testing the mobile UI.

**Verification:** call `GET /api/mobile/sync` with curl and assert the returned JSON contains the new keys. Do not rely on the service's internal dict alone.

### 13. Auto-login QA hook uses a non-hoisted arrow function

During simulator verification it is convenient to auto-log in a test user. A `useEffect` that calls a `const handleLogin = async () => ...` defined later in the component will fail silently because the const is not hoisted.

**Fix:** use a hoisted `async function` declaration, or inline the login call inside the effect:

```tsx
useEffect(() => {
  if (!AUTO_LOGIN_TEST_USER) return;
  async function run() {
    await login(TEST_EMAIL, TEST_PASSWORD);
    if (useAuthStore.getState().isLoggedIn) {
      await performSync();
      (navigation as any).replace('MainTabs');
    }
  }
  run();
}, []);
```

When `AuthLogin` is the stack's initial route (typical for QA builds), use `navigation.replace('MainTabs')` instead of `navigation.goBack()`, which has no previous screen to return to.

See [`references/ios-qa-auto-login-pattern.md`](references/ios-qa-auto-login-pattern.md).

**When the app starts on `MainTabs` (production setup), auto-login in `AuthLogin.tsx` never fires** — the screen never mounts because `initialRouteName="MainTabs"`. The auto-login `useEffect` sits in a component that is never rendered, so the test user is never logged in and the Today screen shows an empty state with a "Log In" button.

**Fix**: place the auto-login in `App.tsx` inside the post-migration `.then()` block, not in `AuthLogin.tsx`:

```tsx
useEffect(() => {
  runMigrations()
    .then(async () => {
      setMigrated(true);
      // TEMP QA: auto-login + sync — REMOVE BEFORE COMMIT
      try {
        const { login } = useAuthStore.getState();
        await login('test@example.com', 'TestPass123');
        await performSync();
      } catch (err) {
        console.error('Auto-login/sync failed', err);
      }
    })
    .catch((err) => setMigrationError(String(err)));
}, []);
```

This runs on every app launch regardless of which screen is the initial route. Revert (remove the `async` block and the auth/sync imports) before committing.

**When `xcrun simctl io input tap` is unavailable** (some macOS/Xcode versions don't support it), you cannot programmatically tap the "Log In" button on the simulator. Don't waste time on AppleScript CGEventPost or Quartz Python click attempts — they fail on the Simulator process. The auto-login code approach above is the reliable workaround.

### 14. Optimistic mutations before sync

### 15. Adding a new sync payload section requires updating the whole chain

If you add rich team details (or any new section) to `/api/mobile/sync`, the change must propagate through **five layers** before the UI works:

1. **Backend service** — build the new section (`_build_team_details_for_sport`).
2. **Backend Pydantic response model** — add the section to `MobileSyncPayload` (and a typed item model like `MobileTeamDetail`). FastAPI strips any undeclared section silently.
3. **Mobile SQLite schema** — add a new table in `db/migrations.ts` matching the backend item model.
4. **Mobile types + ingestion + query helpers** — add the Zod schema, update `ingestSyncPayload` to clear/insert the table, and add `getXxx()` / `listXxx()` helpers with JSON parse.
5. **Mobile UI** — read the offline data and render it.

Skipping any layer causes a confusing symptom: the backend builds it, but the mobile app sees nothing (model strips), or it lands in SQLite but the screen stays empty (missing ingest/UI), or the app crashes on migration (missing table).

**Fix:** treat the backend Pydantic model and the mobile Zod/SQLite schema as a single contract. Update them in the same commit, and add a backend test that asserts the new section exists in `/api/mobile/sync`.

### 16. SQLite row typing with JSON columns

When a table stores JSON blobs, the raw SQLite row has string columns. If you type the row as `MobileTeamDetail & Record<string, any>` and spread it (`{...row, team_json: JSON.parse(...)}`), TypeScript still sees the original typed object underneath, and the parsed arrays/objects fail assignability. It also risks silently keeping stale typed fields.

**Fix:** type the row as a plain `Record<string, any>` (or a dedicated `DbRow` interface with all strings) and construct the typed return object explicitly:

```ts
const row = await db.getFirstAsync<Record<string, any>>(
  'SELECT * FROM team_details WHERE mobile_id = ?', [mobileId]
);
if (!row) return null;
const typed: MobileTeamDetail = {
  mobile_id: row.mobile_id,
  team_id: row.team_id,
  sport: row.sport,
  team_json: JSON.parse(row.team_json || '{}'),
  history_json: JSON.parse(row.history_json || '[]'),
  // ... every field explicit
};
return typed;
```

### 17. Backend narrative helpers may return dicts, but Pydantic wants strings

`generate_team_narrative` (and similar helpers) can return a structured dict like `{headline, summary, form_story, outlook, key_stat}`. If the response model declares `narrative: str`, FastAPI throws `ResponseValidationError` at runtime.

**Fix:** flatten the dict to a single string inside the sync service before returning:

```python
narrative_obj = generate_team_narrative(team, history, scenarios, divergence)
narrative = ""
if isinstance(narrative_obj, dict):
    narrative = " ".join(
        p for p in [
            narrative_obj.get("headline"),
            narrative_obj.get("summary"),
            narrative_obj.get("form_story"),
            narrative_obj.get("outlook"),
            narrative_obj.get("key_stat"),
        ] if p
    ).strip()
elif isinstance(narrative_obj, str):
    narrative = narrative_obj
```

Alternatively, update the Pydantic model to accept a nested `TeamNarrative` object if the mobile UI can render the structure.

### 18. Zod `.optional()` rejects JSON `null` — use `.nullable().optional()`

When the Python backend sends JSON `null` for a field (common for optional computed values like `mc_playoff_odds`, `narrative`, `mc_simulated_at` when MC hasn't run), Zod's `.optional()` does NOT accept it. `.optional()` means "the key may be absent", not "the value may be null". The sync fails silently with:

```
Sync payload validation failed: [{"code": "invalid_type", "expected": "number", "received": "null", "path": ["team_details", 0, "mc_playoff_odds"]}]
```

**Fix**: every field that can be `null` from the backend needs `.nullable().optional()`:

```typescript
// WRONG — rejects null values
narrative: z.string().optional(),
mc_playoff_odds: z.number().optional(),

// RIGHT — accepts absent OR null
narrative: z.string().nullable().optional(),
mc_playoff_odds: z.number().nullable().optional(),
```

This is the single most common sync-validation failure in this project. When sync fails with no visible error on screen, always suspect this. Add a debug status overlay during QA to surface `SYNC FAIL: ${err.message}` — see pitfall #21.

### 19. Do not cap sync payload size for offline-first SQLite apps

A sync payload cap (e.g., 200 KB) is a premature optimization that defeats the purpose of offline-first storage. Device SQLite handles megabytes trivially — 5 MB payloads are routine. Truncating data means the user gets less data in their local DB, not faster sync.

**The only real constraint is computation time, not payload size.** If the sync endpoint takes > 10 seconds, the bottleneck is computing per-entity details (roster, scenarios, narrative, rating history), not network transfer or SQLite writes. Fix the computation scope (pitfall #20), not the payload size.

**Fix**: raise the cap to 5 MB as a safety net only. Remove all proportional truncation logic (`halve team_history if payload > N`). The user will see this as an unnecessary complexity and ask why the data is truncated.

### 20. Compute expensive per-entity details only for visible entities

Building rich per-team details (roster, scenarios, narrative, rating history) for every team in every sport is O(sports × top-N teams × compute_cost). For 3 sports × 20 top teams = 60 expensive computations, each involving ELO replay, MC alignment, and narrative generation — this took **45 seconds**.

**Fix**: compute rich details only for teams the user will actually interact with:

- **Favorite teams** (always) — the user explicitly cares about these
- **Teams in the upcoming schedule** (next 7 days) — the user sees these on Today/Schedule screens

The `ratings` section already carries lightweight data (rating, RD, trend) for all top-20 teams per sport. Details are only needed for the Team Detail screen, which the user reaches by tapping a specific team.

```python
# WRONG — details for all top-20 teams per sport (slow)
team_ids_for_details = sport_fav_teams.union(schedule_team_ids).union(top_team_ids)

# RIGHT — details for favorites + schedule teams only (fast)
team_ids_for_details = sport_fav_teams.union(schedule_team_ids)
```

This reduced from 62 teams / 45s to 34 teams / 4.8s — a 9× speedup with zero data loss for visible screens.

### 21. Metro serves stale JS bundles for Zod/schema changes

When you modify a Zod schema in `types/api.ts` (or any file Metro bundles), the running Metro server may serve the cached bundle instead of recompiling. The app silently runs the old code, and the fix you just applied doesn't take effect.

**Fix**: after any non-trivial TypeScript change that doesn't seem to work on the simulator:

1. Kill Metro: `kill $(lsof -ti :8081)`
2. Restart with `--clear`: `npx expo start --clear`
3. Relaunch the app: `xcrun simctl terminate <UDID> <bundle-id>; sleep 2; xcrun simctl launch <UDID> <bundle-id>`

During QA, add a visible debug overlay to `AuthLogin.tsx` that shows the API base URL and step-by-step sync status (`Logging in...` → `Login OK, syncing...` → `SYNC OK` / `SYNC FAIL: ${err.message}`). This makes stale-bundle issues immediately visible — you see the old error message instead of the fix.

### 22. expo-sqlite `execAsync` silently skips statements in multi-statement DDL

`db.execAsync(multiStatementString)` is unreliable for migrations containing multiple `ALTER TABLE` statements separated by semicolons. On some expo-sqlite versions, the first statement executes but subsequent ALTER TABLEs are silently skipped — no error thrown, `PRAGMA user_version` is still set, and the app boots with a partially-applied schema. The missing columns then cause ingest failures with `table X has no column named Y` later.

**Symptoms**: migration appears to succeed (no error, user_version advances), but the table is missing columns that migration 2 was supposed to add. The error surfaces only when `ingestSyncPayload` tries to INSERT into the missing columns.

**Fix**: split migration SQL into individual statements and execute each separately:

```ts
export async function runMigrations(): Promise<void> {
  const db = getDb();
  const { user_version: currentVersion } = await db.getFirstAsync<{ user_version: number }>(
    'PRAGMA user_version'
  ) ?? { user_version: 0 };

  const targetVersion = Object.keys(MIGRATIONS).length;
  for (let v = currentVersion + 1; v <= targetVersion; v++) {
    const sql = MIGRATIONS[v];
    if (!sql) continue;
    // Split into individual statements — expo-sqlite execAsync can silently
    // skip remaining statements if one ALTER TABLE fails mid-batch.
    const statements = sql
      .split(';')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    for (const stmt of statements) {
      try {
        await db.execAsync(stmt);
      } catch (err) {
        // Ignore "duplicate column" errors from ALTER TABLE (idempotent migrations)
        const msg = String(err);
        if (msg.includes('duplicate column') || msg.includes('already exists')) continue;
        throw err;
      }
    }
    await db.execAsync(`PRAGMA user_version = ${v}`);
  }
}
```

**Also**: do NOT silently swallow migration errors in `App.tsx`. If `runMigrations()` throws, show the error on screen — do not proceed with an incomplete schema:

```tsx
// WRONG — swallows error, boots with partial schema
runMigrations()
  .then(() => setMigrated(true))
  .catch(() => setMigrated(true)); // ← hides the real problem

// RIGHT — surface the error
runMigrations()
  .then(() => setMigrated(true))
  .catch((err) => setMigrationError(String(err)));
```

### 23. Ingest INSERT column names must match migration column names exactly

When a migration adds `home_top_hitters_json` (with `_json` suffix) but the ingest INSERT statement references `home_top_hitters` (without `_json`), the error is `table schedule has no column named home_top_hitters` — but only at sync time, not at migration time. This is hard to catch because:

1. The migration succeeds (it creates `home_top_hitters_json`).
2. TypeScript compiles (column names are just strings, not type-checked).
3. The error only surfaces when `ingestSyncPayload` runs during actual app usage.

**Fix**: after writing any migration that adds columns, cross-check every column name in the ingest INSERT statement against `PRAGMA table_info`:

```bash
# From the simulator — verify column names match ingest SQL
DB=$(find ~/Library/Developer/CoreSimulator/Devices/*/data/Containers/Data/Application/*/Documents/SQLite -name "elo_offline.db" 2>/dev/null | head -1)
sqlite3 "$DB" "PRAGMA table_info(schedule);" | awk -F'|' '{print $2}'
```

**Prevention**: name JSON blob columns consistently with the `_json` suffix throughout the codebase. Never mix `home_top_hitters` and `home_top_hitters_json`.

### 24. MC histogram data is null locally — don't run MC simulation to fix it

When the mobile sync returns `mc_home_win_pct: null`, `mc_histogram: null`, and `mc_confidence_low/high: null` for every game, the natural instinct is to run the Monte Carlo simulation locally to populate the data. **Don't.** The MC game dist data lives on the production PostgreSQL database, refreshed daily by the scheduler. Local SQLite has an empty or near-empty `mc_game_dist` table.

**Symptoms:**
- Backend enrichment code looks correct (calls `corpus.load_mc_game_dist()`, attaches fields to response dict).
- All MC fields are `null` in the sync payload even though the code path is wired.
- `simulate_and_persist('mlb')` fails locally with column mismatch errors because the local schema is out of date.

**Fix:** accept that MC data is a production artifact. The code is correct — it just has no data locally. Verify the MC fields render by testing against the production API, or by accepting that the UI gracefully hides MC elements when the fields are null.

**Do NOT:**
- Run `simulate_and_persist()` locally to "populate test data"
- Add columns to the local `mc_game_dist` table manually
- Assume the enrichment code is broken just because the fields are null

The MC simulation runs once daily at 2AM US/Eastern via APScheduler on the main Railway app. It populates `mc_game_dist` in production PostgreSQL. The mobile sync endpoint reads from the same PostgreSQL on production. On local dev, the SQLite `mc_game_dist` table is empty — that's expected, not a bug.

### 25. Navigator has no auth gate — app bypasses login, stale data can't refresh

The RootNavigator sets `initialRouteName="MainTabs"` unconditionally. The app always opens to the main tabs regardless of `isLoggedIn`. The AuthLogin screen is registered in the stack but never shown because it's never the initial route and nothing navigates to it.

**Symptoms:**
- App opens directly to Today/Schedule/Ratings — no login screen.
- Pull-to-refresh appears to work (spinner spins) but data never updates. No error is shown.
- The `SyncOrchestrator`'s `maybeSync()` checks `isLoggedIn` and silently returns (`if (!isLoggedIn) return;`). Since the user was never authenticated, sync never fires.
- Stale SQLite data from a previous session's sync (or test seed) is displayed, making the app appear functional when it's actually disconnected.

**This is especially insidious** because the app *looks* like it works — it shows game cards, ratings, and schedules from the local SQLite cache. The only clue is that pull-to-refresh has no effect and the data never updates.

**Fix:** Gate the navigator on `isLoggedIn` with conditional screen rendering:

```tsx
export default function RootNavigator() {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn);

  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName={isLoggedIn ? 'MainTabs' : 'AuthLogin'}>
        {!isLoggedIn && (
          <Stack.Screen name="AuthLogin" component={AuthLoginScreen} options={{ headerShown: false }} />
        )}
        {isLoggedIn && (
          <>
            <Stack.Screen name="MainTabs" component={MainTabs} options={{ headerShown: false }} />
            <Stack.Screen name="AuthLogin" component={AuthLoginScreen} options={{ title: 'Log In', presentation: 'modal' }} />
            {/* other authenticated screens */}
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

When `isLoggedIn` flips to true (after successful login), Zustand re-renders the navigator. The conditional screens swap, MainTabs becomes the initial route, and the auth screen disappears. `navigation.replace('MainTabs')` inside AuthLogin's login handler also works for the modal case.

**Debugging tip:** if pull-to-refresh spins but data doesn't change, check `useAuthStore.getState().isLoggedIn` first — not the sync endpoint, not the cache, not the API key. A missing auth gate is the highest-impact, hardest-to-spot cause.

### 26. SQLite `id INTEGER PRIMARY KEY AUTOINCREMENT` shadows the logical entity ID

When a table uses `id INTEGER PRIMARY KEY AUTOINCREMENT` as a rowid column AND stores the real team identifier in a separate `entity_id TEXT` column, `SELECT *` returns the auto-increment rowid (1, 2, 3...) — NOT the text column. This causes a **silent ID mismatch** that is invisible at the API layer and extremely hard to debug.

**Symptoms:**
- Backend sync correctly returns abbreviation IDs (`MIL`, `CWS`, `NYY`)
- Device SQLite has the right data in `entity_id`, but `getRatings()` returns rowid integers (101, 102...)
- `getTeamDetail('mlb:101')` returns null because `team_details` has `mobile_id = 'mlb:MIL'`
- The detail screen shows team name and rating (from the ratings row) but no overview, roster, or scenarios (from the detail lookup)
- The mismatch is invisible when curling the API — the server returns the correct IDs

**Root cause:** SQLite's `INTEGER PRIMARY KEY` is an alias for `rowid`. When you `SELECT *`, the `id` column contains the rowid, not the logical value stored in `entity_id`. This is standard SQLite behavior but easy to miss when the schema column name (`id`) shadows the logical field name.

**Fix:** Explicitly select `entity_id AS id` in the query, never `SELECT *`:

```ts
// WRONG — returns rowid as `id`
const rows = await db.getAllAsync<MobileRating>('SELECT * FROM ratings');

// RIGHT — maps entity_id to the expected `id` field
const rows = await db.getAllAsync<MobileRating>(
  'SELECT mobile_id, entity_id AS id, name, sport, rating, rd, trend, rating_delta_10g, position_change FROM ratings'
);
```

**Prevention:** Never use `SELECT *` on a table with `id INTEGER PRIMARY KEY AUTOINCREMENT` when the app expects a logical entity ID. Either:
1. Name the rowid column `_id` or `row_num` (not `id`), OR
2. Always use explicit column lists with `entity_id AS id`, OR
3. Make the logical ID the primary key: `id TEXT PRIMARY KEY` (no auto-increment needed for sync data).

### 27. Pydantic response model type mismatch crashes the entire sync endpoint

When production data contains float values (e.g., MC histogram percentages like 22.5, 30.5) but the Pydantic response model declares the field as `list[int]`, FastAPI throws a `ResponseValidationError` and returns **500 Internal Server Error**. The entire `/api/mobile/sync` endpoint fails — not just the affected rows.

**This is especially insidious** because:
- The sync endpoint worked perfectly in local dev (local SQLite had only 1 MC row with integer histograms)
- After importing production data (373 rows with float histograms), every sync silently fails with 500
- The app shows stale data from the last successful sync with no visible error
- Server logs show the Pydantic validation error but it looks like a data issue, not a code bug

**Symptom pattern:** `curl /api/mobile/sync` returns `Internal Server Error` (21 bytes). Server log shows `int_from_float` validation errors.

**Fix:** Align Pydantic model types with actual data. When a field stores computed percentages or distributions, use `float` even if the values look like integers:

```python
# WRONG — crashes when data has 22.5, 30.5
mc_histogram: list[int] | None = None

# RIGHT — handles both integer and float values
mc_histogram: list[float] | None = None
```

**Prevention:** after importing production data into local dev, always smoke-test the sync endpoint with curl and check for 500 errors. The data import exposes type mismatches that local-only test data hides.

### 28. Debug "data not showing" by inspecting device SQLite FIRST — not the server

In an offline-first app, the device SQLite is the source of truth for the UI. When data isn't showing, the instinct is to check the server API, response models, and cache layers. **Don't start there.** The server is a transport layer; the device SQLite is what the screen reads from.

**Correct debugging order:**

1. **Device SQLite** — query the device DB directly. Find it with:
   ```bash
   APP_CONTAINER=$(xcrun simctl get_app_container booted <bundle-id> data)
   DEVICE_DB=$(find "$APP_CONTAINER" -name "*.db" | head -1)
   sqlite3 "$DEVICE_DB" "SELECT COUNT(*) FROM <table>"
   sqlite3 "$DEVICE_DB" "SELECT * FROM <table> LIMIT 3"
   ```
   Check: row counts, column values, ID formats, JSON field lengths.

2. **Read query** — verify the `getXxx()` function returns what you expect. Check for `SELECT *` issues (pitfall #26), column name mismatches, JSON parse failures.

3. **Ingest path** — verify `ingestSyncPayload` inserts into the right columns. Check that INSERT column names match the migration schema.

4. **Server API** — only after confirming device SQLite has (or lacks) the expected data. Curl the sync endpoint and compare.

5. **Response model** — check Pydantic/Zod validation isn't silently dropping fields (pitfalls #12, #18, #27).

**Key insight:** if the server returns correct data but the device shows wrong data, the problem is between the device SQLite write and the device SQLite read — NOT in the server. Spending time debugging the server when the device SQLite has a column shadowing bug wastes the entire debugging window.

## Verification checklist

After any change to the mobile data layer:

1. `pnpm run typecheck` — must pass with 0 errors (subagents frequently introduce TS errors even when tests pass).
2. `pnpm run test` — mobile unit tests pass.
3. `pytest tests/test_mobile_api.py -q` — backend sync/favorites endpoints pass.
4. E2E smoke (controller session):
   - Use FastAPI `TestClient` or start local `uvicorn`.
   - Register/login a test user → get JWT.
   - Call `GET /api/mobile/sync` and assert payload keys present and response < 5 MB. Do NOT cap at 200 KB — device SQLite handles megabytes trivially (see pitfall #19).
   - Add favorites → call sync again → assert `team_history` populated.
   - Measure sync response time. If > 10s, you are computing too many per-entity details — limit to visible entities (see pitfall #20).
5. If a simulator is available: `pnpm run ios` or `pnpm run android` and verify login → sync → offline read.
6. **Zod validation check**: after changing any Zod schema, verify the actual API JSON validates by running the app — a stale Metro bundle or a null-vs-absent mismatch will silently fail sync with no visible error unless you add debug status text (see pitfalls #18 and #21).

### 29. Never modify a migration that has already shipped — add a new one

When you change a migration's SQL (e.g., changing what Migration 4 creates from `app_kv` to `signal_history`), devices that already ran the original Migration 4 will **never run the updated version** because `PRAGMA user_version` is already 4. The migration runner sees `current_version >= migration_version` and skips.

**Symptom:** New table doesn't exist on device even after rebuild. `getSignalStats()` returns null. No error — the migration simply never ran.

**Fix:** Always add a new migration number. Never edit a shipped migration:

```ts
// WRONG — editing Migration 4 that already ran on devices
const MIGRATION_004_SIGNAL_BARS = `... CREATE TABLE signal_history ...`;

// RIGHT — keep Migration 4 as-is, add Migration 5
const MIGRATION_004_SIGNAL_BARS = `... CREATE TABLE app_kv ...`; // original, unchanged
const MIGRATION_005_SIGNAL_HISTORY = `CREATE TABLE IF NOT EXISTS signal_history ...`;
```

Update the test assertions to expect the new version number. See [`references/migration-versioning.md`](references/migration-versioning.md) for the full pattern including device-side SQL aggregation.

### 30. Send raw per-game data, let the device aggregate — not pre-computed JSON

When a mobile feature needs aggregated stats (e.g., per-signal-type accuracy), the server should send per-game classification rows (`{sport, signal_type, model_correct, is_draw}`), not pre-aggregated JSON. The device stores these in a table and computes accuracy with a SQL `GROUP BY`:

```sql
SELECT sport, signal_type,
  COUNT(*) as total,
  SUM(CASE WHEN is_draw = 0 THEN 1 ELSE 0 END) as dir_count,
  SUM(model_correct) as correct
FROM signal_history GROUP BY sport, signal_type
```

This matches the offline-first pattern: raw data in SQLite, computation on device, no server roundtrip needed for rendering. The user explicitly prefers this over server-side pre-aggregation.

## References

- [`references/refresh-key-hook-pattern.md`](references/refresh-key-hook-pattern.md) — copy-paste refresh-key pattern for offline hooks.
- [`references/auth-login-guard-pattern.md`](references/auth-login-guard-pattern.md) — correct post-login navigation guard using Zustand `getState()`.
- [`references/rich-mobile-sync-payload.md`](references/rich-mobile-sync-payload.md) — field contract for rich offline game cards.
- [`references/rich-team-detail-payload.md`](references/rich-team-detail-payload.md) — field contract for rich offline team detail screens.
- [`references/migration-versioning.md`](references/migration-versioning.md) — never modify a shipped migration; device-side SQL aggregation pattern.

## Out of scope

- Visual design system (defer to a separate UX skill/plan).
- Social login, push notifications, in-app purchases, subscriptions, deep linking.
- Real-time/live odds beyond the existing backend pipeline cycle.
