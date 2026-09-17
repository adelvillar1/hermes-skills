# 02 — Primitives (questions)

Source: `/primitives`, `/primitives/choice`, `/primitives/score`, `/primitives/noul`.

Primitives come in **pairs**: a *question* defines one judgment for a System One model to make about
a state, and its *answer* is the typed value that comes back. You compose the answers in code.

## The three types

| Type | Answers | Returns |
|---|---|---|
| `choice` | Which of these options? | `choice`, `probabilities`, `confidence` |
| `score` | Which level? | `score`, `legend`, `probabilities`, `confidence` |
| `noul` | Is this true? | `noul` (0 to 1) |

## Question anatomy

Every question has:

- **ID** — the key you choose (e.g. `refund_requested`). Identifies the answer in the response.
  **The id is NOT sent to the model**, so never rely on it to convey the question.
- **`type`** — one of `choice`, `score`, `noul`.
- **`instructions`** — the question you are asking about the state. This is where evaluation logic
  goes. Write it as a clear, specific question, or as a statement for the model to judge.
- **`criteria`** — the possible answers. Choice: a map of options. Score: an ordered list of levels.
  Noul: optional description of what yes and no mean.

## Choosing a type

- **Choice** — a known set of options with **no order between them**: routing a ticket to a
  department, classifying a document type, detecting a programming language. Give the full list and
  add an `other` / `none of the above` option when the list may not cover every input.
- **Score** — the answer falls on a **spectrum you can describe in steps**: bug severity, customer
  frustration, skill level. Levels are yours to define; the model returns a position along them.
- **Noul** — a clean **yes/no** where the probability itself is the useful signal: does this message
  report a bug, is a refund being requested, does the resume mention distributed systems.

**Tie-breaker:** if two types both fit, prefer the one whose answer your code can act on directly. A
Choice between `refund`/`rebook`/`information` maps onto three code paths; a Score maps onto a
threshold; a Noul maps onto an `if`.

**Trap:** "Is this candidate strong in Python?" needs a definition of *strong*. A Noul of `0.5` means
yes and no are equally likely — **not** medium skill. To measure skill, use a Score with defined
levels (no experience / some familiarity / daily use / deep expertise). For a yes/no, define the
condition concretely: "Does the resume state that the candidate has used Python at work?"

---

## Choice

### Request
```json
{"department": {"type": "choice",
  "instructions": "Which team should handle this?",
  "criteria": {"returns": "Exchanges, refunds, wrong or damaged items",
               "shipping": "Delivery status, delays, lost packages",
               "billing": "Charges, invoices, payment problems"}}}
```
- `criteria` is a **map**; each key is an option name and each value a description. **Both names and
  descriptions are sent to the model**, so write descriptions that separate options from each other.
- **Up to 255 options.** Adding options costs a few tokens each — give the full list, not a shortlist.
- Use `null` as a description when the option names are self-explanatory (`{"calm": null, ...}`).

### Response
```json
{"department": {"type": "choice", "choice": "returns", "confidence": 1.0,
  "probabilities": {"shipping": 0.0, "returns": 1.0, "billing": 0.0}}}
```
- `choice` — the option with the highest probability.
- `probabilities` — the full distribution across **every** option; values sum to 1.
- `confidence` — 0 to 1, computed from how `probabilities` is spread. Flat = low; single peak = high.

### Reading the distribution
A `department` answer of `returns` at 0.60 with `billing` at 0.38 gives confidence **0.39** — the top
option is clear enough to act on, but the second is not noise. Code can act on the top option *and*
notify the runner-up: `for team, p in department.probabilities.items(): if team != department.choice
and p > 0.25: notify(ticket, team=team)`.

### Structured option descriptions
When two options are similar and the model keeps confusing them, replace the string with an object:
```json
{"return_policy": {"what": "Rules for whether an item can be returned",
                   "not_for": "The status of a specific return",
                   "examples": ["What is your return window?"]},
 "return_status": {"what": "Where a specific return is in the process",
                   "not_for": "The general policy",
                   "examples": ["Where is my refund?"]}}
```
**Field names are not part of the API and none are reserved.** You choose them (as you choose option
names). Use short names that label what follows: `question`, `focus`, `what`, `not_for`, `examples`.

