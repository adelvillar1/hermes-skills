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

- **Unknown question fields are dropped SILENTLY.** The question schema accepts only `type`,
  `instructions` and `criteria`. A script that passed its payload as a separate `text` key got a
  **200 OK** and 26 answers — all landing inside a 0.22-0.29 band, because every question in the
  request was IDENTICAL. There is no error and no warning: a malformed question fails quietly and
  the uniform answers look like a weak signal rather than missing data. Put the per-question content
  INSIDE `instructions` (or `criteria`), and treat a suspiciously tight answer band as a data bug.
- **Check the SPREAD, not just the values.** A batch of answers clustered within a few hundredths of
  each other means the questions were not actually differentiated. Ranking 26 items whose scores span
  0.02 is ranking noise. Measure `max - min` before trusting any ordering, and compare against a
  single-item run of the same question as a control.
- **Do not wrap the primitives in a composite you invented without measuring it.** A weighted
  composite built on top of System One answers can be WORSE than a single raw answer. Measured on a
  real JD-vs-candidate scoring task (n=771): the raw `relevance` Score correlated with two independent
  LLM judges at r=+0.64 / +0.73 and separated kept-vs-rejected items at 0.658, while a
  0.65*relevance + 0.35*seniority composite scored r=+0.44 / +0.50 and separated at 0.631. The
  composite lost information the primitive already carried. **Score the raw primitives against your
  labels first; only add weights when they demonstrably help.**
- **Guards must CAP, they must not sum.** A disqualifying question ("is hands-on build a primary
  duty?") folded into a weighted average can be outvoted by a generous relevance reading, letting an
  ineligible item clear the bar. Apply blockers as a `fit = min(fit, cap)` override and record which
  one fired.
- **Do not ask one holistic question to replace a whole rubric.** Documents that System One is for
  judgments "a knowledgeable person makes in a second"; a single "rate this 0-10" over a long document
  is exactly the broad question the docs say to decompose.
- **Confidence is per-question, not per-request.** A high-confidence `role_family` can sit next to a
  `primary_function` at 0.42. Read them individually; a low one on the question that drives the branch
  is the signal to escalate, even when the others are confident.
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

## Access model — invite-only preview, NO BILLING MODE (2026-09-17)

**TypeSafe is an invite-only preview. There is no way to buy credits.** This is load-bearing:
when the API returns `HTTP 402` with

```json
{"detail":{"error_type":"billing_error","message":"Your organization has no available
 TypeSafe API credits. Please add more credits and/or set up auto-reload at
 https://console.typesafe.ai/settings/billing"}}
```

that message is MISLEADING — it points at a billing page that does not exist for a preview
account. **I told a user to add credits and enable auto-reload; both were impossible.** A 402 here
is TERMINAL: retrying, paying, and auto-reload are all unavailable. The only path back is asking
TypeSafe to grant more preview credits.

**Confirming it is credit exhaustion and NOT rate limiting** (the two are easy to confuse, and
the distinction decides whether to wait or to re-plan):

| Test | Credits out | Rate limited |
|---|---|---|
| Status code | **402** Payment Required | **429** Too Many Requests |
| `Retry-After` / `X-RateLimit-*` headers | **absent** | always present |
| Minimal 1-question call | fails identically | usually succeeds |
| Repeat over ~10s | refuses EVERY time | recovers on a sliding window |
| Error body | typed `error_type: billing_error` | typed rate-limit error |

Also check `x-envoy-upstream-service-time`: a request answered in ~24ms and then refused was
PROCESSED and rejected on account state; a throttled request is held or dropped instead. The API
exposes **no balance endpoint** (`/v1/usage`, `/v1/credits`, `/v1/account`, `/v1/billing`, `/v1/me`
all 404) — the only balance view is the console, which a preview account may not be able to fund.

## Raise on terminal codes — never return an error sentinel callers ignore (2026-09-17)

A client that returns `{"__error__": ...}` on failure is only safe if EVERY caller checks it. In a
20-script pipeline, **none did** — so an exhausted account was indistinguishable from "the model
found nothing to change": scripts ran to completion, exited 0, and rules silently stopped
enforcing. The ERP/monotony rule was wired into a cron job running every 4 hours and would have
quietly stopped discarding jobs while appearing healthy — the same failure class as a cache that
reports success while serving stale results.

**Raise a distinct exception on account-level codes (401/402/403) and reserve the sentinel for
transient ones.** A terminal condition that a caller might ignore must not be returnable.


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
