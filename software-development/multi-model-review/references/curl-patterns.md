# Working curl patterns for cross-model review (tested 2026-06-12)

## Setup: build the prompt file

```bash
# Write prompt to temp file (don't inline in shell variable for >5KB prompts)
cat > /tmp/review_prompt.txt << 'EOF'
You are reviewing <artifact>. 
REVIEW FOCUS: ...
OUTPUT FORMAT: ...
VERDICT: APPROVE / APPROVE WITH CHANGES / REVISE
EOF

# Append the artifact
cat /path/to/artifact.md >> /tmp/review_prompt.txt
```

## DeepSeek V4 Flash

```bash
source ~/.hermes/.env 2>/dev/null
PROMPT=$(cat /tmp/review_prompt.txt)

curl -sS https://api.deepseek.com/chat/completions \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg p "$PROMPT" '{
    model: "deepseek-v4-flash",
    messages: [{role: "user", content: $p}],
    temperature: 0.3,
    max_tokens: 4000
  }')" > /tmp/review_deepseek.json

# Extract BOTH reasoning_content and content
jq -r '(.choices[0].message.reasoning_content // "") + "\n---OUTPUT---\n" + (.choices[0].message.content // "")' /tmp/review_deepseek.json
```

**Key pitfall:** The useful output is in `reasoning_content`, not `content`. Always extract both.

## GLM-5.1 (Z.AI)

```bash
curl -sS https://api.z.ai/api/paas/v4/chat/completions \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg p "$PROMPT" '{
    model: "glm-5.1",
    messages: [{role: "user", content: $p}],
    temperature: 0.3,
    max_tokens: 4000
  }')"
```

**Key pitfall:** Balance check required — returns `{"code": "1113", "message": "Insufficient balance"}` when credits exhausted.

## Claude Sonnet via OpenRouter

```bash
curl -sS https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENR..._KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg p "$PROMPT" '{
    model: "anthropic/claude-sonnet-4",
    messages: [{role: "user", content: $p}],
    temperature: 0.3,
    max_tokens: 2500
  }')"
```

**Key pitfall:** OpenRouter returns 402 with exact `max_tokens` you can afford. Reduce by 200 and retry. Don't switch providers — it's per-request, not account depletion.

## Recommended fallback order (based on 2026-06-12 experience)

1. DeepSeek V4 Flash (reliable, fast, cheap — ~$0.10/1M input)
2. OpenRouter with Claude Sonnet (quality but credit-limited)
3. GLM-5.1 (check balance first)
4. Kimi (check key type — CN vs international)

## Response extraction

```bash
# Generic: extract content field
jq -r '.choices[0].message.content // "ERROR: no content"' response.json

# DeepSeek: extract reasoning + content
jq -r '(.choices[0].message.reasoning_content // "") + "\n---\n" + (.choices[0].message.content // "")' response.json

# Check for errors
jq -r '.error // "no error"' response.json
```
