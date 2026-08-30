# Multi-Signal Confidence Composite

When a single-variable classifier has no data variation (all inputs cluster in one tier), the fix is adding discriminating signals as a weighted composite.

## The Problem

MLB phi values are all 57-60 mid-season (600+ games played). Combined phi for any matchup is ~82-84. With gates at 80/140/250, every game is "moderate". No variation.

The classifier isn't broken — the input variable just has no discriminative power for this data distribution.

## The Solution: Weighted Multi-Signal Composite

Three signals, weighted by actionability:

| Signal | Weight | What it measures | Source |
|--------|--------|-----------------|--------|
| **Edge** | 50% | How far from 50/50 | Win probability |
| **Phi** | 30% | Rating certainty | Glicko-2 φ |
| **MC alignment** | 20% | Model vs Monte Carlo agreement | MC simulation |

```python
def confidence_label(
    phi_home: float,
    phi_away: float,
    home_win_prob: float | None = None,
    mc_home_win_pct: float | None = None,
) -> str:
    # Signal 1: rating certainty (0-1, higher = more certain)
    combined = math.sqrt(phi_home ** 2 + phi_away ** 2)
    phi_score = max(0.0, 1.0 - combined / 350.0)

    # Signal 2: prediction edge (0-1, higher = clearer favorite)
    edge_score = 0.0
    if home_win_prob is not None:
        edge_score = abs(home_win_prob - 0.5) * 2.0  # 0 at 50/50, 1 at 100/0

    # Signal 3: model-MC alignment (0-1, higher = more agreement)
    mc_score = 0.5  # neutral default when no MC data
    mc_divergent = False  # flag for hard cap at "low"
    if mc_home_win_pct is not None and home_win_prob is not None:
        model_side = home_win_prob >= 0.5
        mc_side = mc_home_win_pct >= 0.5
        if model_side != mc_side:
            # Direction disagreement — hard cap
            mc_score = 0.0
            mc_divergent = True
        else:
            diff = abs(home_win_prob - mc_home_win_pct)
            if diff > 0.15:
                # Significant divergence — hard cap
                mc_score = 0.1
                mc_divergent = True
            elif diff > 0.10:
                mc_score = 0.4
            elif diff > 0.05:
                # Good agreement — same team favored, similar margin
                mc_score = 0.7
            else:
                # Tight alignment
                mc_score = 1.0 - diff * 5.0

    # Blend: 30% phi, 50% edge, 20% MC
    score = 0.3 * phi_score + 0.5 * edge_score + 0.2 * mc_score

    # Hard cap: MC divergence forces "low" regardless of other signals
    if mc_divergent:
        return "low" if score >= 0.15 else "speculative"

    if score >= 0.52:
        return "high"
    elif score >= 0.35:
        return "moderate"
    elif score >= 0.15:
        return "low"
    return "speculative"
```

## Design Principles

1. **Edge gets the highest weight (50%)** — it's the most actionable signal. A 78% favorite is more useful than a 52% coin flip, regardless of rating certainty.

2. **Phi gets moderate weight (30%)** — it measures data quality (how converged the ratings are), not prediction quality.

3. **MC alignment gets the lowest weight (20%)** — it's a consistency check. Agreement boosts confidence; disagreement reduces it.

4. **MC divergence is a hard cap** — direction disagreement OR >15% magnitude gap forces "low" regardless of phi/edge. Two independent methods disagreeing is a red flag that overrides all other signals.

5. **Neutral default for missing signals** — when MC data isn't available, `mc_score = 0.5` (neutral). The classifier still works with partial data.

6. **Domain-calibrated thresholds** — the "high" threshold (0.52) is calibrated to the actual probability distribution the model produces (rarely above 75%), not to theoretical ideals. 65%+ with good MC alignment = "high" in this domain.

## MC Scoring Tiers

| Gap | mc_score | Meaning |
|-----|----------|---------|
| < 5% | 0.8–1.0 | Tight alignment — high agreement |
| 5–10% | 0.7 | Good agreement — same direction, similar margin |
| 10–15% | 0.4 | Moderate divergence — same direction, different margin |
| > 15% | 0.1 + hard cap | Significant divergence — forces "low" |
| Direction disagree | 0.0 + hard cap | Fundamental disagreement — forces "low" |

