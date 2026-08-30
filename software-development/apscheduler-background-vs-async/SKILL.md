---
name: apscheduler-background-vs-async
description: Use BackgroundScheduler for long-running CLI processes (no running event loop needed); use AsyncIOScheduler only when you already have a FastAPI/asyncio event loop. The wrong choice crashes at startup with 'no running event loop' or hangs the FastAPI event loop. Class-level guidance for ANY Python project that needs a cron / scheduled job in a long-running process.
---

# APScheduler: BackgroundScheduler vs AsyncIOScheduler

The right scheduler base class depends on **where the code runs** — not on the language, framework, or "what feels modern." Picking the wrong one causes silent failures (jobs never fire) or startup crashes (`RuntimeError: no running event loop`).

## Decision rule

| Code context | Scheduler class | Why |
|---|---|---|
| **FastAPI / aiohttp / any asyncio app with a running event loop** | `AsyncIOScheduler` | It uses `asyncio.get_running_loop()` internally to schedule jobs onto the existing event loop. Other choices would block the loop. |
| **Standalone CLI process, daemon, Docker container, or any process WITHOUT a running event loop** | `BackgroundScheduler` | Runs jobs in a separate thread. No event loop needed. |
| **Celery / Dramatiq / RQ worker process** | Neither — use the existing worker | You already have a scheduler (the worker supervisor). Adding APScheduler is duplicative. |

## Why AsyncIOScheduler crashes in a CLI

`AsyncIOScheduler.start()` calls `asyncio.get_running_loop()` to bind to the existing event loop. In a sync context, this raises `RuntimeError: no running event loop` and the scheduler never starts.

```python
# ❌ Fails: RuntimeError: no running event loop
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
scheduler.start()  # 💥
```

**Workarounds are all wrong:**
- Wrapping the call in `asyncio.run()` doesn't work — `run()` creates a loop, runs a coroutine, then **closes** the loop, but the scheduler needs the loop to stay alive.
- Calling `scheduler.start()` from inside a running `asyncio.run()`-driven coroutine works for that coroutine's lifetime, but the scheduler dies when the coroutine ends.
- Some projects use `asyncio.new_event_loop()` + `loop.run_forever()` in a separate thread just to host `AsyncIOScheduler`. This is `BackgroundScheduler` with extra steps.

```python
# ✅ Correct for CLI processes
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.start()  # works immediately
```

## Why BackgroundScheduler is wrong inside FastAPI

`BackgroundScheduler` runs jobs in its own thread pool. If your job needs to share the FastAPI event loop's state (e.g., a DB session, the asyncio Lock, an httpx client bound to the running loop), threading across event-loop boundaries causes deadlocks or "attached to a different loop" errors.

If you need scheduled jobs in a FastAPI app, use `AsyncIOScheduler` started from the `startup` event handler — same loop, no thread boundaries.

## The pattern that works (long-running CLI process)

```python
"""Long-running worker with a daily cron. No event loop needed."""
import logging
import signal
import sys
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _run_daily_cycle() -> None:
    """The cron job body. Runs in the scheduler's thread."""
    logger.info("daily cycle starting")
    # ... do work ...
    logger.info("daily cycle done")


_running = True


def _handle_sigterm(signum, frame) -> None:
    global _running
    logger.info("SIGTERM received, shutting down")
    _running = False
    scheduler.shutdown(wait=False)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    # Validate the timezone up front — fail loudly with a clear error
    # instead of APScheduler's "No time zone found with key US/Eastern"
    try:
        from zoneinfo import ZoneInfo
        eastern = ZoneInfo("US/Eastern")
    except Exception as exc:
        raise RuntimeError(
            f"Cannot resolve timezone 'US/Eastern' ({exc}). "
            "Install the 'tzdata' package: pip install tzdata"
        ) from exc

    global scheduler
    scheduler = BackgroundScheduler(timezone=eastern)
    scheduler.add_job(
        _run_daily_cycle,
        trigger=CronTrigger(hour=2, minute=0, timezone=eastern),
        id="daily_cycle",
        name="Daily cycle",
        max_instances=1,  # never overlap a previous run that's still going
        misfire_grace_time=3600,  # run up to 1hr late if the server was down
    )
    scheduler.start()
    next_fire = scheduler.get_jobs()[0].next_run_time
    logger.info(f"scheduler started — next fire: {next_fire}")

    # Block the main thread on a sleep loop so SIGTERM is responsive
    while _running:
        time.sleep(60)
    scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
```

