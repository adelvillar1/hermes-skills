# Backtest-Validated Convergence Classifier

The concrete implementation of the "audit your classifier thresholds" pattern: a threshold-based classifier that combines multiple independent data sources, paired with a backtest endpoint that replays historical data through the classifier to empirically validate the thresholds.

## The Pattern

When building any user-facing indicator that classifies games/predictions into categories (signal bars, edge badges, confidence levels, buy/sell signals):

1. **Pure classifier function** (no I/O) — takes N probability sources, returns (discrete_score, category_type)
2. **JS mirror** for client-side rendering — must be kept in sync with the Python classifier
3. **Backtest endpoint** — replays completed historical games through the same classifier, reports accuracy/Brier per category
4. **Live annotation** — each badge shows the backtested accuracy for its category ("hist 62% (412)")

## Worked Example: Signal Strength Bars (ELO Scenario Lab, 2026-06-16)

### Problem
The old "CLOSE CALL" badge fired when model and market agreed tightly — semantically wrong (agreement = strong consensus, not a close game). MC simulation was ignored entirely.

### Solution
Five signal bars (like phone bars) colored by signal type:

| Bars | Spread (max−min of sources) | Meaning |
|---|---|---|
| 5 | < 3pp | Locked |
| 4 | 3–7pp | Strong |
| 3 | 7–15pp | Moderate |
| 2 | 15–25pp | Weak |
| 1 | > 25pp | Faint |

| Color | Type | Condition |
|---|---|---|
| 🟢 Green | consensus | All agree on direction, spread ≤ 15pp, fav > 55% |
| 🔵 Blue | value | Model + MC agree, market diverges ≥ 7pp |
| 🟡 Amber | mixed | Model & MC disagree on direction, or spread > 15pp |
| ⚪ Gray | none | Coin flip (fav ≤ 55%), or < 2 signals available |

### Architecture (4 layers)

**Layer 1: Pure classifier** (`src/services/signal_classifier.py`)
```python
def classify_signal(model_prob, mc_prob, market_prob) -> tuple[int, str]:
    # Returns (bars 0-5, signal_type 'consensus'|'value'|'mixed'|'none')
```
No I/O, no imports beyond typing. Unit-testable in isolation. 22 tests cover all types + edge cases.

**Layer 2: JS mirror** (`ui/js/lib/signalBars.js`)
```javascript
function classifySignal(modelProb, mcProb, marketProb) {
  // Returns {bars, type} — MUST match Python exactly
}
```
Dual-export pattern (ESM + globalThis). Also contains `signalBarsHTML()` renderer and `loadSignalStats()` async fetcher with per-sport caching.

**Layer 3: Backtest endpoint** (`src/api/routes/signals.py`)
```python
@router.get("/{sport}")
async def get_signals(sport):
    # Replays ALL completed games through the prediction pipeline
    # Adds MC lookup + market odds lookup per game
    # Classifies each game, accumulates accuracy/Brier per signal type
    # Returns: {signal_types: {consensus: {count, accuracy, brier}, ...},
    #           per_bar_count: {5: {count, accuracy}, ...}}
```
Reuses the accuracy endpoint's game loop (engine setup, signal-aware adjustments, market odds batch-load). Key addition: loads `mc_game_dist` once, builds `game_id → home_win_pct` dict, joins per game.

**Layer 4: Live annotation**
Each badge fetches `/api/signals/{sport}` once per sport (cached), shows `hist 62% (412)` alongside the bars.

### Key Design Decisions

1. **Coin flips get gray, not green.** 5 bars means "high convergence," but if everyone agrees it's 50/50, there's no edge to bet. Gray prevents confusing consensus-on-a-coin-flip with consensus-on-a-pick.

2. **Blue is the "buy signal."** When model + MC agree but market lags, the model found something the market hasn't priced. User scans for blue.

3. **Amber means "don't trust this one."** Internal disagreement between model and MC is the strongest warning.

4. **Priority ordering in the classifier matters.** Directional disagreement (mixed) is checked BEFORE value/consensus. A value signal requires model+MC directional agreement first.

### The Dual-Implementation Sync Pitfall

The classifier exists in BOTH Python (`signal_classifier.py`) and JavaScript (`signalBars.js`). If you change thresholds on one side, the live badge (JS) and the backtest endpoint (Python) will disagree. The backtest validates the PYTHON thresholds; the user sees the JS thresholds.

**Mitigation:**
- Document the sync requirement in both files
- The backtest endpoint's per-type counts serve as a canary: if a type has 0 games, the thresholds may be wrong (dead tier)
- When tuning thresholds, update BOTH files in the same commit

### Backtest as Dead-Tier Canary

The backtest endpoint naturally surfaces dead tiers. If "value" has 0 games in the backtest:
- Either the 7pp market gap threshold is too high (model rarely diverges from market by 7pp)
- Or MC data is sparse (only MLB has MC coverage)

Run `curl localhost:8000/api/signals/mlb` and check `signal_types.value.count`. If it's 0, the threshold needs lowering or MC coverage needs expanding.

### MC Coverage Constraint

MC data is sport-specific. In ELO Scenario Lab, 370 of 373 MC rows are MLB. Non-MLB sports get 2-signal classification (model + market only), which means "value" (requires model+MC agreement vs market) rarely fires. The backtest shows this honestly (value count = 0 for non-MLB). This is acceptable — the badge degrades gracefully, showing only what's honestly classifiable.

### Mobile Pipeline

The mobile sync payload includes `signal_bars` (0–5) and `signal_type` computed server-side from the same classifier. The mobile app renders a `<SignalBars>` component that takes pre-computed values — no client-side classification needed on mobile. This avoids the dual-implementation problem on the mobile side.

**Migration:** Each new schedule column requires a migration bump. Migration 4 adds `signal_bars INTEGER` and `signal_type TEXT`. Remember to update `offline.test.ts` version assertions (see `react-native-expo-dev` skill, "SQLite migration version bump" pitfall).
