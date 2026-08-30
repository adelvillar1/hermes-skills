# Pitcher Matchup Modeling for Sports Forecasting

Model starting pitcher matchups as an additional probability adjustment layer on top of base ELO ratings and team-level WAR differentials.

## When to Use

- MLB game predictions where starting pitcher quality significantly impacts outcomes
- Any sport with a clear "starting player vs starting player" matchup that dominates game outcome (NBA star matchup, NFL QB matchup)
- When corpus has individual player stats with role identification (starters vs relievers/bench)

## When to Skip

- Sports where individual matchups are less predictive than team-level quality (soccer, hockey)
- When player role data (starter/reliever/bench) is not available in the corpus
- When the prediction horizon is far enough that projected starters are speculative

## Data Requirements

The corpus must have `player_stats` evidence items with:
- `stat_type`: "pitching" (or equivalent for the sport)
- `games_started`: integer > 0 for starters, 0 for relievers/bench
- `era`, `whip`, `war_proxy`, `innings_pitched`, `strikeouts`, `walks`

Example corpus query to verify data:
```python
import sqlite3, json
conn = sqlite3.connect(".forecast/corpus.db")
row = conn.execute(
    "SELECT payload_json FROM evidence_items WHERE category = 'player_stats' AND sport = 'mlb' LIMIT 1"
).fetchone()
payload = json.loads(row["payload_json"])
starters = [s for s in payload["player_stats"] if s.get("games_started", 0) > 0]
print(f"Starters: {len(starters)}")
```

## Architecture

```
Base ELO Probability
        +
Team WAR Adjustment (hitting/pitching/fielding)
        +
Pitcher Matchup Adjustment (starter ERA/WHIP/WAR + bullpen)
        +
Injury Adjustment
        =
Final Win Probability
```

## Implementation

### 1. Extend Team Stats Loader to Track Rotation

The `_load_player_stats_from_corpus()` function needs to separate starters from relievers:

```python
def _load_player_stats_from_corpus(sport: str) -> dict[str, dict]:
    """Load aggregated player stats per team from the evidence corpus.
    
    Returns team_id -> {hitting_war, pitching_war, fielding_war, total_war,
                        top_hitters, top_pitchers, rotation, bullpen_war}
    """
    # ... existing connection code ...
    
    for stat in payload.get("player_stats", []):
        team_id = stat.get("team_id", "")
        if not team_id:
            continue
        if team_id not in team_stats:
            team_stats[team_id] = {
                "hitting_war": 0.0,
                "pitching_war": 0.0,
                "fielding_war": 0.0,
                "total_war": 0.0,
                "top_hitters": [],
                "top_pitchers": [],
                "rotation": [],  # starters ordered by quality
                "bullpen_war": 0.0,
            }
        
        war = stat.get("war_proxy", 0)
        stype = stat.get("stat_type", "")
        
        if stype == "pitching":
            team_stats[team_id]["pitching_war"] += war
            pitcher = {
                "name": stat.get("player_name", ""),
                "war": war,
                "era": stat.get("era", 0),
                "whip": stat.get("whip", 0),
                "ip": stat.get("innings_pitched", 0),
                "gs": stat.get("games_started", 0),
                "so": stat.get("strikeouts", 0),
                "bb": stat.get("walks", 0),
            }
            team_stats[team_id]["top_pitchers"].append(pitcher)
            
            # Track starters separately for rotation quality
            if stat.get("games_started", 0) > 0:
                team_stats[team_id]["rotation"].append(pitcher)
            else:
                team_stats[team_id]["bullpen_war"] += war
        
        # ... hitting and fielding handling ...
    
    # Sort rotation by WAR (best starters first)
    for tid in team_stats:
        team_stats[tid]["rotation"].sort(key=lambda x: x["war"], reverse=True)
    
    return team_stats
```

### 2. Compute Pitcher Matchup Adjustment

