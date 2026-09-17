# 04 — Patterns

Source: `/patterns`, `/patterns/fan-out`, `/patterns/confidence-routing`,
`/patterns/composite-scoring`, `/patterns/intent-routing`.

Thinking in **discrete, atomic decisions that compose into complex system behaviour** is the core
skill. All four patterns assume you know the primitives and how confidence works.

| Pattern | What it does | Benefits |
|---|---|---|
| Speculative Fan-Out | Send many questions in one call, including speculative ones; code decides relevance | Cost, Speed |
| Confidence-Gated Routing | Use confidence as a second decision axis for safer systems | Reliability, Safety |
| Composite Scoring | Combine several dimensions into a single score | Cost, Reliability, Speed |
| Intent Routing | Classify intent and route to the appropriate handler | Cost, Speed |

---

## 1. Speculative Fan-Out

Put **all** the questions the system needs in a **single request**, then use code to decide what is
relevant after the fact. All questions are evaluated in parallel, so adding questions typically adds
**no latency**.

**Example — support ticket triage.** Classify the ticket; if it is a bug report, also determine
severity. Instead of asking category first and severity in a follow-up call, ask both at once and
ignore severity if the ticket is not a bug report.

- **Speculative questions:** `bug_severity` and `has_reproducible_steps` only matter if the ticket is a
  bug report; `refund_requested` only matters for billing. Include them all upfront — there is no
  speed cost. If the ticket is a feature request, the code path simply ignores the severity answer.

```python
category     = response.answers["category"]
bug_severity = response.answers["bug_severity"]
bug_repro    = response.answers["has_reproducible_steps"]
refund       = response.answers["refund_requested"]
frustration  = response.answers["frustration"]

if category.choice == "bug_report":
    if bug_severity.score > 1.5 and bug_repro.noul > 0.6:
        escalate_to_engineering(ticket_id, severity="high")
    else:
        add_to_bug_backlog(ticket_id)
elif category.choice == "billing":
    if refund.noul > 0.7:
        route_to_billing_with_flag(ticket_id, refund_likely=True)
    else:
        route_to_billing(ticket_id)
elif category.choice == "feature_request":
    log_feature_request(ticket_id)

# Frustration is useful regardless of category
if frustration.score > 1.5:
    flag_for_priority_response(ticket_id)
```

Everything needed for the full decision tree comes from **one call**. Speculative questions are
ignored when irrelevant and save a round trip when they are not.

**Measured:** 13 questions batched into one call = **11.5x cheaper and 9.6x faster** than 13 separate
calls, with **no change in the answers**.

---

## 2. Confidence-Gated Routing

Be intentional about gating decisions on confidence to build systems that are both reliable and safe.
The key idea: **the threshold depends on the stakes of the specific action**, not on the model.

**Example — voice banking.** You always want reasonable confidence in interpreting intent, but riskier
actions demand a higher threshold. Full code in `03-confidence.md`; the shape is: a low floor (0.6)
that catches genuine uncertainty for every action, then a per-action threshold (e.g. >0.85 for
approving a transfer) that triggers a confirmation step instead of acting.

```python
if action.confidence < 0.6:
    route_to_support_agent(account_id)
elif action.choice == "check_balance":
    show_balance(account_id)                       # worst case: a wrong read-out
elif action.choice == "approve_transfer":
    if action.confidence > 0.85:
        approve_transfer(account_id)
    else:
        ask_user_to_confirm("Just to confirm: you would like to approve this transfer, is that correct?")
```

---

## 3. Composite Scoring

To rank items on several criteria at once: **break the judgment into independent dimensions, score
each separately, and combine them with weights you control in code.**

**Example — resume screening.** Score each dimension independently, then normalize and weight. The
same scores produce different rankings for different roles, and the weights are visible in code:

```python
py      = response.answers["python_depth"].score / 4
lead    = response.answers["team_leadership"].score / 4
arch    = response.answers["system_design"].score / 4
general = response.answers["generalist"].score / 4

# Senior IC
ic_score = (0.40 * py) + (0.10 * lead) + (0.40 * arch) + (0.10 * general)

# Engineering Manager
em_score = (0.15 * py) + (0.40 * lead) + (0.20 * arch) + (0.25 * general)
```

**Why this beats one big question:** the composite gives visibility into exactly how the final score
is calculated. If the top-ranked candidates don't match expectations, **adjust the weights** rather
than rewriting a prompt. Individual nuance is preserved because each dimension keeps its own answer.

The normalized-score idiom used in the docs' ticket-priority example:
```python
def normalized(answers, question_id):
    top_level = len(TRIAGE_QUESTIONS[question_id].criteria) - 1
    return answers[question_id].score / top_level

# A detailed report helps an engineer investigate, so it raises priority a little.
return 0.6 * severity + 0.3 * frustration + 0.1 * report_quality
# 0.6 x 0.62 + 0.3 x 0.725 + 0.1 x 1.0 = 0.6895 -> 0.69
```

**Composition can go further than weights:** use the probabilities as **features in a downstream
classical ML model** for learned composition. If you have no labels for that model, use an ensemble of
expensive reasoning models to generate them.

---

## 4. Intent Routing

Not every request needs the same handler. Some are answered by a database lookup, some need an LLM
with domain context, some need a human. **System One sits in front as a fast, cheap classifier that
determines which handler to invoke** — rather than sending every message through an expensive LLM to
find out what kind of request it is.

```python
def route_ticket(ticket_id, response):
    intent = response.answers["intent"]
    complexity = response.answers["complexity"]

    if intent.confidence < 0.5:
        # If we don't have enough confidence to classify, route to a human agent
        return route_to_human_agent(ticket_id)

    if intent.choice == "order_status":
        handle_order_status(ticket_id)                      # deterministic, no LLM
    elif intent.choice == "product_question":
        handle_with_llm(ticket_id, PRODUCT_SPECIALIST)      # specialist LLM
    elif intent.choice == "return_exchange":
        handle_with_llm(ticket_id, RETURNS_SPECIALIST)      # different specialist
    elif intent.choice == "complaint":
        low_confidence = complexity.confidence < 0.5
        if complexity.score > 1 or low_confidence:
            route_to_human_agent(ticket_id)
        else:
            handle_with_llm(ticket_id, COMPLAINT_RESOLUTION)
```

One intent routes to deterministic code with **no LLM involved**; two route to different specialist
LLMs with different context; one uses the complexity score to choose between an LLM and a human. The
classification is a **single quick call**, and the expensive resources are invoked **only for requests
that actually need them**.

**Note the second confidence check** on `complexity.confidence` — a low-confidence score should route
to a human rather than silently taking the fast path.

---

## Choosing between them

- Need several signals from one document/record and want to act on all of them? **Fan-Out.**
- Have a ranked or scored output whose threshold decides act-vs-escalate? **Confidence-Gated Routing.**
- Need to rank many items, or the criteria have adjustable relative importance? **Composite Scoring.**
- Have heterogeneous downstream handlers and want the cheapest one that can serve the request?
  **Intent Routing** (usually combined with Confidence-Gated Routing).
