---
name: streaming-llm-response-reliability
description: "Use when a streaming LLM chat hangs or dies silently."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [llm, streaming, reliability, chat-ui, timeouts, observability, error-handling]
    related_skills: [llm-tool-answer-reliability, systematic-debugging, multi-tier-cache-matching]
---

# Streaming LLM Response Reliability

Build and debug streaming LLM responses (chat UIs, AI copilots, any `streamText` → browser pipeline) so that **a response can never hang permanently, and every failure path is observable and recoverable.**

## The Governing Principle (user-stated)

> "Regardless of whether there is a cached answer, it should never hang — and it must always pass the correct query to the synthesizer (or return a clean fallback)."

Two non-negotiables for any streaming LLM feature:

1. **No permanent hang.** Every await on a stream, an LLM call, or a tool call has a bounded timeout. The UI always reaches a terminal state (answer, error, or retry prompt) — never an indefinite spinner.
2. **Graceful degradation over silent death.** If the synthesizer or a provider fails mid-stream, the user gets a clean, honest message — not a frozen bubble. And the failure is logged.

## The Core Anti-Pattern: Silent Stream Death

The single most common failure in streaming LLM chat features. The fingerprint is unmistakable:

```
Symptom:  UI spinner / "..." sits forever. No error shown. No retry offered.
          The query leaves NO entry in the usage/analytics log.
```

**Why it happens — the mechanics:**

1. The server returns an HTTP **200 with streaming headers immediately** (before any LLM output exists). From this point the server *cannot* return a 4xx/5xx — the status is already sent.
2. The LLM stream (`streamText` / SSE) errors or stalls mid-flight — a transient provider 404/429, a proxy idle-timeout, a network blip, an unhandled throw inside `onFinish`.
3. The stream dies **without a clean end marker**. There is no `onError` handler, or the error is swallowed.
4. The frontend reads the stream with `while (true) { await reader.read() }` and **no `AbortController` / no timeout**. `reader.read()` never resolves `done:true` and never throws — it just blocks forever.
5. Usage logging fires only in `onFinish` / after completion — which never runs — so **the failure is invisible in analytics too.**

**The diagnostic fingerprint (memorize this):**

| Observation | Meaning |
|---|---|
| UI stuck on "..." / spinner, no error | Stream died after 200 headers were sent |
| Query absent from usage/analytics log | Logging is completion-gated; the stream never completed |
| A *similar* query seconds later succeeds | Confirms it's a transient stream death, not a data/logic bug |
| Only *some* query shapes hang | Those shapes route to the streaming/multi-LLM path; others take a robust non-streaming path |

When you see "stuck UI + no error + no log entry," **stop looking for a data bug.** It is a stream-resilience bug. Go straight to the timeout/abort/observability gaps below.

## Frontend Resilience Pattern

The browser side must guarantee a terminal state. Three pieces, all required:

```typescript
// 1. AbortController with an IDLE timeout (reset on each chunk received)
const controller = new AbortController();
let idleTimer: ReturnType<typeof setTimeout>;
const IDLE_TIMEOUT_MS = 45_000;
const armIdle = () => {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => controller.abort(), IDLE_TIMEOUT_MS);
};
armIdle();

try {
  const response = await fetch('/api/ai-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
    signal: controller.signal,           // ← wire the abort signal
  });
  if (!response.ok) throw new Error((await response.json()).message || 'Request failed');

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let full = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    armIdle();                            // ← reset idle timer on every chunk
    full += decoder.decode(value, { stream: true });
    setAssistantContent(full);
  }
} catch (err) {
  // 2. Surface a REAL error + 3. offer a retry — never leave the bubble on "..."
  if ((err as Error).name === 'AbortError') {
    setError('The response took too long. Please try again.');
  } else {
    setError(err instanceof Error ? err.message : 'Something went wrong.');
  }
  // Remove or mark the empty assistant bubble so "..." doesn't persist
} finally {
  clearTimeout(idleTimer);
  setIsLoading(false);
}
```

**Rules:**
- Use an **idle** timeout (reset per chunk), not a single hard timeout — long legitimate responses that keep streaming must not be aborted.
- On abort/error, **clear the loading state and show an error + retry button.** An empty assistant bubble that renders `"..."` while `isLoading` is true is the visual symptom; make sure `isLoading` always clears.
- A hard overall ceiling (e.g. 90s) in addition to the idle timeout is a reasonable backstop.

## Backend Resilience Pattern

The server side must bound every external call and fail loudly-but-gracefully:

```typescript
// 1. Bound every LLM call with an abort signal
const haiku = await generateText({
  model: anthropic(HAIKU_MODEL),
  ...,
  abortSignal: AbortSignal.timeout(30_000),   // ← hard cap on the routing call
});

// 2. Stream with an onError handler that emits a graceful final chunk
const ds = streamText({
  model: deepseek(DEEPSEEK_MODEL),
  ...,
  abortSignal: AbortSignal.timeout(60_000),
  onError: async ({ error }) => {
    console.error('[AI-CHAT] stream error:', error);
    await logAIChatUsage(userId, query, toolsUsed, {   // ← LOG THE FAILURE
      success: false,
      errorMessage: error instanceof Error ? error.message : 'stream error',
      latencyMs: Date.now() - startTime,
    });
  },
});

// 3. Wrap the stream so a mid-stream failure yields a clean fallback message
//    instead of a dead connection. (Pattern: catch the stream error and enqueue
//    a final "I hit a problem generating that — please try again." chunk.)
```

