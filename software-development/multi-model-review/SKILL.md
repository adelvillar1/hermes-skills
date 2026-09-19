---
name: multi-model-review
description: "When the user wants multiple distinct LLM opinions on the same artifact (UI review, code review, architecture critique, design feedback) and a synthesized cross-model report. Covers how to discover which models are actually configured with API keys, call them in parallel via direct HTTP, and collate findings. Load when the user says 'get a second opinion', 'cross-model review', 'multi-agent critique', 'ask the other models', 'compare perspectives', or names specific models (GLM/Kimi/Mimo/etc) for the same task."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [multi-model, cross-model, review, critique, comparison, parallel, orchestration]
    related_skills: [model-delegation, adversarial-review, llm-provider-config, project-warmup]
---

# Multi-Model Review

Get the **same artifact reviewed by multiple distinct LLMs in parallel** and synthesize a single report. Distinct from `model-delegation` (which routes to subagents on the same agent infrastructure) and `adversarial-review` (which uses 2 reviewers for spec/quality gates on code changes).

## When to use

- User wants diverse perspectives on a UI mockup, design, code architecture, or written artifact
- User explicitly names specific models ("ask GLM, Kimi, and Mimo")
- User says "cross-model review", "multi-agent review", "second opinion from a different model", "compare what X and Y would say"
- User wants to find **model-disagreement** as a signal (consensus = likely correct; disagreement = worth investigating)

## When NOT to use

- Single-model code review on a PR → `adversarial-review` skill
- Generic `delegate_task` to a single strong reasoning model → `model-delegation` skill
- Mechanical multi-step work (file edits, DB queries) → `delegate_task` directly
- Pure speed/latency routing between providers → `llm-provider-config` skill (fallback chains)

## Pre-flight: discover what's actually wired

**Before promising to call a model, verify it has a configured API key and provider.** Do not claim to "commission" a model you cannot actually invoke.

```bash
hermes config show
```

Look for two things:
1. **Main / `auxiliary_models` slots** — which providers are already wired with keys (vision, web extract, etc.)
2. **Env keys in `~/.hermes/.env`** — `GLM_API_KEY`, `KIMI_API_KEY`, `XIAOMI_API_KEY`, `DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `OPENROUTER_API_KEY`

```bash
grep -E "API_KEY|BASE_URL" ~/.hermes/.env | sed 's/=.*$/=<set>/' | sort -u
```

**If a model has no key, you cannot call it.** Tell the user honestly which models are available and offer to:
- (a) Use only the configured ones
- (b) Help them add the missing key (only if they want to)
- (c) Fall back to a single best-available model

Do **not** impersonate unconfigured models by writing prompts that look like them. That's fabricated cross-model validation.

## The pattern: read → bundle → parallel curl → collate

`delegate_task` is **not** the right tool for this — it routes through the main agent's infrastructure, not directly to the auxiliary providers. Use direct HTTP.

### Step 1 — Read the artifact yourself (you are reviewer 1)

Whatever the artifact is (HTML/JS, code, design, doc), read it in full first. Form your own opinion. This is reviewer 1, and the most important one — you set the synthesis baseline and catch what other models might miss.

### Step 2 — Build a single self-contained prompt

Write one prompt that works for any reviewer. Include:
- The artifact (inlined text, code blocks, or referenced file paths the model can read)
- The review brief (what lens, what to prioritize, output format)
- Output schema if you want structured cross-model collation

**Do not** include any "you are model X" framing — models shouldn't be told what they are, just given the brief. The whole point is that diverse training produces diverse output.

### Step 3 — Call each model in parallel via curl

Use the OpenAI ChatCompletions-compatible endpoint for most providers. Examples:

```bash
# CRITICAL: source the .env file before running these — keys are not auto-loaded
source ~/.hermes/.env 2>/dev/null

# GLM 5.2 via Ollama Cloud (RECOMMENDED — usually works when z.ai direct fails)
curl -sS https://ollama.com/v1/chat/completions \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg p "$PROMPT" '{model:"glm-5.2:cloud", messages:[{role:"user", content:$p}], temperature:0.3, max_tokens:3500, stream:false}')"

# GLM 5.1 via Z.AI direct (FAILS with 401 if GLM balance is empty — fall back to Ollama)
curl -sS https://api.z.ai/api/paas/v4/chat/completions \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg p "$PROMPT" '{model:"glm-5.1", messages:[{role:"user", content:$p}], temperature:0.3}')"

