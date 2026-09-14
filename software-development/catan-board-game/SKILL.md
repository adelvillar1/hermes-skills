---
name: catan-board-game
description: Rules, strategy, expansions, and history of Catan.
---

# Catan (Board Game) — Knowledge Base

Everything needed to answer questions about Catan: authoritative base-game rules (5th & 6th edition), setup, probability math, strategy, the expansion/family catalog, official tournament rules, and history. It is a distilled knowledge base, not a copy of the rulebooks — verify exact wording against the canonical PDFs listed below when a ruling matters. No dependencies; one optional stdlib-only sim script.

## When to Use
- "How does the robber work?", "Can I trade on someone else's turn?", "Distance rule questions"
- "What are the odds of rolling a 7 / a 6?", "Which numbers are best?"
- Opening-placement and trading strategy advice
- "What's the difference between Seafarers and Cities & Knights?", "Can I combine expansions?"
- Tournament format/rules (CATAN Championship Program), edition differences (5th vs 6th)
- "Is there a 2-player Catan?", "How many VP does a city give?"

## Prerequisites
None. Canonical sources (fetch with `web_extract` if exact text is needed):
- 6th Ed rulebook (2025): https://www.catan.com/sites/default/files/2025-03/CN3081%20CATAN%E2%80%93The%20Game%20Rulebook%20secure%20%281%29.pdf
- 5th Ed rules + Almanac (2020): https://www.catan.com/sites/default/files/2021-06/catan_base_rules_2020_200707.pdf
- All rulebook PDFs index: https://www.catan.com/understand-catan/game-rules
- Tournament rules (rev. July 2025): https://catanevents.com/hosts/tournament-rules/

## Core Model (always loaded)
- **Win**: first player with 10+ VPs *during their own turn* wins. Everyone starts with 2 settlements = 2 VP, so 8 more needed.
- **VP sources**: settlement 1, city 2, Longest Route/Road tile 2, Largest Army tile 2, VP dev card 1. Roads and knights themselves: 0 VP.
- **Turn** = Production phase (optionally play 1 dev card → roll 2d6 → collect or resolve 7) then Action phase (trade, build, buy dev cards — any order, any number of times), then pass dice left.
- **Costs**: road = 1 wood + 1 brick; settlement = 1 wood + 1 brick + 1 wheat + 1 wool; city = 2 wheat + 3 ore; dev card = 1 ore + 1 wool + 1 wheat.
- **Supply totals**: 19 cards each of brick/wood/wool/wheat/ore (95); 25 dev cards; 15 roads / 5 settlements / 4 cities per color.
- **Placement**: roads on edges, buildings on intersections; **Distance Rule** = no building within 2 edges of any existing building; settlements must connect to your own road network; cities only by upgrading your own settlement.
- **7 rolled**: more than 7 resource cards in hand → discard half (rounded down); robber MUST move to a different hex (may go to desert); steal 1 random card from someone on that hex; robbed hex produces nothing.
- **Trade**: only on your turn; no gifts, no dev cards, no like-for-like; bank 4:1, 3:1 port, 2:1 resource port. Dev cards don't count toward hand limit and can't be robbed.
- **Editions**: 5th Ed (2015) = "Settlers of Catan" renamed *Catan*; 6th Ed (Apr 2025) = Longest Road→**Longest Route**, Soldier→**Knight**, Year of Plenty→**Invention** (take 2 from supply), official Fixed Setup added. Same math, same core rules.

## Reference Index — load on demand with `skill loader (name="catan-board-game", file_path=...)`
- `references/base-rules.md` — full turn/rule mechanics: trades, building rules, dev-card by dev-card text, 7-resolution, bank exhaustion, edition diff table. Load for any rules ruling.
- `references/setup.md` — Fixed vs Variable setup (spiral number placement A-B-C, port assignment), 3/4-player differences, 5–6 player extension building phase. Load when someone asks how to set up or about 5–6 players.
- `references/probability.md` — 2d6 distribution + per-roll yields, pip/frequency hex composition, robber cadence, bank exhaustion math, board-balance scores. Load for odds/"best number" questions.
- `references/strategy.md` — official Almanac tactics + standard heuristics: opening placement, diversification, ports, blocking, development-card EV, trading leverage. Load for "how do I win / where to settle".
- `references/expansions.md` — Seafarers, Cities & Knights, Traders & Barbarians, Explorers & Pirates, Oil Springs, Frenemies: what each adds, key mechanics, compatibility matrix. Load for expansion questions.
- `references/family-history.md` — full product family (Card Game, Rivals, Junior, Dice Game, Starfarers, spinoffs, licensed editions) + design/publication history, awards, sales, Netflix adaptation. Load for franchise/history questions.
- `references/tournaments.md` — CATAN Championship format tiers, timed placements, timer settings, code-of-conduct clarifications (port tokens banned, no AI software), World Championship facts. Load for organized play.
- `references/glossary.md` — terms (hex, pips, maritime/domestic trade, metropolis, ...) and FAQ of the most-argued edge cases. Load to resolve terminology or disputes quickly.

## How to Run
Knowledge-only: answer from the core model, then load the matching reference file via `skill loader` before ruling on detail. For custom production/odds calculations beyond the tables, invoke `scripts/catan_sim.py` through the `terminal` tool (stdlib only).

## Quick Reference
| Question | Answer |
|---|---|
| Players / time | 3–4 (5–6 w/ extension) · ~60–120 min · age 10+ |
| Designer / first published | Klaus Teuber (1952–2023) · 1995 (Kosmos), 32M+ sets, 40 languages |
| Dice odds 6 or 8 | 13.89% each · 5 or 9: 11.11% · 7: 16.67% · 2 or 12: 2.78% |
| 7 every ~ | 6 rolls (1/6 chance) |
| Settlement / city / road cost | see Core Model costs |
| Hand limit | discard half if >7 resource cards on a 7 (dev cards exempt) |
| Longest Road / Army | ≥5 continuous roads / ≥3 knights played, first to do so, 2 VP each |
| 6th Ed win score | 10 VP · C&K: 13 VP · most Seafarers scenarios: 12 VP |

## Pitfalls
- Rulebook PDFs render icons as missing text when extracted (cost lines read empty). Costs in this skill are stated in words from the 2020 Almanac — don't re-extract the PDF expecting costs.
- Common misquote: "8 or more must discard" appears on forums; the books phrase it as "more than 7 resource cards", keeping half rounded down (e.g. 9 → discard 4). Same result, but quote the book.
- The initial placement (setup) follows the Distance Rule too — commonly missed.
- Tournament rules differ from casual play (no port tokens, timed placements, victory must be declared on your turn).
- Facts here are synthesized notes about the sources, not quoted rules; for a tournament-legal ruling, `web_extract` the canonical PDF.

## Verification
`python3 scripts/catan_sim.py` (via `terminal`) prints a 2d6 distribution matching the table in `references/probability.md` (7 → ~16.67%) — confirms the skill's probability core.
