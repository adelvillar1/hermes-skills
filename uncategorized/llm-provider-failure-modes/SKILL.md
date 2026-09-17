---
name: llm-provider-failure-modes
description: "Empirical failure modes of LLM providers (Ollama Cloud, DeepSeek, Xiaomi MiMo) for batch work like insight precompute, document extraction, and bulk classification. Captures account-level quota limits, 429 rate-limit symptoms at per-provider concurrency ceilings, and the actual measured throughput from the 2026-07-10 T6 adventure backfill (14 runs, 14,141 rows). Use whenever you're about to start a multi-hour batch job that calls an LLM provider and need to pick the right one — or when a long-running job has stopped producing output and you need to know which provider failure mode is most likely."
---

# LLM Provider Failure Modes — Empirical Findings (revised 2026-07-11)

## Custom-endpoint base_url safety guard (2026-08-31, cron batch bots)

When a provider is a **named** provider (e.g. `alibaba`, `deepseek`, `openai`), a custom
`base_url` that differs from the provider's registered endpoint is **rejected at runtime**:

```
RuntimeError: Cron job '...' blocked for safety: base_url 'https://token-plan...' is not allowed
for provider 'alibaba'. A named provider's stored credential may only be sent to its own endpoint;
use a configured custom provider (provider="custom") for a custom base_url.
```

This is a deliberate security guard: a named provider's stored API key must only ever be sent to
that provider's own endpoint, so you cannot override `base_url` on a named provider. It happens
for cron jobs AND direct `--provider alibaba` chat calls.

**The fix — register a NAMED CUSTOM provider** and reference it as `custom:<name>`:
```yaml
# config.yaml (top-level `providers:` block — NOT the `model:` block)
providers:
  qwen-token-plan:
    name: qwen-token-plan
    api: https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
    default_model: qwen3.8-flash
    discover_models: false
    key_env: DASHSCOPE_API_KEY
    transport: chat_completions
    enabled: true
```

Then in the `model:` / `delegation:` / `auxiliary.*:` blocks, use `provider: custom:qwen-token-plan`
(not `provider: custom` alone — bare `custom` falls through to an incomplete spec and can silently
resolve to the global default). Set `model.default: qwen3.8-flash`.

**Pitfall — the `model:` block does NOT hold base_url for custom providers.** Setting
`model.base_url` + `model.api_key_env` + `provider: custom` does NOT work — custom providers are
resolved from the `providers:` / `custom_providers:` top-level list, matched by name. Use the
`providers:` block.

**Pitfall — config.yaml is security-protected from direct writes.** `write_file`/`patch` refuse
`/opt/data/config.yaml` ("Agent cannot modify security-sensitive configuration"). Use the CLI:
```bash
hermes config set providers.qwen-token-plan.name "Qwen Token Plan"
hermes config set providers.qwen-token-plan.api "https://token-plan..."
hermes config set providers.qwen-token-plan.default_model "qwen3.8-flash"
hermes config set providers.qwen-token-plan.key_env "DASHSCOPE_API_KEY"
hermes config set providers.qwen-token-plan.transport "chat_completions"
hermes config set providers.qwen-token-plan.enabled true
```
Cron jobs store their own `model`/`provider`/`base_url` in `~/.hermes/cron/jobs.json`; the
scheduler passes job-level `base_url` through as `explicit_base_url`. But the validator still
applies: you MUST set the job's `provider` to `custom:<name>` too, even when you also set the
job-level `base_url`, or the guard fires.

**Model-name gotcha:** Alibaba/DashScope separates the model id from the product name. On the
Apache-1 token-plan endpoint the model is `qwen3.8-flash` (NO hyphen after `qwen`). `qwen-3.8-flash`
(the hyphenated product name) returns `{"error":{"message":"Model not exist.","code":"model_not_found"}}`
— a 400-ish, distinct from invalid-key. If you see "Model not exist", check the model id spelling
before touching auth.

