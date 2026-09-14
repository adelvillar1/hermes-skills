# Python Data Pipeline Survey Patterns

When surveying a Python project with a data pipeline (ETL, scrapers, sports data extractors, ML inference pipelines).

## 1. Check extractor coverage

```bash
ls src/data_pipeline/extractors/
```

Look for: base extractor, sport-specific extractors (mlb, nba, nfl), factory pattern.

## 2. Verify API endpoint structure per sport

Different sports often use different API versions or endpoint structures from the same provider (e.g., ESPN). MLB may use `statsapi.mlb.com`; NBA/NFL may use `site.api.espn.com/apis/v2/sports/...`. The v2 standings API returns `children` → `standings` → `entries` with `stats` as a list of `{name, value}` dicts. The site v2 API may return only `{"fullViewLink": ...}` for some sports during offseason.

**Always verify the actual API response before writing the extractor.** Use curl or a quick Python probe:

```python
import requests
resp = requests.get("https://site.api.espn.com/apis/v2/sports/basketball/nba/standings", timeout=10)
print(list(resp.json().keys()))  # See what fields are actually present
```

## 3. Check for double-serialization bugs

The `CorpusLoader` passes payloads to `SportsEvidenceIngestor`. The ingestor's methods expect Python dicts/lists and call `json.dumps()` internally. If the loader pre-serializes with `json.dumps()`, the ingestor double-serializes, producing a JSON string instead of a dict.

**Symptom:** `could not convert string to float: '{"count": ...}'`

**Fix:** Pass Python dicts directly to ingestor methods. Do NOT pre-serialize.

```python
# WRONG
return self._load("game_results", json.dumps(payload))  # ❌

# RIGHT
return self._load("game_results", payload)  # ✓
```

## 4. Check injury field mapping consistency

ESPN returns injuries at different nesting levels per sport:
- MLB: `injury.details[0].shortComment`
- NBA/NFL: `injury.shortComment` (flat)

The extractor must handle the actual response structure, not assume consistency across sports.

**Probe:**
```python
import requests
resp = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries", timeout=10)
for team in resp.json().get("injuries", [])[:1]:
    for injury in team.get("injuries", [])[:1]:
        print("Keys:", list(injury.keys()))
        print("Has details:", "details" in injury)
        print("Has shortComment:", "shortComment" in injury)
```

## 5. Check offseason handling

Some sports have no games during offseason. The pipeline should return `success=False` and `games=0` gracefully, not crash. The API endpoint should fall back to mock data or last-season standings.

## 6. Check corpus schema

```bash
sqlite3 .forecast/corpus.db ".schema"
sqlite3 .forecast/corpus.db "SELECT sport, category, COUNT(*) FROM evidence_items GROUP BY sport, category;"
```

## 7. Check multi-sport pipeline execution

```python
for sport in ["mlb", "nba", "nfl"]:
    config = DataSourceConfig.for_sport(sport)
    pipeline = SportsDataPipeline(config, corpus_db=".forecast/corpus.db")
    result = pipeline.run_daily_sync(f"{sport}-season", days_back=7)
    print(f"{sport}: {len(result.elo_ratings)} teams, {result.games_normalized} games")
```

## 8. Check injury data field mapping from live APIs

ESPN's injury API uses different field names than assumed in many extractors. A common bug: the extractor looks for `team.name` and `athlete.fullName`, but the actual API returns `displayName` at the team level and `athlete.displayName` for players.

**Symptom:** All injuries extract with empty `team_id`, `player_id`, and `player_name`. Injury count shows correctly but per-team filtering fails, so scenario adjustments always compute zero severity.

**Probe the actual API:**
```bash
curl -s "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); t=d['injuries'][0]; print('Team keys:', list(t.keys())); print('Team displayName:', t.get('displayName')); print('Athlete keys:', list(t['injuries'][0].get('athlete',{}).keys()))"
```

**Fix:** Map to the actual field names:
- `team_data.get("team", {}).get("name", "")` → `team_data.get("displayName", "")`
- `player.get("fullName", "")` → `athlete.get("displayName", "")`
- `player.get("id", "")` → `athlete.get("id", "")`

Always verify the real API response before assuming field names match other sports or previous API versions.

## 9. Check advanced player stats availability

Many sports APIs provide player-level statistics (hitting, pitching, fielding) but not aggregated advanced metrics like WAR. The pipeline can compute WAR-like proxies from available stats.

**Check if the project already has player stat extractors:**
```bash
ls src/data_pipeline/extractors/
grep -r "player_stats\|player_stats_url\|war_proxy\|ops\|era\|fielding" src/data_pipeline/
```

**Key questions:**
- Does the extractor fetch hitting/pitching/fielding stats separately?
- Does it handle placeholder values like `"-.--"` for rate stats?
- Is there a WAR proxy computation function?
- Are player stats stored in the corpus as a separate evidence category?
- Does the schedule/prediction endpoint load and apply team-level WAR differentials?

**Common placeholder bug:** The MLB Stats API returns `"-.--"` for rate stats (OPS, ERA, WHIP, fielding percentage) when a player has no qualifying data. `float("-.--")` raises `ValueError`. Guard with:
```python
ops_raw = stat.get("ops", ".000") or ".000"
ops = float(ops_raw) if ops_raw != "-.--" else 0.0
```

**WAR proxy sanity check:** Full-season WAR proxies should be in the 0-10 range. If values are negative or >20, check the normalization formula.

**Team aggregation check:** The API endpoint should aggregate player stats to team level and apply as a probability adjustment. Look for `_load_player_stats_from_corpus()` and `_compute_stats_adjustment()` in the schedule endpoint.

**Frontend indicator:** Game cards should show a WAR badge ("WAR: X vs Y") when player stats are available.
