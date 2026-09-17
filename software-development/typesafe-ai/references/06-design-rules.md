# 06 — Design rules for AI-powered software

Source: `/concepts/how-to-build-with-system-one`, `/introduction`.

System One is for building **AI-powered software, not agents**. It does not generate code or choose
its own next action. It provides primitives that embed into software, so **code remains in control**
while the model handles common-sense judgments over unstructured data.

**Summary: build a normal software workflow and insert System One only where AI is needed.**

- Keep control flow, deterministic rules, and side effects in code.
- Break broad judgments into narrow, typed questions with explicit instructions and criteria.
- Give each question only the context it needs.
- Use probabilities and confidence to act, ask for review, or escalate.
- Ask independent questions together, then compose their answers in code.

## The three architectures

| | Who owns flow | Who decides |
|---|---|---|
| Traditional software | code | code |
| LLM agents | the model picks its next action | the model |
| **AI-powered software** | **code** | **code, informed by model judgments** |

Traditional code is a complex decision tree built from simple, reliable primitives. Because each
primitive is reliable, developers compose them into higher-level abstractions. System One is meant to
be such a primitive — reliable enough to compose.

## The eight steps

### 1. Use code when you can
Keep deterministic work in code — it is reliable and cheap. **Avoid agent `while` loops when a software
workflow can express the same behaviour.**
```python
days_overdue = (today - invoice.due_date).days
if days_overdue > 30:
    route_to_collections(invoice)
```

### 2. Decompose the input state
Include **only the context relevant to the current questions**. This helps the model avoid distractions
and **context rot**. Do not rely on knowledge stored in model weights when current information can come
from your own knowledge base.

### 3. Use structure in the input state
Use nested JSON for `state` and `questions`. Point questions at specific values when that removes
ambiguity, and **include the backtick characters around each path inside the question** — e.g.
`` `support.tickets[0].message` ``.

### 4. Decompose the questions
The most important concept in the guide. **Ask the most explicit, narrow, specific, atomic questions
you can.** Break complex or ill-defined questions into separate questions that each evaluate one
property. Broad questions hide several judgments behind one answer; atomic questions expose them so
you can inspect, tune, and combine them in code.

### 5. Use structure in the questions
Keep atomic questions short. When instructions or criteria need several kinds of guidance, use objects
or arrays **with named fields** instead of flattening everything into a dense prose string — this makes
the decision boundary easier to scan, review, and tune.

For a Choice: describe what belongs in each option, **what belongs in a neighbouring option instead**,
and a few representative examples. **Use the same field names across options** so the model can compare
directly. A short, unambiguous question or criterion can remain a string — add structure when it
separates guidance that would otherwise blur together. (See `07-structured-inputs.md`.)

### 6. Ask a lot of questions
Ask many narrow, independent questions about the same state in one request. This maximizes
**effectiveness and intelligence per dollar**: questions run in parallel, and code can combine their
signals without adding serial model round trips.

### 7. Combine question outputs in code (or feed a classical ML model)
Combine independent answers with deterministic rules or weighted sums:
```python
answers = response.answers

# Combine independent signals into one application-specific score.
quality = (0.4 * answers["answers_request"].noul
           + 0.4 * answers["citations_are_supported"].noul
           + 0.2 * (1 - answers["contradicts_context"].noul))
```
For **learned composition**, use the probabilities as features in a downstream classical ML model.
Without labels for that model, generate them with an ensemble of expensive reasoning models, then
train the classical model on System One outputs.

### 8. Route on uncertainty
Make code take different actions for confident and unconfident answers. **Escalate uncertain cases to
a person or a more expensive reasoning model.** Test thresholds by plotting confidence against
accuracy on your data.
```python
answer = response.answers["card_help_topic"]
if answer.confidence < 0.8:
    route_to_human_review(ticket)
else:
    route_to_handler(answer.choice, ticket)
```

