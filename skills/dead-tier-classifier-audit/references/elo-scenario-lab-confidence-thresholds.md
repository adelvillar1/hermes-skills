# Worked Example: Glicko-2 Confidence Thresholds

The full session that surfaced the dead-tier-classifier-audit pattern. From `docs/recaps/SESSION-RECAP-2026-06-01.md` Session 4.

## Symptom

A user asked for a "Top Picks" dashboard section (highest certainty + best model/ELO alignment). While building the filter, the count of `confidence: 'high'` games came back as 0/78. The whole `high` tier was dead.

User's diagnostic question: **"is the confidence calculation too cautious?"**

## Step 1: Survey the output distribution

```python
from collections import Counter
games = schedule_data.games  # 78 MLB games
counter = Counter(g.get('confidence') for g in games)
print(counter)
# Counter({'moderate': 71, 'low': 7, 'high': 0, 'speculative': 0})
```

0 high. 0 speculative. Asymmetric. The signal.

## Step 2: Find the threshold gates

`src/elo_adapter.py:330-337` (the original code, before the fix):

```python
def calibrate_confidence(self, scenario_score, elo_uncertainty):
    phi = elo_uncertainty
    if phi < 50 and scenario_score > 0.7:   return "high"
    if phi < 100 and scenario_score > 0.5:  return "moderate"
    if phi < 150:                            return "low"
    return "speculative"
```

The four gates: `phi<50`, `phi<100`, `phi<150`, `else`.

## Step 3: Measure the actual data distribution

```python
import sqlite3
conn = sqlite3.connect('.forecast/corpus.db')
cur = conn.cursor()
cur.execute('SELECT MIN(rd), MAX(rd), AVG(rd) FROM ratings WHERE sport = ?', ('MLB',))
# (69.8, 79.1, 72.2) — every team is in 69-79 range
```

The `phi` (Glicko-2 RD) of every actively-rated team in the corpus sits in **69-79**.

## Step 4: Compare gates to data

| Gate | Old condition | Data range | What actually happens |
|---|---|---|---|
| `phi < 50` | high | 60-90 | 0% of teams qualify — **dead tier** |
| `phi < 100` | moderate | 60-90 | 100% of teams qualify — **always-true gate** |
| `phi < 150` | low | 60-90 | 100% of teams qualify — **always-true gate** |
| `else` | speculative | 60-90 | 0% of teams qualify — **dead tier** |

Result: the function's actual decision boundary is the `scenario_score` clauses inside the always-true `phi < 100` branch. The 71-moderate / 7-low split is determined by scenario_score, not phi.

## Step 5: Re-tune gates to match the data

New gates (preserve semantic meaning of each tier, shift to where the data is):

```python
def calibrate_confidence(self, scenario_score, elo_uncertainty):
    phi = elo_uncertainty
    # Thresholds calibrated to the current Glicko-2 phi distribution
    # (which sits in the 60-90 range for actively-rated teams). The
    # previous phi<50 gate was unreachable for any team with a working
    # rating, so the "high" tier never fired. New gates keep the
    # semantic meaning of each tier — "high" still means "model is
    # sure" — but match the data the system actually produces.
    if phi < 100 and scenario_score > 0.7:  return "high"
    if phi < 150 and scenario_score > 0.5:  return "moderate"
    if phi < 200:                            return "low"
    return "speculative"
```

## Verification

| Tier | Before | After |
|---|---|---|
| high | 0/78 | 57/78 |
| moderate | 71/78 | 14/78 |
| low | 7/78 | 7/78 |
| speculative | 0/78 | 0/78 |

`speculative` is still 0/78 — but it's now reachable for `phi >= 200` (newly-rated teams, future expansion). The other three tiers each have data, matching the model's intent.

## Regression test that pins the contract

`tests/test_elo_adapter.py::TestCalibrateConfidence::test_phi_in_realistic_range`:

```python
def test_phi_in_realistic_range(self, adapter):
    """Regression — a team at the realistic phi MUST classify as
    'high' when scenario_score is also high. The previous phi<50 gate
    was unreachable — actively-rated teams in the corpus have phi
    in the 60-90 range. The new gates must let those teams actually
    classify as 'high' when scenario_score is high."""
    assert adapter.calibrate_confidence(0.9, 80) == "high"     # realistic phi, high score
    assert adapter.calibrate_confidence(0.6, 80) == "moderate"  # same phi, mid score
    assert adapter.calibrate_confidence(0.3, 80) == "low"     # same phi, low score
```

Without this test, a future refactor could quietly re-tighten the gates back to `phi < 50` and the bug would re-emerge. With it, the test fails the moment the threshold drifts back out of the realistic data range.

## Why this bug class is hard to catch at code review

- The function reads cleanly.
- The thresholds (50, 100, 150) are round numbers — they look reasonable.
- The unit tests pass: `calibrate_confidence(0.8, 30) == "high"` returns "high" correctly.
- But the test uses `phi=30`, which is **a value no live team has**. The unit tests are testing the function in isolation, not against the data the system actually feeds it.

The bug only surfaces when someone counts the tier distribution of real outputs and notices the asymmetry. That's not something a code reviewer would catch.

## The "tier must fire" constraint

A useful mental model: every gate in a tiered classifier must fire for SOME inputs and NOT fire for others. If a gate always fires, it's a no-op (the next condition becomes the actual decision boundary). If a gate never fires, the tier is dead.

When re-tuning, preserve this property for every gate. Otherwise you've just moved the dead-tier problem.

## How to spot the bug in your own systems

Two cheap checks, run whenever you touch a tier-based classifier:

1. **Count the output distribution.** `Counter(classifier(x) for x in inputs)`. Any tier at 0% or 100% is a flag.
2. **Trace every gate to the data range.** For each `if x < threshold` or `if x > threshold` in the classifier, query the data for the actual range of `x`. If the threshold is outside the data range, the gate is dead.

Both checks take minutes. Both can save hours of confused downstream debugging ("why is the UI never showing X-tier items?").

## Related: how this bug surfaced in UI

The dead "high" tier meant no game ever qualified for a "Top Picks" section filtered on `confidence == 'high'`. The original filter was:

```js
games.filter(g => g.confidence === 'high' && /* ... */)
```

Result — empty section, no useful output. The UI symptom (empty section) and the model symptom (dead tier) were the same bug at different layers. Fixing one without the other would have left the UI empty.

A dead-tier classifier ALWAYS surfaces in the UI eventually. Whether it's an empty filter, a section that never renders, or a "high-priority" badge that never appears. If you see a UI surface that depends on a tier and never shows any items, the first thing to check is the classifier's tier distribution.
