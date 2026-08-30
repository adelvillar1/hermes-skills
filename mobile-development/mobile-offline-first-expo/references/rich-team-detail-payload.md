# Rich offline team detail payload

When the mobile app shows a **Team Detail** screen offline, the single `/api/mobile/sync` call must carry enough data to render the screen without any follow-up network requests.

This reference documents the contract used in the ELO Scenario Lab project. The same pattern applies to any offline-first mobile app where entity-detail screens need rich signals.

## Backend payload shape

Add a `team_details` array to the `MobileSyncPayload` response. Each item is a snapshot for one favorite team:

```json
{
  "mobile_id": "mlb:NYY",
  "team_id": "NYY",
  "sport": "MLB",
  "team_json": { "id": "NYY", "name": "Yankees", "rating": 1556.2, "rd": 52.1, ... },
  "history_json": [{ "date": "2026-05-01", "rating": 1530.0, "rd": 60.0 }, ...],
  "scenarios_json": [{ "type": "Ace injury", "description": "...", "confidence": "high", ... }],
  "divergence_json": [{ "id": "div-NYY-xxx", "divergence_pct": 12.5, "explanation": "..." }],
  "next_opponents_json": [{ "date": "2026-06-16", "opponent_id": "BOS", "opponent_name": "Red Sox", "venue": "away", "win_probability": 0.42 }],
  "last_5_results_json": [{ "date": "2026-06-10", "is_win": true, "rating_change": 2.3 }],
  "form_trend_json": { "current": 1556.2, "delta_7d": 27.1, "delta_14d": 18.4, "delta_30d": 48.2 },
  "roster_json": {
    "team_id": "NYY",
    "team_name": "Yankees",
    "sport": "MLB",
    "war": { "hitting": 35.2, "pitching": 42.1, "fielding": 8.4, "total": 85.7 },
    "rotation": [{ "name": "G. Cole", "war": 4.2 }],
    "bullpen_war": 3.1,
    "top_hitters": [{ "name": "A. Judge", "war": 6.1 }],
    "injuries": [{ "name": "J. Stanton", "status": "10-day IL" }]
  },
  "strengths_json": ["Powerful lineup", "Deep bullpen"],
  "weaknesses_json": ["Injury-depleted"],
  "narrative": "Yankees are surging — 27 points in the last 7 days...",
  "mc_playoff_odds": 0.847,
  "mc_division_odds": 0.321,
  "mc_simulated_at": "2026-06-15T02:00:00Z"
}
```

## How to compute it

Reuse the web route's corpus loaders. In this project the web `/api/teams/{sport}/{id}/history` already loads ratings, MC odds, schedule, player stats, injuries, and narratives. The mobile sync service mirrors that logic but:

- **Skips LLM calls** — use the deterministic `generate_team_narrative` helper and flatten any dict it returns to a string.
- **Caps arrays** — limit `scenarios_json` and `divergence_json` to 10 items; `next_opponents_json` to 3; `top_hitters` and `rotation` to 5.
- **Recomputes history** by replaying completed games through the signal-aware Glicko-2 engine day-by-day.
- **Computes WAR strengths/weaknesses** from `corpus.load_player_stats_aggregated()` heuristics.

## Mobile SQLite contract

```sql
CREATE TABLE team_details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mobile_id TEXT NOT NULL UNIQUE,
  team_id TEXT NOT NULL,
  sport TEXT NOT NULL,
  team_json TEXT DEFAULT '{}',
  history_json TEXT DEFAULT '[]',
  scenarios_json TEXT DEFAULT '[]',
  divergence_json TEXT DEFAULT '[]',
  next_opponents_json TEXT DEFAULT '[]',
  last_5_results_json TEXT DEFAULT '[]',
  form_trend_json TEXT DEFAULT '{}',
  roster_json TEXT DEFAULT '{}',
  strengths_json TEXT DEFAULT '[]',
  weaknesses_json TEXT DEFAULT '[]',
  narrative TEXT DEFAULT NULL,
  mc_playoff_odds REAL DEFAULT NULL,
  mc_division_odds REAL DEFAULT NULL,
  mc_simulated_at TEXT DEFAULT NULL
);
```

Store every `*_json` column as a JSON string. Parse it back to objects in `getTeamDetail()` / `listTeamDetails()`.

## Mobile UI layers

1. **Zod schema** — `MobileTeamDetailSchema` with every field optional/defaulted.
2. **Sync payload schema** — `team_details: z.array(MobileTeamDetailSchema).optional()` so existing tests without the field still compile.
3. **Ingest** — clear `team_details` and insert each item in `ingestSyncPayload()`.
4. **Query** — `getTeamDetail(mobileId)` returns a parsed `MobileTeamDetail`.
5. **Screen** — hero (rating, MC playoff odds, narrative), form-trend grid, strengths/weaknesses chips, last-5 results, upcoming opponents, tabbed roster/scenarios.

## Size guard

Team details can be large because of history arrays. Add the section to the payload-size truncation loop with a low cap (e.g., keep 3 items if over the mobile limit).

## Verification

1. `pytest tests/test_mobile_api.py -q` — backend sync still passes and asserts `team_details` exists.
2. `pnpm run typecheck` — mobile TypeScript compiles.
3. `pnpm run test` — mobile unit tests pass.
4. Simulator smoke: login → sync → tap a favorite team → Team Detail renders with narrative, form trend, and roster tabs.
