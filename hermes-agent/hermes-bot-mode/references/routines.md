# Routines (a Bot's recurring work)

Source: Bot Mode docs — "Routines"; Cron docs — model resolution, drift guard, preflight, skills,
workdir, context chaining, no-agent mode.

## What a routine is

- The **Routines** pane docks beside the chat while the Bots tab is active and attaches recurring tasks
  to the Bot that does them. It steps aside when you switch back to Sessions (older builds keep it
  always visible).
- A structured schedule picker builds the schedule (frequency first, then only the detail that matters),
  with an **Advanced** field exposing the raw Hermes schedule string.
- Routines are **plain Hermes cron jobs** namespaced `[bot:<name>] <routine>`: they appear in
  `hermes cron list` and the core Cron page. **Runs land in the Bot's own chat history**, so the result
  sits where you would talk to that Bot anyway.
- Therefore: the pane is a UI over `~/.hermes/cron/jobs.json` — edit from either side, never by hand-patching
  the file (write-safety can block it silently).

## Creating one

```
cronjob(action="create", schedule="0 9 * * *", name="[bot:scout] Morning inbox summary",
        skill="email-inbox-triage", prompt="Summarize unread mail and flag anything needing a reply.")
```

Or CLI: `hermes cron create "every 2h" "<prompt>" --skill email-inbox-triage --name "[bot:scout] …"`.
Mutations (`pause`, `resume`, `run`, `remove`, `edit`) accept a job **name** case-insensitively in place
of the hex ID; ambiguous names are refused with the candidate list.

## Cron semantics a bot owner must know

- **Every run is a fresh agent session** with the normal static tool list — the prompt must contain
  everything the job needs that attached skills don't provide. Vague prompts ("check on that server
  issue") are the classic failure; write the SSH target, the exact command and the success criterion.
- **Model resolution at fire time:** per-job pin → `cron.model`/`cron.model_provider` → global default.
  The `cronjob` tool **cannot** set a per-job model — inference pins are user-owned (`hermes cron edit
  <id> --provider <p> --model <m>`). If neither pin nor `cron.model` is set, Hermes snapshots the global
  provider/model at creation and the job **fails closed** on later global changes: it skips the run, makes
  no inference call, and alerts **once**, staying silent on subsequent ticks until acted on. For any
  recurring bot routine, either pin it or set `cron.model`. The guard is `cron.model_drift_guard: false`
  to disable (at the cost of unattended jobs silently inheriting paid defaults).
- **Per-job reasoning effort** (`--reasoning-effort none|minimal|low|medium|high|xhigh|max|ultra`)
  overrides global thinking level for that job only — run a heavy analysis at `high` while cheap
  recurring jobs run at `minimal`. No effect on `no_agent` jobs.
- **Preflight validation** runs before agent machinery is built: provider key resolves (skipped when a
  `fallback_providers` chain exists), attached skills are ready, delivery targets are known with gateway
  credentials. Failure ⇒ `last_status: blocked_config`, ONE alert, **no LLM call**. `cron.preflight: false`
  disables it.
- **Skills** can be attached (`skill=` / `skills=[…]`), loaded in order with the prompt layered on top —
  the right way to give a routine a reusable workflow without stuffing it into the prompt.
- **`workdir`** (absolute, must exist) injects that directory's `AGENTS.md`/`CLAUDE.md`/`.cursorrules`
  and points terminal/file tools there. Jobs with a workdir run **sequentially** on the scheduler tick
  (process-global cwd), workdir-less jobs still run in parallel. `workdir=""` clears it.
- **`context_from=["other-job", …]`** injects the most recent completed outputs of upstream jobs as
  context — it does not wait for upstream jobs in the same tick.
- **Delivery**: origin chat, local files, or configured platform targets (`local`/`origin` are never
  credential-checked). For a bot whose whole point is one chat, delivering into its Bot Chat is what
  makes the result land in the right place.
- **No-agent mode**: a script on a schedule whose stdout is delivered verbatim, zero LLM involvement —
  the cheap option when a routine is pure polling/formatting.
- **A cron run cannot create cron jobs** unless explicitly enabled in config; when enabled, `deliver:
  origin` inside a cron run resolves at create time to the creating job's concrete target so no job can
  point at a dead session.
- Scheduling infrastructure: the **gateway daemon ticks every 60 s**; cron jobs and the desktop Routines
  pane both need the owning profile's gateway alive. Outputs: `~/.hermes/cron/output/{job_id}/{timestamp}.md`.

## Bot-specific pitfalls

- A Bot with shared keys but its own gateway is fine; a Bot with routines and **no running gateway**
  looks broken and is not — start/install the gateway for that profile.
- Cloning a Bot does **not** clone its routines. Recreate them under the new profile and pause/remove the
  originals only after the new ones have fired successfully.
- Prompts are scanned for prompt-injection and credential-exfiltration patterns at create/update time.
- The `cronjob` tool works from a normal session; scheduled *agents* cannot schedule recursively by
  default — that is deliberate anti-runaway behaviour, not a bug.