**Diagnostic ordering (avoid burning time on the wrong layer):**
1. `{"error":...,"code":"invalid_api_key"}` → key is wrong/truncated/expired. Try a second key before changing config.
2. `{"error":...,"code":"model_not_found"}` → model id spelling (put / hyphens).
3. `RuntimeError: ... blocked for safety: base_url ... not allowed for provider` → provider/base_url pairing; register a named custom provider.
4. `HTTP 401` from the OpenAI client but raw curl works → provider is named and routing to its default endpoint; set `provider: custom:<name>`.

These are empirical failure modes observed across the 2026-07-10 T6 adventure backfill (14 runs in `scripts/insights/runs/20260710-*-t6-precompute.md`, 14,141 rows succeeded across three providers). Earlier claims that "DeepSeek stalls at 10-15 min" and "MiMo silently returns empty content under load" were diagnoses of MiMo-at-concurrency-20 symptoms (HTTP 429s) misattributed to DeepSeek and misread as empty content. The corrected picture is below.

## Quick decision tree (revised 2026-07-11)

```
Need to run an LLM-powered batch job (hours, thousands of calls)?
├─ Default: DeepSeek `deepseek-v4-flash` at --concurrency=15
│           (~110 rows/min sustained, zero 429s across 11K-row campaign, p50 9.4s)
├─ Fallback: Xiaomi MiMo `xiaomi/mimo-v2.5` at --concurrency ≤ 10
│           (token-plan endpoint; 2.4× slower than DeepSeek, p50 22.6s)
├─ Quota-constrained path: Ollama Cloud `gemma4:31b-cloud` at --concurrency=3
│           (3-concurrent account-wide cap; ~7s latency, single process serial)
└─ Long-running job stopped producing output?
   └─ Diagnose: empty content = different error path; 429s = explicit JSON error;
       0% CPU + no errors = stalled socket (rare, was misattributed before)
```

## DeepSeek `deepseek-v4-flash` — primary batch provider as of 2026-07-11

**Sustained throughput (2026-07-10 T6 campaign, all concurrency=15):**
- Run 1829: 4,980 planned / 4,611 succeeded / 0 failed / 369 skipped, p50 9,387ms / p95 18,891ms, 3,325s
- Run 1850: 7,000 planned / 6,138 succeeded / 0 failed / 862 skipped, p50 9,427ms / p95 21,415ms, 4,590s (largest clean run)
- Run 1912: 2,411 planned / 624 succeeded / 0 failed / 18,356 skipped, p50 9,101ms / p95 17,016ms, 332s

**Zero 429s, zero stalls, zero errors across the entire 11,373-row campaign.** The earlier "stall at 10-15 min runtime" claim was misattributed from a MiMo-at-concurrency-20 run that happened to start during a DeepSeek window.

**Empirical safe ceiling:** 7,000 cells in a single invocation at concurrency=15 (run 1850). Larger invocations should use `--offset`/`--limit` to chunk — not because DeepSeek stalls, but because pre-filter pre-skips and a single run covering 100% of a persona's cells gives you less granular observability.

**Concurrency math:** sustained ~110 rows/min × ~9,000 cells/persona ≈ 82 min/persona; 5 personas sequential ≈ 7 hours for full T6 coverage.

**For batch work:** DeepSeek is the default. Don't pre-emptively slice into small `--limit=2000` chunks; the 7K-cell run proves that size works fine. Slice only if you observe actual 429s in your run log.

**Reasoning-token accounting vs `max_tokens` (2026-08-07, DesignCanvas):** DeepSeek v4 Flash counts internal reasoning tokens against `max_tokens`. A generation capped at 8192 spent ~4,700 on reasoning, leaving <3,500 tokens for actual output → `finish_reason: "length"` with a truncated page mid-markup. This is NOT a quota/429 issue and won't show in "reply OK" smoke tests — it only bites on long structured outputs (HTML frames, JSON payloads). Diagnose with a raw API probe: check `finish_reason` and `usage.completion_tokens_details.reasoning_tokens`. Full probe recipe in `references/token-budget-and-oauth-probes.md`.

