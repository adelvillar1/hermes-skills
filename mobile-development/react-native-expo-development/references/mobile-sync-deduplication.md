# Mobile Sync Deduplication

Session-specific reference for the duplicate-ID bug that aborts SQLite sync in multi-sport apps.

## Symptom

App logs in, calls `/api/mobile/sync`, then SQLite throws:

```
Error code 19: UNIQUE constraint failed: ratings.mobile_id
```

The transaction rolls back and no data appears in any tab. The app may show a red React Native error toast: `Calling the 'finalizeAsync' function has failed`.

## Root cause

Team IDs are unique *within* a sport but not *across* sports. If the backend returns all sports in one payload, the same `id` (e.g., `HOU`, `TOR`, `CLE`) appears multiple times. If the mobile SQLite schema declares `mobile_id` as the primary key and the backend sets `mobile_id = team_id`, the second insert for the same ID violates the constraint.

## Fix on the backend

Make `mobile_id` unique across `(sport, team_id)` by prefixing the ID:

```python
def _stable_team_id(team: dict) -> str:
    sport = str(team.get("sport", "")).lower()
    return f"{sport}:{team.get('id', '')}" if sport else str(team.get("id", ""))
```

Keep `id`/`entity_id` as the original team ID so the UI can still navigate to team detail.

## Fix on the frontend

Even after the backend is fixed, use `INSERT OR REPLACE` for every synced table so a future collision or partial sync never aborts the whole transaction:

```ts
await db.runAsync(
  'INSERT OR REPLACE INTO ratings (mobile_id, entity_id, name, sport, ...) VALUES (?, ?, ?, ?, ...)',
  [r.mobile_id, r.id, r.name, r.sport, ...]
);
```

Also avoid `db.withTransactionAsync()` if the Expo SQLite version emits `finalizeAsync` failures inside transactions; use explicit `BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK` via `db.execAsync()` instead.

## Deriving missing schedule team names

The corpus `load_schedule` often only stores team IDs, not names. The mobile sync should build a name lookup from the ratings corpus for that sport and fill in `home_team_name` / `away_team_name` before sending the payload:

```python
def _build_schedule_for_sport(sport: str, team_ids: set[str] | None = None) -> list[dict]:
    games = corpus.load_schedule(sport)
    if not games:
        return []
    team_name_by_id = {
        t.get("id", ""): t.get("name", "")
        for t in corpus.load_ratings(sport)
        if t.get("id")
    }
    results: list[dict] = []
    for g in games:
        home_id = g.get("home_team_id", "")
        away_id = g.get("away_team_id", "")
        results.append({
            "mobile_id": _stable_game_id(g),
            "date": g.get("date"),
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_team_name": g.get("home_team_name") or team_name_by_id.get(home_id, home_id),
            "away_team_name": g.get("away_team_name") or team_name_by_id.get(away_id, away_id),
            "sport": sport.upper(),
        })
    return results
```

## Verification

1. Call `/api/mobile/sync` with a token.
2. Count `ratings` `mobile_id` values and confirm `len(ids) == len(set(ids))`.
3. Confirm schedule items have non-empty `home_team_name` and `away_team_name`.
4. Install the app fresh, log in, and confirm the Today tab renders games/ratings without a red error banner.

## Related skill

`react-native-expo-development` covers the broader offline SQLite + sync architecture; `mobile-offline-first-expo` covers the client-side sync lifecycle and auth flow.
