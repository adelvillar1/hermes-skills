# Ranking UIs — Filter/Sort Hierarchy and Honest Labeling

The "Top N" / "Best of" / "Featured" / "Recommended" UI pattern shows up across many products. This reference covers the four-layer filter/sort hierarchy that makes those surfaces honest, plus the badge-copy tiering that prevents them from misleading users.

## The Pattern: Decisiveness → Alignment → Confidence → Spread

When a ranking surface filters items by "two methods agree" (e.g., ELO + Monte Carlo, deterministic + simulation, intent + outcome), there are four quality signals to combine. They have a strict hierarchy:

```
PRIMARY GATE:  decisiveness   (favored side >= 65% — the model commits)
SECONDARY:     alignment      (smallest gap between methods)
TERTIARY:       confidence     (model's own self-rating)
TIEBREAKER:     spread/CI      (narrowest uncertainty band)
```

**Why this hierarchy, in this order:**

1. **Decisiveness is the gate.** Without it, alignment near 50/50 is trivially satisfied — both methods cluster at the uncertain end, so their agreement is meaningless. A 51% / 53% pair has 2% alignment but is a coin-flip. The user's complaint "this section shows toss-ups" almost always traces back to a missing decisiveness gate.

2. **Alignment is a quality multiplier.** Given the model is decisive, how tight is the agreement between the two methods? Smaller alignment = higher quality pick.

3. **Confidence is the model's own rating.** Useful as a tiebreaker but NOT the primary gate — confidence and decisiveness are different. A high-confidence 51% prediction is still a coin-flip.

4. **Spread/CI is the final tiebreaker.** When everything else is equal, prefer the prediction whose uncertainty band is narrowest.

**Anti-pattern:** sorting purely by alignment. A 51% / 53% (Δ 2%) "beats" a 70% / 75% (Δ 5%) by the sort, and gets surfaced as the top pick. The user sees a section that looks like picks but is actually coin-flips.

## Honest Label Tiering (not Soft Labels)

When a section title promises a quality bar — "Top Picks," "Featured," "Best of" — the items in it must meet that bar. Three options when items don't:

| Option | What it looks like | Verdict |
|---|---|---|
| Soften the label | "✓ Model + MC agree" on a 14.5%-delta card | 🔴 Bug — the label lies. |
| Add a "diverge" tier | "◌ Model & MC diverge" (between agree and within 10%) | Honest, but conflicts with the section title. |
| **Filter it out** | Card doesn't appear in the section | ✅ Right answer for ranked surfaces. |

The pattern: tier the label by data quality, with a hard cutoff above which the item simply doesn't qualify. For the Top Picks surface:

```js
const alignedTag = p.alignmentDelta < 0.03
  ? '✓ Model + MC agree'
  : '△ Model & MC within 10%';
// Note: alignmentDelta >= 0.10 gets filtered out (don't surface in "Top Picks")
```

The tiered copy is for the items that *did* qualify. Items that don't qualify don't appear in the section at all. Honest emptiness > dishonest fullness.

## The Section Title Is a Contract

A "Top Picks" section promises winners. A "Recent" section promises chronological. A "Best of 2025" section promises the best of 2025. The user reads the section title as a quality bar; if the items don't meet that bar, the section is broken even if the filter is "working."

**Practical rule:** when a section's items look wrong to the user (and the user can articulate *what's* wrong — "these are toss-ups," "this isn't really a pick"), the section is broken. Two failure modes:

- **Filter too loose** — missing a prerequisite gate (decisiveness, freshness, etc.). Fix: add the gate.
- **Data not there** — the items the user wants don't exist in the current dataset. Fix: render the empty state explicitly and tell the user why. Don't ship a sparse section that misleads.

**Visual review catches this.** Code review cannot. A "Top Picks" section that labels a 14.5%-delta card as "Model + MC agree" looks fine in the source — the bug only appears in the rendered output. The vision tool catches it; the line-by-line review does not.

## Reproduction Recipe

To reproduce this bug pattern in any new ranked surface:

1. Build a "Best X" / "Top X" / "Featured" section
2. Filter on a quality metric (alignment, score, value, etc.)
3. Without a prerequisite gate, the filter is dominated by cases where the metric is trivially satisfied
4. The section fills with low-quality candidates that happen to pass the quality filter
5. The user complains "this section shows the wrong thing"

Fix:
- Add a prerequisite gate (decisiveness, quality floor, freshness)
- Tier the label by data quality (not soft labels)
- Visual review before shipping — would a child reading the rendered output understand why these are top picks?

## Test Pin

```js
// In tests/test_ranking_ui.js or equivalent
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

function test_diverge_label_filtered_not_relabeled() {
  const diverge = { confidence: 'high', home_win_prob: 0.79, mc_home_win_pct: 0.61 };  // Δ 18%
  const result = computeTopPicks([diverge]);
  assert(result.length === 0);  // don't surface with a softer label
}
```

Lock these in. A future refactor that removes the decisiveness gate will silently regress.

## Cross-Skill Reference

- **`dead-tier-classifier-audit`** — the parent class. The decisiveness gate is a *downstream consequence* of a similar tier-mismatch problem. When a classifier's "high" tier never fires, the downstream UI that filters on it is always empty. When it does fire but the underlying data is in the coin-flip zone, the section is "full but full of toss-ups."
- **`llm-render-with-canonical-numbers`** — the philosophical sibling. Both are about honest output at boundary cases. The LLM skill says "guard the LLM from contradicting truth"; this says "guard the ranking from surfacing coin-flips as Top Picks." The defense in both is a *guard at the data-source level*.
- **`design-review`** (parent skill) — the visual review pass caught this exact bug class. Without vision, the source code looks fine. With vision, the rendered output tells the truth.

## Worked Example: Sports Analytics "Top Picks"

The full reproduction in `dead-tier-classifier-audit/references/downstream-ui-consequence.md`. The bug, the diagnosis, the four-layer hierarchy fix, and the tiered-label pattern are documented there in detail.

## When to Use This Pattern

Use it whenever:
- A UI surface surfaces a subset of items from a larger pool (Top N, Featured, Best Of, Recommended, Watchlist, etc.)
- The items are filtered or sorted by a quality metric
- The section title promises a quality bar
- The user might be misled by a "soft" version of the same label

Don't use it when:
- The surface is chronological (Recent, Latest, Today) — chronological surfaces don't promise quality
- The user explicitly wants all items, ranked or not (e.g., a full league table)
- The filter is on a single high-confidence criterion (e.g., "all games where the model is high-confidence")
