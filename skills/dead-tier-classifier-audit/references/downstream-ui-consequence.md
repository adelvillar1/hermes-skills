# Dead-Tier Classifier Bug — Downstream UI Consequence

The dead-tier audit skill's original worked example stopped at "fix the threshold and the model now produces a sensible tier distribution." But the v1 skill didn't catch the *downstream* bug that surfaces once the tier starts firing: a UI section that filters on the now-live tier is still empty, and the user complains.

This reference documents the Top Picks worked example from 2026-06-01 — the bug, the diagnosis, and the fix.

## The Setup

After the dead-tier fix in `elo_adapter.calibrate_confidence` (gates bumped from 50/100/150/200 to 100/150/200), the confidence distribution for 78 MLB games went from `0/71/7/0` to `57/14/7/0`. The "high" tier was now live.

A new "Top Picks" dashboard section was added to the Home view, filtering on:

```js
filter: g.confidence in ['high', 'moderate']
       && g.home_win_prob != null
       && g.mc_home_win_pct != null
sort:   best alignment first, then narrowest MC CI
```

The user saw the rendered section and reported:

> "the top picks are there, but are for games that are essentially a toss-up 50%-55%. I was expecting games with much higher probability in either direction and with tight MC alignment with probability."

## The Diagnosis

The filter was *working* — it correctly found games with `confidence in ['high', 'moderate']` AND tight alignment. But **alignment near 50/50 is trivially small** because both methods cluster at the uncertain end:

| Game | ELO | MC | Δ | "Aligned"? |
|---|---|---|---|---|
| Marlins @ Nationals | 0.690 | 0.700 | 1.0% | Yes (Δ=1%) — but a 70/30 prediction is the *minimum* quality pick |
| Royals @ Twins | 0.704 | 0.754 | 5.0% | Yes (Δ=5%) — but still close to the boundary |
| Tigers @ Rays | 0.795 | 0.815 | 2.0% | Yes (Δ=2%) — but this is the *real* Top Pick |

Wait, the first two look fine. Let me re-read... oh, the real bug was the OPPOSITE — the filter was surfacing 51% / 53% games. Let me re-trace:

The first version of `computeTopPicks` sorted by alignment (smallest first). The smallest alignments come from the games closest to 50/50. Why? Because if ELO says 51% and MC says 53%, the alignment is 2% — which would tie with the genuinely-aligned 69%/70% case. And on tie, the sort had no stable secondary key. The result: 51%/53% coin-flips ranked alongside 69%/70% picks.

The user perception "essentially a toss-up 50%-55%" was the right call. The filter wasn't gating on decisiveness — it was finding the games with the smallest alignment, period.

## The Fix

Two changes, both at the filter level (not the model level):

### 1. Add a decisiveness gate

```js
const DECISIVENESS_FLOOR = 0.65;  // favored side must be >= 65%

if (Math.max(g.home_win_prob, 1 - g.home_win_prob) < DECISIVENESS_FLOOR) {
  return false;  // reject toss-ups
}
```

This is a prerequisite for alignment to mean anything. A 51% / 53% pair has 2% alignment but is a coin-flip. Without the gate, "alignment" rewards uncertainty.

### 2. Reorder the sort — decisiveness first, alignment second

```js
.sort((a, b) => {
  // 1. Most decisive first (PRIMARY)
  if (a.eloDecisiveness !== b.eloDecisiveness) {
    return b.eloDecisiveness - a.eloDecisiveness;
  }
  // 2. Then best alignment (SECONDARY)
  if (a.alignmentDelta !== b.alignmentDelta) {
    return a.alignmentDelta - b.alignmentDelta;
  }
  // 3. Then highest confidence
  if (a.confRank !== b.confRank) return a.confRank - b.confRank;
  // 4. Then narrowest MC CI
  if (a.mcSpread != null && b.mcSpread != null && a.mcSpread !== b.mcSpread) {
    return a.mcSpread - b.mcSpread;
  }
  return 0;
})
```

