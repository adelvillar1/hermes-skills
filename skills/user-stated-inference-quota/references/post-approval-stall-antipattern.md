# Post-Approval Stall Anti-Pattern

A specific failure mode observed repeatedly in batch-data work: the user explicitly approves an action, the agent re-litigates scope/cost before executing, the user has to repeat themselves to get progress.

## The pattern

1. User says "proceed with phase N" or "deprecate the stale records in production and then sync"
2. Agent acknowledges ("Phase 1 only...")
3. Agent asks another clarifying question or surfaces a new cost estimate that wasn't part of the approval
4. User says "didn't I tell you explicitly to run it? were my instructions unclear or ambiguous?"
5. Agent finally executes (often after the user has to repeat themselves a second time)

## Real examples from the wild

**2026-07-15 Plan A**: User said "proceed with phase 4" mid-session. Agent stalled on a cost-projection paragraph and asked a multi-choice question about scope. User fired back "didn't I ask you explicitly to run it? were my instructions unclear or ambiguous?" Agent executed 486 cells of MiMo backfill immediately after.

**2026-07-15 T6 prod sync**: User said "deprecate the stale records in production and then sync." Agent acknowledged, then asked "Plan B scope — given 1,507 leftover active 1.1.0 rows... which path?" User answered empty (no choice from the menu). Agent defaulted to the most-conservative interpretation. Had to push through with manual interventions.

**2026-07-15 Plan B**: User said "proceed with phase 2." Agent stalled on throughput reality vs estimate (1.5 cells/min vs plan's 33), asked "Plan B Phase 2 throughput reality vs estimate... How do you want to scope the launch?" User said "didn't I ask you to proceed with phase 2?" Agent launched immediately.

## The rule

**When the user has given explicit per-action approval for a class of operation, that approval IS the contract. Execute the operation as designed, then report results. Do NOT re-litigate scope/cost/efficiency after explicit approval has been granted.**

The decision tree:

```
Did the user explicitly approve this operation?
├── YES (any form: "proceed with phase N", "do X then Y", "yes", "✓")
│   └── EXECUTE THE OPERATION AS DESIGNED
│       - Report results when complete
│       - Note any mid-flight surprises in the results report
│       - If the operation reveals unexpected data (e.g., 1,507 leftover rows
│         after a campaign completes), surface that as a NEW observation
│         in the results report — do NOT halt the in-flight operation to
│         ask about it
│
└── NO (user is clarifying, asking a question, asking your opinion)
    └── THEN clarifying questions ARE appropriate
        - State your recommendation
        - Present a multi-choice with a clear "do nothing" option
        - Estimate cost honestly
```

## What "explicit approval" looks like

Triggers ASKING mode:
- "what's the best way to..."
- "should I..."
- "what do you recommend..."
- "I have a question about..."

Triggers EXECUTE mode:
- "proceed with phase N"
- "yes"
- "do it"
- "deprecate X then sync Y"
- "launch it"
- "run it"
- anything that names the operation directly without asking for opinion

When in doubt, ask once for clarifying scope BEFORE executing. But once the user has answered, do not re-ask.

## What to do when surprising data appears mid-execution

If you're running a 5-minute operation and at minute 3 you notice a problem:

```python
# WRONG: stop and ask
"... actually, I'm seeing 1,507 leftover rows. Should I..."

# RIGHT: let it finish, then report
[operation completes]
"Operation complete. N rows affected. Note: 1,507 rows in the
related table are stale due to [reason] — should we clean those
up as a follow-up? Recommendation: [yes/no]."
```

For multi-hour operations (background campaigns), the rule is even stricter:
- Do NOT interrupt
- Do NOT re-prompt mid-flight
- Wait for the natural completion (FINISHED marker, log tail signal)
- THEN surface observations

## How this skill's existing guidance maps

This is a specialization of the user's 2026-07-11 rule: **"never take unilateral action on the user's data, assets, or time."** That rule has two halves:

1. **Don't act without approval** for novel/destructive work (the skill's "ask first" pattern)
2. **Once you have approval, execute the approved plan without re-litigating** (this file)

The original skill body covers (1) heavily. This anti-pattern captures (2) — the failure mode that comes from over-applying the "ask first" rule past the point where approval has already been given.

## Companion skill: pipeline-worker-long-running-campaigns

When the operation in question is a multi-hour background campaign (LLM backfill, batch compute, etc.), the same rule applies with extra emphasis on "do not interrupt once launched." The campaign's natural completion signal is what the watchdog waits for — interrupting to ask for clarification is the most expensive form of self-derailment because it wastes the inference budget already spent.
