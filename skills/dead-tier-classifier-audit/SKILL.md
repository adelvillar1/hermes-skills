---
name: dead-tier-classifier-audit
description: Use when a threshold-based classifier produces suspicious output distributions — one tier never fires, or fires for nearly every input. The pattern is to check whether the classifier's threshold gates are actually reachable for the data the system produces, and re-tune them to match the real distribution. Use whenever a model emits categorical labels (high/medium/low, tier 1/2/3, severity A/B/C) gated on numerical thresholds — confidence models, Glicko-2 RD tiers, rating buckets, content moderation categories, priority levels. Trigger phrase is "the X calculation seems too cautious" or "we never see any X-tier results."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [classifier, calibration, threshold, tier, debugging, ml, glicko, confidence]
    related_skills: [debug-issue, systematic-debugging, root-cause-first-debugging, llm-render-with-canonical-numbers, design-review]
---

# Dead-Tier Classifier Audit

The failure mode this skill addresses — a threshold-based classifier (one that assigns each input to a categorical tier based on numerical thresholds) has a tier that never fires, or fires for nearly every input. The model isn't expressing uncertainty — its gates are structurally unreachable for the data the system actually produces.

**Concrete example.** A sports analytics confidence model:

```python
if phi < 50 and scenario_score > 0.7: return "high"
if phi < 100 and scenario_score > 0.5: return "moderate"
if phi < 150: return "low"
return "speculative"
```

The model "told" the user that 78 upcoming MLB games were `moderate` (71/78) or `low` (7/78), and never `high` (0/78) or `speculative` (0/78). The user reasonably concluded the system was being too cautious. The real cause — the actively-rated teams in the corpus have Glicko-2 `phi` values in the 60-90 range, so the `phi < 50` gate for `high` was **unreachable** for any team with a working rating. The "high" tier was a dead branch in the model.

The model wasn't saying "I'm uncertain about all 78 games" — it was structurally incapable of saying "high" given the data the system produces.

## The Pattern (5 steps)

### 1. Survey the output distribution of the classifier

When a user reports "the X is too cautious" or you notice a tier that never fires, the first step is to **count** how many inputs hit each tier. Not guess — count.

```python
from collections import Counter
tier_counts = Counter(classifier(x) for x in inputs)
print(tier_counts)
# Counter({'moderate': 71, 'low': 7, 'high': 0, 'speculative': 0})
```

If any tier is at 0% or 100%, **stop and investigate** before assuming the model is miscalibrated by design. The asymmetry is the signal.

### 2. Find the threshold gates in the classifier source

Grep for the tier-returning code:

```bash
grep -rn "return 'high'\|return 'moderate'\|return 'low'\|return 'speculative'" src/
```

Read the function. For each tier, find the numerical threshold (e.g., `phi < 50`, `confidence > 0.7`, `RD > 200`). Write them down.

### 3. Measure the actual data distribution for each threshold variable

For each variable that gates a tier, query the corpus for its actual range. The variables that gate a tier MUST be observable in the data the classifier runs on.

```python
# What range of phi does the corpus actually have?
cur.execute('SELECT MIN(rd), MAX(rd), AVG(rd) FROM ratings WHERE sport = ?', ('MLB',))
# (69.8, 79.1, 72.2) — every team is in 69-79 range
```

The threshold gates are about to be compared to this distribution. If a gate says `phi < 50` and the data is 60-90, the gate is dead.

### 4. Check whether the gates ever fire for the data distribution

For each gate, ask the simple question — **does any input from the data distribution satisfy the gate?**

- Gate `phi < 50`, data range 60-90 → **0% of inputs satisfy** → dead tier
- Gate `phi < 100`, data range 60-90 → **100% of inputs satisfy** → gate is effectively no-op; the next gate or score condition becomes the actual classifier
- Gate `phi < 150`, data range 60-90 → **100% of inputs satisfy** → same issue
- Gate `phi < 200`, data range 60-90 → **100% of inputs satisfy** → same

