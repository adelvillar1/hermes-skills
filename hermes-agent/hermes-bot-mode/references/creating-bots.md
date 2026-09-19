# Creating, editing, and cloning Bots

Source: Bot Mode docs — "Creating a Bot", "Editing, duplicating, deleting"; Profiles docs — clone
semantics, OAuth sharing, aliases. CLI forms verified against this install's `hermes profile --help`
surface and `hermes-multi-profile-architecture`.

## Quick path

**New Agent** in the roster → three fields (**Name**, **Title**, **Description**) → the Bot exists in
seconds and self-introduces as the first message of its new Bot Chat. The Title/Description become the
role text other Bots see, so write them as instructions-to-teammates, not marketing.

## Advanced surface

- **Clone from an existing profile** — start from another Bot's config, skills, SOUL and memory, or
  pick **Fresh profile** for a clean start.
- **Create empty** — skip the bundled skills entirely for a minimal profile.
- **Model & provider pin** — any provider/model pair Hermes knows; different Bots can run different
  models side by side. Leave unset to inherit from the launch profile.
- **Custom SOUL.md** — persona and standing instructions (injected unconditionally, stronger than
  memory recall).
- **Per-skill, per-toolset, per-MCP-server enablement** — tick exactly what the specialist needs.
- **Shared keys** (default) — the Bot shares one OAuth/token pool with the main profile so credential
  refreshes cannot invalidate each other. Older gateways copy credentials instead: still functional,
  just forked.

## Creating on another machine

With more than one connection registered the dialog grows a **Create on** picker; the profile is
created on **that** machine's backend and your window never switches gateways. The Bot then shows up
as a Connections Bot (with an `@name-device` handle when the name exists on several machines).

Remote-creation notes:

- **Clone source** is a profile of the *target* machine (its `default`) — a remote box doesn't have
  your local profiles to clone.
- The live Capabilities tab pins to the target machine's backend, so skills/tools/MCP you configure
  land on the machine the Bot will live on. Older desktop builds fall back to staged checklists; both
  read the target machine's catalog.
- Cancelling the dialog discards the draft profile on whichever machine it was created.
- With a single connection the picker is hidden and the Bot is created locally (the old behaviour).

## Edit / duplicate / delete

- **Edit Profile** (right-click) reopens the same surface on the live profile any time: avatar, title,
  description, model pin, skills, toolsets, MCP servers, full SOUL.md.
- **Duplicate** (right-click) is a full clone — config, skills, SOUL.md, memory and its look.
- **Delete Profile** permanently removes one behind the same destructive confirmation the desktop's
  profile menu uses. **The default profile cannot be deleted.**

## CLI equivalents

```
hermes profile create <name> --description "<role>"   # role feeds kanban routing and bot rosters
hermes profile create work --clone                    # config + .env + SOUL + skills, fresh memory
hermes profile create backup --clone-all              # everything except history and cron jobs
hermes profile create work --clone-from coder         # explicit source profile
hermes profile rename <old> <new>                     # updates mention tags too
hermes profile list ; hermes profile show <name> ; hermes profile use <name>
```

Each profile also gets a command alias at `~/.local/bin/<name>`, so `coder chat`, `coder cron list`,
`coder gateway start` all work — they are `hermes -p <name> …` under the hood.

## Profile facts that shape Bot design

- **A profile is a Hermes home** (`HERMES_HOME`): config.yaml, .env, SOUL.md, skills, sessions,
  memory, cron, gateway state. That is the whole Bot.
- **One writer per profile.** Two agent processes on one home compound each other's memory until the
  state stops being anything you configured. Bots that need shared memory should use an external
  memory provider instead.
- **Cron jobs are never cloned** (`--clone`, `--clone-all`, `--clone-from`): a clone that inherited
  them would run every job twice. A new Bot starts with an empty `cron/` — recreate the routines it owns.
- **OAuth logins are shared, not copied.** Anthropic/Codex/xAI logins use single-use refresh tokens;
  clones drop those rows and keep reading the root `~/.hermes/auth.json`, so a refresh anywhere keeps
  every Bot signed in. Give a Bot its own login only deliberately: `hermes -p <name> auth add <provider>`.
- **Profiles are not sandboxes.** Same filesystem access as your user; `terminal.cwd` only sets where
  terminal/file tools start (and `cwd: "."` means "launch directory", not the profile directory).
- **SOUL.md is injected, not enforced** — it guides the model but is not a workspace boundary, and
  changes land cleanly on a new session.
- **Host profiles share the real OS `HOME`** by default so `git`/`gh`/`npm`/Codex credentials keep
  working; `terminal.home_mode: profile` opts into a per-profile home at the cost of re-initializing
  those credentials inside it.
- Distributions/export exist for shipping a whole Bot: `hermes profile export <name>` /
  `hermes profile import`, or a git-based distribution installed with `hermes profile install`.
