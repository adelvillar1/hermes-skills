# Server-side SSE heartbeats vs proxy silence timeouts (Cloudflare 524, nginx)

Class of bug: a long LLM pipeline whose HTTP response dies at the reverse proxy even though the server keeps working. Proven fix (2026-08-09, design-canvas `/api/generate`, commit `07c3730`).

## The failure

Reverse proxies kill connections that carry NO data for a fixed window:

- Cloudflare origin timeout: ~100s of silence → origin returns HTTP 524 (request may CONTINUE server-side after the connection dies — work silently persists).
- nginx `proxy_read_timeout`: 60s default.

A blocking route handler that awaits all models before writing its JSON response is silent for the entire pipeline duration → guaranteed 524 for anything slower than the window. Platform function timeouts (`maxDuration` on Vercel, Railway) are often NOT the constraint — the proxy is. (Railway has no function timeout; Vercel's `maxDuration` may be higher than the proxy window anyway.)

## The fix: never be silent

Stream `text/event-stream` from request start; emit data continuously.

### Event schema for a fan-out pipeline (N models × variants)

| event | data | purpose |
|---|---|---|
| `start` | `{tasks:[{model,label,index,total}], brief}` | client renders chips instantly |
| per-task | `{model,index,status:"building"\|"done"\|"error", error?, frames?}` | emitted on task start and on settle |
| `status` | `{done,total,elapsedSec}` | **heartbeat every ~10s** — defeats the silence window |
| `done` | final payload | **SAME shape as the old blocking JSON response** so client completion logic is unchanged |
| `error` | `{error}` | fatal path (e.g. all tasks failed) |

### Server skeleton (Next.js App Router)

```ts
const stream = new ReadableStream<Uint8Array>({
  async start(controller) {
    let closed = false;
    const send = (event: string, data: unknown) => {
      if (closed) return;
      try { controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)); }
      catch { closed = true; } // stream cancelled (client gone) — stop emitting
    };
    const onAbort = () => { closed = true; };
    req.signal.addEventListener("abort", onAbort);
    try {
      send("start", { tasks, brief });
      const settled = await Promise.allSettled(tasks.map(async (t) => {
        send("variant", { ...t, status: "building" });
        try { const r = await generate(...); send("variant", { ...t, status: "done" }); return r; }
        catch (e) { send("variant", { ...t, status: "error", error: msg }); throw e; }
      }));
      const heartbeat = setInterval(() => send("status", { done, total, elapsedSec }), 10_000);
      await Promise.allSettled(settled);          // all tasks done
      clearInterval(heartbeat);                    // clear on completion AND on abort
      // ...DB persistence — unchanged from the blocking era...
      send("done", { reply, frames, modelErrors });
    } catch (e) { send("error", { error: `Generation failed: ${e?.message}` }); }
    finally {
      req.signal.removeEventListener("abort", onAbort);
      try { controller.close(); } catch { /* already closed/cancelled */ }
    }
  },
});
return new Response(stream, {
  headers: {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache, no-transform",   // no-transform stops proxies buffering
    Connection: "keep-alive",
    "X-Accel-Buffering": "no",                    // nginx hint
  },
});
```

### Key semantics

- **Abort ≠ kill.** On client disconnect set `closed=true`; sends become no-ops but task promises + DB writes keep running — late-persisted results are a FEATURE (the 524 era proved the server outlives the connection).
- **Guarded enqueue is mandatory**: `controller.enqueue` THROWS once the stream is cancelled; unguarded, the whole stream errors.
- **Clear the heartbeat on completion AND on abort** (interval leak).
- **`done` event carries the old JSON shape** → the client's post-response logic (frame patching, error surfacing) is untouched.

### Client (browser)

Replace `const data = await res.json()` with a ReadableStream loop: buffer += `decoder.decode(value, {stream:true})`, split on `\n\n`, parse `event:`/`data:` lines; read to EOF THEN act on the stashed `done` payload (don't patch per-event). Keep 402/non-OK JSON handling before the stream read. Guard `if (!res.body) throw` for old browsers.

### Verification

1. `curl -s -N -b <jar> -H 'Content-Type: application/json' --data @brief.json http://localhost:3000/api/generate` → confirm `start`, `building`, heartbeat at ~10s, `done`; exit HTTP 200.
2. Real browser run: trigger from the UI, screenshot the progress card mid-run, then confirm via API the work persisted.

## Design rule: progress events, not reasoning tokens

When the LLM emits HTML/JSON directly (`disableThinking: true` — reasoning tokens would eat the output budget), there is NO readable rationale to pipe. Token-streaming the raw markup is noise. The honest equivalent is deterministic pipeline facts: per-model chips flipping building→done, elapsed timer, X-of-Y bar. **Never fake internal stages the pipeline can't observe** ("writing copy…") — dishonest UI. Only build token-level streaming when the model actually produces a readable stream. (If designer commentary is wanted, that's a separate dual-output prompt feature.)

## Full worked recipe

design-canvas skill, `references/sse-streaming-generate.md` — the complete implementation (event contract, server code, GenerationCard UI, client parser, verification steps) in a real codebase.