## Common patterns

### Stub function for sync callables

`BackgroundScheduler` runs **sync** callables. If your existing code is `async def`, you have two options:

```python
# Option A: Wrap with asyncio.run() per call (simple, slow for high-frequency jobs)
async def _do_work_async():
    # ... your async logic ...
    pass

def _do_work_sync():
    asyncio.run(_do_work_async())

scheduler.add_job(_do_work_sync, ...)


# Option B: Use AsyncIO scheduler in a thread that owns an event loop
# (overkill for most cases — only do this if A is too slow)
```

For most "daily scrape" or "hourly sync" workloads, **Option A is fine** — the `asyncio.run()` overhead is sub-millisecond compared to the actual work.

### Expose scheduler state for ops

Always add a `get_scheduler_status()` function that returns a serializable dict. Even if you don't add an HTTP endpoint, CLI commands like `python -m myapp scheduler` should be able to show next-fire time and last-run summary.

```python
def get_scheduler_status() -> dict:
    if scheduler is None:
        return {"running": False}
    jobs = scheduler.get_jobs()
    return {
        "running": True,
        "next_run": jobs[0].next_run_time.isoformat() if jobs else None,
        "jobs": [{"id": j.id, "name": j.name, "next_run": j.next_run_time.isoformat()} for j in jobs],
    }
```

### Reset stuck jobs on startup

If your scheduler writes status to a DB and might be restarted mid-run, add stuck-job reset on startup so the next run can re-process them:

```python
from src.services.jobs_corpus import reset_stuck_jobs

def main():
    # ... before scheduler.start() ...
    reset_count = reset_stuck_jobs()
    if reset_count:
        logger.info("Reset %d stuck jobs from prior crash", reset_count)
    scheduler.start()
```

### Timezone handling

`CronTrigger(hour=2, minute=0, timezone=ZoneInfo("US/Eastern"))` handles DST automatically — the cron fires at 2:00 EST in winter and 2:00 EDT in summer.

**The `tzdata` pitfall:** on `python:3.13-slim` Docker images, the OS timezone database is stripped. `zoneinfo.ZoneInfo("US/Eastern")` raises `ZoneInfoNotFoundError`. Fix:

```toml
# pyproject.toml
dependencies = [
    "tzdata>=2024.1",  # IANA tz database — needed by zoneinfo on slim Docker images
]
```

Validate the timezone at startup with a clear error message:

```python
try:
    eastern = ZoneInfo("US/Eastern")
except ZoneInfoNotFoundError as exc:
    raise RuntimeError(
        f"Cannot resolve timezone 'US/Eastern' ({exc}). "
        "Install the 'tzdata' package: pip install tzdata"
    ) from exc
```

**Test the missing-tzdata path explicitly** — don't just test the happy path. If `tzdata` is missing in production, the worker should crash with a clear error, not with `ZoneInfoNotFoundError` after the cron tries to fire.

## Background vs queue-loop polling

**Use BackgroundScheduler (a real cron), not a queue-loop polling every N seconds.** A real cron:
- Fires exactly when the schedule says, not "within the last N minutes"
- Survives system clock changes gracefully
- Is what ops people expect (`crontab` semantics)
- Allows easy ops commands like "what's the next fire time?"

A queue-loop polling every 5 min is wasteful and lazy:
- Wakes up every 5 min just to check "anything pending?"
- Workloads cluster around the poll interval instead of firing on schedule
- Hides issues — if the loop crashes, you don't notice until the next 5-min wake
- A real cron is a few extra lines of code; polling is a hack

**Pattern for the CLI: a single `python -m myapp run` that boots the scheduler and blocks on a sleep loop until SIGTERM.** No queue poll, no work dispatcher, no state machine. The scheduler does the work.

## Reference: minimal complete example

The "minimum viable" worker that does the right thing:

