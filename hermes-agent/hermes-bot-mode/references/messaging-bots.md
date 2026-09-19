# Bot-to-bot messaging, the injected protocol, and peers

Source: Bot Mode docs — "Bots message each other", "Bot-to-bot across machines", "Peers"; verified
against `tools/bot_mode_dm.py`, `tools/bot_mode_probe.py`, `agent/system_prompt.py`,
`hermes_cli/subcommands/peer.py` and `tools/bot_relay.py` in this install.

## Mentions in any chat

- Type `@researcher have a look at this` in any chat: the active Bot hands the message off, waits for
  the reply, and reports back.
- Mention names are validated against the **live roster**, so an email address or an unknown `@` passes
  through untouched.
- Renamed Bots answer to their renamed tag (`@research-buddy`, `@researchbuddy`) and to the old profile
  name; the composer autocomplete offers both.
- **Across machines**: mentioning a Bot on another registered connection (use `@name-device` when names
  collide) delivers over the Connections registry in the background. The active Bot stays on this
  device, the desktop routes the message, the reply is relayed back attributed to that agent — your
  window's gateway never switches.

## The `message_agent` tool

Contract (schema injected, never registered in a toolset or the registry):

- **Gate:** present **only** in a canonical `Bot Chat` session on a Bot-Mode-managed install
  (a profile carrying `ui_meta['hermes-bots']`). Regular chats, group-room member sessions and CLI
  sessions never see it.
- **Fire-and-forget / asynchronous**, "like texting": it validates the target against the live roster,
  delivers into the target's own Bot Chat with attribution prefixed server-side, and immediately returns
  a delivery acknowledgement. It does **not** return the reply; the reply arrives later as a
  background-process completion notification. Never wait or poll.
- **Attribution prefix:** `Message from 🤖 <sender> (@<sender>):` — added by the tool, not the model.
- **Targets:** a teammate profile name, a peer form (`<peer>` or `<peer>/<agent>`), or a Desktop-relay
  agent handle on another connected machine. Targets are validated against the live roster.
- **Message transport is a real parameter** — nothing shell-interpreted; quotes, `$(...)` and backticks
  arrive verbatim.
- **Composition rules the tool tells the model:** compose every message yourself (say what *you* need
  from that agent), never forward the user's words verbatim, never reveal private 1:1 chat content, and
  message **one** clearly relevant teammate — don't fan out unless the user explicitly asked.
- **Receiving side:** a `Message from 🤖 …` message means a teammate agent is talking, not the user.
  Address them, reply concisely via `message_agent` to their handle, and stay silent on a pure FYI —
  never ping-pong acknowledgements.
- **Delivery is per-invocation**: the receiving Bot picks the message up when it next runs. Live
  interrupt of a Bot mid-conversation is future work — design handoffs as asynchronous.

## The protocol section

- Heading: `## Messaging other agents`; built at prompt-build time for the canonical Bot Chat session
  only — regular sessions and your SOUL.md stay untouched.
- Contains: the fire-and-forget contract, composition rules, the live roster of teammates **with roles
  from their profile title/description**, plus addenda for peer gateways and for agents on other
  Desktop-connected machines (each only when that roster is non-empty).
- Toggle: `agent.bot_mode_protocol: true` (default on) in `config.yaml`.
- **Capability epoch:** Bot Chats are effectively eternal, so "build the prompt once" would strand
  capability changes. A 12-hex fingerprint of the capability surface (disabled skills, enabled toolsets,
  MCP config, SOUL bytes, installed skill names, roster + roles, peers, relay roster) is embedded in the
  prompt and the prompt is rebuilt only when the stored epoch differs from disk — once per change, never
  per-turn drift. Registering or removing a peer refreshes each Bot Chat's protocol on its next message.
- Older desktop builds appended a frozen copy of the section to `SOUL.md`; `strip_legacy_protocol`
  removes it at load time so the live roster is the only copy any session sees.

## Peers (cross-machine, no desktop in the loop)

```
hermes peer add spark --url http://spark.lan:8377 --key <API_SERVER_KEY>
hermes peer list
hermes peer dm spark < /tmp/dm.txt                 # body from a file: nothing shell-interpreted
hermes peer dm spark/researcher < /tmp/dm.txt      # named profile on a multiplexed peer
hermes peer run spark --idempotency-key ticket-123 < long-task.txt
hermes peer status spark run_abc123 ; hermes peer stop spark run_abc123
hermes peer remove spark
```

- Verbs and aliases: `add|set` (`--url` required, `--key`, `--note`), `list|ls`, `remove|rm`, `dm`,
  `run`, `status`, `stop`. Peer name pattern: `^[a-z0-9][a-z0-9_-]{0,63}$`.
- `dm` resolves the remote **canonical Bot Chat** (creating it if missing) and runs ONE synchronous turn
  (600 s timeout), printing the reply — the exact cross-machine twin of `hermes -p <bot> chat`. `run`
  uses the async Runs API (`/v1/runs`) with an idempotency key; `status`/`stop` manage that run.
- Targets: `<peer>` = the peer's main agent; `<peer>/<agent>` = a named profile via the peer's
  `/p/<profile>/` mirror.
- Requirements: the peer machine runs the `api_server` gateway platform with a strong `API_SERVER_KEY`;
  reachability is your network's business (LAN, Tailscale, VPN). Key lives in `~/.hermes/.env` as
  `HERMES_PEER_<NAME>_KEY` (upper-cased, `-` → `_`); peer names/URLs live in `config.yaml` under
  `bot_peers`. The peer URL is user-registered and a cross-origin redirect will not carry the bearer key.
- Exit codes: 0 ok, 1 delivery/peer error, 2 usage error. If a peer does not advertise restart-durable
  run replay, `peer run` warns — keep the run ID and avoid blind retries after a gateway restart.
- The peer's API server is the transport: no new server surface, and the key is a credential — treat
  `HERMES_PEER_*` like any other secret.

## Desktop relay (agents on other connected machines)

For machines registered as Connections rather than peers, the gateway-side relay is file plumbing under
`<root>/bot_relay/` — `roster.json` (union roster pushed by the Desktop via `bot_relay.roster.sync`),
`outbox/` (envelopes queued by `message_agent`), `replies/` (one JSON per envelope via `bot_relay.reply`,
watched by a waiter spawned at send time so the reply wakes the sender like a local DM). No network:
**the Desktop owns every socket.** Enqueuing raises `EnvelopeRefusedError` when the target is
*definitively offline* — fail fast instead of queueing a DM nobody will drain.

## Verification

```
hermes -p <bot> chat -Q -q "Reply in 2 lines: the exact heading of your messaging-protocol section, and one teammate with its role."
hermes peer list
```

A bot that returns the heading and a real teammate proves the managed flag, the canonical-title gate and
`agent.bot_mode_protocol` are all live.
