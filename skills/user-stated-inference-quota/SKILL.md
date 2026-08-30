---
name: user-stated-inference-quota
description: "Recognize and honor user-stated constraints on inference quota, cost, concurrency, data, assets, or time. Captures the pattern of pausing before any operation that costs the user something — tokens, money, time, or working artifacts — and asking the right clarifying questions. Triggers: 'expensive', 'cost', 'pro plan', 'concurrency', '3 simultaneous', 'can't have more than N', 'don't touch', 'don't delete', 'ask first', 'never take unilateral action on my data', 'we should not recompute anything that's still valid'. Encodes the three-layer protection against wasted calls, the Ollama Cloud 3-concurrent-request account-wide cap, and the persistent-state-mutation gate."
---

# Honoring User-Stated Inference Quota Constraints

A pattern for AI-assisted batch work where the user has hard limits on inference quota, cost, or concurrency. Most batch-job recommendations default to "just run it" — this skill encodes the right way to ask first, plan around the limit, and not waste calls.

## Trigger signals

The user has given a quota, data, or state constraint when you see ANY of:
- "inference is expensive" / "costs, that's the only reason"
- "we should not recompute anything that's still valid"
- "we cannot have more than N simultaneous requests at the same time"
- "I can have a background process running inference for as long as I want using the pro plan as long as I don't go over the concurrency limits"
- "concurrency must be set at N because I'm on the pro plan"
- **"don't touch the data" / "do not delete" / "never take unilateral action on my data, my assets, or my time"**
- **"ask first" / "ask before destroying anything" / "explicit per-operation permission"**
- **"the graph is fine, the data is fine" — assertion that current state is acceptable**

These signal: **the user has done the cost math, or the user has set a hard rule about persistent state. Don't dismiss, don't push back, don't act unilaterally. Stop and ask before kicking off any job that costs them something.**

## What NOT to do when you see these signals

❌ **Don't start the backfill immediately to "make progress."** The user told you the limit. Respect it.

❌ **Don't parallelize across personas to "go faster."** The concurrency cap is account-wide, not per-process. 5 personas × `--concurrency=3` = 15 concurrent requests, which exceeds the cap.

❌ **Don't use `--force` to "skip the pre-filter" and speed things up.** The pre-filter is the only thing protecting the quota budget. `--force` recomputes valid rows, wasting quota.

❌ **Don't dispatch subagent processes for parallel backfill work.** Each subagent is a separate Node process, and each counts against the account-wide concurrency cap. Sequential, one Node process at a time, is the right shape.

❌ **Don't pick an LLM provider other than what the user specified.** If the user says "Ollama Cloud only" or "I have DeepSeek credits but Ollama is what's running," use what they said. Don't test alternatives "to see if they're faster."

❌ **Don't "clean up" working data because you noticed a quality issue.** A 92% duplicate rate, an outdated CLAUDE.md, a stale cache, an untrimmed log — these are observations, not user-reported problems. The bar for touching persistent artifacts is "is the current state causing a problem the user has reported?" not "could it be slightly better?" See **Persistent State Mutations** below for the full pattern.

❌ **Don't wipe a working directory (cache, build output, knowledge graph) without per-operation permission.** The user pays for the inference that built it, the time it took, and the data inside it. Deletion is permanent.

## What TO do

✅ **STOP before kicking off the job.** Ask: "do you want me to start this? What's the right time to run it?"

✅ **Encode the constraint in the plan document.** Plans should have a "Concurrency constraints" section that quotes the user's exact words.

✅ **Build the three-layer protection against wasted calls:**

1. **Pre-filter is the primary guard.** The precompute script's `(entityId, personaId, season, promptVersion)` unique constraint + `--no-delta` flag skip cells that already have current-prompt-version insights. **Do not bypass with `--force`** for routine coverage gap-fills.

2. **Persona isolation is preserved.** A `couples@prompt_version_1.2.0` insight is NOT a `family@prompt_version_1.2.0` insight. The pre-filter correctly counts persona-specific cells as missing for OTHER personas. This is not "recomputing valid work" — each persona has a distinct insight. Don't "optimize" by treating all-persona coverage as the valid state for a pair.

3. **Phase ordering prevents wasted reruns.** If a plan has Phase 1 (deprecate stale rows) and Phase 2 (backfill), Phase 1 must run first. If you backfill first and then deprecate, the deprecation will mark the fresh rows as deprecated and Phase 2 needs to re-run — wasting quota.

