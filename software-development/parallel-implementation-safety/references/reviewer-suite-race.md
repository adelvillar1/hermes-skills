# Reviewer full-suite race with a concurrently-dispatched implementer

Extends the "one writer per path" rule: a race exists not only when two
writers edit the same file, but also when a dispatched **implementer** edits a
file that a concurrently-running **reviewer's suite run** reads.

When a spec-compliance reviewer verifies a change by running the full suite
(e.g. `npx vitest run apps/table`), and you concurrently dispatch a downstream
implementer that edits a file the suite reads (any `*.test.ts`, or a source
file with a test asserting against it), the reviewer's suite run and the
implementer's write race — the reviewer sees a half-edited tree: flaky PASS/FAIL,
or a suite failing for reasons unrelated to the change under review, so the
review conclusion is untrustworthy.

**Real incident (the D&D VTT project, 2026-08-24):** Phase 1 (wire `ATTACK` echo → VFX) was
parent-implemented and reviewed. Phase 2 (port 4 VFX materials) edits
`apps/table/src/three/vfx/profiles.ts` **and** `profiles.test.ts`. The Phase 1
reviewer's verification runs `npx vitest run apps/table`, which reads
`profiles.test.ts`. Dispatching Phase 2 at the same moment would let the
implementer rewrite that test file mid-suite-run, corrupting the Phase 1 review.
Resolution: **hold Phase 2 until the Phase 1 review lands**, then dispatch.

## Rule

1. When a reviewer verifies via the **full suite**, freeze the tree for the
   review's duration. Only dispatch work whose file reads/writes the suite does
   not touch.
2. If a downstream phase edits a file the suite reads, **serialize** it after
   the review.
3. Dispatch reviewers **read-only** (`toolsets=['file','terminal']`); if you
   cannot serialize, re-run the suite AFTER all conflicting writes settle.

## Cheap pre-flight

`rg -n "<downstream-file>" <suite-entry>` — if a pending implementer's file is
imported/asserted by any test the reviewer runs, it's a race → serialize.
