# 03 — Confidence

Source: `/confidence`, plus the confidence material in `/concepts/how-to-build-with-system-one` and
`/patterns/confidence-routing`.

## What it is

Every Choice and Score answer carries a `probabilities` distribution across the options (Choice) or
levels (Score). **The *shape* of that distribution is what tells you how certain the model is:**
concentrated on one outcome = confident; spread out = uncertain.

The answer's `confidence` collapses that shape into a **single number from 0 to 1** so you can
threshold on it without doing the math yourself.

- **Noul answers do not carry a `confidence`.** The `noul` value *is* the probability.
- `confidence` is a **statistic computed from the probability distribution the answer already gives
  you** — TypeSafe computes it for you on every Choice and Score answer.
- It is a **solid default**, but you are never locked into TypeSafe's definition. If a different
  measure suits your evaluation better, compute your own from the full `probabilities` in the
  response. (The docs hold discussion of different computations for a separate cookbook.)

**`confidence` describes the model's own answer — it is not a guarantee that the answer is correct.**
A confidence of 1.0 means the returned distribution puts all its probability on one option.

## What low confidence means by type

- **Choice** — none of the options is a clear winner over the others.
- **Score** — the levels are **ambiguous**, the question is **multi-dimensional**, or the state
  **doesn't contain enough** to place it.

## "I don't know" is a useful signal

If an intelligent system — human or machine — cannot express honest uncertainty, it cannot be trusted.
Confidence is the built-in mechanism for the model to say *"I'm not sure about this one,"* which lets
code implement different behaviour for different levels of certainty. This is the foundation for
systems you can rely on.

## The three paths

A useful starting pattern divides confidence into three ranges, each producing different system
behaviour:

| Band | Behaviour |
|---|---|
| **High confidence** | **Act automatically.** A clear read; proceed without human involvement. |
| **Medium confidence** | **Proceed with caution.** A reasonable answer but not certain — confirm with the user, flag for review, or gather more information before acting. |
| **Low confidence** | **Do not act.** Route to a human, request clarification, or fall back to another system. The model is saying it lacks information or the question is a poor fit. |

**Where you draw those boundaries depends on the stakes.**

## Thresholds scale with risk

**A confidence threshold is not one number.** Different actions in the same system should be gated at
different levels depending on the consequences of getting it wrong.

```python
action = response.answers["action"]
confidence = action.confidence

if confidence < 0.5:
    # Model is genuinely unsure. Don't guess.
    route_to_human(user_message)

elif action.choice == "check_balance":
    # Low stakes. Showing the wrong screen is recoverable.
    show_balance(account_id)

elif action.choice == "approve_transfer":
    if confidence > 0.9:
        # High stakes, high confidence. Proceed with confirmation.
        confirm_then_execute(account_id)
    else:
        # High stakes, moderate confidence. Verify first.
        ask_user_to_confirm(account_id)
```

**The 0.5 floor catches anything the model reports as genuinely uncertain.** Above that floor, the
threshold for acting without confirmation is **higher for a destructive operation than for a
read-only one**. Your code encodes the risk tolerance.

The voice-banking variant uses a **0.6 floor** plus a **0.85** gate on the risky action:

```python
action = response.answers["intent"]

if action.confidence < 0.6:
    route_to_support_agent(account_id)          # below 0.6 on ANY action -> human
elif action.choice == "check_balance":
    show_balance(account_id)                     # low stakes: 0.6 is sufficient
elif action.choice == "approve_transfer":
    if action.confidence > 0.85:
        approve_transfer(account_id)             # high stakes + high confidence
    else:
        ask_user_to_confirm("Just to confirm: you would like to approve this transfer, is that correct?")
else:
    route_to_support_agent(account_id)
```

Checking a balance at 0.6 is fine because the worst case is a wrong read-out; approving a transfer
needs >0.85 or an explicit confirmation.

## The confidence floor is separate from the type decision

A common bug in intent routing: gating on the *intent* confidence but ignoring the confidence of the
secondary question that actually drives the branch. If you branch on `complexity.score`, also check
`complexity.confidence` — a low-confidence complexity reading should route to a human rather than
silently pick the fast path:

```python
low_confidence = complexity.confidence < 0.5
if complexity.score > 1 or low_confidence:
    route_to_human_agent(ticket_id)
```

## Practical guidance

- **Start conservative, test with your own data, adjust.** The correct thresholds depend on your
  domain and on the model's performance for your use case.
- **Test thresholds by plotting confidence against accuracy** on your own labelled data.
- **Read `probabilities`, not just the top answer**, when the decision is consequential. Two answers
  can share a `confidence` while differing in which alternatives are close.
- **Escalate on uncertainty rather than guessing.** The pattern of routing uncertain cases to a person
  or a more expensive reasoning model is what makes the fast path safe.
- Remember the calibration caveat: probabilities are calibrated **across groups of predictions**, so
  a single confident answer can still be wrong.