---

## Score

### Request
```json
{"bug_severity": {"type": "score",
  "instructions": "How severe is the reported issue?",
  "criteria": ["Cosmetic; no impact to functionality",
               "Broken or degraded feature, but workaround exists",
               "Blocking issue; no workaround exists"]}}
```
- `criteria` is an **ordered array** from low to high. **Minimum 2 levels, maximum 10.**
- **The array order IS the numbering.** A level's number is its index starting at 0.
- **Each level is judged on its own against the state.** The model sees the descriptions and nothing
  else — it does not see the level numbers or the neighbouring levels.

### Response
```json
{"bug_severity": {"type": "score", "score": 1.3, "confidence": 0.54,
  "legend": {"0": "Cosmetic; no impact to functionality", "1": "Broken or degraded feature, but workaround exists", "2": "Blocking issue; no workaround exists"},
  "probabilities": {"0": 0.0, "1": 0.7, "2": 0.3}}}
```
- `score` = **probability-weighted mean of level numbers**: `0 x 0.0 + 1 x 0.70 + 2 x 0.30 = 1.30`.
  For a 3-level scale it runs 0 to 2 and **can land between levels**.
- `legend` — each level number mapped back to its description.
- `probabilities` — keyed by level number **as a string** in the raw API. The Python SDK keys
  `probabilities` and `legend` by **integer** level instead.

### Reading a Score

| State | `score` | `confidence` | P(0) | P(1) | P(2) |
|---|---|---|---|---|---|
| Button misaligned by a few pixels | 0.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| Export does nothing; CSV workaround takes ages | 1.0 | 1.0 | 0.0 | 1.0 | 0.0 |
| Export spinner never finishes; mixed reports | 1.12 | 0.81 | 0.0 | 0.88 | 0.12 |
| Crashes in Safari; works in Chrome, some users only Safari | 1.3 | 0.54 | 0.0 | 0.7 | 0.3 |
| Nobody can log in; 500 on every attempt | 2.0 | 1.0 | 0.0 | 0.0 | 1.0 |

**Different distributions can produce the same score.** A score of `1.0` can mean all probability on
level 1, *or* half on each of levels 0 and 2. Always read `probabilities` and `confidence` alongside
`score`. A fractional score is a *position*: rank by it, or round to the nearest level when code needs
one outcome.

Low confidence on a Score usually means: the levels **overlap** for this state, the question is
measuring **more than one thing**, or the state **doesn't say enough** to place it.

### Writing good levels
- **Describe situations, not degrees.** "Broken or degraded feature, but workaround exists" gives the
  model something to match. "Moderately severe" does not.
- **Numbers in the descriptions or instructions do NOT help.** `criteria: ["0","1","2"]` with
  "Rate severity from 0 to 2, where 2 is worst" scored **0.57 at confidence 0.35** on a report that
  the descriptive levels scored **0.0 at confidence 1.0**. The model has nothing to match against and
  splits the probability.
- **Keep each Score to ONE dimension.** "Punctual and smart and experienced" measures three things;
  an input high on one and low on another cannot be placed. Split into one Score per thing.
- **Use as many levels as you can describe distinctly, up to 10.** Three is fine. Don't add levels you
  can't describe distinctly.
- **Give a rare extreme case its own level** if you need to act on it differently — a sentiment scale
  ending at "very angry" can add "abusive or threatening", otherwise both messages score near the top.
- **If there is no in-between at all**, use a Choice or split into several Noul questions.
- **Test levels against your own data.** Two wordings of the same scale behave differently.

### Structured level descriptions
When the model keeps scoring between two neighbouring levels on inputs you think are clear, give each
level an object with what it covers plus example situations — **the same field names on every level**
so the model can compare like with like:
```json
{"0": {"what": "Cosmetic; no impact to functionality", "examples": ["typo in a label", "misaligned icon"]},
 "1": {"what": "Broken or degraded feature, but workaround exists", "examples": ["export fails in one browser but works in another"]},
 "2": {"what": "Blocking issue; no workaround exists", "examples": ["cannot log in", "data loss"]}}
```

