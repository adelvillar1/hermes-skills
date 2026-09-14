---
name: hermes-bot-mode
description: "Bot Mode: rosters, group chats, routines, peer DMs."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Hermes, Bots, Multi-Agent, Profiles, Routines]
---

# Hermes Bot Mode

Bot Mode turns Hermes profiles into a roster of named **Bots** in the desktop app: each Bot has
its own role, model pin, skills, SOUL, memory and avatar, can run recurring **routines**, deliberate
in **group chats**, and message other Bots through `message_agent` or across machines via **peers**.
This skill covers designing a bot fleet and operating all four orchestration surfaces, plus the
CLI-visible reality behind every one of them. It does NOT cover desktop plugin authoring or the
generic profile-splitting procedure (that is `hermes-multi-profile-architecture`) — and it assumes
no filesystem isolation: a Bot is a profile, not a sandbox.

**The one mental model:** *a Bot **is** a Hermes profile*. Bot Mode is a UI over that primitive —
no core patches, no daemons, no extra storage. Everything is inspectable from a shell:
`hermes -p <bot> chat`, `~/.hermes/profiles/<bot>/`, `hermes cron list`, `hermes profile list`.
When a UI behaviour looks mysterious, find its CLI twin first.

## When to Use

- "Create a bot / new agent", "give this bot a role", "pin a model to that bot".
- "Why didn't my bot reply in the group chat?" / "bots aren't answering each other".
- "Make my bots talk across machines" / "register another gateway" / `hermes peer`.
- "Attach a routine to this bot" / "the bot's scheduled job didn't run".
- "Two agents are both named research" / `@name-device` handles / renamed bots.
- "Hide this bot from the roster", bot avatars, AI portraits, pixel pets.
- Deciding whether work belongs in a **Bot**, a **skill**, a **routine**, or `delegate_task`.

## Prerequisites

- Hermes install with the desktop app. Bot Mode ships bundled and **on by default** (toggle:
  Settings → Plugins → Bots); no install step.
- `agent.bot_mode_protocol: true` in `config.yaml` (the default) — this is the gate for the
  teammate protocol injected into canonical Bot Chats.
- For cross-machine DMs without a desktop: the peer machine runs the `api_server` gateway platform
  with a strong `API_SERVER_KEY`; its key is stored locally as `HERMES_PEER_<NAME>_KEY` in
  `~/.hermes/.env` and peer names/URLs live in `config.yaml` under `bot_peers`.
- Routines fire from the owning profile's **gateway** — a bot with routines needs its gateway up.

## How to Run

Bot Mode is entirely CLI-mirrorable — drive it with `terminal` and inspect it with `read_file`:

```
hermes profile list                 # the roster
hermes -p <bot> chat                # a Bot's chat (same agent the UI opens)
hermes cron list                    # routines appear as '[bot:<name>] <routine>'
hermes peer list                    # cross-machine teammates
```

Ask the agent for UI-side work in plain language ("create a bot named Dixie that watches my inbox");
Bot Mode's create/edit/roster surfaces are desktop-only, so hand the user the click path rather than
inventing a CLI flag for them.

## Quick Reference

| Thing | Value |
|---|---|
| Bot home | `~/.hermes/profiles/<bot>/` (default profile is `~/.hermes` itself) |
| Canonical chat title | `Bot Chat` — exactly; the protocol section is gated on this title |
| Protocol heading | `## Messaging other agents` |
| Protocol toggle | `agent.bot_mode_protocol` (default `true`) |
| Managed flag | `ui_meta['hermes-bots']` in a profile's `profile.yaml` |
| Routine naming | `[bot:<name>] <routine>` (plain cron jobs) |
| DM tool | `message_agent(target=..., message=...)` — canonical Bot Chat only |
| Attribution prefix | `Message from 🤖 <sender> (@<sender>):` (added server-side) |
| Default-profile handle | `@hermes` |
| Peer CLI | `hermes peer add\|set`, `list\|ls`, `remove\|rm`, `dm`, `run`, `status`, `stop` |
| Peer target form | `<peer>` or `<peer>/<agent>` (`/p/<profile>/` mirror on the peer) |
| Peer DM timeout | 600 s (one synchronous turn) |
| Group caps | 2–6 Bots · 3 serial rounds · 10 messages per send |
| Jobs / output | `~/.hermes/cron/jobs.json`, `~/.hermes/cron/output/{job_id}/{timestamp}.md` |

## Procedure

1. **Inventory the fleet before changing it.** `hermes profile list`, then `search_files` for
   `hermes-bots` across `~/.hermes/profiles/*/profile.yaml` to see which profiles Bot Mode manages.
   A profile only receives the teammate protocol when *some* profile carries the managed flag.
2. **Create a Bot with its role in the metadata.** The UI's three fields (Name, Title, Description)
   become the roster **role** text injected into every other Bot's prompt — treat Title/Description
   as prompt engineering, not decoration. CLI equivalent: `hermes profile create <name> --description "<role>"`.
3. **Pin capability deliberately.** Model/provider pin per Bot (unset = inherit the launch profile),
   tick only the skills/toolsets/MCP servers that specialist needs, write its `SOUL.md`, and prefer
   **shared keys** so credential refreshes can't invalidate each other. See
   `references/creating-bots.md`.
