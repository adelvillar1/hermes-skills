# Probability & Math (reference)

All numbers computed exactly from the 2d6 sample space (36 outcomes) and the official card counts; verified by 2M-roll simulation. Sources: rules PDFs + `scripts/catan_sim.py`.

## 2d6 distribution (the table to quote)
| Roll | Combos | Prob | Pips on token | Rolls per occurrence |
|---|---|---|---|---|
| 2 | 1 | 2.78% | 2 | 36 |
| 3 | 2 | 5.56% | 3 | 18 |
| 4 | 3 | 8.33% | 4 | 12 |
| 5 | 4 | 11.11% | 5 | 9 |
| 6 | 5 | 13.89% | 6 | 7.2 |
| 7 | 6 | 16.67% | — | 6 (robber, no production) |
| 8 | 5 | 13.89% | 6 | 7.2 |
| 9 | 4 | 11.11% | 5 | 9 |
| 10 | 3 | 8.33% | 4 | 12 |
| 11 | 2 | 5.56% | 3 | 18 |
| 12 | 1 | 2.78% | 2 | 36 |

The dots (pips) under each number token ARE the combo count — a beginner-reading shortcut worth teaching.

## Production per adjacent building per roll
Expected resource cards/roll = P(roll) × (1 per settlement, 2 per city).
- 1 settlement on a 6 or 8: 0.139/roll → ~1 card every 7.2 rolls
- on a 5 or 9: 0.111 → every 9 rolls; on 4/10: 0.083 → every 12
- on 3/11: 0.056 → every 18; on 2/12: 0.028 → every 36
- A city doubles all of the above. The robber doesn't halve — it zeroes the hex.

## Board composition facts that drive balance
- 18 discs on 19 hexes: the desert takes none. 6+8 supply 4 tokens and 5+9 supply 4 tokens — identical pip totals, so WHICH resources sit on high numbers matters more than raw pips.- 19 cards per resource. Wheat is the most-demanded type (in settlement + city + dev costs); ore is the expensive bottleneck (city + dev). Typical shortage order in mid-game: ore ≈ wheat > brick ≈ wool ≈ wood (situation-dependent).
- Bank exhaustion is real: 2 cities on one 6-wheat hex + enemy settlements on the same hex drain the 19-card wheat stack over a long game; when a roll can't be fully paid, NOBODY collects (unless only one player is affected).

## The robber
- 7 hits 1/6 of rolls → one disruption every ~6 rolls (~1.5 per 4-player lap). Knights add extra activations on top.
- Placement EV: expected loss to victims ∝ their pip share on the robbed hex. Standard play: rob an opponent's 6/8, and alternate victims so no one keeps losing the same card (also: never park where YOU produce).

## Development-card draw odds (25-card deck)
Knight 14 (56%), VP 5 (20%), Monopoly 2, Road Building 2, Invention 2 (8% each). Direct VP EV per purchase ≈ 0.2 VP + army tempo; buying devs is a 56% chance of another robber hit per card. In a long game the deck thins — count remaining cards when VP-card odds matter.

## Board-balance model (boardgameanalysis.com, 2020)
Scores 0–1, lower = more balanced (per-player expected-production inequality). Beginner fixed layout = 0.094; a 2016 tournament map = 0.106; 100M random layouts ≈ normal, clustered ~0.25. Use this to explain why random boards feel unfair and tournament boards are hand-tuned.

## Heuristics that follow from the math
- 5+9 on different resources ≈ same pips as 6+8 but better combined robber-and-variance defense; diversification is convexity, not just caution.
- Two settlements touching the SAME hex pair share dice correlation — one robber placement hurts both; one 7 storm hurts your hand twice as hard.
- Ports re-price your surplus: 2:1 port = your overflow resource worth 2× bank rate; 3:1 = 1.33×. A 2:1 wheat port with two wheat-producing hexes is effectively another settlement.
- Hand ceiling discipline: >7 cards = exposed to half-hand loss; strong players hover near 6–7 right before likely 7s.
