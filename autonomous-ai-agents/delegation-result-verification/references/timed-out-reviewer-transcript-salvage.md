# Timed-out review subagent: transcript mining + repo sweep (graphics review, 2026-08-08)

## The incident

A spec-compliance + code-quality review subagent (`deleg_b2377a6e`) was dispatched against
commit `827d9f8` (P7 wall-aware fog). It returned `status=timeout` at the 1800s wall with
42 API calls and NO summary: `(no summary — status=timeout: Subagent timed out after
1800.0s with 42 API call(s) completed)`.

## Why this was a salvageable failure (not a re-dispatch case)

- api_calls was HIGH (42) → NOT Pitfall 5 rate-limit pileup (that signature: LOW counts 7–12).
- Duration was the full wall → NOT Pitfall 4 instant provider death.
- The subagent was mid-investigation: it had built GPU probe harnesses and was chasing
  a real bug when the wall hit. The transcript tail held its probe outputs.

## What the transcript contained

```
REVEAL-ORIENTATION {southWest_alpha: 255, southEast_alpha: 255, northWest_alpha: 255, ...
think | I've confirmed the reveal mask is Y-mirrored in the actual shader—revealed regions ...
ANGLE-MAPPING {east_behindWall: 255, west: 255, north: 255, south: 255, correct_if: "east=255, ...
RAW-SAMPLING {SW: {R_reveal: 0, G_lookup: 255}, NW: {R_reveal: 255, G_lookup: 255}, ...
```

The `think |` lines were the gold: the reviewer had concluded the reveal mask was
Y-mirrored in the real shader. That was a genuine MAJOR bug (see below).

## The junk files the subagent left behind (must sweep)

```bash
git status --short | grep -v "^ M\|^M "      # find untracked
ls .p7-* apps/web/p7-* scripts/.p7-* 2>/dev/null
```

In this case, 7 files: `.p7-flip-check.html`, `apps/web/p7-angle-check.html`,
`apps/web/p7-angle-check.ts`, `apps/web/p7-raw-check.html`, `apps/web/p7-raw-check.ts`,
`apps/web/p7-reveal-check.html`, `apps/web/p7-reveal-check.ts`. All removed with `rm -f`
before committing. (Reverse of Pitfall 12: there the subagent DELETED repo files; here it
CREATED probe junk.)

## Why the parent's own E2E had missed the bug

The live E2E revealed ALL 100 regions of the scene. A Y-mirror of an all-ones mask is
still an all-ones mask → the board rendered correct, all tests green, tsc clean. The
bug was only visible with a PARTIAL reveal.

## The verified fix (parent did this inline — no re-dispatch)

1. **Paper math first.** `setRevealed` wrote south regions to CPU row `n-1-cellY`; the
   shader samples the south edge at `regionUv.y ≈ 0`; `DataTexture.flipY = false`
   (three r168 default) means CPU row 0 ↔ v≈0. Net: vertical mirror. South wrote to
   v≈1.0, shader read v≈0.
2. **Fixed the write side** (`row = cellY`, no inversion) — the shader's world→UV→texel
   path was provably correct.
3. **Updated the unit test** — it had been *asserting the bug* with a wrong comment
   ("the shader flips Y back" — it doesn't).
4. **Live partial-reveal proof**: SQL-updated the scene's `fog.revealedRegionIds` to the
   south half (gy 0..16 → 50/100 regions), logged in as PLAYER (unrevealed = black),
   screenshot, PIL quadrant analysis:
   - TOP half: 32.0 avg lum, 129/7872 bright
   - BOTTOM half: 95.2 avg lum, 3135/7872 bright
   - Clean horizontal step between the 52–62% and 42–52% vertical strips.
   South-half reveal rendered in the BOTTOM half → mirror dead.
5. Restored scene to 100 regions, full suite green (315/315), web tsc clean,
   committed `cdec737`.

## Key takeaways

- **High-api_calls timeout on a reviewer = mine the transcript, don't re-dispatch.**
- **Never trust the transcript's probe outputs at face value** — the reviewer's own
  probes also showed "fogged-everywhere" which CONTRADICTED the live app; treat probe
  numbers as leads, re-derive from source + live E2E.
- **Test-data degeneracy hides bugs**: all-revealed test scenes cannot detect mask
  orientation errors. Always verify GPU texture orientation with a partial pattern.
- Prevention: brief review subagents to write intermediate probe conclusions to a
  notes file as they go, so a timeout never loses the reasoning.
