# Backend sync enrichment recipe

When the mobile app needs to render rich game cards offline, the `/api/mobile/sync` endpoint must compute the same signals the web schedule view exposes — not just raw schedule rows.

## Pattern

The mobile sync service should be a **local, batched version** of the public schedule route. It runs synchronously inside the sync handler and writes everything into the response payload at once.

### 1. Import the same building blocks the web route uses

```python
from src.services import corpus, probabilities
from src.services.market_odds import ml_to_implied_prob, devig
from src.services.narrative import generate_match_narrative
```

### 2. Load raw data, then enrich

```python
def _build_schedule_for_sport(sport: str, team_ids: set[str] | None = None) -> list[dict]:
    games = corpus.load_schedule(sport)
    if not games:
        return []
    ratings = corpus.load_ratings_dict(sport)
    injuries = corpus.load_injuries(sport)
    team_stats = corpus.load_player_stats_aggregated(sport)

    # filter to next 7 days / favorite teams
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=7)
    next_week = [
        g for g in games
        if g.get("date") and today <= datetime.strptime(g["date"].split("T")[0], "%Y-%m-%d").date() <= cutoff
    ]
    if team_ids:
        next_week = [
            g for g in next_week
            if g.get("home_team_id") in team_ids or g.get("away_team_id") in team_ids
        ]

    # build market odds lookup
    market_odds: dict[tuple[str, str, str], float] | None = None
    if next_week and os.environ.get("MARKET_BLEND_DISABLED", "").lower() != "true":
        dates = sorted({g.get("date", "") for g in next_week if g.get("date")})
        raw_rows = corpus.load_market_odds(sport, dates[0], dates[-1]) if dates else []
        market_odds = {}
        for row in raw_rows:
            home_ml = row.get("home_close_ml")
            if home_ml is None:
                continue
            try:
                raw_prob = ml_to_implied_prob(int(home_ml))
                market_odds[(row["date"], row["home_team_id"], row["away_team_id"])] = devig(raw_prob)
            except (ValueError, TypeError):
                continue
        if not market_odds:
            market_odds = None

    # compute probabilities
    enriched = probabilities.compute_game_probabilities(
        next_week, ratings, sport, "balanced",
        injuries_by_team=injuries,
        team_stats=team_stats,
        market_odds=market_odds,
    )

    # attach MC alignment
    mc_by_id = {str(r.get("game_id", "")): r for r in corpus.load_mc_game_dist(sport)}
    for game in enriched:
        mc = mc_by_id.get(game.game_id)
        if mc:
            import json as _json
            hist = mc.get("win_histogram")
            if isinstance(hist, str):
                hist = _json.loads(hist)
            if hist:
                game.mc_histogram = hist
                game.mc_home_win_pct = mc.get("home_win_pct")
        if game.mc_home_win_pct is not None:
            home_phi = ratings.get(game.home_team.id, {}).get("phi", 350)
            away_phi = ratings.get(game.away_team.id, {}).get("phi", 350)
            game.confidence = probabilities.confidence_label(
                home_phi, away_phi,
                home_win_prob=game.home_win_prob,
                mc_home_win_pct=game.mc_home_win_pct,
            )

    # generate sync-friendly narratives (skip LLM to keep payload small)
    for game in enriched:
        game.narrative = generate_match_narrative(game.model_dump())

    # flatten to dicts the mobile client expects
    results = []
    for game in enriched:
        g = game.model_dump()
        home, away = g["home_team"], g["away_team"]
        factors = g.get("factors") or {}
        model_raw = factors.get("base_probability")
        mkt = g.get("market_implied_prob")
        edge_gap = None
        edge_label = ""
        if model_raw is not None and mkt is not None:
            edge_gap = abs(model_raw - mkt)
            if 0.10 <= edge_gap <= 0.20:
                edge_label = "MODEL EDGE"
            elif edge_gap > 0.30:
                edge_label = "CAUTION"
            elif edge_gap < 0.10:
                edge_label = "CLOSE CALL"

        results.append({
            "mobile_id": stable_game_id(g),
            "date": g["date"],
            "home_team_id": home.get("id", ""),
            "away_team_id": away.get("id", ""),
            "home_team_name": home.get("name", ""),
            "away_team_name": away.get("name", ""),
            "sport": sport.upper(),
            "home_win_prob": round(g["home_win_prob"], 3),
            "away_win_prob": round(g["away_win_prob"], 3),
            "mc_home_win_pct": g.get("mc_home_win_pct"),
            "mc_confidence_low": g.get("mc_confidence_low"),
            "mc_confidence_high": g.get("mc_confidence_high"),
            "mc_histogram": g.get("mc_histogram"),
            "confidence": g.get("confidence"),
            "narrative": g.get("narrative", ""),
            "market_implied_prob": mkt,
            "edge_gap": edge_gap,
            "edge_label": edge_label,
            "home_team_rating": round(home.get("rating", 0), 1),
            "away_team_rating": round(away.get("rating", 0), 1),
            "home_team_rd": round(home.get("rd", 0), 1),
            "away_team_rd": round(away.get("rd", 0), 1),
            "home_projected_starter_name": (home.get("projected_starter") or {}).get("name"),
            "away_projected_starter_name": (away.get("projected_starter") or {}).get("name"),
            "home_top_hitters": (home.get("top_hitters") or [])[:3],
            "away_top_hitters": (away.get("top_hitters") or [])[:3],
            "home_top_pitchers": (home.get("top_pitchers") or [])[:3],
            "away_top_pitchers": (away.get("top_pitchers") or [])[:3],
        })
    return results
```

### 3. Update the Pydantic response model before testing the UI

`src/services/mobile_models.py` (or equivalent) must list every field the service now returns. If a key is missing from the model, FastAPI strips it and the mobile client receives a thin payload.

### 4. Keep the payload under the mobile cap

If this enrichment pushes the payload over the mobile cap, trim low-value fields first:
- full WAR tables (keep only top 3)
- full histogram buckets (keep only `mc_home_win_pct`, not the full `mc_histogram`)
- per-player stat detail beyond the essentials (`war`, `ops`, `era`)

## Verification

After backend changes:
1. `pytest tests/test_mobile_api.py -q` passes.
2. A direct curl of `/api/mobile/sync` returns the new keys in the JSON body.
3. The response body size stays under the project's mobile payload cap (e.g., 200 KB).
