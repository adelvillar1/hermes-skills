# Async Background Jobs with Progress Polling

Pattern for long-running FastAPI endpoints (>2s) that need user-visible progress.

## When to use

- Simulation runs (Monte Carlo, backtesting)
- Batch data processing
- Model training / inference
- Any endpoint where the user needs feedback during execution

## Backend: three-endpoint pattern

1. **POST** — validates input, starts work, returns `job_id` immediately
2. **GET /{job_id}/progress** — polls job state (status, iteration, total, elapsed)
3. **DELETE /{job_id}** — optional cancellation

### Job state storage

- **Single-worker**: in-memory dict `_jobs: dict[str, dict]`
- **Multi-worker**: Redis key `job:{job_id}` with JSON value + TTL
- **Persistent**: Postgres `jobs` table with status enum

### Progress callback pattern

The computation engine accepts an optional `progress_callback` and `progress_interval`:

```python
class MonteCarloEngine:
    def simulate(self, ..., progress_callback=None, progress_interval=100):
        for i in range(iterations):
            # ... run iteration ...

            if progress_callback and (i + 1) % progress_interval == 0:
                progress_callback({
                    "iteration": i + 1,
                    "total": iterations,
                    "elapsed": time.time() - start,
                })
```

This decouples the engine from the job tracking — the engine doesn't know about HTTP, threads, or job IDs.

### Threading for CPU-bound work

```python
thread = threading.Thread(target=_run_sync, daemon=True)
thread.start()
```

Use `daemon=True` so the thread dies if the server shuts down. Do NOT use `asyncio.to_thread()` for very long-running CPU work — it can starve the event loop's thread pool.

## Frontend: poll loop with animated progress bar

```javascript
async function triggerJob(params) {
    const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    });
    const { job_id } = await res.json();
    startPolling(job_id);
}

function startPolling(jobId) {
    const poll = setInterval(async () => {
        const res = await fetch(`/api/jobs/${jobId}/progress`);
        const data = await res.json();

        // Update progress bar (CSS transition handles animation)
        const pct = data.total > 0 ? (data.iteration / data.total * 100) : 0;
        progressBar.style.width = `${pct}%`;
        progressText.textContent = `${data.iteration}/${data.total} (${data.elapsed.toFixed(1)}s)`;

        if (data.status === 'completed') {
            clearInterval(poll);
            showSuccess(data.result);
        } else if (data.status === 'failed') {
            clearInterval(poll);
            showError(data.error);
        }
    }, 500);  // 500ms is a good balance — responsive without hammering
}
```

### CSS for smooth progress bar

```css
.progress-bar {
    height: 8px;
    background: var(--accent);
    border-radius: 4px;
    transition: width 0.3s ease;  /* smooth animation between polls */
    width: 0%;
}
```

## Pitfalls from real usage

1. **Must expose the trigger function on the public API object** — In IIFE/module-pattern JS, adding a function inside the closure but forgetting to export it on `window.dashboard = { ... }` causes onclick handlers to silently resolve to `undefined`. The button appears to do nothing. Always check the public export after adding onclick-bound functions.

2. **Progress callback interval matters** — Calling every iteration on a 10K-iteration run means 10K dict updates + 10K DOM updates (if frontend polls during). Use `progress_interval=100` or higher.

3. **Job cleanup** — In-memory `_jobs` dicts grow forever. Add a simple TTL sweep:
   ```python
   # Every request, purge old jobs
   now = time.time()
   _jobs = {k: v for k, v in _jobs.items() if now - v.get("_created", now) < 3600}
   ```

4. **Thread safety** — Python dicts are thread-safe for simple get/set by key. But if you do read-modify-write on a nested dict, use `threading.Lock()`.

5. **`run_in_executor` vs `threading.Thread`** — `loop.run_in_executor(None, fn)` uses the default ThreadPoolExecutor. Fine for most cases, but the pool has a fixed size (default `min(32, os.cpu_count() + 4)`). If you might run multiple concurrent jobs, `threading.Thread` is simpler and doesn't compete for pool slots.

6. **Pydantic response model must include every field the frontend reads.** The data flows: `engine result → _jobs[job_id] dict → progress endpoint reads dict → builds Pydantic response → JSON → frontend reads data.X`. If the engine computes `optimal_hfa` but the Pydantic response model doesn't declare it, the frontend gets `null` and shows "—". The engine was correct; the plumbing dropped the field. **Always trace the full chain** when adding new result fields: engine writes it → job dict stores it → progress endpoint returns it → response model declares it → frontend reads it. A break at any point = silent null.

7. **JSON string vs dict in job result fields.** If the engine stores `optimal_params` via `json.dumps(params)`, the job dict value is a string. The progress endpoint must `json.loads()` it before putting it in the response. The frontend must also guard: `if (typeof params === 'string') params = JSON.parse(params)`. Mismatch at any layer = frontend sees a raw JSON string instead of an object.