```python
def _compute_pitcher_matchup_adjustment(
    home_rotation: list[dict],
    away_rotation: list[dict],
    home_bullpen_war: float,
    away_bullpen_war: float,
) -> tuple[float, dict, dict]:
    """Compute win probability adjustment from starting pitcher matchup.

    Uses the #1 starter from each rotation as the projected matchup.
    Compares ERA, WHIP, and WAR to estimate which starter has the edge.
    Also factors in bullpen strength (relievers not in rotation).

    Returns (adjustment, home_starter_dict, away_starter_dict).
    """
    if not home_rotation and not away_rotation:
        return 0.0, {}, {}

    home_ace = home_rotation[0] if home_rotation else {"war": 0, "era": 4.5, "whip": 1.35}
    away_ace = away_rotation[0] if away_rotation else {"war": 0, "era": 4.5, "whip": 1.35}

    # ERA differential (lower is better, so invert)
    league_avg_era = 4.5
    home_era_adv = (league_avg_era - home_ace.get("era", league_avg_era)) / league_avg_era
    away_era_adv = (league_avg_era - away_ace.get("era", league_avg_era)) / league_avg_era
    era_diff = home_era_adv - away_era_adv  # positive = home starter better

    # WHIP differential (lower is better)
    league_avg_whip = 1.35
    home_whip_adv = (league_avg_whip - home_ace.get("whip", league_avg_whip)) / league_avg_whip
    away_whip_adv = (league_avg_whip - away_ace.get("whip", league_avg_whip)) / league_avg_whip
    whip_diff = home_whip_adv - away_whip_adv

    # WAR differential
    war_diff = home_ace.get("war", 0) - away_ace.get("war", 0)

    # Bullpen differential
    bullpen_diff = home_bullpen_war - away_bullpen_war

    # Composite starter score (weighted)
    starter_score = era_diff * 0.40 + whip_diff * 0.30 + (war_diff / 5.0) * 0.30

    # Bullpen matters ~30% as much as starter for a single game
    bullpen_score = bullpen_diff / 10.0  # normalize

    total_adjustment = starter_score * 0.08 + bullpen_score * 0.03
    return max(-0.08, min(0.08, total_adjustment)), home_ace, away_ace
```

**Formula rationale:**
- ERA: 40% weight — most predictive single pitching stat for game outcomes
- WHIP: 30% weight — measures baserunner prevention, highly correlated with run prevention
- WAR: 30% weight — captures overall value including volume and context
- Bullpen: ~30% as impactful as starter for a single game (relievers handle 3-4 innings)
- Cap at ±8% — prevents overfitting on a single pitcher when lineup/bullpen also matter

### 3. Apply in Prediction Loop

```python
# In _compute_probabilities():

# Apply team-level WAR adjustment (existing)
stats_adjustment = _compute_stats_adjustment(home_stats, away_stats)
adjusted_home_prob += stats_adjustment
adjusted_home_prob = max(0.05, min(0.95, adjusted_home_prob))

# Apply pitcher matchup adjustment (MLB only)
pitcher_adjustment = 0.0
home_starter = {}
away_starter = {}
if sport.lower() == "mlb":
    home_rotation = home_stats.get("rotation", [])
    away_rotation = away_stats.get("rotation", [])
    home_bullpen = home_stats.get("bullpen_war", 0)
    away_bullpen = away_stats.get("bullpen_war", 0)
    pitcher_adjustment, home_starter, away_starter = _compute_pitcher_matchup_adjustment(
        home_rotation, away_rotation, home_bullpen, away_bullpen
    )
    adjusted_home_prob += pitcher_adjustment
    adjusted_home_prob = max(0.05, min(0.95, adjusted_home_prob))
```

### 4. Rotation Quality Label

```python
def _rotation_quality(rotation):
    if not rotation:
        return "unknown"
    ace_war = rotation[0].get("war", 0)
    if ace_war >= 3.0:
        return "elite"
    elif ace_war >= 2.0:
        return "strong"
    elif ace_war >= 1.0:
        return "average"
    return "weak"
```

### 5. Extend API Models

