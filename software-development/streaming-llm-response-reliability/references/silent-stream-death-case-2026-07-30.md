# Case Study: Silent Stream Death in a Tri-Stage AI Chat (2026-07-30)

A real instance of the core anti-pattern from the parent skill, in a production
tri-stage AI Chat (regex classifier → cheap router LLM → expensive streaming
synthesizer). Useful as a concrete reproduction + fix template.

## The report

User asked the copilot: **"compare regal princess, celebrity silhouette, and msc
seashore"** (3 ships). The answer bubble sat on "..." forever — no answer, no
error, no retry. Seconds later they asked **"compare msc, princess, and celebrity"**
(3 cruise *lines*) and it answered fine in ~5s.

## The fingerprint that cracked it

Querying the `ai_chat_usage` analytics table:

- The **3-ship** query had **zero rows** — it was never logged at all.
- The **3-line** query was logged: `success=true, latency=5075ms, pipeline=haiku-only`.
- Last-24h failure count: **0**. (Because failures were never logged either.)

"Stuck UI + no error + query absent from the log + a near-identical query works"
= silent stream death on the fragile path. Not a data bug.

## Why the two queries diverged (the routing split)

The classifier sets `complexity = 'complex'` when **2+ categories** match, else
`'simple'`. Complexity picks the path:

| Query | Matched categories | Complexity | Path | Resilience |
|---|---|---|---|---|
| compare 3 **ships** | `ship` + `cruiseLine` (2) | complex | router LLM → **streaming** synthesizer | fragile |
| compare 3 **lines** | `cruiseLine` (1) | simple | single router LLM, non-streaming | robust |

The 3-ship query matched both `ship` (ship names detected) and `cruiseLine`
(the word "compare"), so it took the two-LLM streaming path — the only path with
no timeout, no `onError`, and completion-gated logging. The 3-line query took the
single-call path and survived.

**Lesson:** when "only some queries hang," diff the routing. The category/complexity
split is sending different query shapes down paths of different resilience.

## Reproduction shape (per-stage timing with timeout races)

Don't call the full pipeline blindly — script it stage-by-stage, each wrapped in a
`Promise.race` timeout, so a hang is *reported at the exact stage* instead of
blocking the terminal forever:

```typescript
function race<T>(p: PromiseLike<T>, ms: number, label: string): Promise<T> {
  return Promise.race([
    Promise.resolve(p),
    new Promise<T>((_, rej) => setTimeout(() => rej(new Error(`TIMEOUT ${ms}ms: ${label}`)), ms)),
  ]);
}

// Stage 2: router LLM (with a representative tool) — bounded
const router = await race(generateText({ model: routerModel, tools, ..., }), 30_000, 'router');
// gather toolResults from router.steps[].toolResults

// Stage 3: streaming synthesizer — bounded, with first-chunk timing
let firstChunkMs = -1, full = '';
const ds = streamText({ model: synthModel, ..., onChunk: ({chunk}) => {
  if (chunk.type === 'text-delta') { if (firstChunkMs < 0) firstChunkMs = Date.now()-t; full += chunk.text; }
}});
await race(ds.text, 45_000, 'synth stream');
// report: first chunk at Nms, total Mms — or which stage timed out
```

Findings from this case: the router LLM completed fine (~5s). The streaming
synthesizer was the fragile stage. **Testing the provider directly** (streaming +
non-streaming, small + large prompt) returned HTTP 200 on all four combos — the
provider was healthy, so the hang was the pipeline's missing timeout/abort, not a
provider outage. (A transient 404 seen once during repro was just that — transient;
the durable bug is the absent resilience, not the provider.)

## The fix (two files, both required)

**Frontend (`AIChatPanel`-style client):**
- `AbortController` wired into `fetch({ signal })`
- **Idle** timeout (~45s) reset on every chunk received + a hard ceiling (~90s)
- On abort/error: clear `isLoading`, show a real error message + a **retry** button
- Ensure the empty assistant bubble can never render "..." permanently

**Backend (the streaming route):**
- `abortSignal: AbortSignal.timeout(...)` on every `generateText` / `streamText`
- `onError` handler on the stream that **logs the failure** to `ai_chat_usage`
  with `success: false` (so hangs stop being invisible) and emits a graceful
  fallback chunk ("I hit a problem generating that — please try again.") instead
  of dying silently
- Verify by killing the stream mid-flight → UI must reach error+retry, never a
  permanent spinner

## Takeaways

1. The diagnostic fingerprint (stuck UI + no error + no log row + sibling query
   works) identifies silent stream death instantly — don't waste time on data bugs.
2. Completion-gated logging makes the worst failures invisible. Log failures too.
3. Multi-LLM pipelines have one fragile (streaming) path and one robust path; the
   complexity/category split decides which queries hit the fragile one.
4. A transient provider error is not the root cause — the missing timeout is.
   Capture the resilience pattern, not "the provider broke."