# DeepSeek V3 via OpenRouter (RECOMMENDED — direct DeepSeek API key may fail auth)
# OpenRouter key is in ~/.hermes/.env but NOT auto-sourced into shell env
curl -sS https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENR..._KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg p "$PROMPT" '{model:"deepseek/deepseek-chat", messages:[{role:"user", content:$p}], temperature:0.3, max_tokens:3500}')"

# Direct DeepSeek (auth often fails — use OpenRouter above instead)
# curl -sS https://api.deepseek.com/v1/chat/completions \
#   -H "Authorization: Bearer ***" ...

# Kimi-k2.6 via kimi-coding (uses Anthropic Messages endpoint, see llm-provider-config)
# Xiaomi/Mimo via xiaomi
# MiniMax via minimax
```

For exact base URLs, auth headers, and quirks per provider, load **`llm-provider-config`** — it has the live reference.

**Run all calls in parallel** (background terminal sessions, or one shell with `&` + `wait`). Don't serialize. If one fails, retry it independently; don't block the others.

### Step 4 — Collate, don't just concatenate

A bad collation = "Model A said X. Model B said Y. Model C said Z." That's noise.

A good collation surfaces:
- **Consensus** — what 2+ models flagged independently. Highest signal.
- **Unique findings** — what only one model caught. Often the most valuable (most reviewers miss it).
- **Disagreements** — where models split. Worth investigating but rarely actionable on its own.
- **Priority ranking** — if all 3 say "fix X", it's priority 1. If 1 says "fix Y" and 2 are silent, it's priority 2.

### Step 5 — Be honest about which model said what

When the user reads the report, they should be able to trace each recommendation back to its source. Don't anonymize ("one reviewer said...") — name the model. This lets them weight by trust in each model over time.

## Output template

```markdown
# Cross-Model Review: <artifact>

**Models:** GLM-5.1 (me), Kimi-k2.6, Mimo-m2.5
**Date:** YYYY-MM-DD
**Artifact:** <file path or description>

## Top recommendations (consensus — 2+ models)

1. **<recommendation>** — flagged by [GLM-5.1, Kimi-k2.6]. Why it matters: <reasoning>.
2. ...

## Unique findings (worth investigating)

- **<recommendation>** — only Kimi-k2.6 caught this. Confidence: <low/med/high>.
- ...

## Disagreements (split opinion)

- **<topic>** — GLM-5.1 says X; Kimi says Y. Likely correct: <your call after re-reading artifact>.

## Per-model summary

### GLM-5.1 (this session)
<2-3 sentence summary of my own take>

### Kimi-k2.6
<2-3 sentence summary of what it emphasized>

### Mimo-m2.5
<2-3 sentence summary of what it emphasized>
```

## Pitfalls

- **Don't promise to call models you can't reach.** Check keys first. If a model isn't wired, say so and offer alternatives.
- **Don't impersonate unconfigured models.** If Kimi is not in the user's config, don't write a prompt that says "you are Kimi". Just call whatever IS configured.
- **`source ~/.hermes/.env` before running the curl — keys are NOT auto-loaded into shell env.** Running `curl` with `$GLM_API_KEY` etc. without sourcing the .env file silently fails auth (the env var is empty). The keys ARE in the file; they just aren't exported into your shell. Add `source ~/.hermes/.env 2>/dev/null` as the first line of any review snippet that uses env vars.
- **GLM via Ollama Cloud is more reliable than GLM direct via Z.AI.** `https://ollama.com/v1/chat/completions` with `model: "glm-5.2:cloud"` works when the Z.AI direct endpoint returns 401 "token expired or incorrect" (often a balance issue on the Z.AI account, not actually a key problem). The Ollama Cloud key (`OLLAMA_API_KEY`) is usually funded even when Z.AI isn't. **Default to GLM 5.2 via Ollama Cloud unless explicitly told otherwise.**
- **Direct DeepSeek API key may fail auth even though it's correctly set.** Use DeepSeek via OpenRouter (`model: "deepseek/deepseek-chat"`) instead — the OpenRouter key is reliably funded and DeepSeek works fine through it. Direct DeepSeek has hit "Authentication Fails" errors when the key looks valid.
- **`delegate_task` is the wrong tool.** It routes through the main agent. For distinct model APIs, use direct HTTP (curl + the provider key).
- **Don't serialize the calls.** They're independent. Run them in parallel.
- **Don't anonymize the report.** "One reviewer said..." loses information. Name the model.
- **Don't make 3 sequential clarifying questions to the user.** Ask once with up to 4 choices; if they back out, stop. The user values forward motion over exhaustive scoping.
- **Cap the prompt size.** If the artifact is huge, summarize key sections in the prompt and let models request more if needed. Most API calls have 32k-128k context, but bigger is slower and more expensive.
- **The "reviewer 1 = me" baseline matters.** If you skip reading the artifact yourself, you can't synthesize — you can only compare. Synthesis needs an opinion.
- **DeepSeek output truncation.** DeepSeek V4 Flash sometimes returns truncated `content` but a complete `reasoning_content` field. When the output looks cut short, extract the reasoning: `jq -r '.choices[0].message.reasoning_content'`. The reasoning contains the full analysis even when the final output is truncated by max_tokens. Always check both fields.
- **OpenRouter credit limits.** OpenRouter returns HTTP 403 with `"requires more credits"` when the token budget exceeds remaining credits. Reduce `max_tokens` incrementally (2500 → 1800 → 1200) to find what fits. If credits are truly exhausted, fall back to a single model review.