If a tier's gate is unreachable, that tier is dead. If a tier's gate is always-true, that tier's *next* gate becomes the actual decision boundary.

### 5. Re-tune gates to match the data distribution

The fix — shift gates to where the data actually is, preserving the semantic meaning of each tier.

```python
# Before (gates unreachable for phi in 60-90):
if phi < 50 and scenario_score > 0.7:   return "high"
if phi < 100 and scenario_score > 0.5:  return "moderate"
if phi < 150:                           return "low"
return "speculative"

# After (gates calibrated to actual phi distribution):
if phi < 100 and scenario_score > 0.7:  return "high"
if phi < 150 and scenario_score > 0.5:  return "moderate"
if phi < 200:                           return "low"
return "speculative"
```

The new gates:
- `high` requires `phi < 100` (data max is 79.1, so some teams qualify when paired with high scenario_score) — preserves "high = model is sure"
- `moderate` requires `phi < 150` (always true) but with `score > 0.5` — score becomes the differentiator
- `low` requires `phi < 200` (always true) with default score
- `speculative` is the safety net for fresh data with phi >= 200 (newly-rated teams)

The semantic meaning of each tier is preserved. Only the gates move.

## Why This Bug Class Is Hard to Spot

The classifier looks correct in isolation. The threshold `phi < 50` is a perfectly reasonable number. The function reads cleanly. Unit tests pass when called with `phi=30, score=0.8` — they return "high" correctly. The problem only shows up when you compare the threshold to the **actual data distribution** the system produces.

This is a **boundary problem**, not a logic problem. The unit tests are testing the function in isolation; they don't test the function against the data the system actually feeds it.

The fix requires:
1. Knowing the data distribution (query the corpus)
2. Knowing the function's thresholds (read the source)
3. Comparing the two

Any one of those without the other two produces a confidently-wrong answer.

## What "Re-tuning" Means (and Doesn't)

**Re-tuning is NOT** "lower every threshold to make the dead tier fire." That just inverts the dead-tier problem — now the "high" tier fires for everything and the lower tiers become dead.

**Re-tuning IS** "shift the gates to where the data actually falls, so the distribution of tier assignments reflects the model's intent."

If the data has phi in 60-90, gates at 50/100/150/200 are wrong. Gates at 100/150/200/250 would be right (one tier per 50-point band). Gates at 100/200/300/400 would also be right (fewer tiers, each meaningful).

The constraint is — each gate must fire for SOME inputs and NOT fire for others. If a gate always fires (or never fires), it's not a gate — it's a constant.

## The Re-Tuning Has a "Test What Real Data Does" Companion

After re-tuning, write a test that asserts the new gates behave correctly against the real data range:

```python
def test_phi_in_realistic_range(self, adapter):
    """Regression — a team at the realistic phi MUST classify as
    'high' when scenario_score is also high."""
    # 2026-06-01 fix — gates were unreachable for phi in 60-90
    assert adapter.calibrate_confidence(0.9, 80) == "high"   # realistic phi, high score
    assert adapter.calibrate_confidence(0.6, 80) == "moderate"  # same phi, mid score
    assert adapter.calibrate_confidence(0.3, 80) == "low"   # same phi, low score
```

This test would have caught the dead-tier bug at the time it was introduced. The bug shipped because nobody asked "does a team at phi=80 ever reach the high tier?" — the unit tests only checked `phi=30` (a value no live team has).

## Worked Example: Glicko-2 Confidence Thresholds

The full session that surfaced this pattern is in `references/elo-scenario-lab-confidence-thresholds.md`. The data:

| phi range | # teams in MLB | What gate "fires" |
|---|---|---|
| 0-50 | 0 | dead gate (no team qualifies) |
| 50-100 | 30 (all of them) | always fires |
| 100-150 | 0 | impossible (above max) |
| 150-200 | 0 | impossible |
| 200+ | 0 | impossible |

