---
name: ocr-code-review
description: Set up and run the alibaba/open-code-review `ocr` CLI.
---

# Open Code Review (`ocr`)

Deterministic scaffolding (file selection, rule resolution) around a review.
Two modes:

| Mode | Who reasons | Needs LLM endpoint |
|---|---|---|
`ocr review` | OCR's own agent | yes |
`ocr delegate preview\|rule` | host agent (you) | **no** |

## Install

`npm install -g @alibaba-group/open-code-review` → `/usr/local/bin/ocr`.
npm may warn about `allow-scripts`; the binary installs fine anyway
(platform packages ship it; the postinstall download is only a fallback).

## Configuration gotchas (cost me several attempts — all verified)

1. **`ocr` defaults to the Anthropic protocol.** An OpenAI-compatible endpoint
   404s as `POST <url>/v1/messages`. You must set `provider`, not just `llm.url`.
2. **With `provider` active, `llm.*` keys are IGNORED** — ocr prints a warning
   but still accepts the write. Set `providers.<name>.*` instead.
3. **The field is `url`, NOT `base_url`.** `base_url` errors and prints the
   supported list: `api_key, api_key_cmd, url, protocol, model, models,
   auth_header, timeout_sec, extra_body, extra_headers, retry_codes,
   aws_region, aws_profile`.
4. `ocr config get` / `config list` do not exist — read state with `ocr llm test`.
5. Verify with `ocr llm test` before a real run; it prints Source/URL/Model.

Working recipe (OpenAI-compatible):

```bash
ocr config set provider ollama-cloud
ocr config set providers.ollama-cloud.api_key "$KEY"
ocr config set providers.ollama-cloud.url "https://ollama.com/v1"
ocr config set providers.ollama-cloud.model "glm-5.3-flash"
ocr llm test
```

`ocr llm providers` lists ~27 built-ins with protocol + base URL — check it
before hand-rolling `llm.*`.

## Which local key reaches which model (verified 2026-09-12)

- **glm-5.3-flash → Ollama Cloud.** `OLLAMA_API_KEY` in `~/.hermes/.env`,
  `https://ollama.com/v1`. Same path Hermes itself uses
  (`provider: ollama-cloud`). Best quality here.
- **z.ai PAYG key → only `glm-4.5-flash` has quota.** `glm-4.5/4.6/4.7/5-turbo/
  5.3/5.3-flash` all return `1113 Insufficient balance` even though
  `/v1/models` lists them. Listing a model ≠ being able to call it.
- `open.bigmodel.cn` is a separate balance from `api.z.ai` — funded on one can
  be broke on the other.
- The ~100M free ZCode Coding Plan tokens are NOT on the PAYG key. They need
  `~/.zcode/proxy/zcode-proxy.py` (spawns ZCode's `zcode.cjs app-server`), and
  model calls need a **fresh Aliyun captcha token** (~<10 days old). Stale
  token = `AiSdkModelAdapterError: captcha verify failed`. Skip it when Ollama
  Cloud works.

## Model choice changes the answer, not just the cost

Same commit, two models:

| | glm-4.5-flash | glm-5.3-flash |
|---|---|---|
Findings | 4 (3 were praise) | 9 (1 high, 3 medium bugs) |
Tokens | 16.7k | 430k |
Wall clock | **12m37s** | **6m46s** |
Tool calls | 1 | 32 (code_search 14, file_read 11) |

The cheaper model was SLOWER and near-useless. glm-5.3-flash actually uses the
repo-context toolset. Don't cheap out on review models.

## Running

```bash
ocr review --commit HEAD --audience agent --format json -o /tmp/ocr.json
# branch range: --from main --to feature
```

- It is SLOW (minutes). Run as a **background** process, never foreground.
- `--format json -o FILE` (v1.10+); prefer over shell redirection to avoid
  truncation. On older CLIs `--output` errors `unknown flag` — upgrade.
- JSON keys: `summary` (files_reviewed/comments/total_tokens/elapsed),
  `comments[]` (path, start_line, end_line, severity, category, content),
  `warnings`, `manifest`.
- Always read `warnings` — a `review_round_failed` (429) means a round was
  silently dropped and coverage is worse than the file count implies.
- Writes session state to `~/.opencodereview` (~2MB). Does NOT dirty the repo.

## Delegate mode (free, no LLM)

`ocr delegate preview --from HEAD~1 --to HEAD` → file list + merge_base.
`ocr delegate rule <paths>` → grouped rule checklist.
Use when you want the deterministic file manifest + coverage ledger but supply
the reasoning yourself. Instant, zero cost. Its SKILL.md ships at
`skills/open-code-review-delegate/` in the repo.

## GitHub Action hardening (verified 2026-09-12, 11 repos)

Using `uses: alibaba/open-code-review@main`. Four non-obvious requirements:

1. **`llm_use_anthropic` must be the string `'false'`, NOT `''`.** The action
   maps an explicitly-empty string to Anthropic; the run then fails with
   `llm_reasoning_effort is supported only with OpenAI-compatible protocols`.
2. **Add a `concurrency` group per PR** (`cancel-in-progress: true`) — rapid
   pushes otherwise stack duplicate review runs (2x token spend, conflicting
   comments).
3. **Gate the `issue_comment` trigger to collaborators**
   (`author_association in OWNER/MEMBER/COLLABORATOR`) — on public repos any
   user typing `/open-code-review` otherwise burns your LLM quota.
4. **Same-repo PRs only**
   (`head.repo.full_name == github.repository`) — fork PRs get no secrets and
   would fail red; skip them. Cloud agents push to the origin repo, so this
   matches the workflow.

**Fine-grained PATs CANNOT set Actions secrets on PUBLIC repos** (403 on the
secrets API) — private repos work. For public repos, add
`OCR_LLM_URL`/`OCR_LLM_AUTH_TOKEN` secrets + `OCR_LLM_MODEL` var via the web UI
(Settings → Secrets and variables → Actions).

Canonical hardened workflow lives at
`the platform repo's .github/workflows/ocr-review.yml`; copy it to new repos.
Requires `fetch-depth: 0` on checkout (merge-base resolution).

## Integrating into a review process

OCR's real value is the **coverage ledger**: `preview` emits the authoritative
file list and the workflow requires every file end as `reviewed` or `skipped`
*with a reason*, plus `coverage_rate`. That is the guarantee an LLM-only review
cannot make (agents skip files on large changesets). Use it as a stage-0 gate
ahead of an existing review rather than adding another standalone review skill.