## OpenRouter Credit Management

OpenRouter has limited credits. When you get a 402 error ("requires more credits, or fewer max_tokens"):

1. **Read the error message** — it tells you exactly how many tokens you can afford (e.g., "can only afford 1910")
2. **Reduce `max_tokens`** to slightly below the stated limit (e.g., 1800)
3. **Retry** — don't give up on the model
4. **If still failing at <1000 tokens**, the output will be too truncated to be useful — skip that model and note it in the synthesis

Typical credit budget per session: 3 reviews (one per plan). Each review uses ~1500-2500 output tokens. Budget accordingly.

## DeepSeek Reasoning Mode

DeepSeek V4 Flash returns a `reasoning_content` field alongside `content`. The reasoning trace is often **more thorough** than the final output (which may be truncated by max_tokens). Always extract both:

```bash
jq -r '(.choices[0].message.reasoning_content // "") + "\n\n---OUTPUT---\n\n" + (.choices[0].message.content // "")' response.json
```

If the `content` is truncated, the `reasoning_content` usually has the complete analysis. Use it as the primary source.

## Synthesis Template

After extracting both reviews, produce a single report with:

1. **Consensus** (both flagged) — highest signal, fix first
2. **Unique findings** (one model only) — often the most valuable
3. **Disagreements** — where models split, make your own call
4. **Your synthesis** (Reviewer 1 = you) — what to actually fix

