---
name: ws-room-wire-testing
description: "Wire-test WebSocket room servers with real clients."
tags: [websocket, testing, room-server, multiplayer, vitest]
related_skills: [subagent-driven-development, vtt-table-live-client, delegation-result-verification]
---

# WebSocket Room-Server Wire Testing

Use when building or testing a room-server transport (VTT family (catan-style room servers)): one process = one room; client sends `join`/`op`/`ping`, server pushes `welcome`/`projection`/`event`/`error`; redacted per-seat projections. Tests are written with REAL `ws` clients. The failure modes below cost hours each; they are harness and lifecycle traps, not server-logic bugs — diagnose accordingly.

## Harness rules (the race traps)

1. **The server sends `event` + `projection` in one synchronous burst.** A waiter armed AFTER the send ("wait for next frame matching X") misses frames that already arrived — it looks exactly like a server dispatch-ordering bug and can burn an entire agent budget chasing ghosts. Defense: the test client records ALL frames with the monotonic `serverSeq`, and waits MATCH BY SEQ, not by arrival order:
   - `act(op)` = arm waiters **before** sending, then await the `event` whose `serverSeq` is new.
   - `syncTo(client, seq)` = drain frames until `serverSeq >= seq` — **mandatory before any cross-socket read** (broadcasts to non-actors are async, so `clients[cur].moves` right after another seat acted reads stale/empty frames).
   - A `refresh()` helper that returns at the projection is unsound for terminal assertions: order the server so the terminal event (`gameEnded`) ships **before** the final projection (document this as load-bearing in the protocol doc), and await `gameEnded` per client explicitly before asserting on it.
2. **Frame-level trust in tests is asymmetric on purpose**: malformed *inner* ops die at the strict wire schema (`error{badMessage}` + parse strike) and never produce `event{rejected}`; a wire-valid op with forged `seat` is an authority rejection (`event{rejected}`). Don't write a rejected-event assertion for the first case.
3. **JS falsy-seat trap in test loops**: `if (!seat) continue` skips seat 0 — the most common actor. Index-valued seats must be compared `seat === null`/`=== undefined`, never truth-tested.
4. **Fixtures must not over-specify game reality.** If a test needs "seat X holds resource R" or "a pending trade exists", derive give/want from each side's **own visible hand in the actual projection** for the chosen seed — don't hard-code a resource the seed may never deal that seat across 85 turns. The projection being honest about your own hand is the redaction contract; failing to find wood isn't a leak, it's the game.
5. **Teardown hygiene to prevent cross-test flake attribution**: client teardown must clear armed waiter timers (and NOT reject outstanding waiters — a rejection after the test settled surfaces as an unhandled-rejection warning blamed on whoever runs next); module-level globals used by helpers (`CURRENT_SERVER`) must be nulled in `afterEach`; give multi-iteration wire loops an explicit per-test timeout instead of the default 5s vitest cap.

## Seat lifecycle invariants (transport over a pure room core)

Every path that ends a connection must run the SAME cleanup: release **every** seat the socket owns and broadcast `playerLeft`. The three paths are easy to get individually wrong:

- **close (FIN)** — must release all seats mapped to the socket (a `#seatOwner` map scanned by socket identity, not just `conn.seat`, in case bindings ever multiply).
- **stale sweep (dead peer no FIN saw)** — must call the room's disconnect + broadcast, not just `ws.terminate()`. Terminating without releasing leaves `isConnected(seat) === true` behind a CLOSED socket → the seat is permanently `inSeatTaken` and, under a "lobby waits for partially-claimed rooms" policy, **the room stalls forever**. Any sweep test that only asserts the noisy client noticed will miss this: assert `room.isConnected(seat) === false` after the drop.
- **strike-drop (protocol-violator kick)** — route through the close handler; hand-deleting from the conn map makes the later real close early-return and orphan the seat (ghost variant #2).

**One join per socket.** A second `join` on a bound socket is an error (`badMessage`), not a rebind. Rebind-on-join must be defended: churn patterns (`join 0 → 1 → 2` then close) orphan every seat but the last — the seat-claim is a *credential* (token), decoupled from connection, so "release on close" semantics + multi-join = lobby DoS. If you allow token-rejoin while the old socket is still open (legit for wifi-drop recovery before FIN arrives), treat the token as a bearer credential explicitly: rotation retires it on use, and fence the superseded socket from acting (`error{notSeated}` on ops), then document the ruling.

## Determinism gate

A transport suite that aggregates green can hide a 2-in-5 flake on the flagship test (other files' latency papers the race over). Before declaring an M2/transport phase done: run the wire suite **in isolation 3–5×** (`vitest run apps/<room>/src/server.test.ts` repeatedly) and require identical results. Aggregate `npm test` green is necessary, never sufficient.

## Provider/send hygiene

- `ws.send` on a CLOSING socket: wrap every send in try/catch — one dead peer must not abort a broadcast loop over all conns.
- Add a `bufferedAmount` ceiling (e.g. 256KB) per connection: a client that can't drain gets stopped, not OOMed; it resyncs via the `serverSeq` gap.
- Never echo server-side `Error.message` text to other clients on rejections if it can interpolate client-controlled values (names); ship `code` + structured `details` only (and audit that `details` carries no hidden state before keeping it).

## Escalate

After the pure-room core and the wire suite are both reviewed, a final human gate pays for itself: `npm run start` with env-configurable port/seed/player-count, plus a **text-mode client with an `--auto` bot mode that plays strictly from shipped `legalMoves` frames** (never recompute client-side) driving N real sockets to a real winner — captured under `docs/e2e-review/`. The bot mode doubles as a regression harness and proves the wire contract is *playable*, not just schema-valid.
