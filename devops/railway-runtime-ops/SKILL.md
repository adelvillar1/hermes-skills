---
name: railway-runtime-ops
description: "Operate Railway deploys and runtime triage from a CLI box."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Railway, Deploy, Postgres, Triage]
---

# Railway runtime operations from a CLI-driven box

## When to Use

- Diagnosing a failed or stuck Railway deployment from the CLI (no dashboard) after a push, on any project — including the "build succeeded but production never picked it up" confusion.
- Recovering Postgres advisory locks after container churn, deciding whether an "idle in transaction" backend is zombie or live, or verifying what is actually serving.
- Any scripted `railway ssh` / redeploy / log-pull against a live service, before trusting a log's silence or an "it's healthy" reading.

## Always-on rules

- **Never `railway up` to deploy** — deploy state moves by git push only; the CLI's upload path bypasses the repo trigger the platform watches. Recovery after a failed deploy is `railway redeploy -s <service> --from-source -y` (pulls the latest commit of the connected repo and rebuilds — no push, no PR, no code change needed for a transient builder failure).
- **`railway logs` with no deployment ID resolves to the most recent SUCCESSFUL deployment.** Reading "the logs" while a deployment is FAILED silently shows the previous healthy build — the classic false-alarm conclusion. When investigating a failure, get the failing deployment's ID from `railway deployment list -s <service>` and pass it explicitly.
- **Build failure vs deploy failure are different evidence**: `railway logs <id> -b` reads the build; `-d` reads release/start. A Next build that compiled and pushed an image but never came up is a deploy-side failure (start command, migration, boot) — check `-b` FIRST for `Build Failed ... build daemon` lines: a `buildkitd.sock: use of closed network connection` class error is Railway's builder infrastructure faulting before compiling anything; the fix is a redeploy retry, never a code hunt.
- **`railway status` service line is the truth surface**: `Online · Deploy failed (N m)` means the OLD deployment still serves while the new one failed — production is running stale code by hours. Treat any deploy-failed suffix as the top action item.
- **Cron/scheduled services run their start command on EVERY container boot, not only on scheduled fires.** A redeploy, a restart, or a crashloop replacement all trigger a fire immediately. Plan advisory-lock-held operations (nightly pipelines, sweeps) around every container churn event, and expect a benign `skipped="another run is in progress"` fire exit to show as a FAILED deployment on the dashboard.
- **A container restart leaves the dead client's `pg_advisory_lock` on the Postgres server** until TCP keepalives finally notice the peer — often far longer than the next run's patience. Sessions blocked on it skip with "another run in progress" while nothing is running. Detection: `SELECT l.pid, a.backend_start, a.state, now()-a.xact_start AS xact_age, left(a.query,90) FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid WHERE l.locktype='advisory'`. Zombie signature: `state='idle in transaction'`, xact_age wildly larger than any legitimate pause, `backend_start` within a minute of a known container churn, and no live process for it in the container. Fix: `SELECT pg_terminate_backend(<pid>)` — safe precisely because a dead client's uncommitted transaction rolls back on termination and holds no committed state.
- **A live long-running pipeline also looks like `idle in transaction`** when its ledger writes ride a run-scoped transaction and pacing sleeps and hosted model calls stretch between statements — do not terminate a backend by that shape alone. Before terminating, verify the client process is actually gone IN the container (see next rule).
- **Slim service images lack `ps`/`pgrep`** — enumerate processes from `/proc`: scan `/proc/[0-9]*/cmdline` (null-separated) for the process family, and read `/proc/1/cmdline` to see the container's actual start command (often the only way to confirm what a boot fired). `stat -c %y /proc/<pid>` gives process start time to match against `backend_start`.
- **`railway ssh` is refused during container activation windows** with `Your service's container is not running (status: created)` — that is a race with the deploy you just triggered, not a broken key. Poll (e.g. every 5 min) until the service reports Online, then retry; a scripted wait-loop must retry the whole sequence, not just the first step.
- **Never probe with `| tail` on evidence output.** The decisive line in pg/process listings is routinely late in the stream; tailing the ssh pipe has hidden exactly the process that mattered. Read probes unfiltered (or write them to emit summaries themselves) — the tool guidance against head/tail truncation doubles when the output is evidence.
- **Empty deploy-log output is not evidence of absence.** Cron containers' start-command stdout often appears nowhere in `railway logs -d`; measure progress from the product's own tables (row counts, ledger stages, run-note JSON) instead of inferring from log silence.
- CLI flag constraints: `--from-source` and `--commit <SHA>` are mutually exclusive on redeploy — check `railway redeploy --help` before combining flags by memory.

## Post-merge deploy verification procedure

1. `git rev-parse origin/main` for the SHA just merged.
2. `railway deployment list -s <each service>` — confirm every service that shares the repo has a deployment born at the push timestamp and reaching SUCCESS (one push can and does fail per-service on builder faults).
3. For any FAILED: `railway logs <failing-deployment-id> -b` + `-d` — if the build log shows the builder-daemon error, `railway redeploy -s <service> --from-source -y` and re-check list until SUCCESS.
4. Confirm the service status line drops the deploy-failed suffix and the URL answers its health probe (status-code class, not just 200: 307/405 still proves the route server is alive).
5. Only then reason about behavior "since the merge" — until every service shows SUCCESS, production has been running pre-merge code.