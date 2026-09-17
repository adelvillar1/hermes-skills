# 05 — API and SDKs

Source: `/api`, `/sdk`, `/introduction/quickstart`.

## Endpoint

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

API key: `https://console.typesafe.ai/settings/keys`. Playground (no code):
`https://console.typesafe.ai/playground`.

Evaluate a `state` against a map of typed `questions`; get back structured `answers`, one per question.

## Request body

| Field | Type | Required | Notes |
|---|---|---|---|
| `state` | string \| object \| array | yes | content to evaluate; plain string for text, structured for chat logs/records/app state |
| `model` | string | yes | `"jev-latest"` |
| `questions` | map<string, Question> | yes | each entry is a typed Question you name; answers return under the same keys |

The **question key is not sent to the underlying model** and is not used in inference. It exists only
to key the answer back to your code.

```json
{
  "state": "Help! My payouts have been failing for 3 days.",
  "model": "jev-latest",
  "questions": {
    "is_urgent": {"type": "noul", "instructions": "Does this convey urgency?"}
  }
}
```

## Question schemas

All three share `type` and `instructions`; each adds its own `criteria`.

**Noul** — `type: "noul"`
| Field | Type | Required |
|---|---|---|
| `instructions` | string \| object \| array | yes — the yes/no question to evaluate |
| `criteria` | object with `true` and `false` string descriptions | no |

```json
{"is_urgent": {"type": "noul", "instructions": "Does this convey urgency?",
  "criteria": {"true": "Explicitly time-sensitive", "false": "No urgency expressed"}}}
```

**Choice** — `type: "choice"`
| Field | Type | Required |
|---|---|---|
| `instructions` | string \| object \| array | yes — what the model should decide |
| `criteria` | map<string, string \| null> | yes — option to rubric description; `null` when an option needs no extra detail |

```json
{"department": {"type": "choice", "instructions": "Which team should handle this?",
  "criteria": {"billing": "Payments, invoicing, refunds",
               "technical": "Bugs, outages, integrations",
               "sales": "Pricing, upgrades, new accounts"}}}
```

**Score** — `type: "score"`
| Field | Type | Required |
|---|---|---|
| `instructions` | string \| object \| array | yes — what the model should rate |
| `criteria` | array | yes — ordered level descriptions, **minimum 2** |

```json
{"frustration": {"type": "score", "instructions": "How frustrated is the customer?",
  "criteria": ["Calm", "Frustrated", "Very angry"]}}
```

## Response body

| Field | Type | Notes |
|---|---|---|
| `model` | string | the model that performed the evaluation |
| `answers` | map<string, Answer> | one Answer per question, under the same ids |
| `usage` | object | `input_tokens`, `output_tokens` |

```json
{"model": "jev-latest",
 "answers": {"is_urgent": {"type": "noul", "noul": 0.92}},
 "usage": {"input_tokens": 312, "output_tokens": 48}}
```

### Answer fields

| Type | Field | Type | Notes |
|---|---|---|---|
| noul | `noul` | number | the yes/no answer, 0 (no) to 1 (yes) |
| choice | `choice` | string | highest-probability option |
| choice | `probabilities` | map<string, number> | every option to its probability (sum to 1) |
| choice | `confidence` | number | certainty derived from probabilities |
| score | `score` | number | probability-weighted answer across levels; **can land between levels** |
| score | `legend` | map<string, string> | each level number mapped back to its description |
| score | `probabilities` | map<string, number> | each level (string key) to its probability (sum to 1) |
| score | `confidence` | number | certainty derived from probabilities |

Every answer carries a `type` matching its question. Choice and Score also carry `confidence`.

```json
{"department": {"type": "choice", "choice": "technical",
  "probabilities": {"billing": 0.08, "technical": 0.85, "sales": 0.07}, "confidence": 0.82},
 "frustration": {"type": "score", "score": 1.6,
  "legend": {"0": "Calm", "1": "Frustrated", "2": "Very angry"},
  "probabilities": {"0": 0.05, "1": 0.3, "2": 0.65}, "confidence": 0.78}}
```

## Errors

Standard HTTP status codes with a JSON body describing what went wrong.

| Status | Meaning |
|---|---|
| `401 Unauthorized` | Missing or invalid API key. Check the `Authorization` header. |
| `422 Unprocessable Entity` | Request body failed validation — missing required field or malformed question. The body details the **offending field**. |
| `429 Too Many Requests` | Rate limit exceeded. Back off and retry after a short delay. |
| `529 Overloaded` | TypeSafe temporarily overloaded. Retry after a short delay. |

**Handle 429/529 with exponential backoff, not immediate retry.** The official SDKs do this
automatically under their default retry policy, so no extra handling is needed when using one.

## SDKs

| Language | Install |
|---|---|
| Python (requires Python >= 3.10) | `pip install typesafe-sdk` or `uv add typesafe-sdk` |
| JavaScript / TypeScript | see `/sdk` |

Any language can call the HTTP API directly.

### Python usage notes

- The client **reads `TYPESAFE_API_KEY` from the environment** and calls **`jev-latest` by default**.
- Import typed question classes: `from typesafe_sdk import Choice, Noul, Score, TypeSafeClient`.
- Call `client.system_one(state=..., questions={...})`; the client supports `with` (context manager).
- Structured Noul criteria use a `NoulCriteria` helper:
  `criteria=NoulCriteria(true={...}, false={...})`.
- **The SDK keys `probabilities` and `legend` by integer level**, whereas the raw API uses string
  keys. `ScoreAnswer` exposes `score`, `confidence`, `probabilities`, `legend` as typed fields.

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient()                       # reads TYPESAFE_API_KEY
response = client.system_one(
    state="My running shoes arrived in the wrong size. Can I swap them for a size 10?",
    questions={"department": Choice(
        instructions="Which team should handle this?",
        criteria={"billing": "Payment or subscription issues",
                  "technical": "Bugs or integration problems",
                  "sales": "Pricing or account questions"})},
)
print(response.answers["department"].choice)     # "technical"
```

## The agent skill (separate from this one)

TypeSafe publishes its own agent skill for coding agents:

- Claude Code: `claude plugin marketplace add typesafe-ai/skills` then
  `claude plugin install typesafe@typesafe-ai`
- Other agents: `npx skills add typesafe-ai/skills --skill typesafe-ai`
- Read directly: `https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md`
  (raw: `https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md`)

Its guidance includes putting **many questions in each call**, including speculative ones.
