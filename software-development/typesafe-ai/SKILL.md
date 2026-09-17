---
name: typesafe-ai
author: Hermes
description: Build typed AI decision calls your code can branch on.
version: 0.1.0
metadata:
  hermes:
    tags:
      - TypeSafe
      - System One
      - Classification
      - Structured Output
      - Confidence
---

# TypeSafe / System One

TypeSafe's System One models (Jev) make **fast, structured judgments** that software consumes
directly. You send a `state` (the content to judge) plus a map of typed `questions`; you get back
typed `answers` — no generated text, no parsing. This skill covers the request/response contract,
question design, confidence gating, and the four composition patterns.

It does NOT cover chat/agent patterns — System One deliberately does not generate prose, choose its
own next action, or explain its reasoning. If you need generated text, that is a different tool.
Reference-only: no SDK is vendored here; calls go out over HTTP or the Python/JS SDK.

## When to Use

- "Classify / route / triage this text" where the output must drive code, not a human reader.
- "Score this on a rubric", "rate severity/frustration/relevance" with defined levels.
- "Is this statement true?" — yes/no judgments whose probability is the useful signal.
- Deciding whether a model decision is certain enough to act on automatically.
- Replacing prompt-and-parse pipelines (`return JSON, no markdown`) with typed answers.
- Choosing between Choice, Score, and Noul for a given judgment.

## Prerequisites

- API key from the dashboard (`https://console.typesafe.ai/settings/keys`), exposed as
  `TYPESAFE_API_KEY`. Never inline the key in a command — read it from the environment.
- Python SDK: `pip install typesafe-sdk` (requires Python >= 3.10) or `uv add typesafe-sdk`.
- Endpoint: `POST https://api.typesafe.ai/v1/systemone`. Model: `jev-latest` (SDK default).
- Playground for probing a question before writing code: `https://console.typesafe.ai/playground`.

## How to Run

HTTP calls go through the `terminal` tool; SDK code goes through `terminal` (a script file) or
`execute_code`. The Python client reads `TYPESAFE_API_KEY` from the environment and defaults to
`jev-latest`:

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

with TypeSafeClient() as client:
    response = client.system_one(
        state="My running shoes arrived in the wrong size. Can I swap them for a size 10?",
        questions={
            "department": Choice(
                instructions="Which team should handle this?",
                criteria={"returns": "Exchanges, refunds, wrong or damaged items",
                          "shipping": "Delivery status, delays, lost packages",
                          "billing": "Charges, invoices, payment problems"},
            ),
        },
    )
    print(response.answers["department"].choice, response.answers["department"].confidence)
```

Raw HTTP, for any language — invoke through the `terminal` tool with the key from the env:

```bash
curl -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" -H "Content-Type: application/json" \
  -d '{"state": "Help! My payouts have been failing for 3 days.", "model": "jev-latest",
       "questions": {"is_urgent": {"type": "noul", "instructions": "Does this convey urgency?"}}}'
```

## Quick Reference

| | |
|---|---|
| Endpoint | `POST https://api.typesafe.ai/v1/systemone` |
| Model | `jev-latest` |
| Request | `{state, model, questions}` — `questions` is a map of id -> Question |
| Latency | most queries ~100 ms |
| Token budget | ~32,000 tokens shared by `state` + `questions` (~150,000 chars) |

| Type | Answers | Read it as |
|---|---|---|
| `choice` | `choice`, `probabilities`, `confidence` | one of a fixed list; `choice` = highest-probability option |
| `score` | `score`, `legend`, `probabilities`, `confidence` | position on ordered levels; **can land between levels** |
| `noul` | `noul` (0-1) | probability the answer is yes; **no separate `confidence`** |

Question fields: `type` (always), `instructions` (always), `criteria` (Choice: map of option->description;
Score: ordered array, 2-10 levels; Noul: optional `{true, false}` descriptions). Choice accepts up to
255 options. Question ids are yours, never sent to the model — put the full question in `instructions`.

## Procedure

1. **Keep control flow in code.** Deterministic work (date math, status checks, thresholds) never
   goes to the model. Insert System One only where a judgment over unstructured input is needed.
2. **Build the state.** Use an object with descriptive names over a bare string when there is more
   than one part; include only context the questions actually need (extra context causes context rot).
3. **Decompose into atomic questions.** Ask the narrowest question a knowledgeable person could
   answer in a second. "Does this message convey urgency?" yes; "analyze and decide the best action"
   no. One question per independent factor.
