# Operational Throughput Review — recipe

For live-operations tools where humans process items at a fixed rate during a window:
dismissal queues, dispatch boards, checkout lines, event intake. The review's whole
point is "does the process work end-to-end at the required rate?" — not "is it pretty."

Worked example: the school-dismissal SaaS 600-car school dismissal queue (2026-08-06).

## Step 0 — extract the operator model BEFORE any finding

Confirm with the user (or domain docs) before writing a single finding:

- **Throughput target**: 600 riders / 40 min = 15/min = 1 every 4s.
- **Who does what**: speed-entry operator (fire-and-forget, must never block),
  teachers (read the wall display, move page batches), admin (fixes errors after).
- **Persistence**: cars are NEVER removed. Queue is append-only; pagination advances
  the display through 24-car page batches (12 per color queue). Queues reset daily.
- **Failure policy**: invalid numbers silently ignored (no error surface on entry);
  duplicates allowed but flagged for admin review.

## Step 1 — measure the critical path, don't assume

Timed simulation against the live API (login → clear → N appends → measure → verify):

```python
# shape: fire-and-forget appends exactly like the frontend does
t0 = time.time(); ok = 0
for n in range(101, 151):
    c, r = call("POST", "/api/queue/speed_append", {"primary_number": n}, tok)
    if c == 200 and r.get("status") == "ok": ok += 1
dt = time.time() - t0
print(f"{ok}/{N} queued in {dt:.1f}s = {ok/dt*60:.0f}/min sustained")
```

- Theoretical max = 1000/avg_latency_ms * 60 entries/min; compare to required rate.
- the school-dismissal SaaS result: 195ms avg → 308/min theoretical → **20× headroom**. Entry speed
  was NOT the constraint; stop auditing entry latency after this.

## Step 2 — audit the silent-loss paths (the real risk class)

In fire-and-forget entry, dangerous bugs are the ones that swallow data. Four checks:

1. **Payload contract mismatch.** Mobile screen sent camelCase `primaryNumber` to a
   snake_case endpoint → 422 → `.catch(() => {})` → operator sees success, ZERO
   entries land. Verify by calling the endpoint with the EXACT payload the frontend
   builds (read the JSX), not the corrected one.
2. **"Ignored" response never read.** Backend returns 200 `{status: 'ignored',
   reason: 'student not found'}`; frontend only checks `response.ok`, so a rejected
   number flashes green + beeps + shows in "recent entries" but never enters the
   queue. Admin cannot see it either (no audit log) — the "admin fixes errors" flow
   has nothing to act on.
3. **Flag fields that never render.** Dashboard read `item.isDuplicate` (camelCase),
   API returned `is_duplicate` (snake_case) → duplicate warning icon + count were
   invisible. Fix: normalize in the fetch layer (`.map(n => ({...n, isDuplicate:
   !!n.is_duplicate}))`), then verify visually with seeded duplicates.
4. **Inconsistent roster gates.** One entry path validates the roster, the other
   accepts any number → phantom "Unknown" rows on the public display. Make both
   paths silently ignore non-roster numbers.

## Step 3 — verify with seeded live data + real browser

- Seed a duplicate scenario → confirm the flag renders + count > 0 (vision check,
  not just code read).
- Type an entry in the actual browser screen (mobile + desktop) → confirm it lands
  via the API queue read.
- At scale: seed 50-60 items past the config "capacity" → confirm pagination handles
  it and no hard cap silently drops entries.

## Step 4 — the fixes that satisfy a fire-and-forget design

- Duplicate marking must NOT block entry: set `is_duplicate=True` server-side and
  return 200 — admin cleans up on the dashboard (edit/delete per row already there).
- Roster validation returns `{status: 'ignored'}` — so the endpoint's
  `response_model=` annotation MUST be removed or the dict shape 500s with a
  ResponseValidationError (see `fastapi-query-param-validation` skill pitfall).
- Dashboard "Add to Queue" (admin path, has time) shows a warning toast on ignored;
  speed entry (operator path, no time) stays silent.

## The exact user corrections to internalize (2026-08-06)

These were delivered mid-review, one per turn, after I flagged each as friction:

- "pagination is not a problem, that's how teachers move the queue in batches of 12 per page"
- "speed entry should not stop if there is an error, and admin takes care of errors"
- "12 cars per color queue" → "so it's 24 per page"
- "cars are never removed, the pagination is what moves the queue"
- "only numbers that have an student assigned should be accepted, if a number is
  not valid it should silently be ignored"
- "speed entry is something that happens during a dismissal session, and all queues
  get erased the next day"

Pattern: I flagged by-design behaviors as friction. The user corrected the domain
model four times before the review stabilized. Present the model back to the user
BEFORE writing findings — one confirmation round-trip beats four corrections.
