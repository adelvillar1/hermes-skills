# Utilization playbook: designing a Bot fleet

Synthesis of the Bot Mode docs (roster, groups, routines, peers) plus profile/cron/delegation
mechanics. Use this when deciding *what* to build, not *how* to click it.

## 1. Choose the right primitive

| Need | Use | Why |
|---|---|---|
| Recurring unattended work with one owner and a place to read results | **Bot + routine** (`[bot:<name>]` cron) | Runs land in that Bot's chat; delivers to a target; cheap to audit in `hermes cron list` |
| A standing identity with its own model, memory, skills, and cross-session continuity | **Bot** | A Bot *is* a profile: durable state, own credentials view, own SOUL |
| Reusable procedure any agent should follow | **Skill** | Loaded on demand; no second identity or memory to drift |
| One deterministic task chain inside the current conversation | `delegate_task` | Ephemeral subagents, same profile, minutes; no new identity |
| Independent long-running mission | Spawned `hermes` process / profile | Full tool access, hours-to-days, real isolation |
| Work that must live on another machine | **Connections / peers** | The agent's state stays where its data is |

Do not create a Bot to hold *knowledge* — that is a skill. Do not create a Bot to do one task once —
that is `delegate_task` or a routine. Create a Bot when **identity, isolation, and continuity** are the
point.

## 2. Design roles, not org charts

- One Bot = one clear role, written into **Title** and **Description**. Those strings are the roster role
  text injected into every other Bot's prompt (and into kanban routing), so vague descriptions degrade
  every teammate's recipient choice.
- Prefer a small fleet of generalists-plus-one-specialist over a project × function matrix: the matrix
  explodes combinatorially and multiplies shared-skill sync burden (same rule as profile topology in
  `hermes-multi-profile-architecture`).
- **Never point two agents at one profile.** Both write memory; each loads the other's writes; the state
  stops being anything you configured. Isolation is the feature, not overhead.

## 3. Route models per role

- **Model pin per Bot**: different Bots can run different models side by side. Pin the strong reasoner to
  the Bot that does hard analysis; leave chatter/group Bots on a cheap fast model, or leave them unset to
  inherit the launch profile (usually the cheapest correct answer).
- **Routines have their own axis**: pin the job (`hermes cron edit <id> --provider … --model …`) or set a
  fleet-wide `cron.model`. Unpinned jobs follow the global default and then **fail closed** when it
  changes — a silent-looking stalled routine is usually this drift guard, not a broken gateway.
- **Per-job reasoning effort** (`--reasoning-effort`) lets a heavy nightly routine think while cheap
  recurring ones don't. This is the cheapest available knob: set it before reaching for a bigger model.
- Keep a routine's prompt + attached skills stable; capability changes trigger a prompt rebuild (epoch)
  but per-turn drift is explicitly avoided — that is prompt-cache friendly by design.

## 4. Design groups for deliberation, not pipelines

- 2–6 members, mention-scoped rounds, three rounds max, 10 messages per send. Use groups when you want
  **specialists with different context to cross-check each other** (review, triage, planning), and say so
  in the members' descriptions.
- Expect **passes**: members speak only when they have something new. A silent member is normal; only a
  fully silent round settles the room.
- Give members a channel to escalate: `@user` + **needs you** badge is the designed decision handoff —
  tell them in their SOUL when to use it.
- Room members have no `message_agent`, so rooms can't cascade into DM storms — keep it that way rather
  than asking a room to "coordinate by DMing each other".
- A room is shared across your gateways and desktops with per-gateway merge and durable identity; renames
  are display-only, disbanding is permanent everywhere, and re-creating the same name makes a fresh room.

## 5. Place work where the data is

- A Bot's chats, sessions, memory and routines live on the machine that owns its profile. Put an agent
  next to the repo/DB/service it works on.
- **Peers** (no desktop in the loop) require the remote machine to run `api_server` with a strong
  `API_SERVER_KEY`, reachable over your network; the key is a credential in `~/.hermes/.env`. Use
  `hermes peer` for scripted/unattended cross-machine work, and the Desktop relay when a desktop owns the
  sockets.
- Registering a peer teaches every Bot Chat about the new teammate automatically (capability epoch), so
  there is no prompt-plumbing chore after adding a machine.
- Prefer shared keys/one OAuth pool for credential hygiene; a forked OAuth copy with single-use refresh
  tokens can invalidate the original. Give a Bot its own login only on purpose.

## 6. Anti-patterns

- Bot-per-function matrix (`cruising-implementer`, `cruising-reviewer`, …) instead of role-shaped Bots.
- Treating a Bot as a sandbox: profiles isolate *state*, not the filesystem. Use `terminal.cwd` and
  separate Bots for parallel writers instead.
- Parking standing guardrails (prod rules, never-touch tables) in memory only — SOUL.md is injected
  unconditionally and is the right home for rules that must never be *recalled* late.
- Asking a Bot to "wait for the reply" from `message_agent` — it is fire-and-forget. Or to interrupt
  another Bot mid-conversation — live interrupt is not implemented.
- Expecting every group member to answer, or expecting an unknown `@handle`/email-looking mention to
  resolve. Both are documented behaviour, not delivery failures.
- Hiding a Bot and then wondering why its routines still fire (correct) or assuming hidden means paused
  (it does not).
- Forgetting that a clone starts with an **empty cron store** and forked credentials — recreate routines
  and re-check keys after `--clone*`.
- Building "is this Bot busy/done?" logic on the presence strip: it is a 90-second write heuristic.

## 7. Operating rhythm

1. Add a Bot only when its role is clear; write Title/Description deliberately.
2. Smoke-test identity + protocol in one query (see SKILL.md Verification / `scripts/bot_roster_check.sh`).
3. Attach one routine at a time and confirm it fired (output file + chat history) before adding the next.
4. Re-audit the fleet occasionally: `hermes profile list`, `hermes cron list`, `hermes peer list`,
   `search_files` for the `hermes-bots` managed flag across profiles.
