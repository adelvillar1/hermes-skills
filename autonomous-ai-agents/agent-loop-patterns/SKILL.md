---
name: agent-loop-patterns
description: "Use when designing recurring agent loops (cron, watchdogs)."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Agents, Automation, Loops, Cron, Orchestration]
    related_skills: [kanban-orchestrator, pipeline-advance-orchestrator, webhook-subscriptions, worker-durable-handoff, pipeline-event-log, ab-testing, programmatic-seo]
---

# Agent Loop Patterns

Use when designing **recurring autonomous agent workflows** — cron jobs, watchdogs, janitors, monitors, experiment watches, SEO verdict loops. Distilled from Loopany templates (loopany.ai/templates, 2026-08-10) — see `references/loopany-source-notes.md`.

## The core contract

1. **Never create a blind loop.** Before creating any recurring loop, verify a concrete way to observe its subject exists on the machine (logs, metrics, an MCP tool, a URL, a CLI like `gh`) and **smoke-test it once by hand**. If nothing can actually be observed, say so — do not create the loop. A loop with no verified read path is a lie on a schedule.
2. **Quiet while healthy, speak up when it breaks.** The default report is *what changed*, not *everything is fine*. A run that finds nothing stays silent (Hermes cron: `no_agent=True` script with empty stdout = silent watchdog).
3. **Dated reports, not chatter.** Each run writes one dated `type: report` entry; report a run metric when one is natural. Never invent numbers — a failed read is reported MISSING, never written as 0.
4. **Never scale silently, never kill silently.** Every verdict gets a date and a number.
5. **The loop reads and judges, it does not act** (watches/verdicts) — unless it is explicitly a fix-shipper, in which case: **one provably safe PR per run**, fresh git worktree off main and outside the loop folder, never while a previous PR from the same loop is unmerged. Zero is a valid run.

## Archetypes

- **Watchdog** (follow-up tracker, metrics digest, funnel watch): watches something just shipped or live; alerts only on real trouble; quiet otherwise. Define the **finish condition before creating** (closed) or declare it an open monitor. "It does not score a change against a number" — if a metric decides, it's an experiment watch.
- **Janitor / fix-shipper** (error sweep, tech debt, docs maintainer, test guardian, security sweep): finds ONE provably safe issue, fixes in isolation, lands one PR. Group repeated symptoms into incidents; separate actionable from noise and upstream failures; trace to root cause. "One per run" is the anti-accumulation rule.
- **Bet manager** (SEO try/scale): two loops — one opens cheap bets and scores them on the daily series, the other compounds winners. Day-N verdicts (SCALE/LEAVE) with dates; the loop proposes, the **human ticks** the scale action. Most bets are duds by design — cheap failure is the point.
- **Closed-loop experiment watch** (A/B): one deciding metric + threshold + **guardrail** metric + decision window; verdict is exactly one of **ship it / kill it / extend** (extend only with a concrete new deadline and a reason). Never call early on a noisy metric — report "not conclusive yet." Never touch the traffic split or feature flag; it reads and judges.

## Hard rules

- **Audit whole-repo state, never the local checkout**: a drift/freshness monitor that reads `git log -1` reports whichever branch the working clone happens to sit on — a stale or side-branch checkout yields false positives on clean projects *and* false negatives on genuinely drifted ones. Read all refs (`git log --all`), and take recency from durable data (dates embedded in filenames, commit dates), never from working-tree file mtimes: clone/checkout rewrites mtimes, so every file in a fresh clone can share one timestamp. Compare at day granularity — same-day ordering between a recap and its commits is not drift. When the probe asks *which work is uncovered*, count only real work: drop CI-only paths and merge commits, because a branch-refresh merge carries no new work yet is the newest-dated commit, so it gets reported as the uncovered session.
- **Verify-first, always**: the observation path is smoke-tested once at setup; a failed read is MISSING, never 0.
- **Cadence fits the thing being tracked**: "never check hourly on a metric that only moves weekly."
- **Stagger sibling loops** (scale "staggered off siblings"; error sweep never runs while a previous PR is unmerged).
- **Randomness/guardrails live in a cheap deterministic pre-stage**: fixed cron fires, a zero-LLM workflow rolls the dice (reads the ledger, checks gaps/caps), the agent wakes only when the pre-stage says go. "Fixed cron for reliability, cheap deterministic pre-stage for randomness and guardrails, and the agent only when the pre-stage says go." A skipped slot never touches an LLM.
- **Shared-account automation needs ONE shared ledger** (e.g. `<account>-account-ledger.md`): min gap between any two posts (default 21 min, jittered), combined daily cap (default 5), every automation on the account reads/writes the same ledger and yields slots when another loop has an approved batch.
- **Quality gate — skipping is the strategy**: zero is a valid run; never lower the bar to hit a count. The killer gate: "does someone else already occupy my angle?" — add a genuinely distinct angle or walk away.
- **Self-reflect & evolve**: a weekly grading pass re-fetches real outcomes, tallies by category (sub/angle), retires losers, doubles winners. "Act, record, measure against the real system, adjust. An agent that posts is a toy; an agent that checks whether its posts worked and changes what it does next week is a system."
- **Human-verdict lanes**: autonomous lane = PR off origin/main; approval lane = draft-pending-approval. Never spawn/scale/merge silently — the loop proposes, the human ticks.
- **Never copy credentials, tokens, or personal data into reports or PRs.**
- **Dashboard at creation**: embed of the latest report + a chart of the run metric; declare metric keys from day one so runs report them.

## Implementing in Hermes

- `cronjob` tool: `no_agent=True` + script for silent watchdogs (empty stdout = silent); agent jobs for reasoning loops; `repeat` count for closed loops (the finish line); `deliver` targets for where alerts land; `context_from` to chain loops (bet manager → scale loop).
- `pipeline-event-log` for the dated report contract; `worker-durable-handoff` for finish-line state; `pipeline-advance-orchestrator` when a loop needs a DB-backed state machine instead of a task file.
- Report shape: front matter `type: report`, `title`, `date`; run metric as a named key; a failed read is reported MISSING, never 0.

## Verification

- A designed loop starts with a smoke-tested observation path before any schedule exists.
- A detector is validated in **both directions** before its output is trusted: a known-drifted subject must fire and a known-clean subject must stay silent. A loop that only ever reports one of the two states is measuring the checker, not the subject.
- Verdicts/PRs carry a date and a number; nothing scales or dies silently.
- Reports are dated, metric-keyed, and quiet when nothing changed.