4. **Pick the type by the answer's shape.** Fixed unordered set -> `choice`; ordered spectrum you can
   describe in steps -> `score`; yes/no where the probability is the signal -> `noul`. When two fit,
   pick the one your code can act on directly.
5. **Write level/option descriptions as situations, not degrees.** "Broken but workaround exists"
   beats "moderately severe". Levels are judged independently — the model never sees a level's number
   or its neighbours, so "worse than the previous level" and numbers in the text mean nothing.
6. **Point questions at specific fields with backticked paths** — `` `ticket.messages[0].text` `` —
   when the state is structured.
7. **Send every question you might need in ONE request.** They run in parallel; adding questions
   adds tokens but negligible latency. Include speculative ones whose answers only matter on some
   code paths and ignore them where irrelevant.
8. **Compose answers in code** with explicit weights or boolean logic, and **route on confidence**:
   act when certain, confirm when moderately certain, escalate when not.

## Pitfalls

- **One question per request** is the most common mistake (coding agents default to it). It costs
  round trips for no benefit; batch them.
- **Chaining questions in one request does not work.** Questions are independent — one answer is not
  context for another. If a later question genuinely depends on an earlier answer, use a *second*
  request — only when your code cannot construct the second request without the first answer.
- **A Noul `0.5` is not "medium".** It means yes and no are equally likely. To measure a position on
  a scale, use a Score with defined levels.
- **A Score's `score` is a probability-weighted mean, not a fraction.** `1.0` can mean all weight on
  level 1, or half on levels 0 and 2. Read `probabilities` and `confidence` alongside it.
- **`confidence` is not correctness.** 1.0 means the distribution is peaked — the model's own
  certainty, not a guarantee the answer is right.
- **Numbers in level descriptions do not help** ("rate 0 to 2 where 2 is worst" with criteria
  `["0","1","2"]` splits probability and loses confidence). Give each level a described situation.
- **Reusing question ids as the only statement of the question.** The id is not sent to the model.
- **Trusting a low-confidence answer because the top option looks plausible.** Check `probabilities`.
- **Forgetting an `other` / `none of the above` option** on a Choice whose list may not cover input.
- Errors: `401` bad key, `422` body failed validation (names the offending field), `429`/`529` —
  back off with exponential backoff (SDKs do this automatically). Not a bug: a Score landing on a
  fractional value, or a Choice returning near-equal probabilities.

## Verification

Prove the round trip before wiring anything: run the Quickstart request through the `terminal` tool
and confirm the response has one `answers` entry per question id, each with a `type` matching its
question. A `422` means the body shape is wrong; a valid response that returns typed fields (not
prose) means the integration works.

```bash
curl -s -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" -H "Content-Type: application/json" \
  -d '{"state": "Help! My payouts have been failing for 3 days.", "model": "jev-latest",
       "questions": {"is_urgent": {"type": "noul", "instructions": "Does this convey urgency?"},
                     "frustration": {"type": "score", "instructions": "How frustrated?",
                                      "criteria": ["Calm", "Frustrated", "Very angry"]}}}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print({k:v.get("type") for k,v in d["answers"].items()})'
```

## Reference Files

Load on demand with `skill_view(name="typesafe-ai", file_path="references/<file>")`.

- `references/01-system-one-model.md` — what System One is, RLCD vs RLHF/RLVR, state design, Machine Native Intelligence. Load when explaining *why* it works this way or choosing state shape.
- `references/02-primitives.md` — the three question types in full, choosing between them, question design rules. Load when writing or debugging a question.
- `references/03-confidence.md` — probabilities -> confidence, the three confidence bands, risk-scaled thresholds. Load when deciding when to act, confirm, or escalate.
- `references/04-patterns.md` — Speculative Fan-Out, Confidence-Gated Routing, Composite Scoring, Intent Routing, with code. Load when designing a workflow.
- `references/05-api-sdk.md` — full request/response schemas, answer fields, error codes, SDK install. Load when integrating or debugging a 4xx.
- `references/06-design-rules.md` — the eight-step build workflow and the anti-patterns of AI-powered software. Load when starting a new integration.
- `references/07-structured-inputs.md` — `EntryType` (where objects/arrays are accepted), structured criteria, taxonomy walking. Load when explaining a boundary or classifying into a deep taxonomy.
- `references/glossary.md` — terms with section refs. Load when a term is unfamiliar.
