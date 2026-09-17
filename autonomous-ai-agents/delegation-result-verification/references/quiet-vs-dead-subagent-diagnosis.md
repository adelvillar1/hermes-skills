# Quiet ≠ Dead: Diagnosing a "Stalled" Subagent Mid-Edit

A subagent editing a large file (1000+ lines) with several sequential `patch` calls will go quiet for minutes between transcript lines while it composes edits. This silence has TWO very different causes, and the right response is opposite for each:

- **Quiet-but-alive:** the subagent is in a long patching phase. It will recover and finish.
- **Dead-partway:** the subagent process actually died (model error, timeout, crash) after writing only part of its change, leaving a half-written file.

## Diagnostic (run all three, don't guess)

1. `stat -f "%Sm" <live-transcript.log>` + `wc -l` — is the mtime advancing and line count growing over a ~60s window? Advancing = alive.
2. `grep -c <expected-markers> <target-file>` + `git diff --stat <target-file>` — are the promised markers appearing/increasing? Increasing = alive and making progress.
3. `process(action='list')` — is the subagent's process still listed? Empty list + frozen transcript mtime + only-partial markers = **dead**, take over the work yourself.

## Real incident (2026-07-23, a landscape-visual-upgrade build)

Two subagents went quiet on big files:

- **Phase 4-server** (`terrainGenerator.ts`) was quiet-but-alive — markers climbed 0→7→10 and the transcript kept advancing; it finished fine.
- **Phase 1** (`tableRenderer.ts`, 3072 lines) was dead-partway — transcript frozen, `process list` empty, only 13 scaffolding lines of a 150-line change written (Sky import + fields + tone-mapping init, but none of the actual hemisphere/fog/sky/shadow logic).

Confusing the two is costly: killing a live subagent wastes its progress; waiting on a dead one wastes your whole turn.

## Take-over atomicity — never leave a dangling reference

When you finish a dead subagent's half-written change yourself (or implement any feature that spans "add a call site" + "add the symbol it calls"), **complete the entire atomic unit and reach `tsc --noEmit` clean BEFORE committing or ending the turn.** Do not commit — or let the turn end on — a call site that references a not-yet-defined function/method/field.

Real failure: a turn ended with `this.applyVegetationWind(...)` called in the load callback but the method not yet written, leaving the tree in a broken-tsc state for the next session to inherit.

The rule: each committed unit (and each turn boundary) must typecheck. If you must stop mid-feature, either finish the minimal definition so it compiles, or revert the call site — never ship the dangling half.
