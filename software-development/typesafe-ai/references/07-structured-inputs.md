# 07 — Structured inputs

Source: `/primitives/advanced`.

System One models are **trained to understand structure**. Structure is not a formatting nicety — it
shapes the decision boundary the model sees.

## Where structure is allowed

Every field below accepts an **`EntryType`**: `string`, `object`, `array`, or `null`.

| Field | Applies to | Accepted shape |
|---|---|---|
| `instructions` | Choice, Score, Noul | string, object, array, null |
| `criteria` values (option descriptions) | Choice | string, object, array, null |
| `criteria` entries (level descriptions) | Score | string, object, array, null |
| `criteria.true` and `criteria.false` | Noul | string, object, array, null |

## When to structure a question

- **When it helps with clarity.** When a question has multiple parts, putting them in JSON helps
  because **the keys are labelled**.
- **When the question needs supporting data.** A schema, a taxonomy, or a database row is already
  JSON. **Use the JSON entirely, or pass the relevant subfields**, instead of serialising them into a
  string template.

Start with a plain string and only add structure when it separates guidance that would otherwise blur
together. A short, unambiguous question stays a string.

## Structured instructions

One `field` object describes the field being checked, and each question refers to it **by key**. The
same shape can drive a Noul that verifies a value, a Choice that picks one from candidates, and Scores
that place a value on a scale — in code you can loop over records and build one question per field,
all sent in a single call.

```json
"instructions": {
  "question": "Does the claimed sender identity conflict with the sending domain?",
  "compare": ["ticket.sender.display_name", "ticket.sender.email"],
  "focus": "Compare the named organization with the email domain."
}
```

**Arrays work too** — use one when the instruction is a **list of things to check or to compare**, as
in the `compare` field above.

Observed field names in the docs (none are reserved — you choose them):
`question`, `focus`, `compare`, `inspect`, `what`, `not_for`, `examples`, `signals`.

## Structured Choice options

A Choice option description can be a structured object.

### JSON rubric for boundary clarification

Tell the model **what each option does and does *not* cover**. This sharpens the boundary between
options — the single most effective fix when two options keep getting confused.

```json
{"return_policy": {"what": "Rules for whether an item can be returned",
                   "not_for": "The status of a specific return",
                   "examples": ["What is your return window?"]},
 "return_status": {"what": "Where a specific return is in the process",
                   "not_for": "The general policy",
                   "examples": ["Where is my refund?"]}}
```

### Walking a taxonomy

To classify into a deep taxonomy, **ask one Choice per level and walk the tree in code**. At each step
the options are the **children of the current node**, and each option's value is the **child's subtree**.

Why show subtrees: the model gets to see what lives under a branch **before committing to it**, which
matters when an item belongs to a leaf whose name is not obvious from the branch name. A bottle listing
plausibly fits under two departments; showing the subtrees lets the model see that both
`Sporting Goods > Cycling > Bike Bottles & Cages` and `Home & Kitchen > Drinkware > Water Bottles`
exist, and weigh the listing's emphasis on bike cages against everyday drinkware.

The `probabilities` on that answer tell you whether the split is **close enough to explore both
branches**. Then ask the next Choice with that department's children as options and their subtrees as
values, repeating until you reach a leaf. In code this is a loop over a nested dict where each
question's `criteria` is simply the current node.

**Trim large subtrees:** if a branch is too large, reduce the value to its **direct children and a
sample of leaves**.

For keeping several candidate paths alive when probabilities are close, use a beam search that keeps
the best `K` candidate paths at each level instead of committing to a single greedy path.

## Structured Score levels

Each entry in a Score `criteria` array can be an object. **Use the same field names on every level** so
the model can compare like with like:

```json
[
  {"what": "Cosmetic; no impact to functionality",
   "examples": ["typo in a label", "misaligned icon"]},
  {"what": "Broken or degraded feature, but workaround exists",
   "examples": ["export fails in one browser but works in another"]},
  {"what": "Blocking issue; no workaround exists",
   "examples": ["cannot log in", "data loss"]}
]
```

Examples measurably change the answer — see the confidence table in `03-confidence.md`:
plain string 1.30 / 0.54, useful example 1.07 / 0.90, unrelated example 1.28 / 0.57.

**Examples only help when they look like your real inputs**, and **higher confidence does not
establish which answer is correct**. Choose examples with known expected levels, then test the revised
descriptions on separate inputs before keeping them.

## Structured Noul criteria

Noul `criteria` is **optional**. When the yes/no boundary is subtle, structured `true` and `false`
descriptions pin it down with a definition and examples on each side:

```python
criteria=NoulCriteria(
    true={"what": "Asks the recipient to disclose a listed credential",
          "examples": ["Reply with your password", "Send us your API key"]},
    false={"what": "Does not ask the recipient to disclose a credential",
           "not_for": "A legitimate instruction to reset a credential",
           "examples": ["Use this link to reset your password"]})
```

Note the `not_for` on the `false` side doing real work: it excludes a message that *mentions* a
credential in a safe framing from being counted as requesting one.

## Field-name rules

- Field names are **not part of the API** and **none are reserved**.
- You choose them the same way you choose option names and question ids.
- **The model sees the names along with the values**, so use **short names that label what follows**.
