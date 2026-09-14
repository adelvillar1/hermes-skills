# Autonomous full-game driver policy

For the harder sibling of a smoke test: a headless driver that must **play a whole game to a win condition** (10 VP, checkmate, etc.) across N browser tabs, unattended. A smoke test proves a click works; this proves the app can be finished. Nearly every failure here is the *driver's policy*, not the app — distinguish the two before touching app source.

## Run the control experiment FIRST

Before attributing a stalled game to the app, run the project's existing kernel/headless bot to a win (e.g. a fixed-seat bot suite) and confirm it still reaches the target in the expected op count. If the bots win, the app is fine and only the browser driver policy is at fault; if they do not, you have a real regression. This one test separates "app broken" from "my bot plays badly" and prevents days of tuning a policy against a phantom bug. Re-run it after any app change that could affect game flow.

## Mirror the winning bot's tie-breaking EXACTLY

When a reference bot exists, its per-bucket selection rule is load-bearing, not incidental. Diff these against your driver:

- **Priority order** — e.g. roll before build and trade. Ranking trades above the income action makes the driver trade every turn and never produce; a 4:1 trade burns three cards for one, so it must come after production.
- **Tie-break within a bucket** — if the bot picks a **uniform random** member, an always-first driver gives every tab the identical (and typically worst) opening. Symptom of always-first: all seats equally starved and an untouched purchase pile after thousands of ops.
- **Phase gating** — placement vs. main-play ladders differ.

## Latches must key on a per-TURN value, not a per-FRAME one

A "once per turn" guard keyed on a monotonically increasing server sequence re-fires on every frame, because seq changes constantly. Key on the turn counter / active seat identity instead. Symptom: the same offer re-sent hundreds of times.

## Never repeat a refused proposal

In multi-tab negotiation, maintain a set of already-refused proposal keys (e.g. `give→want` pair) and skip them forever. A partner that cannot pay will refuse the identical ask every time, producing a self-feeding spin loop that burns the whole time budget with nothing built. Vary the asked-for resource across attempts, and cap proposals per turn.

## Verify legality from the acting client's OWN state before acting

Accept/consent actions that the server ships unconditionally to the target will be **rejected** if the target cannot actually pay. Read the pending proposal from public state, then check the *acting tab's* own private state (its rail/hand DOM) before clicking Accept. Never blind-accept: a rejection breaks a zero-rejection gate and looks like an app bug.

## Spectator / redacted views cannot supply private state

Joining an extra probe tab while the driver tabs hold all seats lands you in spectator mode with private fields stripped (hands empty, move lists empty). Read private data from a *seated* page or from the driver's own in-memory snapshot — never from a spectator DOM.

## Pre-flight the driver before every launch

A syntax error costs an entire run's wall-clock. Before launching:

- `node --check <driver>.mjs` (and `bash -n` for the stack script).
- Confirm the room code reaches the driver process as an **env var on the node command** (`RC=xxxx node driver.mjs`) — a shell variable assigned in a prior chained command is not exported to the child.
- Confirm any test-only win/force hooks you rely on are actually permitted for this run, and grep the driver to prove forbidden ones are absent.

## Instrument for the failure you cannot see

When a driver silently spins:

- **Log throws with context.** A main loop that catches and discards into a result object turns a hard TypeError into an infinite re-entry loop with no diagnosis. Log the message and stack at the catch site.
- **Flood-dedup the log.** Identical repeated lines collapse to a few mentions; without this a single wedge produces tens of thousands of lines that hide the real signal.
- **Census the actions.** Count each action type (rolls, builds, trades, discards, rejects). A census showing thousands of rolls and zero builds localizes the fault instantly, where prose reasoning does not.
- **Watchdog with a dump.** On a sequence stall exceeding the budget with no modal open, dump every tab's status and fail honestly rather than looping.

## `page.evaluate` templates must be CALLED

An IIFE-shaped template written as `(() => [...].map(...))` without a trailing `()` is an *uncalled arrow*; `page.evaluate` serializes it to `undefined` and the caller's `.filter`/`.map` throws a TypeError that a swallowing catch hides. End call-style templates with `()`. Compare against a sibling template known to work.

## Honest failure beats a forced green

If the win condition is not reached, say so and record *why* (with the census) rather than relaxing the target, enabling a cheat hook, or declaring partial success a pass. A starvation analysis that names the responsible policy is a real deliverable; a faked win is worse than useless.