The old gates `phi < 50 / 100 / 150 / else` mapped to a data range where only the second gate was reachable, making "high" dead and "moderate" the only meaningful outcome.

After the fix:

| New gate | What it means | Realistic phi |
|---|---|---|
| `phi < 100 and score > 0.7` | high | qualifies when team is well-calibrated AND model is confident |
| `phi < 150 and score > 0.5` | moderate | always (phi) + some (score) |
| `phi < 200` | low | always |
| else | speculative | safety net |

Verified — confidence distribution went from `0/71/7/0` to `57/14/7/0`. Every tier now has data.

## Variant: Single-Variable Classifier with No Data Variation

A harder case: the threshold gates ARE reachable, but the input variable has no variation in the data. All inputs land in the same tier because the variable is clustered, not because the gates are wrong.

**Real example:** MLB phi values are all 57-60 (mid-season, 600+ games played). Combined phi for any matchup is ~82-84. With gates at 80/140/250, every game lands in "moderate" (80-140). The gates are correct for the variable — the problem is that the variable itself has no discriminative power for this data distribution.

**The fix isn't threshold re-tuning — it's adding more discriminating signals.** Redesign the classifier as a weighted multi-signal composite:

```python
def confidence_label(phi_home, phi_edge, home_win_prob=None, mc_home_win_pct=None):
    # Signal 1: rating certainty (phi) — 30% weight
    combined = sqrt(phi_home**2 + phi_edge**2)
    phi_score = max(0.0, 1.0 - combined / 350.0)

    # Signal 2: prediction edge (win probability) — 50% weight
    edge_score = abs(home_win_prob - 0.5) * 2.0 if home_win_prob else 0.0

    # Signal 3: model-MC alignment — 20% weight
    mc_score = compute_mc_alignment(home_win_prob, mc_home_win_pct)

    score = 0.3 * phi_score + 0.5 * edge_score + 0.2 * mc_score
    # Map to tiers...
```

**Why this works:** When phi has no variation (all ~58), edge and MC alignment become the differentiating signals. A 78% favorite gets "high"; a 52% coin flip gets "low"; MC disagreement downgrades by one tier. The phi component still contributes (early-season with high phi → lower base score), but it's not the sole signal.

**Design principles for multi-signal composites:**
- **Edge (distance from 50%) gets the highest weight** — it's the most actionable signal for the user
- **Phi gets moderate weight** — it measures data quality, not prediction quality
- **MC alignment gets the lowest weight** — it's a consistency check, not a primary signal
- **MC disagreement should always downgrade** — if two independent methods disagree, confidence should decrease regardless of other signals
- **Neutral default for missing signals** — when MC data isn't available, use 0.5 (neutral) so the classifier still works with partial data

See `references/multi-signal-confidence-composite.md` for the full implementation and test cases.

## When to Use This Pattern

Use it whenever:
- A classifier produces categorical labels (high/medium/low, tier 1/2/3, severity A/B/C, etc.)
- The classifier uses numerical thresholds to assign labels
- You see one of: (a) a tier with 0% of inputs, (b) a tier with 100% of inputs, (c) a tier the user never sees ("we never get any X-tier results"), (d) a user reporting "the X calculation seems too cautious"
- The system has been running for a while and the distribution looks suspicious
- A downstream UI filter is `confidence === 'high'` (or any classifier tier) and that filter is suspiciously empty/sparse. The dead tier can manifest as "this section never has any results" or "this section is showing only low-quality matches." Either is a UI signal that the upstream classifier is miscalibrated.

## The Downstream-UI Consequence (the part this skill got wrong in v1)

The first version of this skill described the bug as a model-level problem ("high tier never fires"). It is, but the *user-visible* failure is downstream of the model: a UI section that filters on the dead tier, that always looks empty, that the user debugs as a UI bug when it's really a classifier-tier bug.