**Rules:**
- **Every** `generateText` / `streamText` / tool `execute` gets an `abortSignal` timeout. No unbounded external calls.
- Add an `onError` (or wrap the stream) that (a) logs the failure to the usage table with `success: false`, and (b) emits a graceful fallback chunk so the client receives a clean end-of-stream rather than a dead connection.
- **Log failures, not just completions.** If usage logging only fires in `onFinish`, stream failures are invisible. Add a failure-logging path so hangs stop being unobservable.

## Build Checklist (for any new streaming LLM feature)

Before shipping a streaming LLM endpoint + client:

- [ ] Frontend `fetch` has an `AbortController` signal wired in
- [ ] Frontend has an idle timeout (reset per chunk) + a hard ceiling
- [ ] Frontend clears loading state and shows error + retry on abort/failure
- [ ] No empty assistant bubble can render "..." indefinitely
- [ ] Backend `generateText`/`streamText` calls have `abortSignal` timeouts
- [ ] Backend stream has an `onError` handler (or wrapped fallback)
- [ ] Stream failures are logged to analytics with `success: false`
- [ ] A mid-stream failure produces a clean user-facing fallback message
- [ ] Verified: kill the provider mid-stream → UI shows error+retry, never a permanent spinner

## Pitfalls

- **"It works in my tests" ≠ it survives a stalled provider.** The happy path streams fine; the bug only appears when a provider hiccups mid-stream. Test the failure path explicitly (abort the fetch, point at a dead endpoint, inject a delay) before declaring the feature done.
- **HTTP 200 is already sent before the LLM produces a byte.** You cannot bail out with a 4xx/5xx once streaming starts. All error handling must happen *inside* the stream (fallback chunk + client-side abort), not via response status.
- **Completion-gated logging hides the worst failures.** If you only log on success/`onFinish`, the queries that hang are exactly the ones missing from your logs — making the bug look like "the query never happened." Always log a failure row.
- **Multi-LLM pipelines have one fragile path.** A tri-stage pipeline (cheap router → expensive synthesizer) often has a robust short path (single model, non-streaming) and a fragile long path (multi-call, streaming). Queries that route to the long path hang; queries on the short path work. If "only some queries hang," diff the routing — the category/complexity split is sending different shapes down different-resilience paths.
- **A transient provider 404/429 is not the root cause — the missing timeout is.** The provider will hiccup again. The fix is never "the provider is broken"; it's "the pipeline must survive a provider hiccup." (Do not capture environment-dependent provider outages as durable rules — capture the resilience pattern.)
- **Don't mask a real routing/logic bug with a timeout.** Timeouts + retry make the symptom survivable, but if a query *always* hangs (not transiently), there's a logic bug upstream (wrong tool fan-out, an infinite tool loop, a bad prompt). Reproduce with per-stage timing first; add timeouts to make it observable, then fix the actual stall.

## Diagnostic Recipe (when a chat feature "hangs")

1. **Confirm the fingerprint:** stuck UI + no error + query absent from usage log → silent stream death.
2. **Reproduce with per-stage timing.** Script the pipeline stage-by-stage (classify → router LLM → tool calls → synthesizer stream), each wrapped in a `Promise.race` timeout, so a hang is *reported* at the exact stage instead of blocking forever. See `references/silent-stream-death-case-2026-07-30.md` for a working reproduction script shape.
3. **Test the provider directly** (streaming AND non-streaming, small AND large prompt) to separate "provider is down" from "our pipeline has no timeout." A healthy provider + a hanging pipeline = our bug.
4. **Diff the routing** between a query that hangs and a near-identical one that works — find which path each takes and why one is fragile.
5. **Fix both ends:** frontend abort/timeout/retry + backend timeouts/onError/failure-logging. Verify by killing the stream and confirming the UI reaches a terminal error+retry state.

## References

- `references/silent-stream-death-case-2026-07-30.md` — Full case study: an AI Chat "compare 3 ships" query hung on "..." with no log entry. Root cause was a complex-path stream with no timeout/abort + completion-gated logging. Includes the classifier routing split, the per-stage reproduction script, and the two-file fix shape.
- `references/deepseek-ai-sdk-streaming-failure.md` — DeepSeek-specific: `@ai-sdk/openai` v3.0.54 streaming returns empty/404 for DeepSeek while raw fetch works. Includes the raw fetch + SSE parsing replacement pattern and the intermittent failure headers.

## Related

- `llm-tool-answer-reliability` — prevents *wrong* answers (hallucination, poisoned cache); this skill prevents *no* answer (hangs, silent stream death). Complementary: one is correctness, the other is liveness.
- `systematic-debugging` — the general 4-phase root-cause method; this skill's diagnostic recipe is the streaming-specific instantiation of it.
- `multi-tier-cache-matching` — the cache layer whose misses fall through to the streaming path this skill hardens.