```python
class MatchupTeam(BaseModel):
    id: str
    name: str
    rating: float
    rd: float
    win_probability: float
    top_hitters: Optional[List[Dict[str, Any]]] = None
    top_pitchers: Optional[List[Dict[str, Any]]] = None
    team_war: Optional[Dict[str, float]] = None
    projected_starter: Optional[Dict[str, Any]] = None
    rotation_quality: Optional[str] = None
```

### 6. Include in Response

```python
home_team=MatchupTeam(
    id=home_id,
    # ... existing fields ...
    projected_starter={
        "name": home_starter.get("name", "TBD"),
        "era": home_starter.get("era"),
        "whip": home_starter.get("whip"),
        "war": round(home_starter.get("war", 0), 2),
    } if home_starter else None,
    rotation_quality=_rotation_quality(home_stats.get("rotation", [])),
),
```

## Response Example

```json
{
  "home_team": {
    "id": "PIT",
    "name": "Pirates",
    "projected_starter": {
      "name": "Paul Skenes",
      "era": 1.98,
      "whip": 0.64,
      "war": 3.12
    },
    "rotation_quality": "elite"
  },
  "away_team": {
    "id": "COL",
    "name": "Rockies",
    "projected_starter": {
      "name": "Chase Dollander",
      "era": 3.89,
      "whip": 1.30,
      "war": 1.97
    },
    "rotation_quality": "average"
  },
  "factors": {
    "base_probability": 0.515,
    "stats_adjustment": 0.023,
    "pitcher_adjustment": 0.042,
    "injury_adjustment": -0.009,
    "home_win_prob": 0.57
  }
}
```

## Key Design Decisions

1. **#1 starter as projected matchup:** Uses the best starter by WAR. In reality, rotations cycle, but for a generic "next game" prediction without schedule data, the ace is the most likely high-impact starter.

2. **League averages as baselines:** ERA 4.50 and WHIP 1.35 are MLB-wide averages. Adjust for other leagues/sports.

3. **Bullpen factored at 30% of starter impact:** For a 9-inning game, the bullpen typically handles 3-4 innings (~40% of outs). But bullpen usage is highly variable, so we discount to 30%.

4. **Cap at ±8%:** Even a Cy Young vs replacement-level matchup shouldn't swing probability more than ~8% because lineup, defense, and bullpen also matter.

5. **Sport-gated:** Only applies to MLB (or sports with clear starter/reliever distinction). NFL QB matchups could use a similar pattern with passer rating/QBR.

## Verification Checklist

- [ ] Corpus has `player_stats` with `games_started` field
- [ ] Starters identified correctly (`games_started > 0`)
- [ ] Rotation sorted by WAR (best first)
- [ ] `_compute_pitcher_matchup_adjustment()` returns adjustment in [-0.08, 0.08]
- [ ] Adjustment applied only for MLB (`sport.lower() == "mlb"`)
- [ ] Response includes `projected_starter` with name, ERA, WHIP, WAR
- [ ] Response includes `rotation_quality` (elite/strong/average/weak/unknown)
- [ ] `factors` object includes `pitcher_adjustment`
- [ ] All tests pass after integration
- [ ] Docker container rebuilt and verified

## Extending to Other Sports

### NFL QB Matchup
```python
def _compute_qb_matchup_adjustment(home_qb, away_qb):
    # Use passer rating, QBR, or EPA/play
    rating_diff = (home_qb.get("passer_rating", 90) - away_qb.get("passer_rating", 90)) / 100
    return max(-0.06, min(0.06, rating_diff * 0.06))
```

### NBA Star Matchup
```python
def _compute_star_matchup_adjustment(home_stars, away_stars):
    # Compare top 2 players by PER or VORP
    home_per = sum(p.get("per", 15) for p in home_stars[:2]) / 2
    away_per = sum(p.get("per", 15) for p in away_stars[:2]) / 2
    per_diff = (home_per - away_per) / 30
    return max(-0.05, min(0.05, per_diff * 0.05))
```
