---
name: multiplayer-ws-browser-smoke
description: Use when browser-smoke-testing a multiplayer WS app.
---

# Multiplayer WS Browser Smoke

Browser-in-the-loop smoke tests for a multiplayer WebSocket app (VTT family: catan/mahjong/the D&D VTT project, any room-server + live clients). A unit wire suite proves the protocol; THIS proves a real browser can join, act, and rejoin against live bot clients. One process = one room; the server prints the room code at boot.

## Procedure

1. **Boot the stack, one background process per component.** Room server, each bot, and the dev server each get their OWN `terminal(background=true)` call — a shell `for s in 0 1; do bot & done` loop is rejected by the command guard and would serialize anyway. Capture the room code from the server log BEFORE launching clients: `grep -oE "room [A-Za-z0-9]{6}" /tmp/room.log | head -1 | awk '{print $2}' > /tmp/rc.txt`.
2. **Park bots with an explicit long stall timeout.** Auto bots waiting on a human-held seat hit their DEFAULT stall timeout (seconds) and exit — usually right before the human joins. Pass an explicit `--timeout 900000` (minutes) so the bots hold their seats parked for the whole run.
3. **Join from the browser as the human seat.** Drive headless Chromium via `playwright-core` from a sibling repo's node_modules + the cached `~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64` binary (set `executablePath`; no install needed). Fill the room code, select the human seat **by option `value`, not label or index** (a label miss that falls back to `index: 2` silently selects the wrong seat), submit, then read the rendered error element explicitly — a silent join failure must fail the smoke, not hang it.
4. **Attribution proof: park the other seats, then click.** With bots idle on seats 0+1, no other live client exists, so the `serverSeq` bump after the browser clicks a shipped move button is attributable by construction. Capture seq before, click the first enabled move button, poll until seq grows. Screenshot the moment.
5. **Reload → auto-rejoin, asserted on a LIVE socket.** Reload with `waitUntil: "domcontentloaded"` (see pitfalls), then assert the game state advanced (seq/projection content present AND the status shows the same seat). A "rejoined" banner alone is NOT proof — banner state can persist while the reconnect socket is dead. The strongest proof is a value only the server could send (e.g. a further seq tick, or the human's next click advancing seq again).
6. **Screenshot evidence to the repo's e2e directory** (`docs/e2e-review/<slug>/`), then `your vision tool` each shot — claim nothing about the HUD/panels you have not looked at.
7. **Tear everything down**: pkill room server, bots, dev server; `lsof -nP -iTCP:<port> -sTCP:LISTEN | wc -l` must reach 0 before the run counts as clean.

**Driving a full game to a win condition autonomously?** See `references/autonomous-game-driver-policy.md` — control experiment, mirroring the reference bot's tie-breaks, per-turn latches, refused-proposal sets, and instrumentation.

## Pitfalls

- **Seat claims outlive their sockets (inSeatTaken on re-run).** A disconnected bot's seat stays claimed — rejoinable via its token — until the server's stale sweep releases it. A fresh browser context (fresh localStorage, no token) joining that seat gets `inSeatTaken`; the room is not broken, the seat is in grace. Defense: start a FRESH room per smoke run, or reuse a persistent browser profile so the same seat token rejoins instead of re-claiming. Do not burn time debugging the server for this.
- **`waitUntil: "networkidle"` never resolves with an open WebSocket.** The app's own ws connection (plus the Vite HMR socket in dev) keeps the network busy forever — `page.reload({waitUntil:"networkidle"})` and `page.goto(..., networkidle)` time out after navigating. Use `domcontentloaded` + explicit `waitForSelector` on app-specific markers (e.g. `#hud-panel`).
- **`new URL("blob:...").hostname` is empty — request filters misclassify same-origin work as remote.** troika-three-text (drei `<Text>`) rasterizes glyphs to `blob:` URLs; a "count remote requests" probe that allowlists by `hostname` counts them as remote and reports a false CDN regression. Filter on `u.origin` (blob URLs inherit the creator origin) or explicitly skip `blob:`/`data:` protocols. Verify a suspicious count by logging URLs, not just the number.
- **The lone 404 that pollutes "zero page errors": `/favicon.ico`.** Browsers auto-request it; every fresh page logs a console 404, breaking a strict zero-error gate. Ship an inline SVG data-URI `<link rel="icon" href="data:image/svg+xml,...">` — no asset file, no request, no 404.
- **React StrictMode kills one-shot reconnect latches.** A `useRef(false)` "retried" latch set inside a mount effect SURVIVES StrictMode's simulated unmount (refs are preserved across the double-invoke), so pass 2 early-returns and the reconnect never fires in dev. The fix is to remove the latch and key the reconnect effect on an observable status (`status === "closed"`), letting the hook's own in-flight-socket guard dedupe. If a reload-rejoin "works" in one environment, check whether it worked because the socket never actually died — assert the live-socket criterion (step 5), not the banner.
- **`pkill -f <pattern>` before relaunching anything.** Orphaned room servers hold ports and seat claims across smoke attempts; the seat-grace trap above is usually the symptom. Sweep dev ports to 0 listeners before declaring a run done.
- **Bot log tails lie about aliveness.** "stalled: no frame" in a bot log means THAT bot exited; check `ps aux | grep "[c]li.ts" | wc -l` for the live count before reasoning about who can advance the game.
- **Run the kernel-level control experiment before blaming the app.** When an autonomous driver cannot reach the win condition, first run the project's existing headless bot suite to completion. If the bots still win in the expected number of actions, the app is sound and only the driver's policy is at fault; tune the driver and leave app source frozen. Do this before every round of policy tuning, not after.
- **Give each simulated seat an isolated browser context.** Multiple tabs in one shared context share `localStorage`, so a "last room"-style key written by tab A makes tab B auto-rejoin into an already-taken seat instead of claiming its own. Isolate contexts per seat, and add a filler tab for any seat nobody drives when the room refuses to start until all seats are claimed.

## Guard-layer interop (the harness terminal)

The smoke workflow trips the command guard constantly — expect and route around, never fight:
- `grep -h`/compound grep shapes get intercepted by the `rtk` wrapper and print a usage banner instead of results — use the `search_files` tool for repo greps.
- `echo "...$(cmd | wc -l)"` command substitution, `for` loops with nested `$(...)`, and `&` job control are hardline-blocked — split into separate small `terminal()` calls, one background process per call.
