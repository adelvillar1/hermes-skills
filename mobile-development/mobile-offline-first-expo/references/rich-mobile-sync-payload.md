# Rich mobile sync payload contract

When a mobile app renders game cards offline, the backend `/api/mobile/sync` schedule array must carry the same signal data the web schedule view uses. Raw corpus rows (team IDs, names, dates) are not enough.

This contract comes from ELO Scenario Lab's `MobileScheduleGame` Zod schema and the backend `_build_schedule_for_sport()` enrichment pipeline.

## Required fields per schedule game

| Field | Type | Purpose |
|-------|------|---------|
| `mobile_id` | string | Stable, unique game ID used for navigation and upsert |
| `date` | string ISO | Game date |
| `home_team_id`, `away_team_id` | string | Canonical team IDs |
| `home_team_name`, `away_team_name` | string | Display names (not empty strings) |
| `sport` | string | League/sport key |
| `home_win_prob`, `away_win_prob` | number 0-1 | Model win probabilities |
| `confidence` | 'high' \| 'moderate' \| 'low' | Model confidence label |
| `narrative` | string | 1-2 sentence human-readable analysis |
| `market_implied_prob` | number \| null | De-vigged market home win probability |
| `edge_gap`, `edge_label` | number/string | Model-vs-market edge signal |
| `home_team_rating`, `away_team_rating` | number | Glicko-2 mu (or project-specific rating) |
| `home_team_rd`, `away_team_rd` | number | Glicko-2 phi |
| `home_projected_starter_name`, `away_projected_starter_name` | string \| null | Pitcher / QB / goalie / key player |
| `home_top_hitters`, `away_top_hitters` | `TopPlayer[]` | Top 3 batters / scorers |
| `home_top_pitchers`, `away_top_pitchers` | `TopPlayer[]` | Top 3 pitchers / defenders |
| `mc_home_win_pct` | number \| null | Monte Carlo home win percentage |
| `mc_confidence_low` | number \| null | MC 5th percentile (90% CI lower bound) |
| `mc_confidence_high` | number \| null | MC 95th percentile (90% CI upper bound) |
| `mc_histogram` | number[] \| null | 10-bin win probability distribution (JSON array) |

`TopPlayer` shape:
```ts
{ name: string; war?: number; ops?: number; era?: number }
```

## Where to get this data

Do **not** query the web schedule endpoint from the mobile client. Instead, run the same enrichment inside the sync endpoint so it all lands in SQLite in one write:

1. Load upcoming schedule from the corpus.
2. Filter to next N days (e.g., 7) and optionally to favorite teams/leagues.
3. Compute probabilities with the project's probability engine, passing ratings, injuries, aggregated team stats, and market odds.
4. Attach Monte Carlo per-game distributions if available.
5. Recompute `confidence` with the MC alignment helper.
6. Generate a narrative per game (sync version, not LLM, to keep payload small).
7. Compute model-vs-market edge label.
8. Return all fields in the sync payload; SQLite stores them via `INSERT OR REPLACE`.

## SQLite storage notes

- Keep the original `CREATE TABLE` schema at the version it shipped with.
- Add new rich columns in a numbered migration using `ALTER TABLE schedule ADD COLUMN ...`.
- Store JSON arrays (`top_hitters`, `top_pitchers`) as `TEXT` columns; parse them when reading.
- Use `INSERT OR REPLACE` per row, wrapped in explicit `BEGIN TRANSACTION`/`COMMIT` via `execAsync`, not `withTransactionAsync`.

## UI consumption

- Cards show: `Away @ Home`, win percentages, confidence badge, and a one-line narrative.
- Tapping a card opens a detail screen that renders the full narrative, projected starters, top players, ratings/RD, and market edge — all from SQLite.
- If a name field comes back as an empty string (`""`), fall back to the team ID using logical OR (`||`), not nullish coalescing (`??`).