✅ **Probe the stall before kicking off a long backfill.** Build a `probe-stall.ts` script that runs 50 cells, then sleeps 60s and reports `rows_written_in_first_10_min` vs `rows_written_in_next_60s`. If 60s of "0 rows" happens with 50 cells, the deadlock reproduces — diagnose before kicking off a 30-hour job. If 60s of "0 rows" doesn't happen, the deadlock is a scale issue; use smaller `--limit=N` slices.

✅ **Make the "no-recompute" guarantee verifiable.** Before each `--persona` invocation, run a coverage report and confirm the "missing for this persona at current prompt version" count is stable from before to after. If it drops unexpectedly, the deprecation ran under your feet or the pre-filter is broken.

## Quota-constrained backfill template

When the user gives a quota constraint, the right plan structure is:

```markdown
## Phase N — backfill

**Goal:** [what this fills in]

**Concurrency constraint (account-wide, not per-process):** [user's exact words quoted]

**Hard rule: do not recompute valid rows.** [3-layer protection explained]

**Strategy:** one Node process at a time, `--concurrency=N` per process, sequential across [entities]. Total ~X hours for the full sweep.

1. **Probe the stall** with a 50-cell smoke test before kicking off the full job.
2. **Sequential runs** — one entity at a time, resumable via the pre-filter:
   ```bash
   for entity in [...]; do
     npx tsx scripts/.../precompute-X.ts --$entity=Y --concurrency=N --no-delta
   done
   ```
3. **Verification after each** — coverage report confirms the expected count dropped.
```

The probe + sequential + verification structure is the right shape. Don't deviate by going parallel or by skipping the verification step "to save time."

## Example dialogue pattern

When you see the trigger signals, the right response is:

> "I see the quota/cost constraint. Before kicking off the backfill, let me confirm: [restate the constraint]. The plan has [N] cells to compute at ~7s/call = ~X hours at concurrency=N. Want me to start it now, or do you want to review the plan first?"

This gives the user a clear "yes now" or "wait, let me think" path. Don't just start the job.

## The "is the user really OK with this cost?" sanity check

Before kicking off a multi-hour job, do a quick mental estimate:
- Cells to compute × seconds per call ÷ concurrency = total seconds
- Convert to hours: `~~(cells * 7) / (concurrency * 3600)`
- If hours > 4, ask before starting
- If hours > 24, definitely ask and offer to run the job in the background

This is a heuristic, not a hard rule. The user might say "I have 48 hours of quota budget this month, go" — then 30 hours is fine. But the default is: ask.

**Per-provider ceiling (revised 2026-07-11):** the 7s/call estimate above is the slow-path number. Each provider has its own concurrency ceiling and throughput — use the actual numbers from `llm-provider-failure-modes` rather than a generic estimate:

- **DeepSeek `deepseek-v4-flash` at concurrency=15**: ~9.4s p50, ~110 rows/min sustained. 9,000 cells = ~82 min. Default for new T6/T7 campaigns.
- **Xiaomi MiMo at concurrency ≤ 10**: ~22.6s p50, 2.4× slower than DeepSeek. Use only when DeepSeek quota is exhausted. Do NOT exceed concurrency 10 — MiMo 429s at ≥ 15.
- **Ollama Cloud at concurrency=3**: ~7s p50 but hard cap on account-wide concurrency. Slow path for large campaigns.

The 4-hour "ask first" threshold should be applied to whichever provider the user actually picked.

## Pitfalls of ignoring this pattern

- Wasted 30 hours of quota on a backfill that the user would have stopped if asked
- Missed opportunity to plan around the limit (e.g., use a smaller scope that completes in 2 hours instead of 24)
- Lost trust — the user said "this is expensive" and the agent immediately burned quota anyway
- Wrong provider choice — agent picked DeepSeek because it's faster, but the user has Ollama Cloud credits and would prefer to use those

The pattern exists to prevent all of these. Honoring the constraint is more important than completing the job.

# Persistent State Mutations — The Data, Asset, and Time Equivalent

The "ask first" pattern above is about inference. The same shape applies to **any operation that mutates, deletes, or rebuilds persistent state**: files, caches, knowledge graphs, knowledge bases, databases, build outputs, config files. The user owns the data; the user pays for the inference that built it; the user waits while it runs. **The hard rule: no destructive operation without explicit per-operation permission, no matter how clean the alternative state looks.**

## When this triggers

Any of:
- The user has a working artifact (graph, build, cache, dataset, knowledge base) and a quality observation surfaces
- The agent notices "waste" in a working artifact (duplicates, outdated entries, stale cache, low-quality rows)
- A multi-step plan involves an `rm`, `shutil.rmtree`, cache wipe, or full rebuild
- The user says "proceed with the deferred work" and the deferred list contains destructive items
- A previous step produced useful output that the next step would invalidate