**Decomposition does not require more round trips** — questions over the same state run in parallel.

## The full workflow (support-ticket triage)

A worked example that keeps deterministic work in code, sends only relevant structured context,
evaluates many atomic questions in one request, and composes answers with explicit confidence gates.

1. **Short-circuit deterministic cases** before calling the model at all:
   `if ticket["status"] == "closed": return "no_action"`.
2. **Pre-filter in code** — build `open_orders` from the customer record rather than sending every
   order for the model to sift.
3. **Build a minimal structured state** with only the fields the questions reference: the ticket
   message/sender/links, plan and open orders, and the policy list.
4. **Ask structured atomic questions together** — a Choice for `topic` with `what` / `not_for` /
   `examples` on each option; Nouls for `requests_credentials`, `sender_identity_mismatch`,
   `unexpected_reward`, `refund_requested`, `mentions_open_order`; a Score for `frustration` with
   `what` + `signals` per level.
5. **Compose weights in code** — e.g.
   `spam_risk = 0.45*requests_credentials.noul + 0.30*sender_identity_mismatch.noul + 0.25*unexpected_reward.noul`.
6. **Escalate the uncertain band explicitly** rather than rounding it:
   `spam_is_uncertain = 0.4 < spam_risk < 0.6`; route to a human if uncertain **or** if
   `topic.confidence < 0.75`.
7. **Let code decide which speculative answers matter** on this path::
   `if topic.choice == "billing": route_to_billing(..., refund_requested=(refund_requested.noul >= 0.7))`.
8. **Derive priority from a score plus its confidence**: high priority only when
   `frustration.confidence >= 0.7 and frustration.score >= 1.5`.

### Question shape used throughout

```python
"topic": Choice(
    instructions={"question": "Which team should handle `ticket.message`?",
                  "focus": "Classify the customer's primary request."},
    criteria={
        "billing": {"what": "Charges, invoices, refunds, or subscriptions",
                    "not_for": "Order tracking or account access",
                    "examples": ["I was charged twice", "Where is my refund?"]},
        "orders":  {"what": "Order status, delivery, cancellation, or returns",
                    "not_for": "Charges or account access",
                    "examples": ["Where is my order?", "Cancel my shipment"]},
        "account": {"what": "Login, profile, permissions, or security",
                    "not_for": "Charges or order tracking",
                    "examples": ["Reset my password", "I cannot sign in"]}}},
"requests_credentials": Noul(
    instructions={"question": "Does the message request a sensitive credential?",
                  "compare": ["`ticket.message`", "`policy.sensitive_credentials`"],
                  "focus": "Look for a request to disclose the credential itself."},
    criteria=NoulCriteria(
        true={"what": "Asks the recipient to disclose a listed credential",
              "examples": ["Reply with your password", "Send us your API key"]},
        false={"what": "Does not ask the recipient to disclose a credential",
               "not_for": "A legitimate instruction to reset a credential",
               "examples": ["Use this link to reset your password"]})),
"frustration": Score(
    instructions={"question": "How frustrated does the customer appear?",
                  "inspect": "`ticket.message`",
                  "focus": "Judge expressed frustration, not issue severity."},
    criteria=[
        {"what": "Calm and matter-of-fact", "signals": ["Neutral wording", "No complaint about the experience"]},
        {"what": "Frustrated but civil", "signals": ["Expresses annoyance", "Remains constructive"]},
        {"what": "Very angry or threatening to leave", "signals": ["Hostile language", "Threatens cancellation or churn"]}]),
```

## Anti-patterns

- Asking the model to decide *how* to proceed (that is agent behaviour, not a judgment).
- One broad question ("analyze this and tell me what to do") instead of several atomic ones.
- One question per API call when they share a state.
- Sending the whole record when two fields are the only relevant context.
- Treating a score or choice as correct without looking at confidence in front of a side effect.
- Re-implementing deterministic logic in a prompt.