**Concrete example:** a "Top Picks" dashboard section that filters `confidence === 'high' && alignment < 0.10`. After the dead-tier fix, 57/78 games are `high`, so the filter has 57 candidates. But the user looks at the section and reports "the picks are 50%-55% — essentially toss-ups." The bug is NOT in the filter (the filter is working). The bug is in the *alignment metric* — alignment near 50/50 is trivially small because both methods cluster at the uncertain end, so the filter is correctly selecting the *least-bad toss-ups* instead of *real picks*.

The fix is at the same level as the dead-tier fix: **the decisiveness prerequisite**. The filter needs a *primary* gate (decisiveness, i.e. max(elo, 1-elo) >= 0.65) and a *secondary* gate (alignment) that only matters once decisiveness is established. The two-tier hierarchy:

```
filter criteria, in order:
  1. decisiveness (favored side >= 65% of ELO prediction)  ← GATE
  2. confidence in {high, moderate}                        ← GATE
  3. alignment < 10%                                        ← QUALITY MULTIPLIER
  4. CI width narrowest                                     ← TIEBREAKER
```

Without the decisiveness gate, alignment is meaningless: 51% / 53% is "aligned" by 2% but is a coin-flip. The user's complaint ("essentially a toss-up") is the real signal that the filter hierarchy is wrong.

**The general pattern for ranked UI surfaces:** alignment and agreement are *quality multipliers*, not gates. Decisiveness (distance from 50/50) is the gate. Without the gate, "aligned" just means "both methods agreed the game was a coin-flip" — which is not actionable.

**Cross-skill signal:** this is the same anti-pattern that `llm-render-with-canonical-numbers` warns against (LLM prose contradicts canonical numbers), but applied to ranking/filtering. The principle is the same: **a downstream surface can be confidently-wrong because its inputs are aligned but uninformative.** A guard (the decisiveness gate) is what makes the ranking honest.

## The "Honest Label" Tiering Pattern

When a UI section like "Top Picks" cannot honestly say a single thing about *all* the candidates it surfaces, **tier the label by quality** rather than softening the copy:

- Δ < 3%: "✓ Model + MC agree" (committed assertion)
- Δ < 10%: "△ Model & MC within 10%" (qualified, still actionable)
- Δ >= 10%: **filter out**, don't surface in a "Top Picks" section at all

The alternative — surfacing diverge cards with a softer label like "diverge" — contradicts the section title. A "Top Picks" section promises winners, not coin-flips. If the section is going to be sparse, let it be sparse. Honest emptiness > dishonest fullness.

Don't use it when:
- The classifier is intentionally binary (positive/negative, pass/fail) — check sensitivity/recall instead
- The threshold was tuned adversarially (e.g., for fraud detection where most inputs should be negative) — 0% in a tier is the goal
- The data is genuinely uncertain about the right answer — the classifier is correctly expressing uncertainty, not structurally unable to

## Anti-Patterns to Avoid

- **"Just lower the threshold."** If "high" is dead because the gate is too high, lowering it to phi<60 might make "high" fire — but the score condition is still score>0.7, which is independent. Re-tune all gates together, not just the broken one.
- **"Use percentile-based thresholds."** Percentile-based is more robust to distribution drift, but it changes the semantic meaning of each tier ("top 10%" vs "phi<100"). If the product spec says "high means phi<100," percentile is wrong. If the product spec says "high means top 10% of confidence," percentile is right.
- **"Add a default branch to make dead tiers never fire."** That's a workaround, not a fix. The dead tier is a symptom of miscalibrated thresholds, not a missing default.
- **"Just disable the dead tier."** If a tier never fires, removing it from the output doesn't fix the underlying problem — it just hides it. The user still can't distinguish "high confidence" from "moderate confidence."
- **"Adjust the threshold until the distribution looks right."** Trial-and-error is tempting but produces thresholds that are correct for the current data only. The structural fix is — read the data, set the gates to where the data falls, write a test that pins the contract.

