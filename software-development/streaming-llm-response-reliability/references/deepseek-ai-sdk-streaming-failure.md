# DeepSeek + @ai-sdk/openai Streaming Failure (2026-07-30)

## Environment

- `ai` (Vercel AI SDK): v6.0.170
- `@ai-sdk/openai`: v3.0.54
- DeepSeek API: `https://api.deepseek.com/v1` (model: `deepseek-chat`, resolves to `deepseek-v4-flash`)
- Framework: Next.js 14 route handler

## Observed Behavior

All three SDK streaming patterns return empty for DeepSeek:

| Pattern | Result |
|---------|--------|
| `streamText().toTextStreamResponse()` | HTTP 200, body length 0 |
| `await streamText().text` | Rejects: "No output generated. Check the stream for errors." |
| `for await (const d of streamText().textStream)` | Iterates 0 chunks, acc = "" |

Non-streaming `generateText()` also fails intermittently with "Not Found" (HTTP 404).

## Raw fetch works perfectly

```
fetch('https://api.deepseek.com/v1/chat/completions', { stream: true })
→ HTTP 200, SSE chunks with delta.content populated
→ Non-streaming: HTTP 200, choices[0].message.content populated
```

Tested: streaming small prompt, streaming large prompt (8KB), non-streaming large prompt — all HTTP 200 with correct content.

## Intermittency

The SDK failure is intermittent — sometimes returns 404, sometimes returns empty. Direct fetch never fails. This suggests the SDK's request construction or header handling triggers CloudFront/ELB rejection at DeepSeek's edge.

## Response headers on failure

```
statusCode: 404
server: elb
via: 1.1 xxx.cloudfront.net (CloudFront)
x-cache: Error from cloudfront
content-length: 0
```

## Fix Applied

Replaced `@ai-sdk/openai` streaming with raw `fetch` + manual SSE parsing for the DeepSeek synthesis stage. Kept `@ai-sdk/anthropic` for Haiku (Anthropic's SDK integration works correctly). Added `AbortSignal.timeout()` to all LLM calls and an AbortController idle watchdog on the frontend.

## Raw Fetch + SSE Pattern (the fix)

```typescript
async function streamDeepSeekSynthesis(
  systemPrompt: string, userContent: string,
  onDelta: (delta: string) => void, signal: AbortSignal,
): Promise<{ inputTokens: number; outputTokens: number }> {
  const res = await fetch('https://api.deepseek.com/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ model, messages: [...], max_tokens, temperature, stream: true }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`DeepSeek HTTP ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      const t = line.trim();
      if (!t.startsWith('data:')) continue;
      const payload = t.slice(5).trim();
      if (payload === '[DONE]') continue;
      try {
        const json = JSON.parse(payload);
        const delta = json.choices?.[0]?.delta?.content;
        if (typeof delta === 'string' && delta.length > 0) onDelta(delta);
      } catch { /* partial frame */ }
    }
  }
}
```

## Key Insight

The bug was invisible because:
1. The complex path (multi-entity queries like "compare X, Y, Z ships") routes to DeepSeek synthesis
2. Simple queries (single category) use Haiku-only and work fine
3. The empty stream + no error handler = permanent "..." on the client with zero log entries
4. The user's query left NO trace in `ai_chat_usage` — the definitive fingerprint of a mid-stream silent death
