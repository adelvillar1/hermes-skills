#!/usr/bin/env python3
"""Catan probability utilities (stdlib only).

Usage:
  python3 catan_sim.py                 # 2d6 distribution table
  python3 catan_sim.py <n>             # simulate n rolls, report counts & robber cadence
  python3 catan_sim.py --production    # expected resource yield per settlement/city per number
"""
import sys
import random
from collections import Counter

DIST = {s: sum(1 for a in range(1, 7) for b in range(1, 7) if a + b == s) for s in range(2, 13)}


def table():
    print("roll combos prob%  rolls-per-hit")
    for r in range(2, 13):
        p = DIST[r] / 36
        label = "robber" if r == 7 else str(DIST[r])
        print(f"{r:>4} {label:>6} {p * 100:6.2f} {1 / p:10.1f}")


def simulate(n):
    c = Counter(random.randint(1, 6) + random.randint(1, 6) for _ in range(n))
    sevens = c[7]
    print(f"{n} rolls: 7s = {sevens} ({sevens / n * 100:.2f}%), "
          f"mean gap = {n / max(sevens, 1):.2f} rolls (theory: 6.00)")
    for r in sorted(c):
        print(f"  {r}: {c[r] / n * 100:5.2f}% (theory {DIST[r] / 36 * 100:5.2f}%)")


def production():
    print("expected cards per roll (per building):")
    for r in range(2, 13):
        if r == 7:
            continue
        p = DIST[r] / 36
        print(f"  {r}: settlement {p:.4f} | city {2 * p:.4f} | every {1 / p:.1f} rolls")
    print("total expected/roll across 19 hexes depends on ownership; see references/probability.md")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        table()
    elif sys.argv[1] == "--production":
        production()
    else:
        simulate(int(sys.argv[1]))
