# Glossary

Source refs are chapter files in this skill; each maps to a docs page (noted in its header).

| Term | Meaning | Ref |
|---|---|---|
| **System One model** | A model class built for fast, structured decisions software consumes directly. Jev is the flagship and first. | 01 |
| **Jev** | TypeSafe's flagship System One model. Use `"jev-latest"` in the `model` field. | 01, 05 |
| **Machine Native Intelligence** | AI with software-like properties: structure, reliability, observability, testability, speed, consistency, low cost. | 01 |
| **State** | The content being evaluated — string, object, or array. One request evaluates one state against one or more questions. | 01 |
| **Question** | A typed judgment defined by an id, `type`, `instructions`, and (for Choice/Score) `criteria`. | 02 |
| **Primitive** | A question/answer pair. The three question types are the primitives. | 02 |
| **Choice** | Question type returning one option from a fixed, unordered map of options, plus `probabilities` and `confidence`. | 02 |
| **Score** | Question type returning a position on an ordered list of 2-10 levels, plus `legend`, `probabilities`, `confidence`. | 02 |
| **Noul** | Question type returning a single 0-1 probability that a statement is true. No separate `confidence`. | 02 |
| **Level** | One point on a Score's spectrum, described in words. Its number is its index in `criteria`, starting at 0. | 02 |
| **Legend** | The mapping in a Score answer from level number back to its description. | 02, 05 |
| **`probabilities`** | Full distribution across options (Choice) or levels (Score). Sums to 1. TypeSafe never returns a value outside your supplied options. | 02, 05 |
| **`confidence`** | 0-1 statistic derived from the shape of `probabilities`. Peaked = confident, flat = uncertain. **Not** a guarantee the answer is correct. | 03 |
| **`noul`** | The 0-1 yes-probability returned by a Noul question. | 02 |
| **Calibration** | Across many predictions, outcomes assigned probability `p` occur about `p` of the time. Describes groups, not single answers. | 01, 03 |
| **RLCD** | Reinforcement learning for calibrated decisions — TypeSafe's training path: no text generation, decisions plus calibrated probabilities. | 01 |
| **RLHF** | Reinforcement learning from human feedback. Trains for responses people prefer; can reward sycophancy and hallucinations. | 01 |
| **RLVR** | Reinforcement learning with verifiable rewards. Produces reasoning models strong at math-like tasks, slower and costlier. | 01 |
| **Mode dropping** | RLHF side effect: the model favours one style, narrowing the probability of other outputs. Milder than mode collapse. | 01 |
| **Mode collapse** | Classic GAN failure: a generator repeats one output because it keeps fooling the discriminator. | 01 |
| **Context rot** | Degradation from irrelevant context in the state. Mitigated by sending only what the questions need. | 01, 06 |
| **`EntryType`** | The `string | object | array | null` shape accepted by `instructions` and every `criteria` field. | 07 |
| **Speculative fan-out** | Ask every question the system might need in one call, including ones relevant only to some inputs; code ignores the rest. | 04 |
| **Confidence-gated routing** | Branch on `confidence` with per-action thresholds scaled to the stakes. | 04 |
| **Composite scoring** | Score independent dimensions separately, then combine with code-owned weights. | 04 |
| **Intent routing** | Classify intent with a cheap System One call and dispatch to the cheapest adequate handler. | 04 |
| **AI-powered software** | The architecture TypeSafe targets: code owns the workflow, AI makes narrow structured decisions inside it. | 01, 06 |
| **Beam search** (taxonomy) | Keep the best `K` candidate paths at each level instead of committing to one greedy path. | 07 |
| **Token budget** | ~32,000 tokens shared by `state` and `questions` (~150,000 characters of English). | 02 |

## Answer-field quick map

| Answer type | Fields |
|---|---|
| `noul` | `noul` |
| `choice` | `choice`, `probabilities`, `confidence` |
| `score` | `score`, `legend`, `probabilities`, `confidence` |

Every answer also carries `type`. Choice and Score carry `confidence`; Noul does not.