Don't just concatenate — synthesize. The user wants a single actionable list, not two raw reviews.
- **Watch for reviewer false positives.** A reviewer may flag something as "wrong" that you verified with a live tool call. Trust your own verification over the reviewer's knowledge cutoff. Note the false positive in the synthesis.
- **The "reviewer 1 = me" baseline matters.** If you skip reading the artifact yourself, you can't synthesize — you can only compare. Synthesis needs an opinion.
- **OpenRouter credit limits.** OpenRouter free tier has limited credits. If you get a 402 with "can only afford N tokens", reduce `max_tokens` to fit. Claude Sonnet at 2500 max_tokens still produces useful reviews. Don't retry with the same params.
- **DeepSeek reasoning_content split.** DeepSeek V4 returns both `content` (the output) and `reasoning_content` (the thinking trace). The `content` may be truncated or short while `reasoning_content` has the full analysis. Extract BOTH: `jq '(.choices[0].message.reasoning_content // "") + "\n---OUTPUT---\n" + (.choices[0].message.content // "")'`.
- **GLM balance exhaustion.** GLM/Z.AI returns `code: 1113` with "Insufficient balance" even when the API key is valid. Check for this error and fall back to another provider immediately — don't retry.
- **Kimi auth format.** Kimi uses `api.moonshot.cn` not `api.kimi.ai`. The `KIMI_API_KEY` from the legacy `platform.moonshot.cn` may not work with the new endpoint. Check for `invalid_authentication_error` and fall back.
- **Terminal `&` backgrounding not supported.** The Hermes terminal tool doesn't support `&` for parallel shell processes. Run curl calls sequentially, or use `background=true` with `notify_on_complete` for long calls. For reviews, sequential is fine (~20-30s each).
- **Run `ruff check --fix --unsafe-fixes` after auto-fix.** The `--fix` alone won't catch `UP042` (StrEnum) or other pyupgrade suggestions. The `--unsafe-fixes` flag enables these modernization fixes.
- **⚠️ DeepSeek reasoning_content contains the real output.** When calling DeepSeek V4 Flash (especially with `thinking` enabled or in reasoning mode), the useful review content is in `.choices[0].message.reasoning_content`, NOT `.choices[0].message.content`. The `content` field is often truncated or sparse. Always extract BOTH: `jq -r '(.choices[0].message.reasoning_content // "") + "\n---OUTPUT---\n" + (.choices[0].message.content // "")'`. If you only read `content`, you'll get a 7-line stub when the full review is 135 lines in the reasoning trace.
- **⚠️ Provider fallback chain — don't give up after one failure.** API keys run out of balance, auth fails, credit limits hit. Have a fallback order. Practical pattern observed (2026-06-12): GLM (balance empty) → Kimi (auth failed — CN key vs international endpoint mismatch) → OpenRouter (credit limit — retry with lower `max_tokens`) → DeepSeek (worked). Always check the error body — a 402 with `max_tokens` guidance means retry with fewer tokens, not switch providers.
- **⚠️ OpenRouter credit math.** When OpenRouter returns `"code": 402` with `"you can only afford N tokens"`, reduce `max_tokens` to N-200 (safety margin) and retry. Don't switch providers unnecessarily — the credit limit is per-request, not account-wide depletion.
- **⚠️ Large prompts (>20KB) — use file-based curl.** Build the prompt in a temp file, then use `jq --rawfile` or `jq -n --arg p "$(cat file)"` to pass it to curl. Don't try to inline a 30KB prompt in a shell variable — quoting/escaping breaks silently. Pattern: write prompt to `/tmp/review_prompt.txt`, then `PROMPT=$(cat /tmp/review_prompt.txt)` before the curl call.

## What "cross-model validation" actually buys you

- **Model agreement** on a finding = high confidence the finding is real (multiple training corpora converge)
- **Model disagreement** on a priority = worth a second look at the artifact
- **Unique findings** from one model = highest leverage (everyone else missed it; the user gets a novel insight)
- **Consensus on the *wrong* thing** = possible. Models share common training data. Look for findings that surprise you or contradict your priors.

It does **not** buy you ground truth. It buys you diverse perspectives plus a synthesis you can act on.

## Quantify agreement before you call it agreement

When two models are used as a mutual CROSS-CHECK (not a panel), the rate at which they agree is a
number that is meaningless without the tolerance behind it. Same two models, same 64 items, judged
independently:

| Allowed difference between the two scores | Agreement |
|---|---|
| 1.0 | **49%** |
| 1.5 | 73% |
| 2.0 | 82.5% |
| category-level match (both land in the same bucket) | 73% |

"78% agreement" and "49% agreement" describing the same model pair are both true at different
tolerances. **Pick the tolerance from the measured distribution, and prefer a CATEGORY-level match**
(do both models fall in the same bucket — good/marginal/bad?), because that is the decision the number
actually feeds. A percentage quoted without its tolerance is not evidence, and it will not survive the
first time someone re-measures it.

**Check for a one-directional offset.** Over the same 63 items, one model scored higher on **47**,
equal on 5, lower on 11 (mean offset **+0.85**, stdev 1.48, range -5.1..+3.2). A skew that large means
the pair is not two independent draws around a common truth — one model is simply more generous.
Unflagged, it silently converts your tolerance into a coin flip: at a 1.0 tolerance this pair
"disagreed" on half the set purely from the offset, and a `needs review` flag on half the set is not a
signal. Compute and report the offset whenever you report agreement.

**Escalate disagreements — never average them.** Averaging hides exactly the cases worth seeing: the
item one model calls strong and the other calls unusable. Surface both scores and send that item to a
human (or add a third independent call); an averaged middle number is one neither model believes, and
it destroys the very signal you ran two models to get.

**Agreement is not correctness.** Two models can share a training blind spot and converge confidently
on the same wrong answer. A cross-check bounds the error rate; it does not establish ground truth.

## References

- `references/curl-patterns.md` — copy-paste curl templates for each provider
- `references/openrouter-model-ids-2026-06.md` — live-tested OpenRouter IDs and fallback strategy