## Related Patterns

- **llm-render-with-canonical-numbers** — different failure mode. LLM prose contradicts canonical machine numbers. This skill is about thresholds vs data, not LLMs vs numbers. BUT — the philosophical kinship is real: both are about **honest output at boundary cases**. A dead-tier classifier downstream surface (Top Picks always empty) and an LLM-rendered surface (prose contradicts tile) both fail the same way: the data is right, the rendering is wrong. The defense in both cases is a *guard* at the data-source level (recalibrate gates, or pin the canonical narrative).
- **systematic-debugging** — 4-phase root cause approach. The dead-tier audit IS a kind of systematic debugging applied to classifier thresholds. The other skill's "form a hypothesis from source material, verify once, then fix" applies here directly.
- **design-review** — covers UI-facing dead states. A dead-tier classifier sometimes manifests as a dead UI section (e.g., a "High Confidence" filter that never matches any item). The design review catches the symptom; this skill fixes the cause. Also: the visual review in a design-review pass can catch the *downstream* bug that this skill describes — a Top Picks section labeled "Model + MC agree" on a 14.5%-delta card is a 🔴 honesty bug visible in the rendered output but invisible in the source code.

## Variant: Two Competing Classifier Functions

A harder-to-spot variant: TWO functions compute the same labels with different thresholds. One is dead code with correct thresholds; the other is production with wrong thresholds. Grepping for `return "high"` finds both — you can't tell which is live without tracing the call chain.

**Real example:** `confidence_label()` (combined phi, thresholds 80/140/250) was never called. `adapter.calibrate_confidence()` (avg_phi, thresholds 175/185/250) was production. With MLB phi≈58, avg=58 < 175 → everything "high". The correct function would give combined≈83 → "moderate".

**Diagnostic:** grep for all functions returning tier labels, trace which is actually called, compare thresholds. The fix: replace the production call with the corrected function.

Full writeup: `references/competing-classifier-functions.md`

## Variant: Domain-Calibrated Thresholds

When the model's probability distribution doesn't span the full 0-1 range, thresholds calibrated to theoretical ideals produce a dead zone. The fix: calibrate to the **actual distribution** the model produces, not to what "should" exist.

**Real example:** The sports prediction model rarely produces probabilities above 75%. A threshold of `score >= 0.65` for "high" required ~78%+ predictions to qualify — almost nothing in the actual distribution. The user said "a high probability should be anything above 65%."

**Diagnostic:** Query the actual probability distribution:
```python
# What's the actual range?
probs = [g.home_win_prob for g in games]
print(f"min={min(probs):.0%}, max={max(probs):.0%}, p75={sorted(probs)[len(probs)*3//4]:.0%}")
```

If the p75 is 65%, then "high" should gate at 65%+, not 78%+. The threshold must match the domain, not a universal standard.

**Fix:** Lower the threshold to match the domain distribution. For a model that peaks at 70%, `score >= 0.52` for "high" (requiring ~65%+ with good MC alignment) is more honest than `score >= 0.65` (requiring ~78%+ which almost never happens).

**Anti-pattern:** "But 65% isn't that confident in absolute terms." In YOUR domain, it is. The user who built the model and watches the predictions knows what's actionable. A 65% pick in a sport where the best model gets 70% is a strong signal. Calibrate to the domain, not to theory.

## Variant: MC Divergence Hard Caps

When the model and Monte Carlo simulation disagree significantly, confidence should be capped regardless of other signals. This is a **hard gate** that overrides the composite score.

**Two triggers for the hard cap:**
1. **Direction disagreement** — model says home wins, MC says away wins (or vice versa)
2. **Magnitude divergence** — same direction but >15% gap (model 70% vs MC 52%)

