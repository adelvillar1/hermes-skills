# Loopany source notes (intake 2026-08-10)

Source: https://loopany.ai/templates — "agent loops that actually work".
License note: templates are "free to read"; the site's prompts are displayed openly. Treat as reference patterns (values/rules are facts), not wholesale copy.

## What was sampled

- Landing page (`/templates`) — full catalog: 4 categories × templates (Growth, Business Ops, Codebase Autopilot, CI/Test/Security, Personal, Goal Loops).
- Full template pages: `follow-up-tracker`, `ab-experiment-watch`, `error-sweep`, `reddit-karma`, `seo-try-keywords` (raw prompts + author write-ups).

## Catalog map

| Template | Archetype | Distilled into |
|---|---|---|
| Follow-up Tracker | closed watchdog | agent-loop-patterns (watchdog; finish condition) |
| A/B Experiment Watch | closed experiment watch | ab-testing (ship/kill/extend) + agent-loop-patterns |
| Error Sweep | janitor/fix-shipper | agent-loop-patterns (one PR per run, worktree) |
| Tech Debt Cleanup / Doc Maintainer / Test Guardian / Security Sweep / CI Doctor / Dependency Triage | janitor variants | agent-loop-patterns (one safe PR per run) |
| SEO Try New Keywords / Scale Proven Keywords | bet manager (two-loop) | programmatic-seo (Bet/Verdict Doctrine) + agent-loop-patterns |
| Reddit Karma | growth loop | agent-loop-patterns (ledger, quality gate, self-reflect) |
| Market Monitor / Metrics Digest / Funnel Watch | watchdog (quiet-while-healthy) | agent-loop-patterns |
| Support Triage | triage loop | (covered by pattern set) |
| Morning Briefing / Daily Lesson / Homebrew Updater | personal loops | (cron mechanics, not a skill) |
| Changelog Broadcaster | digest loop | (cron + git, not a skill) |
| Bug Vigil / Release Shepherd | closed loops | agent-loop-patterns (finish lines) |

## The gold (concrete, measured)

- **Never create a blind loop**: "verify a concrete way to observe the outcome exists… and run it once as a smoke test; if nothing can actually be observed, say so and do not create a blind loop." (follow-up-tracker, ab-experiment-watch, error-sweep all carry this.)
- **Quiet while healthy**: "reports what it observes from the first run, then stays quiet unless something goes wrong." (follow-up-tracker)
- **Failed reads are MISSING, never 0**: "a failed read is reported MISSING, never written as 0" (seo-try-keywords); Search Console zero-impression days return position 0 and must be excluded.
- **Daily series, never averages**: trailing average reported "SCALE, confirmed" across seven straight days of decline — 1.42, 1.56, 2.27, 3.70, 4.86. (seo-try-keywords)
- **One PR per fix**: "make the smallest verified fix in a fresh git worktree off the main branch… never while a previous Error Sweep PR is unmerged." (error-sweep)
- **Deterministic pre-stage**: "fixed cron for reliability, cheap deterministic pre-stage for randomness and guardrails, and the agent only when the pre-stage says go." (reddit-karma) ~14 half-hour slots/day, workflow rolls the dice, 3–5 posts/day naturally spaced; skipped slots never touch an LLM.
- **Shared ledger**: "minimum gap of >=21 min between ANY two posts (jittered), and a combined cap of <=5 posts/day… ONE shared ledger file reachable by every automation on the account." (reddit-karma)
- **Skipping is strategy**: "zero is fine (nothing clears the bar -> post nothing and say so, never lower quality to hit a count)." (reddit-karma)
- **Ship/kill/extend**: "state the verdict as one of three words plus a one-line reason… Extend only with a concrete new deadline and a reason the data is not yet conclusive." (ab-experiment-watch)
- **Self-reflect**: "Act, record, measure against the real system, adjust. An agent that posts is a toy; an agent that checks whether its posts worked and changes what it does next week is a system." (reddit-karma)
- **Human ticks the scale**: "never spawn it yourself; the human ticks it" (seo-try-keywords); two lanes: archetype lane (autonomous PR) vs approval lane (draft-pending-approval).
- **Never scale/kill silently**: "Never scale silently, never kill silently. Every verdict gets a date and a number." (seo-try-keywords)
- **Report contract**: dated `type: report` front matter with `title` and `date`; declared metric keys from day one; dashboard at creation (latest-report embed + metric chart). (all templates)
- **Loop type vocabulary**: open loop (ongoing monitor, no finish line) vs closed loop (goal-bound, finishes itself when the goal is met); cadence "never check hourly on a metric that only moves weekly."

## Verification of the fold-in

- `skill_view('agent-loop-patterns')` — archetypes + hard rules inline.
- `skill_view('programmatic-seo')` — Bet/Verdict Doctrine under Post-Launch Monitoring.
- `skill_view('ab-testing')` — Automated Watch Loops subsection.
- Mnemosyne global record `2e84e71ba33cbf94` — source + distilled-into pointers.