The new hierarchy:
- **Decisiveness** is the gate — is the model sure enough that this is a real pick?
- **Alignment** is a quality multiplier — given decisiveness, how tight is the agreement?
- **Confidence** and **CI width** are tiebreakers.

### 3. Tier the honest label by quality

```js
const alignedTag = p.alignmentDelta < 0.03
  ? '✓ Model + MC agree'
  : '△ Model & MC within 10%';
// Note: > 10% gets filtered out (don't surface in a "Top Picks" section)
```

The section is called **Top Picks**. A 14.5%-delta card doesn't belong in it. Two options:
- Soften the label ("diverge", "uncertain")
- Filter it out

The user reviewed both options and chose **filter** — honest emptiness beats dishonest fullness in a "Top Picks" section.

## The General Pattern

This isn't unique to Top Picks. The pattern recurs in any ranked UI surface that surfaces items from a larger pool with a quality filter:

| Surface | "Best of" tag | "Featured" | "Recommended" | "Top performers" |
|---|---|---|---|---|
| Decisiveness gate | "Best of" should mean best of the best, not best of the bad | | | |
| Alignment quality | Agreement is a quality multiplier, not the gate | | | |
| Honest tiering | Don't say "the best" if some of the cards are subpar — label by quality, or filter | | | |

Whenever the user says "this section shows X but I expected Y" — first check whether the filter is missing a prerequisite gate (like decisiveness), then check whether the label is honest about the actual quality.

## The Two Pattern: Decisiveness + Honest Label

This pair is the new technique from this session:

1. **Decisiveness as a prerequisite** for any ranked surface. Without it, the filter rewards uncertainty.
2. **Honest label tiering** — when a section promises a quality bar, the cards that don't meet it shouldn't be relabeled softer; they should be filtered out, or the section title should be softer.

Combined: a ranked section should (a) gate on the prerequisite quality, then (b) tier the label for the items that do pass, with the strongest label only for the strongest items.

## Cross-Skill Reference

- **`dead-tier-classifier-audit`** (parent skill) — the original dead-tier pattern, the threshold-vs-data mismatch, the 5-step audit process.
- **`llm-render-with-canonical-numbers`** — the philosophical sibling. Both are about honest output at boundary cases — the LLM guard prevents prose from contradicting numbers, this prevents a UI from claiming a coin-flip is a Top Pick. The defense in both is a *guard at the data-source level*.
- **`design-review`** — caught this bug in the visual review pass (2026-06-01). The "Model + MC agree" tag on a 14.5%-delta card was flagged by the vision tool, not by line-level code review. A class-level reminder: when a UI shows numbers, the visual review catches honesty bugs the code review misses.

## Reproduction Recipe

To reproduce this exact bug pattern in any new ranked surface:

1. Build a "Best X" section that filters on a quality metric (alignment, score, value, etc.)
2. Without a decisiveness/quality prerequisite, the filter is dominated by cases where the metric is trivially satisfied (e.g., alignment near 50/50, score near 0)
3. The section fills with low-quality candidates that happen to pass the quality filter
4. The user complains "this section shows the wrong thing"

Fix: add a prerequisite gate (decisiveness, or a quality floor) before the alignment filter, and tier the label by quality rather than softening it.

## Test Pin

```js
// In tests/test_top_picks.js or equivalent
function test_decisiveness_filter_rejects_tossups() {
  const tossup = { confidence: 'high', home_win_prob: 0.51, mc_home_win_pct: 0.52 };
  const result = computeTopPicks([tossup]);
  assert(result.length === 0);  // 51%/52% is below the decisiveness floor
}

function test_alignment_is_quality_multiplier_not_gate() {
  const coinflipTight = { confidence: 'high', home_win_prob: 0.51, mc_home_win_pct: 0.52 };
  const pickLoose = { confidence: 'high', home_win_prob: 0.79, mc_home_win_pct: 0.81 };
  const result = computeTopPicks([coinflipTight, pickLoose]);
  assert(result.length === 1);
  assert(result[0].game === pickLoose);  // decisiveness > alignment
}
```

Lock these in. A future refactor that removes the decisiveness gate will silently regress the user experience.