4. **Wire the messaging surface.** Mention a Bot with `@name` in any chat for a handoff; a Bot DMs a
   teammate with `message_agent`. Verify the protocol actually landed before debugging anything else:
   ```
   hermes -p <bot> chat -Q -q "Reply in 3 lines: which profile you are, one teammate from your roster, and the exact heading of your messaging-protocol section."
   ```
5. **Attach routines.** Create the cron job that the Bot owns (UI Routines pane, or `cronjob` tool /
   `hermes cron create`), naming it `[bot:<name>] <routine>` so it reads as that Bot's work in
   `hermes cron list`. Prompts must be self-contained — every run is a fresh session.
6. **Add peers only when no desktop is in the loop.** `hermes peer add spark --url http://spark.lan:8377 --key <API_SERVER_KEY>`,
   then `hermes peer dm spark/researcher < /tmp/dm.txt`. Registering a peer refreshes every Bot Chat's
   protocol on its next message, so bots learn the new teammate on their own.
7. **Verify** with the check in the Verification section, then report which surfaces you actually
touched.

## Pitfalls

- **A Bot is a profile, and one profile has exactly one writer.** Two agent processes on one Bot
  compound each other's memory. Parallel work ⇒ separate Bots.
- **`/new` inside a Bot's canonical chat is rerouted to `/compact`** — deliberate (the forever-chat
  promise). Forgetting this makes "the bot lost its history" look like a bug; regular sessions on the
  same profile keep full `/new` freedom.
- **`message_agent` is fire-and-forget.** It returns an acknowledgement, never the reply; the reply
  arrives later as a background completion notification. Never wait or poll for it.
- **`message_agent` exists only in canonical Bot Chat sessions on Bot-Mode-managed installs.** Not in
  regular chats, not in group-room member sessions, not in CLI sessions. Its schema is injected, never
  registered in a toolset — so "the tool is missing" usually means wrong session or unmanaged install.
- **Delivery is per-invocation.** The receiving Bot picks the message up when it next runs; live
  interrupt of a Bot mid-conversation is not supported. Design handoffs as asynchronous.
- **Group rooms do not all reply.** Members pass when they have nothing to add; only a full silent
  round settles the room. @-mention to scope a round at specific members.
- **Mentions are validated against the live roster.** Unknown `@` or an email address passes through
  untouched — a silent non-delivery here is correct behaviour.
- **Name collisions disambiguate to `@name-device`**, and the default profile answers to `@hermes`.
- **Hidden is display-only.** Hiding a Bot removes it from the roster and toasts but leaves mentions,
  group membership and routines running — unread activity accumulates silently behind the eye toggle.
- **Routines are cron jobs**, so they inherit cron semantics: drift guard fails closed on unpinned
  model changes, a scheduled agent cannot manage cron unless explicitly enabled, and `workdir` jobs run
  serially. See `references/routines.md`.
- **Rooms and roster metadata live on the backend**, mirrored into shared profile metadata — a profile
  move/rename has fleet-wide display effects. Durable room identity means a same-name recreate is a
  genuinely fresh room.
- **Bot Mode never owns your data.** Toggling the plugin off unregisters the UI only; profiles,
  sessions and cron jobs are untouched.

## Verification

One pass proves identity, protocol injection, and routine ownership for a Bot:

```
hermes -p <bot> chat -Q -q "Reply in 3 lines: (1) which profile you are, (2) one teammate from your roster with its role, (3) the exact heading of your messaging-protocol section."
hermes cron list | grep -F '[bot:'
hermes peer list
```

Expected: the bot names itself, lists real teammates with roles (proof the roster reached its prompt),
and quotes the section heading `## Messaging other agents`. If the heading is absent,
check the canonical chat title is exactly `Bot Chat` and `agent.bot_mode_protocol` is true.
`scripts/bot_roster_check.sh` runs this fleet-wide through the `terminal` tool.

## References

Load on demand with `skill_view(name="hermes-bot-mode", file_path="references/<file>")`.

- `references/roster-and-identity.md` — roster rows, presence strip, hide/unhide, forever-chat, rename/tag sync, avatars and pets. Load when working on how Bots appear or are identified.
- `references/creating-bots.md` — New Agent surface (quick + Advanced), clone/empty, model pin, SOUL, capability ticking, Create-on-remote, duplicate/delete, and the profile facts that shape all of it. Load when creating or editing a Bot.
- `references/group-chats.md` — rooms, rounds and caps, mention scoping, needs-you escalation, membership, durability and cross-machine rooms. Load for any group-room question or "why did nobody answer".
- `references/messaging-bots.md` — @mention handoffs, `message_agent` contract, the injected protocol, `agent.bot_mode_protocol`, peers and the Desktop relay. Load for bot-to-bot or cross-machine messaging.
- `references/routines.md` — Routines pane, `[bot:<name>]` cron namespacing, model/reasoning pins, drift guard, preflight, workdir, no-agent mode. Load when scheduling or debugging a Bot's recurring work.
- `references/multi-connection.md` — the Connections registry, device names, `@name-device`, per-source agents, plugin SDK hooks, roster troubleshooting. Load for multi-machine fleets.
- `references/utilization-playbook.md` — decision matrix for Bot vs skill vs routine vs `delegate_task`, role and model design, group design, anti-patterns. Load when designing a fleet or arguing for/against a Bot.
- `scripts/bot_roster_check.sh` — fleet-wide identity + protocol + routine check.
