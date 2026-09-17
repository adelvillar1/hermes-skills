# 01 — The System One model

Source: `/concepts/system-one`, `/introduction/machine-learning-primer`, `/concepts/state`,
`/concepts/how-to-build-with-system-one`, `/introduction`.

## The core bet

Most AI products are built around a **conversation between a model and a person**. TypeSafe starts
from the opposite bet: large-scale automation will be dominated by **AI-to-AI and AI-to-software**
interactions (~99% machine, ~1% human), so the *machine* interface matters more than the chat
interface. TypeSafe calls this **Machine Native Intelligence** — AI with software-like properties:
structure, reliability, observability, testability, speed, consistency, low cost.

The stated design target is a **>100x intelligence-to-speed-and-cost ratio**.

## The mismatch System One removes

LLMs produce text for humans. When code needs a judgment, you end up coercing a text-generation
system into emitting structured decisions and then parsing the result back into something code can
depend on. That parse step is the failure surface.

System One models **evaluate typed questions against a state and return structured results
directly**. No text generation, no parsing. You get typed values and probability distributions that
code can branch on, sort by, and route with.

System One does NOT: write replies, produce code, generate explanations of reasoning, choose its own
next action, or run as an agent. It is a judgment primitive, not a workflow engine.

## Naming

The name comes from Daniel Kahneman's *Thinking, Fast and Slow*. System 1 thinking is fast and
intuitive; System 2 is slow and deliberate. The emphasis here is **fast, focused judgments** inside a
larger workflow that the code owns.

## Training: RLCD

Three post-training approaches for adapting pretrained language models:

| Approach | Optimizes for | Produces |
|---|---|---|
| **RLHF** — human feedback | responses people prefer | chatbots |
| **RLVR** — verifiable rewards | correctness on math-like tasks | reasoning models (slower, costlier) |
| **RLCD** — calibrated decisions | decisions + calibrated probabilities | System One models |

RLCD's output contract: the model does not generate text; it returns decisions and probabilities;
higher probability corresponds to a greater chance the answer is correct.

### Calibration

Across many predictions from a well-calibrated model, outcomes assigned probability `0.2` should
occur ~20% of the time, `0.8` ~80%, `1.0` ~100%. **This describes groups of predictions, not a
guarantee about any single answer.**

### Why not RLHF for this

- Preference optimization rewards **sycophancy** and confident-sounding hallucinations.
- It causes **mode dropping** — the model favours a particular style (e.g. instruction following),
  narrowing the probability distribution of other outputs. (A milder form of GAN **mode collapse**,
  where a generator repeats one output because it keeps fooling the discriminator.)
- Human preference and machine trustworthiness are **different optimization targets**. An output can
  be compelling to a person and still be unreliable for unattended automation.

RLHF remains a good fit for conversational models; production automation needs constrained decisions
and calibrated uncertainty instead.

## State

**State is the content you ask the model to evaluate.** One request evaluates one state against one
or more questions. Every question sees the same state and is evaluated independently.

Think of state as the material you would hand a panel of experts before asking for a judgment.

| Format | Use for | Example |
|---|---|---|
| String | a single message, article, passage | `"My card was charged twice."` |
| Object | named fields, related records, app state | `{"message": "...", "order_id": "A-104"}` |
| Array | a sequence of messages or records | `["Hi", "My customer number is TS1337.", "..."]` |

**Use an object for most requests** so each part has a descriptive name and relationships stay clear.
A string is fine when there is exactly one piece of text.

A state may hold several *kinds* of thing at once and still be one state — e.g. a conversation, an
order, and a refund policy, when the decision requires comparing them:

```json
{
  "ticket": {"subject": "Duplicate charge", "messages": [
    {"from": "customer", "text": "I was charged twice for order A-104. Please refund the duplicate."},
    {"from": "support", "text": "We are checking the charges."}]},
  "order": {"id": "A-104", "charges": [
    {"amount_usd": 49, "status": "captured"}, {"amount_usd": 49, "status": "captured"}]},
  "refund_policy": "Duplicate charges are eligible for a refund."
}
```

### Separate content from questions

State holds **content and supporting facts**. Questions define the **judgments** to make about that
material. Keep the refund request and the policy in the state; ask whether a refund was requested
and whether the policy supports it as questions.

## What makes System One composable

- **Structured** — type-safe by construction; outputs conform to the JSON schema code expects, so
  code never recovers a value from generated prose.
- **Parallel** — questions are evaluated independently and in parallel; one primitive's result is
  never hidden context for another.
- **Comparable** — outputs are sortable and drive `if` statements, thresholds, comparisons.
- **Fast** — most queries complete in about **100 ms**; fast enough for real-time request paths and UIs.
- **Calibrated confidence** — communicates uncertainty through calibrated probabilities rather than
  tending toward overconfidence.
- **Self-consistent** — designed to return stable answers across repeated evaluations.

Every output is constrained to the supplied options, so the model returns a full probability
distribution over those options rather than inventing a value outside the schema.

## Where this sits among architectures

- **Traditional software** — a complex decision tree built from simple, reliable primitives.
- **LLM agents** — the model chooses its own next action; the loop controls flow.
- **AI-powered software** (what TypeSafe is for) — **code owns the workflow** and AI handles narrow,
  structured decisions inside it.

Summary of the stance: build a normal software workflow and insert System One only where AI is
needed. Keep control flow, deterministic rules, and side effects in code.

## The refund-request workflow (canonical example)

1. Build a state containing the customer's message, relevant transactions, and the refund policy.
2. Ask independent questions together: was a refund requested; does evidence indicate a duplicate
   charge; does the policy support a refund.
3. Combine the answers with deterministic checks in code, then route for action or review.