## The four-question gate

Before any destructive operation, the agent must answer — and write out — these four questions:

1. **What specifically will be deleted or invalidated?** Name the files, dirs, rows, or nodes. "The cache" is not specific. `~/.local/pipx/venvs/graphifyy/lib/python3.14/site-packages/graphify/cache/` is specific. `graphify-out/` in three worktrees is specific.
2. **Is the current state causing a user-reported problem?** "The graph has 92% duplicate nodes" is an observation. "I can't find X when I query" is a user-reported problem. The first does not justify wiping; the second does.
3. **What is the cheapest, most reversible fix that doesn't delete?** Rename, exclude-from-future-runs, quarantine-and-stop-using. Wipe is the last resort, not the first move.
4. **What is the user-visible benefit of the destructive option over the reversible one?** If the answer is "the internal state is cleaner" or "the dedup rate is lower," that's not a user-visible benefit. If the answer is "queries return X correctly when they didn't before," that's a user-visible benefit.

If any of the four questions doesn't have a clear answer, **STOP and ask the user**. Do not pick the most ambitious option and execute.

## Forbidden patterns

- ❌ **"Proceed with the deferred work" is not a green light to pick the most ambitious deferred item and execute it.** It is permission to surface what's pending and ask which (if any) to do.
- ❌ **Asking "how do you want to clean up?" is not the same as asking "should we clean up?"** A multi-choice that only contains cleanup options presumes the decision. Always include "do nothing — current state is fine" as one of the options.
- ❌ **Acting on a hypothesis that "this is a quality improvement" when the current state works.** The bar for touching working data is "is the current state causing a problem the user has reported?" not "could it be slightly better?"

- ❌ **Stalling after explicit per-action approval.** Once the user has approved a specific operation ("proceed with phase N", "yes", "do X then Y"), the approval IS the contract. Do not re-litigate scope, cost, or efficiency. Execute the approved plan, report results, and surface new observations AFTER completion — not before. Re-litigating after approval wastes the user's time and triggers explicit corrections. See `references/post-approval-stall-antipattern.md` for the full pattern with real examples.
- ❌ **Spending the user's time or inference budget on speculative cleanups.** The user pays for inference, the user waits for runs, the user has their own queue of priorities. Confirm the cost before paying it.
- ❌ **Wiping caches or build outputs "to start clean" when the work is already running.** If a long-running process is mid-execution, the cache IS the work. Killing it and clearing the cache is destructive even if the user originally said "do the work" — the cost of the work-in-progress is real.

## The wording pattern that caused a real failure (2026-07-13)

User asked: "proceed with the deferred work"

The deferred list contained three items: install worktree hooks, do dedup cleanup, run community labelling.

The agent noticed the merged graph had 92% duplicate labels and framed this as a quality problem requiring full re-extraction. The agent then asked a multi-choice question framed as "how do you want to clean up?" with four options that all assumed cleanup was the right next step. The user picked the most expensive option (full re-extraction). The agent executed `shutil.rmtree` on three `graphify-out/` directories. The previous graph state was unrecoverable. ~26 minutes of work was lost. The user had explicitly said "proceed with the deferred work" but the agent interpreted that as a license to pick the most ambitious option and execute it.

**The right behavior was:** surface the three deferred items separately. Ask which (if any) to do. Note the duplicate observation as a candidate for a future cleanup, not a reason to act unilaterally. Do not wipe working data.

## The wording pattern that prevents it

When the user gives an ambiguous green light, the right response is:

> "I see [observation]. The deferred list has [items]. Each costs approximately [estimate]. Before I act, which do you want done, and is [observation] worth touching or is the current state fine?"

This gives the user a clear "do nothing" path. The "do nothing" path is the right default when the current state works.

## Compatibility with other patterns

This pattern does NOT replace the inference-quota pattern above. Both apply when an operation touches both persistent state and inference. The order is:

1. First, check the inference quota / cost / concurrency pattern (above)
2. Then, check the persistent state mutation pattern (this section)
3. If both pass, proceed. If either fails, stop and ask.

The persistent state pattern is the "outer gate" — even if the cost is fine, the data side is the user's. The inference pattern is the "inner gate" — once you've established the user wants the operation, do it cost-effectively.

## Related references

- `references/post-approval-stall-antipattern.md` — the post-approval stall anti-pattern (stalling after the user has already given explicit per-action approval). Detailed with real examples from the 2026-07-15/16 Plan B Phase 2 + T6 prod sync sessions.