| Level description | `score` | `confidence` |
|---|---|---|
| plain string, no examples | 1.30 | 0.54 |
| + useful example ("export fails in one browser but works in another") | 1.07 | 0.90 |
| + unrelated example ("search fails, but browsing categories still works") | 1.28 | 0.57 |

Examples steer the model **and only help when they look like your real inputs**. Higher confidence does
not establish which answer is correct — choose examples with known expected levels, then test the
revised descriptions on separate inputs before keeping them.

---

## Noul

A single number, `noul` — **the probability that the answer is yes**.

| Field | Required | Description |
|---|---|---|
| `type` | Yes | Must be `"noul"`. |
| `instructions` | Yes | The yes/no question or statement to evaluate. |
| `criteria` | No | Optional `{true, false}` descriptions clarifying what yes and no mean. |

```json
{"is_human_escalation": {"type": "noul", "noul": 0.99},
 "is_repeat_contact":   {"type": "noul", "noul": 0.93}}
```

- **No separate `confidence`** — the probability itself is the signal.
- Near 1 = strong yes; near 0 = strong no; near 0.5 = yes and no equally likely.
- **Phrase it so a high probability means "yes"** so the answer is unambiguous in meaning.
- You can phrase instructions as a **statement to evaluate for truthfulness** instead of a question
  ("the customer is requesting a refund" — near 1 means the statement is true). Try both phrasings
  with your own data.
- Add `criteria` with `true`/`false` descriptions **when the yes/no boundary is subtle**. Try your Noul
  prompts with and without criteria to see which works better.
- Most often you **threshold it into a boolean** when code needs a hard decision.

Example questions: "Is the customer requesting a refund?" / "Does this resume mention experience with
distributed systems?" / "Does the message contain personally identifiable information?"

---

## Asking many questions at once

Send every question that uses the same state **in one request**. Mix types freely. Every question is
evaluated **in parallel**; adding questions barely changes response time and costs only the tokens for
the extra questions, which are cheap. **Asking a question you might not need is close to free.**

**Speculative questions:** ask every question your code might need, including ones whose answer only
matters for some inputs, and let code decide which answers to use. If a ticket turns out not to be a
bug report, ignore the severity answer. (See `04-patterns.md` — Speculative Fan-Out.)

Batching 13 questions into one call measured **11.5x cheaper and 9.6x faster** than 13 separate calls,
with **no change in the answers**. The number of questions per request is limited only by the token
budget, shared by state and questions: **~32,000 tokens (~150,000 characters of English)**.

**Coding agents fall into the one-question-per-call habit** more than people do.

### Two properties that make answers composable

- **Every answer is constrained to the options you supplied** — the model returns a distribution over
  your options/levels, never a value outside them. Code never recovers a value from prose.
- **Every answer is independent** — one question's answer is not hidden context for another. You can
  add or remove questions without changing the others' results.

### Reference specific fields with backticked paths

When the state is a JSON object, name the part a question is about with a **dot-and-index path in
backticks**; the model then knows which part to judge:
```json
{"refund_requested": {"type": "noul", "instructions": "Does `ticket.messages[0].text` request a refund?"},
 "policy_supports_refund": {"type": "noul",
   "instructions": "Does `refund_policy` support the refund requested in `ticket.messages[0].text`, given `order.charges`?"}}
```

### Splitting a complex judgment

A judgment depending on several things becomes **one question per thing**, combined in code with
weights for relative importance. The weights are yours; when the combined result doesn't match what
the team would decide, **change the weights in code and run again** — no prompt rewrite.

### When one question depends on another

Questions in the same request are independent; a later judgment that depends on an earlier answer
requires a **second request in code**. That dependency is real **only when code cannot build the
second request without the first answer** — it needs the answer to fetch more data for the state, to
decide what the state is made of, or to pick the next question's options. Otherwise ask together.
**Two requests are the exception, not the rule.** Real examples: *Skill suggestion* ranks 182 skills,
then fetches the top three and re-judges them against better evidence; *Structure recovery* asks
whether each line break split a sentence, merges blocks from those answers, then classifies the blocks
that did not exist before; *Hierarchical classification* uses each Choice answer to decide the next
request's options.