## Result Distribution (MLB, phi≈58)

| Scenario | Edge | MC Gap | Score | Label |
|----------|------|--------|-------|-------|
| LAD vs COL (78% fave, MC 76%) | 0.56 | 2% | 0.69 | **high** |
| ATL vs TOR (65% fave, MC 63%) | 0.30 | 2% | 0.51 | **high** |
| NYY vs BOS (58% fave, MC 55%) | 0.16 | 3% | 0.41 | moderate |
| CHC vs OAK (52% coin flip, MC 51%) | 0.04 | 1% | 0.43 | moderate |
| Model 70% / MC 52% (divergent) | 0.40 | 18% | — | **low** (hard cap) |
| Model 60% / MC 40% (disagree) | 0.20 | — | — | **low** (hard cap) |
| No MC data + coin flip | 0.04 | — | 0.34 | low |
| No MC data + 60% fave | 0.20 | — | 0.41 | moderate |

## Iteration History

The thresholds went through 4 iterations:

1. **v1 (0.65 for "high")**: Required ~78%+ predictions. Almost nothing qualified. User: "all games show moderate."
2. **v2 (0.55 for "high")**: Better, but 66% with 8% MC gap still showed "moderate" (score 0.53).
3. **v3 (0.52 for "high")**: 65%+ with good MC alignment now hits "high". But MC scoring for 5-10% gap was too harsh (0.5 = neutral).
4. **v4 (0.52 + warmer MC)**: 5-10% gap scored as 0.7 (good agreement). Screenshot games (66-70% with 8-9% MC gaps) all show "high".

The lesson: **iterate with real data, not synthetic test cases.** The user showed a screenshot of actual dashboard cards — that's the ground truth for whether the thresholds are right.

## Tests

```python
class TestConfidenceLabel:
    def test_high_confidence(self):
        # 65%+ with tight MC alignment → "high"
        assert confidence_label(58, 58, home_win_prob=0.65, mc_home_win_pct=0.63) == "high"

    def test_moderate_confidence(self):
        # 58% favorite with MC agreement → "moderate"
        assert confidence_label(58, 58, home_win_prob=0.58, mc_home_win_pct=0.55) == "moderate"

    def test_low_confidence(self):
        # Coin flip with no MC → "low"
        assert confidence_label(58, 58, home_win_prob=0.52) == "low"

    def test_speculative(self):
        # High phi + coin flip → "speculative"
        assert confidence_label(350, 350, home_win_prob=0.51) == "speculative"

    def test_mc_disagreement_downgrades(self):
        # Direction disagreement → hard cap at "low"
        assert confidence_label(58, 58, home_win_prob=0.60, mc_home_win_pct=0.40) == "low"

    def test_mc_magnitude_divergence(self):
        # Same direction but >15% gap → hard cap at "low"
        assert confidence_label(58, 58, home_win_prob=0.70, mc_home_win_pct=0.52) == "low"

    def test_mc_tight_alignment_boosts(self):
        # Strong favorite with tight MC alignment → "high"
        assert confidence_label(58, 58, home_win_prob=0.75, mc_home_win_pct=0.73) == "high"

    def test_no_edge_info(self):
        # Without home_win_prob, edge_score=0 → lower confidence
        assert confidence_label(50, 50) == "low"
```

## When to Use This vs Simple Threshold Re-tuning

| Situation | Fix |
|-----------|-----|
| Threshold is unreachable (phi < 50 but data is 60-90) | Re-tune thresholds |
| All inputs land in one tier (phi clustered at 58) | Add more signals |
| Two competing functions with different thresholds | Delete dead code, use the correct one |
| Classifier works but UI filter is too restrictive | Fix the filter hierarchy (add decisiveness gate) |
| Thresholds are correct but don't match domain distribution | Calibrate to actual distribution |
| Model and simulation disagree → confidence should drop | Add MC divergence hard cap |

## Key Insight

When a single-variable classifier has no variation, the fix is NOT lowering thresholds (that just inverts the dead-tier problem). The fix is adding signals that DO vary. For sports predictions, win probability distance from 50% is the most natural discriminating signal — it directly measures how actionable the prediction is.

And when the domain distribution doesn't span the full theoretical range, calibrate to the domain. A 65% prediction in a sport where 70% is the ceiling IS a high-confidence pick.