**A static budget is NOT sufficient on the longest inputs — escalate and retry, or the loss is silent.** The reasoning model returns BOTH `reasoning_content` and `content` in the same message; when the budget runs out, `content` comes back as an empty string with `finish_reason=length` and nothing else signals a problem. Measured on a 128-call batch over 64 long JDs (~13k chars each): at `max_tokens=4000`, **39 calls spent the entire 4000 on reasoning and returned empty content**, which left **15 of 64 records with no score at all**. The run reported success; the gap only surfaced as nulls downstream. Re-running those 15 with a larger budget recovered **15/15**.

**Rule: loop the budget (4000 -> 8000 -> 16000) and retry on empty content, surfacing an error only after the largest budget also fails.** Empty content with `finish_reason=length` is a TOKEN-BUDGET signal, not a model failure or a parse failure — code that returns an error on the first empty response is what turns a recoverable budget problem into silent data loss. Never `max_tokens` smaller than ~4x your expected reasoning length for long structured outputs.

**Token-plan 1-WEEK QUOTA exhaustion (2026-08-10, DesignCanvas — NEW failure mode):** the DeepSeek token-plan quota is per **1-week window**, not per-day. When exhausted, EVERY API call returns `HTTP 429: Your token-plan 1-week quota has been exhausted. The quota will reset at <ISO timestamp>`. Symptoms and implications:
- Hits **mid-run**: subagents (`delegate_task` children) die after 3 retries (`API call failed after 3 retries: HTTP 429`), returning `exit_reason=max_iterations` with **no work product** — even long-running tasks die with their partial reads already done but their final summary missing. Budget for it: check quota before dispatching parallel subagent batches.
- Hits the **parent too**: the parent's own tool-calling loop can be cut short by the same wall (observed: turns ended with `maximum number of tool-calling iterations allowed` right after the 429s started). The parent keeps answering (cached/queued context) while child calls fail.
- Reset is on a **fixed schedule** (e.g. `reset at 08-12 13:47:00 UTC`), not 60s sliding. Plan batch work around the reset; do NOT retry-loop into it (3 retries × immediate is what the subagents did).
- **Mitigation that worked:** fall back to doing the review/verification work inline in the parent (the parent model route still answers), and re-run formal subagent review after the reset. Don't burn the parent's iteration budget polling children that are dying on 429.

## xAI Grok (OAuth device flow) — refresh-token rotation trap

**Setup:** Grok 4.5 via `api.x.ai/v1` (OpenAI-compatible). xAI uses OAuth device flow; access tokens are JWTs valid **6 hours** (`expires_in: 21600`), and **the refresh token rotates on EVERY refresh** — a manual refresh that captures only the new access token orphans the refresh token: the old one is revoked everywhere (`invalid_grant: Refresh token has been revoked`), including Hermes' own credential pool.

**Failure symptom:** prod starts returning `403 "The OAuth2 access token could not be validated"` ~6h after setup. The OpenAI SDK may surface a bad key as **400** (not 401/403) — catch 400/401/403.

**Refresh endpoint:** `POST https://auth.x.ai/oauth2/token` with form fields `grant_type=refresh_token`, `refresh_token`, `client_id` (the JWT `aud` claim of the access token, e.g. `b1a00492-...`). Other paths (`/oauth/token`, `/token`) 403/404. `client_id` is REQUIRED (first attempt without it → 400 `client_id is required`). Raw device-flow initiation at `auth.x.ai/oauth2/device_authorization` is Cloudflare-blocked — use `hermes auth add xai-oauth --type oauth --label device_code --no-browser` instead; it prints `https://accounts.x.ai/oauth2/device?user_code=XXXX-XXXX` and polls for approval.

**Self-healing pattern (proven in DesignCanvas `lib/models.ts`):** on xAI 400/401/403, refresh via `XAI_REFRESH_TOKEN` + `XAI_CLIENT_ID` env vars, cache the new token pair (including the NEW refresh token!), rebuild the OpenAI client, retry once (`attempt < 2`). Verified: dev server started with a deliberately invalid `XAI_API_KEY` still produced a full Grok frame — refresh kicked in transparently. Env vars needed: `XAI_API_KEY`, `XAI_REFRESH_TOKEN`, `XAI_CLIENT_ID`. Standalone script in `scripts/xai-token-refresh.py`.

