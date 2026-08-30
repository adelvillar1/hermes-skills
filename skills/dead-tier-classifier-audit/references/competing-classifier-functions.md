# Variant: Two Competing Classifier Functions

## The Pattern

A codebase has TWO functions that compute the same categorical labels (high/moderate/low) from the same inputs, but with different thresholds. One is called in production; the other is dead code. The dead-code function has the correct thresholds; the production function has wrong ones.

This is harder to spot than the basic dead-tier pattern because:
1. Grepping for `return "high"` finds BOTH functions — you can't tell which is live
2. The dead-code function looks correct when read in isolation
3. Unit tests may test the dead-code function (which passes) while the production path uses the other

## Real Example (ELO Scenario Lab, 2026-06-04)

Two confidence classifiers existed:

**Function A** (`probabilities.confidence_label`): Used `combined` phi (Euclidean norm) with thresholds 80/140/250.
```python
def confidence_label(phi_home, phi_away):
    combined = sqrt(phi_home**2 + phi_away**2)
    if combined < 80: return "high"
    elif combined < 140: return "moderate"
    elif combined < 250: return "low"
    return "speculative"
```

**Function B** (`adapter.calibrate_confidence`): Used `avg_phi` (arithmetic mean) with thresholds 175/185/250.
```python
def calibrate_confidence(scenario_score, elo_uncertainty):
    phi = elo_uncertainty  # actually avg_phi
    if phi < 175: return "high"
    if phi < 185: return "moderate"
    if phi < 250: return "low"
    return "speculative"
```

**Production code** called Function B (line 680 of probabilities.py):
```python
avg_phi = (home_phi + away_phi) / 2
confidence = adapter.calibrate_confidence(scenario_score, avg_phi)
```

Function A was never called — it was dead code.

**Result:** With MLB phi ≈ 58, `avg_phi = 58 < 175` → everything was "high". The correct `confidence_label()` function would have computed `combined = √(58² + 58²) ≈ 83`, which is > 80 → "moderate".

## Diagnostic Steps

1. **Grep for all functions that return the tier labels:**
   ```bash
   grep -rn "return ['\"]high['\"]" src/
   ```
   If you find multiple functions, note each one's location.

2. **For each function, trace the call chain:**
   ```bash
   grep -rn "confidence_label\|calibrate_confidence" src/
   ```
   Which one is actually called in the production code path? Which is dead?

3. **Compare thresholds between the functions.** If they differ, the dead-code function may have been an attempted fix that was never wired in.

4. **Check if the dead function was a "fix" that replaced the old one in the file but not in the caller.** This is the common pattern — someone updates the function body (or creates a new function with better thresholds) but doesn't update the call site.

## The Fix

Replace the production call with the corrected function:
```python
# Before (wrong function, wrong thresholds):
confidence = adapter.calibrate_confidence(scenario_score, avg_phi)

# After (correct function, correct thresholds):
confidence = confidence_label(home_phi, away_phi)
```

## Prevention

When you fix a classifier's thresholds, grep for ALL call sites and ensure the fixed function is the one being called. Don't assume that defining a better function automatically makes it the one that runs.

## Trigger Signals

- "All games show as high confidence" (100% in one tier)
- A function with correct thresholds exists but the output distribution doesn't match
- Two functions in the codebase return the same tier labels
- A "fix" was committed but the behavior didn't change