**Implementation:**
```python
mc_divergent = False
if mc_home_win_pct is not None and home_win_prob is not None:
    model_side = home_win_prob >= 0.5
    mc_side = mc_home_win_pct >= 0.5
    if model_side != mc_side:
        mc_score = 0.0
        mc_divergent = True
    else:
        diff = abs(home_win_prob - mc_home_win_pct)
        if diff > 0.15:
            mc_score = 0.1
            mc_divergent = True
        elif diff > 0.10:
            mc_score = 0.4
        elif diff > 0.05:
            mc_score = 0.7  # good agreement
        else:
            mc_score = 1.0 - diff * 5.0  # tight alignment

# Hard cap: divergence forces "low" regardless of phi/edge
if mc_divergent:
    return "low" if score >= 0.15 else "speculative"
```

**Why hard cap instead of soft penalty:** A soft penalty (lower mc_score) might not be enough to push the composite below the "moderate" threshold. If phi is low (well-established ratings) and edge is high (strong favorite), even a mc_score of 0.0 might not drop the total below 0.35. The hard cap ensures divergence always produces "low" — which is the honest label when two independent methods disagree.

**MC scoring tiers for agreement cases:**
| Gap | mc_score | Meaning |
|-----|----------|---------|
| < 5% | 0.8–1.0 | Tight alignment — high agreement |
| 5–10% | 0.7 | Good agreement — same direction, similar margin |
| 10–15% | 0.4 | Moderate divergence — same direction, different margin |
| > 15% | 0.1 + hard cap | Significant divergence — forces "low" |
| Direction disagree | 0.0 + hard cap | Fundamental disagreement — forces "low" |

## Variant: Backtest-Validated Convergence Classifier

When building a new threshold-based classifier from scratch (not auditing an existing one), pair it with a **backtest endpoint** that replays historical data through the classifier and reports per-category accuracy. The backtest serves as both validation (are the thresholds right?) and user-facing annotation ("when this pattern appeared, the model was right 62% of 412 games").

Key architectural decisions for this variant:
- **Pure classifier function** with no I/O — unit-testable, reusable on both backend and frontend
- **Dual implementation** — Python for the backtest endpoint, JS mirror for live rendering. They MUST stay in sync; changing thresholds on one side without the other produces a live/backtest disagreement
- **Backtest as dead-tier canary** — if a category has 0 games in the backtest, the thresholds may be unreachable for the actual data distribution (exactly the dead-tier pattern this skill addresses)
- **MC coverage constraint** — when one of the input signals (e.g., Monte Carlo) is only available for some sports, the classifier degrades gracefully (fewer signals → "none" type) rather than producing misleading categories

See `references/backtest-validated-convergence-classifier.md` for the full worked example: the signal strength bars system (5 bars + 4 color types combining model, MC, and market probabilities), the `/api/signals/{sport}` backtest endpoint, the dual Python/JS implementation, and the threshold-sync pitfall.

## References

- `references/backtest-validated-convergence-classifier.md` — the pattern of building a backtest endpoint alongside a new threshold classifier, with the signal strength bars system as the worked example. Covers dual-implementation sync, backtest-as-canary, and MC coverage constraints.
- `references/multi-signal-confidence-composite.md` — when a single-variable classifier has no data variation (all inputs cluster in one tier), the fix is adding discriminating signals as a weighted composite. Includes the phi + edge + MC alignment pattern with design principles and test cases.

- `references/elo-scenario-lab-confidence-thresholds.md` — the full session trace — data query results, gate mapping table, before/after distribution, regression test that pins the contract.
- `references/downstream-ui-consequence.md` — the v2 follow-up: dead-tier classifier downstream of a UI filter (Top Picks section showing 50%-55% coin-flips labeled "Model + MC agree"). The fix: decisiveness gate + tiered honest labels. Includes reproduction recipe and test pin pattern.
- `references/competing-classifier-functions.md` — variant: two competing classifier functions with different thresholds, where the one with correct thresholds is dead code. Diagnostic: trace call chains, compare thresholds.
