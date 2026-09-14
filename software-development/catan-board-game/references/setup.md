# Setup & Player Counts (reference)

Distilled from 6th Ed rulebook (CN3081) §Fixed/Variable Setup, the 2020 Almanac, and the 5–6 player extension rulebook.

## Fixed Setup (6th Ed, recommended first game)
Hexes and number discs laid out exactly as printed in the rulebook diagram; the board is identical every game. Ports sit at fixed coastal spots; the book pre-places 2 starting settlements + roads per color — take the resources of the hexes touching your SECOND settlement. Highest dice roll starts. Balance score of the beginner layout: 0.094 on the boardgameanalysis.com model (lower = more balanced; 100M random boards cluster ~0.25).

## Variable Setup (the standard game)
1. **Frame:** shuffle the 6 sea frame pieces and re-connect via the numbered puzzle tabs — the coast shape varies each game.
2. **Hexes:** the backs are lettered into 3 rows of equal length. Sort face-down rows: row A = 5 hexes, row B = 6, row C = 5. Lay the desert anywhere; assemble the three rows, then place face-up inside the frame so same-letter rows end up in a straight line (flip the group over as a strip if needed).
3. **Number discs:** sort face down in printed alphanumeric order (2; 3,3; 4,4; 5,5; 6,6; 8,8; 9,9; 10,10; 11,11; 12 → letters A–R). Starting in any corner, place discs in a SPIRAL going counterclockwise inward, one per hex, **skipping the desert**. Then flip them all over.
4. **Ports:** the 2:1 port must sit on coast edges bordering a hex of its resource type where possible; the four 3:1 ports fill remaining slots (5th Ed booklets give the swap procedure when the random frame makes this impossible). 6th Ed pre-prints port positions on the frame.
   - **Random-disc alternative (2020 Almanac, Variable Set-up):** discs may instead be placed in RANDOM order from a corner — the only constraint then is that no two RED-number discs (6, 8) sit on edge-adjacent hexes (swap to fix). This red-separation rule belongs ONLY to the random variant.
   - **What the spiral does NOT guarantee (verified by exhaustive computation, all corner starts × desert positions):** printed-order spiral permits adjacent 6/8 (outer→inner ring transition; desert-skip index shifts) and adjacent identical discs. Board geometry facts (any corner hex walk, CCW): 19 hexes in rows 3-4-5-4-3, 54 vertices, 72 edges = 42 interior + 30 coastal; every vertex is coastal on the base island.
5. **Robber** on the desert. Supply: 5 face-up resource stacks + shuffled face-down dev deck. Special tiles beside the board.

## Starting placements ("the opening")
Each player places 1 settlement + 1 attached road, going around once; the SECOND round reverses order (the last placer of round 1 picks first in round 2 — so the worst first pick gets the best second pick). You collect the resources adjacent to your SECOND settlement. The Distance Rule governs everything.
- Highest 2d6 roller picks first; ties re-roll.
- **Who takes the first regular turn:** the player who placed LAST in round 2 — i.e. the one who placed FIRST in round 1 (the starting player) — begins the game (official: "The starting player (the last to place their second settlement) begins the game."). For seats [0..n-1] with round 1 = 0,1,..,n-1 and round 2 reversed, after setup completes it is seat 0's turn. Do NOT rotate to seat 1 — a common implementation bug (caught in the Catan VTT kernel review 2026-09-08).
- **Longest Route counting:** only an OPPONENT's settlement/city interrupts (spokes) a road; your OWN buildings never interrupt your own route. Implementation must filter own-owned vertices out of the break set.
- **3-player games:** use 3 colors only; the unused color's pieces stay boxed; do not place initial settlements/roads on the intersections/edges of the gap where the missing color would sit.

## 5–6 player extension (base game)
Adds components (18 more roads, 5 settlements, 4 cities, resource cards, extra land + sea frame) AND a **second building phase at the end of every turn**: any player may build (roads/settlements/cities/dev cards) if they can pay, but NO trading at all during this phase — not domestic, not maritime. Effectively everyone builds ~twice as fast; expect longer, more interactive games. Win at 10 VP (or 12+ by agreement for 5–6 players).

## CATAN for Two (official 2-player variant)
Ships with Traders & Barbarians (also a standalone 6th Ed "Catan for Two" exists). Two players each control TWO colors: your active color scores VPs; your "second" color blocks, trades at worse ratios, and moves the robber — a designed neutral buffer so trades still have tension.

## Common setup mistakes
- Robber not on the desert at start.
- Number spiral placed clockwise or covering the desert (skip it).
- Initial road placed before its settlement, or not attached to it.
- Collecting starting resources for the FIRST settlement (books say the second).
- Letting a 2:1 port face the wrong terrain without running the documented swap procedure.