```python
"""long_runner.py — long-running CLI with a 02:00 US/Eastern cron."""
from __future__ import annotations
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
_running = True
_scheduler: BackgroundScheduler | None = None


def _do_work() -> None:
    logger.info("work starting")
    # ... actual job body ...
    logger.info("work done")


def _handle_signal(signum, frame):
    global _running
    logger.info(f"received signal {signum}, shutting down")
    _running = False
    if _scheduler:
        _scheduler.shutdown(wait=False)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    from zoneinfo import ZoneInfo
    eastern = ZoneInfo("US/Eastern")  # raises ZoneInfoNotFoundError if tzdata missing

    global _scheduler
    _scheduler = BackgroundScheduler(timezone=eastern)
    _scheduler.add_job(
        _do_work,
        trigger=CronTrigger(hour=2, minute=0, timezone=eastern),
        id="daily_work",
        max_instances=1,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(f"scheduler started — next fire: {_scheduler.get_jobs()[0].next_run_time}")

    while _running:
        time.sleep(60)


if __name__ == "__main__":
    main()
```

## Anti-patterns

| Anti-pattern | Why it's wrong |
|---|---|
| Use `AsyncIOScheduler` from a sync context | Crashes: `RuntimeError: no running event loop` |
| Use `BackgroundScheduler` inside FastAPI | Jobs run in a thread; can't share asyncio.Locks or httpx.AsyncClient bound to the running loop |
| Poll a job queue every N seconds with `time.sleep(N)` | Wasteful wakeups, hides crashes, ops can't see "next fire time" |
| Use a queue loop because "it's simpler than APScheduler" | APScheduler is a few lines: `from apscheduler.schedulers.background import BackgroundScheduler; scheduler = BackgroundScheduler(); scheduler.add_job(fn, CronTrigger(hour=2)); scheduler.start()`. The real cron is simpler. |
| Set `wait=False` on `scheduler.shutdown()` then immediately exit | The scheduler can't gracefully stop the in-flight job. Use `wait=True` for clean shutdown, or accept that SIGTERM kills mid-run. |
| Forget `misfire_grace_time` | A server that was down at 2 AM will never run the job. Default grace is 0 seconds — the cron silently misses. Set 1-4 hours. |
| Forget `max_instances=1` | A long-running daily job that overlaps with the next day's run causes resource thrash. Always set max_instances=1 for daily/weekly jobs. |
| Add `import asyncio; asyncio.run()` to fix "scheduler crashes in tests" | The right fix is `BackgroundScheduler`. Don't paper over the AsyncIO error with a hack. |

## Pitfall: In-memory scheduler state lost on container restart

APScheduler (both AsyncIOScheduler and BackgroundScheduler) keeps job state in memory. On Railway (or any container platform), a restart/deploy/OOM-kill loses all scheduler state — including the last-run timestamp. If the restart happens AFTER the scheduled time + misfire_grace_time, the daily job silently skips that day with no error.

**Catch-up pattern:** on app startup, check when the last successful pipeline run occurred (stored in the database, NOT in memory). If it's older than a threshold (e.g., 20 hours for a daily job), run the pipeline immediately:

```python
@app.on_event("startup")
async def _startup():
    start_scheduler()
    # Catch-up: if last successful run > 20h ago, run now
    last_run = get_last_successful_run_from_db()  # DB, not memory
    if last_run is None or (datetime.now(timezone.utc) - last_run).total_seconds() > 20 * 3600:
        asyncio.create_task(_run_pipeline_and_mc())
```

**Why DB, not memory:** `_last_run` in a module-level global is lost on restart. Store the timestamp in a dedicated table or column (e.g., `pipeline_runs` table with `completed_at`).

**misfire_grace_time is not enough:** APScheduler's `misfire_grace_time` only helps if the scheduler is running but the job fired late. If the scheduler process itself was down, the job was never queued — misfire_grace_time doesn't apply.

## When to use this skill

- Adding a cron / scheduled job to a long-running CLI process
- Adding a cron / scheduled job to a Docker container that runs as the entrypoint
- Debugging "scheduler.start() crashes" or "scheduler never fires"
- Choosing between BackgroundScheduler, AsyncIOScheduler, and BlockingScheduler
- Migrating a queue-loop polling design to a real cron
- Reviewing a PR that adds APScheduler to a project
