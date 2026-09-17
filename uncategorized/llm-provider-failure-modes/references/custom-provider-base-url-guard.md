# Custom Provider + Config detail (Alibaba token-plan / Qwen)

Working config used 2026-08-31 for a bot profile whose cron jobs call Qwen
`qwen3.8-flash` through Alibaba's token-plan endpoint.

## Full profile config.yaml

```yaml
model:
  provider: custom:qwen-token-plan
  default: qwen3.8-flash

delegation:
  provider: custom:qwen-token-plan
  model: qwen3.8-flash

auxiliary:
  compression:
    provider: custom:qwen-token-plan
    model: qwen3.8-flash
  vision:
    provider: custom:qwen-token-plan
    model: qwen3.8-flash
  curate:
    provider: custom:qwen-token-plan
    model: qwen3.8-flash
  search:
    provider: custom:qwen-token-plan
    model: qwen3.8-flash

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

## Key facts
- The endpoint for this token plan is `token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`
  (NOT `dashscope-intl.aliyuncs.com`). Your token may only valid on the ap-southeast-1 region.
- Env var for the key is `DASHSCOPE_API_KEY` (the `alibaba` provider profile declares it too).
- Model id is `qwen3.8-flash` — note NO hyphen after `qwen`. Hyphenated `qwen-3.8-flash` → "Model not exist".
- You must reference it as `custom:qwen-token-plan`, never bare `custom` in this setup.

## Where the key must exist
The profile's `.env` (`/opt/data/profiles/<name>/.env`) holds `DASHSCOPE_API_KEY=...`. For **cron
jobs that run under the DEFAULT profile**, the key must ALSO be in the default `.env`
(`/opt/data/.env`) — cron resolves providers against the default profile's config, not the
the target profile's. If a cron job auth-fails with invalid_api_key while the profile chat works,
this is why.

## Two valid entry points (both hit the guard)
- `model.provider: alibaba` + `model.base_url: <token-plan>`  → BLOCKED by the base_url guard.
- `model.provider: custom` + `model.base_url: <token-plan>`    → does NOT resolve (custom resolves
  from `providers:` list by name, not from model.base_url).
- `model.provider: custom:qwen-token-plan` + `providers.qwen-token-plan` block → WORKS.

## test snippet
```bash
hermes --profile <name> chat -m "qwen3.8-flash" -q "Reply with exactly: ok" -Q
# expect: ok   (no 401, no "Model not exist")
```

## End-to-end proof used
```bash
curl -s -X POST "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen3.8-flash","messages":[{"role":"user","content":"say hi"}]}'
# success -> choices[0].message.content
```
