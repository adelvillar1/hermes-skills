# Token-budget and OAuth probes (from the 2026-08-07 DesignCanvas multi-model work)

Two reproducible probes for provider failure modes that don't show in "reply OK"
smoke tests. Both were used to root-cause live prod issues.

## 1. DeepSeek reasoning-token truncation probe

DeepSeek v4 Flash counts reasoning tokens against `max_tokens`. Symptom:
`LLM response was truncated (max_tokens)` even when the requested output should
fit. Probe the raw API to see the reasoning/content split:

```bash
# Replace $KEY with the DeepSeek API key (never echo it to the transcript —
# read it from env or .env.local inside the script).
curl -s https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ***" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [
      {"role": "system", "content": "You generate HTML landing pages. Output a complete JSON object with name, description, html (full detailed page), tweakSpec, tweakValues. Be thorough."},
      {"role": "user", "content": "Generate a minimal cool-neutral landing page for a boutique coffee roaster with indigo accent. Make the HTML complete and polished."}
    ],
    "max_tokens": 8192,
    "response_format": {"type": "json_object"},
    "stream": false
  }' | python3 -m json.tool
```

Read these fields from the response:

```json
{
  "choices": [{"finish_reason": "length"}],
  "usage": {
    "completion_tokens": 8192,
    "completion_tokens_details": {"reasoning_tokens": 4681}
  }
}
```

- `finish_reason: "length"` at exactly `max_tokens` → the model hit the cap.
- `reasoning_tokens` ≈ 4,681 of 8,192 → ~57% of the budget is consumed by
  reasoning before any HTML is written. The visible content is what's left
  (~3.5K tokens), which truncates mid-markup on long pages.

**Fix:** raise `max_tokens` to 16384 for generation + retry paths (leaves
~10-12K for actual output). Also note: a 8192→16384 bump did NOT change cost
behavior in a harmful way for this workload — reasoning scales with content.

## 2. xAI OAuth device-flow refresh (self-healing pattern)

### Endpoint facts (verified)

- Access token: JWT, `iss=https://auth.x.ai`, `aud=<client_id>`, 6h lifetime.
- Refresh: `POST https://auth.x.ai/oauth2/token`
  - form: `grant_type=refresh_token&refresh_token=<RT>&client_id=<aud>`
  - `client_id` REQUIRED → without it: `400 {"error":"invalid_request","error_description":"client_id is required"}`
  - Wrong path (`/oauth/token`, `/token`) → 403/404 HTML.
  - Success returns `access_token` (6h) **and a NEW rotating `refresh_token`** —
    you MUST persist the new refresh token; the old one is revoked
    (`invalid_grant: Refresh token has been revoked`) on next use.
- Device-flow initiation at `auth.x.ai/oauth2/device_authorization` is
  Cloudflare-blocked for raw scripts. Use instead:
  `hermes auth add xai-oauth --type oauth --label device_code --no-browser`
  which prints `https://accounts.x.ai/oauth2/device?user_code=XXXX-XXXX`,
  then polls for approval (run in a PTY/background and surface the URL to the
  user).

### Self-healing implementation (as proven in DesignCanvas lib/models.ts)

```ts
// module-level token override map; refresh on 400/401/403, retry once
async function refreshXaiToken(): Promise<void> {
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    refresh_token: process.env.XAI_REFRESH_TOKEN ?? "",
    client_id: process.env.XAI_CLIENT_ID ?? "",
  });
  const res = await fetch("https://auth.x.ai/oauth2/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(`xAI token refresh failed: HTTP ${res.status}`);
  const j = await res.json();
  // persist BOTH: new access token AND rotated refresh token
  process.env.XAI_API_KEY=***
  process.env.XAI_REFRESH_TOKEN=*** ?? process.env.XAI_REFRESH_TOKEN;
  _clients.delete("grok"); // rebuild OpenAI client with fresh key
}
```

Retry wrapper: catch `err.status` 400/401/403 for the grok model, refresh,
rebuild client, retry once (`attempt < 2`). The OpenAI SDK reports invalid keys
as **400** ("Incorrect API key provided") — include 400 in the refreshable set.

### Env vars for durable deployment

`XAI_API_KEY`, `XAI_REFRESH_TOKEN`, `XAI_CLIENT_ID` (client_id = JWT `aud`).
Push all three to the deployment platform so expiry self-heals without manual
env surgery.