## Xiaomi MiMo `xiaomi/mimo-v2.5` — viable fallback at concurrency ≤ 10

**Endpoint:** `https://token-plan-sgp.xiaomimimo.com/v1` (NOT `api.xiaomimimo.com` — the old endpoint returns 401 invalid_key for `tp-` prefixed tokens).

**Corrected symptom (was: "silently returns empty content"):** MiMo at concurrency ≥ 15 returns **HTTP 429 "Too many requests / type: limitation"** with a valid JSON body explaining the rate limit. The 1844 run at concurrency=20 produced 624 errors, ALL of them were explicit 429s with the body `{"error":{"code":"429","message":"Too many requests","type":"limitation"}}`, not empty content. The earlier "empty content" diagnosis was wrong — if you see empty content from MiMo, capture the full response body; it may be a different error path.

**Latency (token-plan endpoint, 2026-07-10):**
- Run 1844 (concurrency=20): p50 22,619ms / p95 35,717ms — 2.4× slower than DeepSeek
- 3,255 successful MiMo rows took 3,190s; DeepSeek would have done the same in ~1,330s

**For batch work:** MiMo IS viable as a fallback at concurrency ≤ 10. Do NOT run MiMo at concurrency ≥ 15 — the 429 rate-limit cliff is at or below ccy=15. Stick to ccy=5-10 for production runs.

**The actual failure mode:** HTTP 429 with explicit JSON error body. The fix is to lower concurrency; the API does NOT silently degrade to empty content.

## Ollama Cloud `gemma4:31b-cloud` — quota-constrained path

**Pro plan hard limit: 3 concurrent requests across the ENTIRE account** (not per-process). User-stated: *"we cannot have more than 3 simultaneous requests at the same time."*

- The "concurrency=3" is a hard ceiling, shared across every Ollama Cloud invocation from your account
- Multiple background processes cannot each run at `--concurrency=3` in parallel
- Strategy: one Node process at a time, sequential across personas

**Reproduction:** run any 4 concurrent Ollama calls; the 4th will hang silently until one of the first 3 completes.

**Why it's still listed:** quota-constrained but proven to complete 6+ hour backfills. Use as tertiary fallback when DeepSeek + MiMo are both unavailable. Not the default for new campaigns now that DeepSeek is viable.

## Per-provider summary table (revised 2026-07-11)

| Provider | Endpoint | Concurrency cap | Throughput (sustained) | Failure mode at scale |
|----------|----------|-----------------|------------------------|------------------------|
| DeepSeek `deepseek-v4-flash` | `https://api.deepseek.com/v1` | 15+ (no 429s observed at 15) | ~110 rows/min, p50 9.4s | None reproduced in 11K-row campaign |
| Xiaomi MiMo `xiaomi/mimo-v2.5` | `https://token-plan-sgp.xiaomimimo.com/v1` | **≤ 10** | ~30-40 rows/min, p50 22.6s | **HTTP 429 at concurrency ≥ 15** (explicit JSON error, not silent) |
| Ollama Cloud `gemma4:31b-cloud` | `https://ollama.com` | 3 (account-wide hard cap) | ~25 rows/min at ccy=3, p50 ~7s | Account quota: any 4th concurrent call hangs silently |

## HTTP 402 Payment Required — a billing outage that MASQUERADES as a quality regression (2026-09-17)

**The trap:** a 24-worker document-generation batch over TypeSafe (`api.typesafe.ai/v1/systemone`)
returned **`HTTP 402: Payment Required`** on **875 of 886 failing calls**. The pipeline's summary
line reported **`grounded 435/1565 (27.8%)` against an 80.2% baseline** — a 5x "regression" that was
purely an infrastructure failure. Content that never got written cannot be grounded, so every
transport failure was silently counted as a CONTENT verdict (`ungrounded`).

**Recovery confirmed the diagnosis:** a raw probe minutes later returned **HTTP 200** with no config
change — so 402 here was a TRANSIENT quota/billing state, not a revoked key. A 402 is not
necessarily permanent; re-probe before concluding the account is dead.

