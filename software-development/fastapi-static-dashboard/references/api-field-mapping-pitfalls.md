# API Field Mapping Pitfalls — ESPN & Sports Data APIs

Condensed field-mapping lessons from debugging MLB/NBA/NFL extractors against live ESPN API responses.

## ESPN Injuries API — Field Paths Vary by Sport

The same endpoint shape (`/apis/site/v2/sports/{sport}/injuries`) returns different nesting per sport. Do not assume consistency.

### MLB
```json
{
  "injuries": [
    {
      "id": "29",
      "displayName": "Arizona Diamondbacks",
      "injuries": [
        {
          "athlete": {
            "displayName": "Carlos Santana",
            "id": "30280"
          },
          "status": "10-Day-IL",
          "shortComment": "Santana suffered a setback..."
        }
      ]
    }
  ]
}
```
- **Team name:** `displayName` (root of team object) — NOT `team.name`
- **Player name:** `athlete.displayName` — NOT `athlete.fullName`
- **Player ID:** `athlete.id` — string, may be empty for some entries
- **Status:** `status` (flat string like "10-Day-IL", "60-Day-IL")
- **Description:** `shortComment` (flat string)

### NBA / NFL
```json
{
  "injuries": [
    {
      "team": {
        "name": "Boston Celtics",
        "id": "2"
      },
      "injuries": [
        {
          "athlete": {
            "displayName": "Jayson Tatum"
          },
          "status": "Out",
          "shortComment": "Tatum is out with..."
        }
      ]
    }
  ]
}
```
- **Team name:** `team.name` or `team.displayName`
- **Player name:** `athlete.displayName`
- **Status:** `status` (flat: "Out", "Day-To-Day", "Questionable")
- **Description:** `shortComment` (flat)

### Key Difference
| Field | MLB path | NBA/NFL path |
|-------|----------|--------------|
| Team name | `.displayName` | `.team.name` or `.team.displayName` |
| Player name | `.athlete.displayName` | `.athlete.displayName` |
| Player ID | `.athlete.id` | `.athlete.id` |
| Status | `.status` | `.status` |
| Description | `.shortComment` | `.shortComment` |

**Lesson:** Always inspect the actual API response for the sport you're working on. Never assume field paths are consistent across sports, even on the same API endpoint.

## ESPN Standings API — Version Mismatch

### v2 API (`apis/v2/sports/...`)
Required for NBA/NFL. Returns:
```json
{
  "children": [
    {
      "standings": {
        "entries": [
          {
            "team": {"id": "2", "displayName": "Boston Celtics"},
            "stats": [
              {"name": "wins", "value": 60},
              {"name": "losses", "value": 22}
            ]
          }
        ]
      }
    }
  ]
}
```
- **Standings:** `children[0].standings.entries[]`
- **Stats:** `stats[]` as list of `{name, value}` dicts — NOT flat fields

### site v2 API (`apis/site/v2/sports/...`)
Returns minimal data for some sports:
```json
{"fullViewLink": {"href": "..."}}
```
**Lesson:** If the response only contains `fullViewLink`, you're hitting the wrong endpoint. Switch to `apis/v2/sports/...`.

## Verification Script

Run this to inspect the actual field structure before writing the extractor:

```bash
# MLB injuries
curl -s "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries" | \
  python3 -c "import json,sys;d=json.load(sys.stdin);t=d['injuries'][0];print('Team keys:',list(t.keys()));print('Team name:',t.get('displayName','NO displayName'));i=t['injuries'][0];print('Injury keys:',list(i.keys()));print('athlete:',i.get('athlete',{}))"

# NBA standings
curl -s "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings" | \
  python3 -c "import json,sys;d=json.load(sys.stdin);e=d['children'][0]['standings']['entries'][0];print('Entry keys:',list(e.keys()));print('Stats:',e.get('stats',[])[:3])"
```

## Corpus Loader — Double-Serialization Trap

The `SportsEvidenceIngestor` methods (`ingest_elo_ratings`, `ingest_injury_report`, etc.) call `json.dumps()` internally. Passing a pre-serialized JSON string causes double-serialization.

**Wrong:**
```python
payload = {"count": len(games), "games": games}
return self._load("game_results", json.dumps(payload))  # ❌
```

**Right:**
```python
payload = {"count": len(games), "games": games}
return self._load("game_results", payload)  # ✓
```

**Symptom:** `could not convert string to float: '{"count": 97, ...}'` — the ingestor tries to iterate over the JSON string's characters or calls `float()` on it.