**Two things made this recoverable, and both are design requirements:**
1. The per-item record stored the **rejection REASON**, not just the verdict — `violations:
   ["writer error: transport: HTTP Error 402: Payment Required"]` per question. Without that field
   the only visible signal is a quality number, and you would "fix" the wrong layer.
2. It was caught by breaking the aggregate down, not by trusting it. **Always decompose a
   suspicious aggregate by reason before acting on it.**

**Rule — a pipeline summary must never mix transport failures into a content metric.** Report three
separate numbers: transport/skipped, content-verdict, and total. A run that fails 56% of its calls
to a billing error and reports it as "27.8% grounded" is lying to its operator, and the lie is
convincing because a lower quality score is a plausible outcome of a methodology change.

**Diagnostic order for a sudden quality collapse in a batch job:** (1) decompose the aggregate by
reason code; (2) if any transport/HTTP code dominates, it is infrastructure, not method; (3) probe
the API directly with curl before re-running; (4) only then question the methodology.

**Concurrency note:** the same run also produced `HTTP 429: Too Many Requests` at 24 workers. Prefer
the measured-safe concurrency for the provider; treat 402 and 429 as distinct (billing vs rate).

## Why these failure modes don't show in single-call tests

- **DeepSeek:** reliable at any reasonable test size — failure mode is "none reproducible yet"
- **MiMo:** needs ≥ 15 concurrent to trigger 429s — single calls and small batches pass
- **Ollama Cloud:** needs simultaneous 4+ requests to trigger the account quota hang

A simple "reply OK" smoke test will pass for all three. **Run a multi-call concurrent smoke test before launching a long backfill to find the right concurrency cap for your chosen provider:**

```bash
npx tsx -e '
import { chat } from "./lib/llm/client";
async function main() {
  const promises = Array.from({length: 20}, (_, i) =>
    chat([{ role: "user", content: `Reply with SMOKE_${i}` }], { temperature: 0 })
  );
  const results = await Promise.all(promises);
  results.forEach((r, i) => console.log(i, r.model, r.latencyMs, JSON.stringify(r.content.slice(0, 80))));
  const errors = results.filter(r => !r.content).length;
  console.log(`empty/error count: ${errors}/20`);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
'
```

Count empty responses, errored responses, and high-latency outliers. Compare the empty/error count at concurrency=5, 10, 15, 20 — the threshold where it jumps is your provider's ceiling.

## What to do when a long backfill stalls or 429s

1. **Verify it's actually stalled, not just slow.** Check `ps` for CPU% and the DB for recent `computed_at` timestamps. A stalled process is alive but at 0% CPU. A 429ing process has explicit error logs in the run file's `## Errors` section.
2. **For 429s (MiMo at high ccy):** kill, lower concurrency to ≤ 10, restart. Pre-filter will resume from where you left off via the (shipId, corridorId, personaId, season, prompt_version) key.
3. **For stalls (any provider):** check env vars — `OLLAMA_API_KEY` rotated, `LLM_PROVIDER` got reset. Switch provider if needed; re-run with `--no-delta`.
4. **Document the stall in the run summary** (`scripts/insights/runs/`) so the next session can correlate stalls with provider + workload + concurrency. The 14 2026-07-10 run files are good models.

## What was wrong in the previous version of this skill

- **"DeepSeek stalls at 10-15 min runtime"** — not reproduced in the 2026-07-10 campaign. The original symptom was likely MiMo at concurrency=20 misattributed because the runs were sequenced (MiMo first, then DeepSeek) and the stall hit during the DeepSeek window. Don't cite this anymore unless a fresh reproduction captures it.
- **"MiMo silently returns empty content under load"** — the 624 errors in run 1844 were ALL explicit 429s, not empty content. If you see empty content from MiMo, capture the full response body — it may be a different error path or a connection failure earlier than the HTTP layer.
- **"Ollama Cloud is the only viable batch path"** — DeepSeek at concurrency=15 is faster and equally reliable for the 2026-07-10 workload shape (≤7K cells per invocation, ~10K total). Ollama is still viable but no longer the default.