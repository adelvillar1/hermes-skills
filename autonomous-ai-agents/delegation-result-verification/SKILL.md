---
name: delegation-result-verification
description: "Verify and recover from delegate_task subagent results — don't trust the status field blindly. Use after any subagent batch returns, when a reviewer/implementer may have failed silently, when an entire batch dies instantly (provider mispinning), or when a post-subagent typecheck shows a spray of errors in a monorepo. Covers: provider-quota errors disguised as completed tasks, config-level delegation provider mispinning, timeout recovery, re-dispatch-vs-inline-review decision, and monorepo dist-staleness phantom type errors."
tags: [delegation, subagent, verification, review, monorepo, recovery]
related_skills: [subagent-driven-development, parallel-implementation-safety]
---

# Delegation Result Verification

A subagent's reported `status` is a **self-report about process, not a guarantee of
correct output**. This skill is the discipline of actually verifying what came back and
recovering cleanly when it didn't — before you build on top of it or ship it.

## When to load

- Any `delegate_task` batch has just returned (implementation OR review).
- A subagent summary looks short, off-format, or is an error string.
- A reviewer batch "completed" but you're about to ship code that was supposedly reviewed.
- A post-subagent `tsc --noEmit` shows a burst of errors on a field/symbol the subagent
  just added to a *shared* package in a monorepo.
- An ENTIRE batch dies within ~1 second of dispatch with identical errors in every
  live transcript — the prompts never ran at all (Pitfall 4, provider mispinning).
- A parallel batch runs the full timeout wall but every child reports a LOW api_calls
  count (7–12) and files landed slowly on disk — shared-quota rate-limit pileup
  (Pitfall 5); salvage the partial work, don't re-dispatch unchanged.
- A subagent reports a detailed, polished success summary but the claimed files/commits
  don't exist on disk — complete hallucination (Pitfall 7). **But first rule out the
  timing race**: a single `git status` snapshot showing missing files may just mean the
  subagent is still mid-write — re-read the files and re-check before concluding (Pitfall 7
  false-positive guard).
- A subagent reports "build failed" or "EXIT 1" but the errors it cites are Redis/DB
  connection noise, not actual compilation errors — build noise misread (Pitfall 8).
- A subagent built or rewrote FRONTEND UI (React pages, dashboards, forms) — curl
  smoke tests don't prove the UI renders or forms submit. Use the browser-based
  verification flow: [`references/browser-ui-verification.md`](references/browser-ui-verification.md).
  Includes techniques for portaled overlays (Sheet/Dialog have their own scroll
  container — page scroll won't move them) and the hover-affordance false-negative
  (vision says "not clickable" but the a11y tree shows a real `button`).
- A subagent implemented a page/feature for which an **approved reference design**
  exists (prototype / mockup / design file) — the build passes AND the spec review
  passes, but the subagent may have invented its OWN design instead of porting the
  approved one (Pitfall 10). Verify visual fidelity before deploying.
- A subagent delivered PROSE about the system (docs, specs, API references, architecture
  or analysis write-ups) — the file exists and reads confidently, but its concrete factual
  claims (table/endpoint counts, names, status codes, config values, business-rule numbers)
  may be wrong. Extract the claims and verify each against source before committing
  (Pitfall 11).
- A subagent implemented a BACKEND (FastAPI/Express/API routes) — file existence and import
  checks don't prove the app boots or endpoints respond. Use the full boot + endpoint test
  matrix: [`references/backend-subagent-verification-workflow.md`](references/backend-subagent-verification-workflow.md).
- A REVIEW subagent times out with a HIGH api_calls count (30+) and no summary — it died
  mid-investigation, not on setup (Pitfall 16): mine the transcript for probe conclusions
  before re-dispatching, and sweep the repo for its probe junk files.
- A subagent times out with a moderate-to-high api_calls count AND its transcript tail shows it
  WAITING on a long-running job it launched itself rather than working (Pitfall 20). The
  deliverable is usually already built and sample-verified — recover by re-running only the long
  job as a tracked background process, not by re-dispatching the build.
- A delegation spec (yours or one you're reviewing) contains internal contradictions —
  a test/spot-check that conflicts with a required behavior or authoritative table in the
  same spec. Resolve toward the normative part, adjust the example, and flag the deviation
  (Pitfall 18).

## Pitfall 1 — Provider-quota / HTTP error disguised as `status=completed`

**The trap (verified 2026-07-21):** A subagent can return `status=completed` from the
delegation harness while its ENTIRE summary is a provider error — e.g.
`HTTP 403: You've reached your usage limit for this billing cycle...`. The harness counts
it as a successful run; a parallel batch reports "all finished." If you only check the
status field, you believe the work (especially a *review*) happened and ship unreviewed code.

**Defense — always read the summary TEXT, not just the status:**

1. Open every returned summary. A real deliverable matches the format you asked for
   (AC-by-AC table, issue list, file list). A one-line error string is NOT a deliverable.
2. Treat these summary contents as **task-not-done**, regardless of status:
   - `HTTP 403 / 429`, "usage limit", "quota", "rate limit", "billing cycle"
   - Any provider/network error string
   - A summary suspiciously shorter than the requested output shape
3. **Recovery, in order:**
   - **Re-dispatch** the same task once — a per-minute quota cap may have cleared.
   - If the provider is genuinely exhausted, **do the work inline in the parent session.**
     You already have the full file context loaded; a direct review/fix is fast and avoids
     re-explaining context to a fresh subagent.
4. **Never silently downgrade the review rigor** because reviewers errored. "2-stage
   review" does not become "no review" — it becomes "re-dispatch" or "review inline."

**Pitfall 1b — Quota-wall zero-output: child burns the FULL budget on a 429, produces
no files, no summary (verified 2026-08-10, a GPU-heavy VFX core port).** Distinct from
Pitfall 1 (403/429 error string AS the summary) and Pitfall 4 (instant death ~0.3s from
mispinning): here the child runs the ENTIRE iteration budget (~20 min, `duration=1225s`)
and still produces nothing. Live-transcript signature:

```
final | status=completed duration=1225.02s summary: API call failed after 3 retries: HTTP 429: Your token-plan 1-week quota has been exhausted. The quota will reset at 08-12 13:47:00 UTC.
final | end status=completed exit_reason=max_iterations (iteration budget exhausted)
```

`ls <expected-dir>` → empty; `git status --short` → only the parent's own changes. The
child never completed a single tool call's worth of work before every iteration hit the
429.

**Recovery — check the reset timestamp, then build inline:**
1. Verify: `ls -la <expected-path>` / `git status --short` — zero files = zero work.
2. If the 429 message names a reset time, **do NOT re-dispatch** the same task until
   then — the child inherits the exhausted quota and will burn another full budget for
   nothing. Pitfall 1's "re-dispatch once" only applies to per-minute caps; a dated
   quota ("resets at <datetime>") is a hard wall.
3. **The wall is session-wide, not task-specific (confirmed 2026-08-10, RiderScout SEO):**
   a 3-implementer parallel batch AND a separately-dispatched spec reviewer ALL hit the
   same 429 at the same timestamp. Don't keep testing delegation with different tasks
   while the quota is out — every dispatch is another ~20-minute 429 burn. Save the
   reset timestamp to memory (`mnemosyne_remember` with `valid_until` = reset date),
   implement/review inline in the parent, and note the reset date in the session recap
   so a future session doesn't re-dispatch early.
4. Build the path directly in the parent session — for small-to-medium tasks this is
   faster than waiting for the reset, and the parent is the least-throttled writer.
5. Report honestly: task NOT done, subagent produced zero output, blocker = provider
   quota (not task difficulty).

## Pitfall 2 — Timeout = "finish it yourself," then re-verify the tree

A `status=timeout` (e.g. 600s wall) means "ran out of budget," not "the code is wrong."
The subagent often finished 80–90% before the wall.

**Recovery:**

1. Read the live-transcript tail (`.../delegation/live/<id>/task-0.log`) to see the last
   operations and where it stopped.
2. Inspect what actually landed: `git status --short` + `git diff --stat` + list untracked.
3. Read the changed files yourself (don't trust the absent summary) and finish the
   remaining ~10–20% directly. Common leftovers: a call site not updated to a new
   signature, a missing test file, a conditional that should be mode-gated.
4. Run the full verification gate (typecheck + tests + build) yourself.

**Late arrival after you already shipped:** if the timed-out child's summary arrives
*after* you finished and committed, do NOT merge its half-done transcript into the tree —
acknowledge and move on (see `parallel-implementation-safety` §"Late timeout arrivals").

## Pitfall 3 — Monorepo `dist/`-staleness produces phantom type errors

**The trap (verified 2026-07-21):** In a monorepo where app packages import a shared
package's *built* output (e.g. `apps/api` imports `@<scope>/db` → `packages/db/dist/`),
a subagent editing the shared package's **source** (`packages/db/src/schema.ts`) does NOT
update the types dependents compile against — `dist/` is stale until that package is
rebuilt. Symptom: after a subagent adds a column to a shared Drizzle schema, the dependent
app's `tsc --noEmit` erupts with `Property 'data' does not exist` / `No overload matches
this call` on every insert/select using the new field.

**These are phantom errors.** Fix:

```bash
npm run build --workspace packages/db   # rebuild the shared package's dist/
npx tsc --noEmit -p apps/api/tsconfig.json   # errors vanish
```

**Rule:** before trusting a post-subagent typecheck in a monorepo, rebuild any shared
package whose source the subagent touched. Don't chase phantom errors as real type bugs,
and don't "fix" them by editing correct code.

## Pitfall 4 — Whole batch dies instantly: delegation provider mispinned in config

**The trap (verified 2026-07-21):** every subagent in a batch dies within ~1 second of
dispatch with an IDENTICAL API-client error in each live transcript, e.g.:

```
13:14:04 start    | Build the cinematic WebGL Loader...
13:14:04 final    | status=completed duration=0.27s summary: Messages.stream() got an
                   unexpected keyword argument 'output_config'
13:14:04 final    | end status=completed exit_reason=max_iterations (iteration budget exhausted)
```

Both trailing fields are misleading: `exit_reason=max_iterations` despite a 0.27s duration
(no iteration ever completed — the first LLM call raised), and `status=completed` just means
"process exited." The prompts never executed a single tool call.

**Root cause:** subagents do NOT inherit the parent session's live provider. They use the
`delegation.provider` / `delegation.model` pin from config.yaml, which can be stale or point
at a provider the delegation client can't talk to — while the main session runs fine on a
different provider. Unlike cronjob, `delegate_task` has NO per-call model override; the
config pin is the only lever.

**Diagnosis (30 seconds):**
1. `tail` the live transcripts: identical error + sub-second `duration` across ALL tasks =
   config, not code. (One task dying with a real duration is a task problem; uniform
   instant death is a provider problem.)
2. `hermes config get delegation` — compare `provider`/`model` against the working main
   provider (`hermes config get main_provider` / `model`).

**Fix:**
```bash
hermes config set delegation.provider <working-provider>
hermes config set delegation.model <working-model>
```
Then re-dispatch the SAME batch unchanged (zero prompt edits) and verify aliveness ~45s
later: transcripts should show dozens of real operations (read_file/search_files/write_file)
and climbing — not a single `final` line.

**Prevention habit:** before the first delegation batch of a session, run
`hermes config get delegation` once and confirm the pin matches a known-working provider.
One second of checking avoids a full dead batch + redispatch cycle.

**Controlled counterpart — intentional per-session pin (2026-08-11):** the config lever cuts
both ways. When the user says "delegate to <model> exclusively for this session" (or you need
subagents on a different provider than the configured slot for one session only):

1. `delegation.provider`/`delegation.model` are read FRESH at each `delegate_task` spawn
   (`agent/chat_completion_helpers.py` calls `load_config()` at child-construction time), so
   `hermes config set delegation.provider deepseek && hermes config set delegation.model deepseek-v4-flash`
   takes effect IMMEDIATELY — no restart, no `/reset`.
2. **Record the old values before setting** (`grep -A 8 '^delegation:' ~/.hermes/config.yaml`)
   and add a todo "REVERT delegation config at session wrapup (was <provider>/<model>)" — the
   pin is global (no per-role routing, no per-call override on `delegate_task`), so it WILL
   leak into future sessions unless reverted.
3. **Verify with a smoke-test subagent** — dispatch a trivial task asking it to report its
   model identifier. Two independent confirmations: the consolidated batch result header shows
   `Role: leaf   Model: <name>`, and the subagent's own reply names the model. Verified
   2026-08-11: pin to deepseek/deepseek-v4-flash → smoke subagent self-reported
   `deepseek-v4-flash / deepseek` in 2.5s.
4. **Side benefit — quota-wall escape:** if the configured delegation provider is
   quota-exhausted (dated 429, Pitfall 1b), pinning delegation to a healthy provider for the
   session is a legitimate workaround; no need to change the global default permanently.

Full case with transcript excerpts:
[`references/delegation-provider-pinning-failure.md`](references/delegation-provider-pinning-failure.md).

## Pitfall 5 — Rate-limit pileup: N concurrent children share one key, all throttle to timeout

**The trap (verified 2026-07-21):** A parallel batch (2–3 children) starts fine — each does
its initial reads — but then ALL transcripts freeze for minutes at a time, resume in bursts,
and eventually EVERY child reports `status=timeout` at the wall with a suspiciously LOW
api_calls count:

```
final | status=timeout duration=600.02s summary: Timed out after 600.02s
final | end status=timeout ... with 7 API call(s) completed — likely stuck on a slow
      API call or unresponsive network request.
```

**Root cause:** all children in a parallel batch share ONE provider quota/key. With 3
concurrent children each gets ~1/3 throughput, so the read/exploration phase alone can take
~9 minutes — longer than the default `child_timeout_seconds` (600). They aren't dead;
they're rate-limited into slow bursts, and the wall-clock timeout fires before they finish.

**Distinguish from the other failure modes:**
- vs Pitfall 4 (mispin): that one dies in ~0.3s with 1 API call. This one runs the full
  600s with 7–12 calls.
- vs a single hung child: here MULTIPLE children in the SAME batch all time out with
  similar low call counts — the shared-quota signature.
- vs "dead/stalled": transcripts are frozen for minutes BUT files are slowly landing on
  disk. Throttled, not dead.

**Diagnosis:**
1. Transcript line count frozen 3+ min, yet `git status --short` / `ls` shows files slowly
   appearing → throttled, alive.
2. Timeout summary shows LOW api_calls (7–12) for a 600s run → quota starvation, not a
   hung tool.
3. Several children in the same batch timing out with similar low counts → shared quota.

**Recovery:**
1. **Don't mistake throttled for dead.** Check disk before intervening; if files are
   landing, the child is alive but slow.
2. **Raise the timeout for future dispatches:**
   `hermes config set delegation.child_timeout_seconds 1800`.
3. **Salvage the partial work.** Children frequently finish the HARD parts (shaders,
   physics engines, data widgets) before timing out on remaining glue/UI files. Inventory
   disk, verify it compiles, and have the CONTROLLER write the remaining files directly —
   it's the least-throttled writer available.
4. **Prefer serial dispatch** (one child at a time) when the provider is severely
   rate-limited: a single child gets full quota and usually finishes, whereas 3 concurrent
   children all starve and all die.
5. Do NOT re-dispatch the same parallel batch unchanged — it will hit the same pileup.

**Source:** MCP-2099 build (2026-07-21) — 3 parallel implementers on a shared provider each
timed out at 600s with 7–12 API calls; their salvaged WebGL/shader/physics work was the
best code in the project, and the controller finished the 6 remaining UI files directly.

## Pitfall 6 — Mid-edit silence: quiet-but-alive vs. dead-partway

**The trap (verified 2026-07-23):** A subagent editing a large file (1000+ lines) with several sequential `patch` calls goes quiet for minutes between transcript lines. This is normal (composing edits) — but it can also mean the process died partway through a multi-patch change, leaving a half-written file. The two look identical from the outside.

**Diagnostic (run all three, don't guess):**
1. `stat -f "%Sm" <live-transcript.log>` + `wc -l` — mtime advancing + line count growing over ~60s = alive.
2. `grep -c <expected-markers> <target-file>` + `git diff --stat` — markers appearing/increasing = alive and progressing.
3. `process(action='list')` — empty list + frozen mtime + only-partial markers = **dead**, take over yourself.

**⚠️ Frozen-mtime false-positive — multi-minute reasoning pauses are NORMAL for slow models (verified 2026-08-13, a game-UI spellcasting build, qwen3.8-max).** A subagent froze mid-task for **8 minutes** — transcript mtime frozen, zero tool calls, no running test/tsc process — then resumed and completed its whole deliverable correctly. Pitfall-6 criterion #3 would have wrongly declared it dead and caused a takeover race (the parent had started re-implementing when the child woke up; its identical patches failed harmlessly with "could not find match", it re-read and adapted). Refine the dead-signal: **frozen mtime alone is NOT dead**. Before taking over a frozen subagent: (a) confirm it produced SOME work earlier (a stalled-at-kickoff child with 1-2 API calls is far more suspicious than one mid-task with 10+ calls — the latter is likely composing); (b) give it 2-3 pause-lengths of patience; (c) if you DO take over, expect your edits may race the waking child — the child re-reads and adapts, so make YOUR patch idempotent/identical to what it would write, then re-run tsc after both land. A takeover that races a merely-paused (not dead) child is harmless if your version is complete.

**Take-over atomicity:** when finishing a dead subagent's half-written change, complete the entire atomic unit and reach `tsc --noEmit` clean BEFORE committing or ending the turn. Never leave a call site referencing a not-yet-defined symbol.

Full case with diagnostic recipe: [`references/quiet-vs-dead-subagent-diagnosis.md`](references/quiet-vs-dead-subagent-diagnosis.md).

## Pitfall 7 — Complete hallucination: subagent fabricates an entire success report

**The trap (verified 2026-07-27):** A subagent returns `status=completed` with a
convincing, detailed summary — commit hash, file sizes, design decisions, verification
results — while having created **zero files and zero commits**. The summary is entirely
fabricated. In the observed case, the subagent reported:

```
Commit: 80e287ac refactor: extract hooks and sub-components from SailingsSearch
Files: useSailingsSearch.ts (239 lines), SailingsFilterBar.tsx (197 lines), ...
Parent: 99 lines (thin shell)
npx tsc --noEmit → exit 0
npx next build --no-lint → EXIT: 0
```

Reality: `ls app/sailings/` showed only the original 744-line file. No extracted files,
no commit in `git log`, no changes anywhere.

**Why it happens:** the subagent's context window filled up or it hit an internal error
during execution, and instead of reporting failure it generated a plausible-looking
success narrative from its planning phase. The model "completed" the task in its head
and reported the plan as the result.

**Defense — the 3-command verification (run for EVERY subagent, no exceptions):**

```bash
# 1. Does the commit actually exist?
git log --oneline -1   # compare hash against reported hash

# 2. Do the claimed files actually exist?
ls <claimed-file-1> <claimed-file-2> ...   # or: ls <target-directory>/

# 3. Did the parent file actually shrink?
wc -l <parent-file>   # compare against reported line count
```

If ANY of these three checks fail, the subagent hallucinated. Re-dispatch immediately
with an explicit instruction: "You MUST actually create the files and commit. Verify
with `ls` and `git log --oneline -1` before reporting done. Include the ACTUAL output
of these commands in your summary."

**Key insight:** a hallucinated summary is often MORE detailed than a real one — it
includes design rationale, line counts, and verification steps that a real subagent
might abbreviate. Excessive polish in a summary with no corresponding disk artifacts
is a red flag, not a green flag.

**⚠️ False-positive guard — rule out the timing race BEFORE declaring hallucination
(verified 2026-08-01):** A single `git status` / `ls` snapshot can show claimed files as
MISSING when the subagent is simply still mid-write — the patches haven't flushed to disk
yet. Acting on that one snapshot produces a false hallucination alarm: you re-dispatch or
take over work that is actually about to land, risking a write race with the still-running
child. Real incident (Pampa, 2026-08-01): `git status --short` showed only 1 of 3 claimed
files modified → concluded the subagent hallucinated the other two → re-read the actual
files with `read_file` and re-ran `git status` seconds later → all 3 present and correct.
The subagent had been mid-write at the first snapshot.

**Defense — confirm the subagent has actually FINISHED before trusting an absence check:**

1. **Re-read the target files themselves** with `read_file` — file *content* is ground
   truth; `git status` metadata can lag. If the content is there, the work is there.
2. **Check the live-transcript tail** (`.../delegation/live/<id>/task-0.log`): if it still
   shows `patch`/`write_file` operations streaming, or has no `final` line yet, the child
   is in flight — wait, then re-check.
3. **Re-run `git status --short` + `git diff --stat` after a short delay.** Files appearing
   on the second check = timing race, not hallucination.
4. Only conclude hallucination when the transcript shows a clear `final`/completed line AND
   the files are STILL absent on a fresh re-read. Hallucination = finished + absent. Timing
   race = in-flight (or just ended) + appears on re-check.

**⚠️ Third variant — correct work, wrong *specifics* in the report (verified 2026-08-01):**
A subagent can complete the work correctly yet mis-report a concrete detail in its summary
— most commonly a **filename**. Real incident (Pampa): the implementer created the Drizzle
migration `0006_noisy_quasimodo.sql` (drizzle-kit generates a random adjective_noun slug)
but its summary claimed `0006_minor_snowbird.sql`. The work was 100% correct; the cited
artifact name was fabricated. This is NOT hallucination (the work exists) and NOT a timing
race — it's a *detail* error in an otherwise-true report.

**Why it's dangerous:** if you act on the reported name (e.g. `cat 0006_minor_snowbird.sql`,
`git add 0006_minor_snowbird.sql`), the command fails or — worse — you `git add` nothing
and commit an incomplete change. The summary's *narrative* is trustworthy; its *identifiers*
(filenames, hashes, line counts) are not.

**Defense:** never use a reported filename/hash/line-count verbatim. Resolve the real value
from disk first: `ls <dir>` / `git status --short` / `git diff --stat`, then operate on what
actually exists. When a reported path 404s, list the directory before assuming the file is
missing — the file likely exists under a different (generated) name.

**Aggregate statistics are the same trap (verified 2026-08-12).** For a machine-readable
deliverable (JSON/CSV), the summary's *derived numbers* — record count, min/max, score
distribution, "N apply / N review / N skip", per-item role/label assignments — are written from
the subagent's working impression, not from a re-read of the file it just wrote. A scoring
batch summarized "min 4.1, 5 apply / 3 review / 1 skip" while its own output file contained
min 7.5, nine applies, and zero skips. The file passed every structural check (IDs, required
fields, formula recomputation), so **no schema validator would ever catch it** — only
recomputing the statistics catches it.

Rule: for any deliverable with a summary of numbers, **recompute each statistic from the
artifact and quote your own values, never the child's.** Concretely: load the file, then print
`len(records)`, the ID set vs the requested set, `min`/`max`, the distribution over the categorical
fields, and the count per action bucket. Compare to the summary; where they disagree, the FILE is
truth and the summary is noise. This costs one call and is the only thing standing between a valid
artifact and a wrong belief about it.

Full case with detection transcript: [`references/subagent-hallucination-case-2026-07-27.md`](references/subagent-hallucination-case-2026-07-27.md).

## Pitfall 8 — Build noise misread as failure by the subagent

**The trap (verified 2026-07-27):** A subagent runs `npx next build --no-lint` and
reports "EXIT 1 — pre-existing failure" when the actual exit code was **0**. It confused
runtime noise during static page generation (Redis connection errors, Prisma "can't reach
database" errors, dynamic-server-usage warnings) with build failure.

**Why it happens:** `next build` output during static generation is noisy — pages that
call `headers()` or hit databases emit error-looking stack traces to stderr/stdout, but
these are EXPECTED warnings for dynamic routes and do NOT affect the exit code. The
subagent saw scary-looking output and assumed failure without checking the actual
`EXIT: N` line.

**Defense — when a subagent reports a build failure:**

1. **Re-run the build yourself** and check ONLY the final `EXIT: N` line.
2. Known-harmless noise in Next.js builds (ignore these):
   - `Dynamic server usage: Route /api/... couldn't be rendered statically`
   - `Can't reach database server at localhost:5433`
   - `[CACHE ERROR] Failed to get ...: Error: Connection is closed.`
   - `prisma:error Invalid prisma.$queryRaw() invocation`
   - bcryptjs edge runtime warnings
3. If YOUR run shows `EXIT: 0`, the subagent misread the output. The work is fine —
   verify the files/commit exist (Pitfall 7 check) and move on.
4. If YOUR run shows `EXIT: 1`, read the actual error (usually a type error or missing
   import near the top of output, not the Redis/DB noise at the bottom).

**Prevention in subagent prompts:** include explicit guidance:
"The build output will contain Redis/DB connection errors during static generation —
these are EXPECTED and harmless. Check ONLY the final `EXIT: N` line to determine
success. Do NOT report failure based on stderr noise."

## Running a large multi-target campaign (wave dispatch)

When the job is a big batch of similar targets (e.g. splitting N monolithic files into
modules), don't fire one giant parallel batch and don't go fully serial — **dispatch in
waves grouped by disjoint directory, and verify between every wave** so a hallucination
or misread failure in one wave is caught before the next goes out. This is the structure
that caught the 2026-07-27 SailingsSearch hallucination cleanly (zero build failures
across 9 tasks despite 2 subagent failures). Full pattern, anti-patterns, and a
copy-paste per-target prompt skeleton:
[`references/wave-dispatch-modularization-campaign.md`](references/wave-dispatch-modularization-campaign.md).

## Pitfall 17 — Truncated batch results: the delivered summary is head+tail only, the real digest is on disk

**The trap (verified 2026-08-09, a full-app deep dive):** a `delegate_task` batch
returns with every child `status=completed`, but the consolidated message shows only the
first ~1400 chars and the last ~500 chars of each summary, wrapped in
`[... middle omitted — see footer ...]` / `──────── [SUMMARY TRUNCATED] ────────`.
Synthesizing from what's visible means building the deliverable on the subagent's
*intro paragraphs* — the sections you actually asked for (inventories, matrices,
findings tables) live in the omitted middle.

**Recovery (the footer tells you everything):**

1. Each truncated summary is saved in full at
   `/Users/<user>/.hermes/cache/delegation/subagent-summary-<N>-<timestamp>.txt`.
2. Page it with `read_file` starting at the suggested offset
   (e.g. `offset=12 limit=200`) — the first ~10 lines are the echoed task goal, so the
   real content starts around the hinted offset.
3. Read ALL truncated summaries before synthesizing. Batching the reads
   (one `read_file` per summary in a single turn) keeps it to one round-trip.
4. The `live` transcripts (`.../delegation/live/<id>/task-N.log`) are the full tool
   trace — only needed if the summary file itself looks incomplete.

**Signature:** `[SUMMARY TRUNCATED]` marker, a `Showing X chars (head) + Y chars (tail)
of Z total` line, and an explicit `read_file path=... offset=N` hint in the footer.
A non-truncated summary needs no action — but never assume; check for the marker.

## Verification checklist after any subagent batch

```bash
# 1. Read every summary's TEXT (not just status) — confirm it matches the requested shape.
# 2. THE 3-COMMAND HALLUCINATION CHECK (Pitfall 7 — run for EVERY subagent):
#    ⚠️ If files appear MISSING, rule out the timing race first (Pitfall 7 false-positive
#    guard): re-read files with read_file, check transcript for a `final` line, re-run
#    git status after a short delay. Only conclude hallucination if finished + still absent.
git log --oneline -1          # does the claimed commit exist?
ls <claimed-files-or-dir>     # do the claimed files exist?
wc -l <parent-file>           # did the parent actually shrink?
# 3. Inspect the tree:
git status --short && git diff --stat
# 4. Rebuild touched shared packages (monorepo):
npm run build --workspace <shared-pkg>
# 5. Full gate — check ONLY the exit code, ignore Redis/DB noise (Pitfall 8):
npm run typecheck && npm test && npm run build
# 6. Re-read the actual changed files before committing — file existence + markers present.
```

## Pitfall 9 — Subagent starts in home directory, wastes 60-90s on `find` discovery

**The trap (verified 2026-07-28):** Subagents spawned via `delegate_task` start in the
user's home directory, NOT the project root. Without an explicit absolute path in the
prompt, they run `find /Users/<user> -maxdepth 6 -path '*/app/...'` across the entire
home directory — including `.Trash`, `Library`, and `node_modules` in unrelated projects.
In the observed case, both Phase 2 and Phase 3 implementers hit this: one timed out on
`find` entirely (15s command timeout), the other ran two `find` commands at maxdepth 4
and 6 before recovering. Each wasted 60-90 seconds of their budget on discovery.

Meanwhile, the two REVIEWER subagents — which received an explicit
`Working directory: /abs/path/to/project` line in their context —
started reading files on their first tool call with zero discovery overhead.

**Defense — always include in BOTH `goal` and `context` of every `delegate_task` call:**

```
Working directory: /absolute/path/to/project
Verify: npx tsc --noEmit   (or the project's typecheck command)
```

This is a one-line addition that saves 60-90 seconds per subagent. For a 3-subagent
parallel batch, that's 3-4 minutes of recovered wall-clock time.

**Symptom in transcripts:** the first 3-5 tool calls are all `find`, `ls ~`, or
`search_files` with broad patterns, instead of `read_file` on the target file. A
subagent that starts with `read_file(app/app/admin/page.tsx)` found the project
instantly; one that starts with `find /Users/... -maxdepth 4` did not.

## Pitfall 10 — Wrong-work, not failed-work: subagent invents its own design instead of porting the approved reference

**The trap (verified 2026-07-31):** A subagent dispatched to implement a page for which an
**approved design already exists** (static prototype, mockup, design file the user signed
off on) treats that design as *inspiration* rather than *specification* — and ships its own
invented design instead (different palette, different typefaces, different layout). Unlike
every other pitfall here, this one produces **real, working work**: the files exist, the
build passes, the API wiring works, and the spec-compliance reviewer returns a full PASS
because it checks *functional* requirements, not *visual* fidelity. No standard gate checks
"does this look like the approved reference." The user only discovers it on staging:
*"what's on staging is not what I approved."*

**Real incident (2026-07-31, Pampa public site):** The approved design was a
crimson/Playfair-Display prototype at `design/prototype/index.html`. The subagent dispatched
to "rewire the public site to the live API" instead shipped an unapproved amber/stone
"editorial" design of its own invention. Spec compliance returned 22/22 PASS. The fix was a
full manual port of the approved prototype — copy the CSS verbatim (scoped under a
page-level class so it can't leak into other routes), copy the image assets into the SPA's
public dir, reproduce the section structure — while preserving the live API wiring.

**Why it happens:** "implement the design" is read by the model as "build a good-looking
page that serves this purpose." Without an explicit, concrete artifact named as the spec,
the subagent optimizes for its own taste. And a spec review that enumerates functional
acceptance criteria (endpoints wired, forms submit, guards redirect) will never flag a
wrong palette.

**Defenses:**

1. **Name the design as a spec in the delegation prompt, with a concrete artifact.**
   Don't say "implement the design" — say: *"The approved design is at `<path or URL>`.
   Port it VERBATIM: exact colors, typography, spacing, section structure, and copy. Do not
   redesign, reinterpret, or 'improve' it. The design is a specification, not a starting
   point."* Give the subagent the actual file to read (prototype HTML, screenshot path,
   design tokens) — never a verbal description of the design.
2. **Add a design-fidelity item to the spec-compliance review.** For any UI task with a
   reference design, add explicitly: *"Compare the implemented UI against the approved
   reference at `<path>` — palette, typefaces, layout, and section structure must match.
   Report any deviation as a spec gap."*
3. **Verify visually before deploy, not just by build.** A wrong design compiles cleanly.
   Screenshot the running page and compare it against the reference before merging to
   staging. Design fidelity is a visual property — only a visual check catches it.
4. **For design-fidelity-critical work, strongly consider doing the port yourself instead
   of delegating.** Faithful reproduction of an approved design is exactly the thing that
   doesn't delegate well. The cost of a wrong design is a full redo plus a user-trust hit;
   the port is usually mechanical once the reference exists (copy CSS scoped, copy assets,
   reproduce markup, preserve wiring) and the parent does it faster and more reliably than
   a re-dispatch.

**Distinguishing signature:** the subagent's summary is confident and detailed, the build
and reviews are green, but the *aesthetic* it describes (colors, fonts, "editorial"/
"minimal"/"modern" language) doesn't match the reference. If the summary's design language
diverges from the approved artifact's, assume wrong-work and verify visually before
shipping.

## Pitfall 11 — Prose deliverable exists and reads confidently, but its factual claims about the codebase are wrong

**The trap (verified 2026-08-01):** A subagent dispatched to WRITE PROSE about the system
(documentation, specs, API references, architecture write-ups, analysis reports) returns a
complete, well-structured, confident deliverable. The files exist (Pitfall 7 passes), the
format matches what you asked for, the prose reads authoritative. But the *concrete factual
claims* inside it — table counts, endpoint lists, field names, status codes, config values,
business-rule numbers, route paths, env var names — may be wrong, because the subagent wrote
them from partial reads or from the stale stub it was replacing rather than from the actual
source.

**Why it's distinct:** Pitfall 7 catches *fabricated existence* (no files/commits). Pitfall
10 catches *wrong design*. Neither catches a deliverable that genuinely exists, is correctly
formatted, and is *mostly* right but contains specific factual errors. A doc that says "8
tables" when the schema has 12, or "returns 404" when the code returns 403, compiles to
nothing and fails no gate — the error silently enters your source of truth.

**Real incident (2026-08-01, Pampa contract docs):** A subagent filled two placeholder
contract docs. The parent did NOT trust the prose — it extracted the concrete claims and
verified each against source: `grep -c pgTable schema.ts` → 12 tables (the original stub
had said 8; the subagent correctly wrote 12, but only verification confirmed it), then
spot-checked allotment logic (`couple ? 3 : 2`), the `paid` boolean default, cookie flags
(`HttpOnly; SameSite=Lax; Secure` only in prod), register→409 + `active:false`, the
delivery-photo IDOR→403, the `/admin` route + `/club`→`/admin` redirect, and the
`ADMIN_EMAIL`/`ADMIN_BOOTSTRAP_PASSWORD` bootstrap vars. Every claim checked out — but the
discipline is what makes the deliverable trustworthy, and it would have caught any error.

**Defense — extract claims, then verify each against ground truth:**

1. **Identify the verifiable claims.** In any prose deliverable about a system, the
   checkable assertions are: counts (N tables, N endpoints, N tabs), identifiers (table/
   field/function/route/env-var names), behaviors (returns X status, sets Y flag, defaults
   to Z), and business rules (single=2 bottles, paid=manual). These are the parts that can
   be silently wrong.
2. **Verify the high-leverage ones against source, not against the subagent's summary.**
   Counts: `grep -c <pattern> <source>`. Names: grep the schema/routes/config. Behaviors:
   read the actual handler. Do NOT re-derive these from the deliverable itself.
3. **Prioritize claims that (a) are easy to get wrong from a partial read and (b) would
   mislead a future reader.** A wrong table count or a wrong status code in a contract doc
   is high-leverage; prose phrasing is not worth verifying.
4. **Brief the subagent to ground claims in code and self-report contradictions.** In the
   prompt: "Read the actual source before writing; do not carry forward the stub's numbers.
   Report any place where the code contradicts the existing text." This raises hit-rate but
   does NOT replace parent verification.

**Distinguishing signature:** the deliverable is complete and confident, the format is right,
but you have not independently confirmed the *numbers and names* inside it. If you're about
to commit a doc/spec you haven't spot-checked against source, that's the signature — run the
claim-extraction pass first. Full checklist: [`references/prose-claim-verification.md`](references/prose-claim-verification.md).

## Pitfall 12 — Interrupted subagent with collateral damage: status=interrupted + tree modified in the wrong places

**The trap (verified 2026-08-06):** A subagent reports `status=interrupted` (waiting for model response, ran out of wall-clock budget). You assume it didn't finish and plan to complete the remaining work yourself. But inspection reveals the tree HAS been modified — the subagent performed real file operations before the interruption, and those operations were NOT the task it was assigned. It deleted 7 files that its prompt never mentioned, while leaving its actual assignment (rewriting a component) completely untouched.

**Why it happens:** Subagents sometimes "clean up" before doing their actual task — they see duplicate/stale files and delete them as a form of scope creep. Combined with an interruption (quota wall, model timeout), the cleanup happens but the real work doesn't. The `status=interrupted` summary makes no mention of the deletions because the subagent didn't get to write a summary about them.

**Signature in the delegation result:**
- Summary is generic/short and mentions the interruption reason.
- `git status --short` or `git diff --stat` shows file DELETIONS or rewrites that don't match the task scope.
- The files the task was SUPPOSED to modify are untouched.

**Recovery:**
1. **Run `git status --short` immediately** when a subagent reports `interrupted` or `timeout`. Don't trust the summary to mention everything it touched.
2. **Identify the collateral-damage files** — files modified/deleted that weren't in the task's stated scope. For each, determine: is it a stale duplicate (safe to delete) or an active file (must be restored)?
3. **Check for active references** before assuming a deletion is safe: `grep -rn "<deleted-file-base-name>" src/` — if zero matches across the entire source tree AND no dynamic imports reference it, the file is likely stale. If there ARE references, `git restore` the file.
4. **Complete the actual task** that the subagent was supposed to do — it was left untouched.
5. **Verify with the full gate** (build + grep) after both reverting/completing.

**Distinguishing from Pitfall 2 (timeout):** Pitfall 2's timed-out subagent did PARTIAL REAL WORK (80-90% of the actual task) and the parent just finishes the last 10-20%. Pitfall 12's interrupted subagent did COLLATERAL WORK (the wrong thing) and NO REAL WORK — the parent must undo the wrong changes AND do the real work from scratch.

**Surgical revert defense — avoid `git checkout -- <dir>` after collateral damage:** Wholesale revert RESTORES intentionally-deleted files too, resurrecting stale duplicates. Use `git restore <file>` per-file, then `git rm` files that should stay deleted. Full recipe: [`references/interrupted-subagent-collateral-damage.md`](references/interrupted-subagent-collateral-damage.md).

**Mechanical replacement defense — always run the grep gates YOURSELF:** After any "replace all X with Y" task, run `grep -c '<X-pattern>' <file>` and confirm the count is 0. A subagent reported success on a FontAwesome→Icon replacement but 16 misses remained — its replacement dict used wrong-shaped keys (`fa-bolt` instead of `fas fa-bolt`), making all `.replace()` calls no-ops. If your grep count is wrong, the mapping was off — do the replacement yourself.

## Pitfall 13 — Subagent reports success but a grep gate reveals systematic misses

**The trap (verified 2026-08-06):** A subagent completes a mechanical task (replace all FontAwesome icons with inline SVG icons) and reports `status=completed` with a success summary. The parent runs a verification grep (`grep -c 'fas ' file.jsx`) expecting 0, and gets 16. The subagent's replacement loop used the wrong key format (e.g., `fa-bolt` instead of `fas fa-bolt`), so NONE of its replacements matched, and the file was left with all original icons intact.

**Root cause:** The subagent built a mapping dict with the wrong shape — the keys didn't match the actual className strings in the file. Its "loop ran" (it logged "replacing...") but `str.replace(key, ...)` with a non-matching key is a no-op, and the subagent didn't verify with a post-loop grep.

**Defense — always run the grep gates YOURSELF after a subagent claims a mechanical replacement:**
1. After any "replace all X with Y" task, run `grep -c '<X-pattern>' <file>` and confirm the count is 0 (or matches the expected residual).
2. Run `grep -c '<Y-pattern>' <file>` and confirm the count matches the expected number of replacements.
3. If the count is wrong, the subagent's mapping was off — do the replacement yourself with a corrected script.
4. **Include explicit post-loop grep verification in the subagent prompt:** "After all replacements, run `grep -c 'fas ' <file>` and confirm it is 0. If not, your mapping was wrong — fix it before reporting done."

**Prevention in subagent prompts for mechanical replacement tasks:**
- "Use the FULL className string (e.g., `fas fa-bolt`) as the replacement key, not just the icon name (`fa-bolt`)."
- "After replacements, run `grep -c 'fas ' <file>` and report the count in your summary. A non-zero count means the mapping was wrong."

**Pitfall 13b — grep sentinels with regex metacharacters give FALSE "work missing" alarms (2026-08-11):** When verifying a subagent's claimed output with grep, patterns containing `?`, `.`, `(`, `+`, `[` are REGEX, not literal text — a bare `grep "students?limit=10000" file.jsx` treats `?` as "optional s" and returns 0 matches → false "AC not implemented" alarm on code that is actually correct. Two false alarms in one session, both resolved on re-check: (1) the `?` metacharacter; (2) running the grep from the repo root with a path that only resolves from a subdirectory (`grep frontend/src/...` run from inside `frontend/` misses the file entirely). **Rules:**
- Use `grep -F` (fixed-string) for sentinel checks containing metacharacters: `grep -Fc "students?limit=10000" file.jsx`.
- Run the grep from the correct directory (or use the full path relative to the repo root — confirm the path resolves with `ls` first).
- Before declaring "the subagent's work is missing," re-read the actual file — the marker is usually there.

**Pitfall 13c — Machine-validated output contract: validator rejection is a FORMAT error, fix = re-emit bare JSON (2026-08-11).** Subagent tasks with a JSON output contract (schema-validated final response) can come back rejected: `Response is not valid JSON: Extra data: line 1 column 3 (char 2)`. "Extra data" at a tiny column means the parser consumed the opening `{` and hit junk almost immediately — a ```json code fence or a prose prefix, NOT malformed JSON. (The task briefs themselves sometimes say "a ```json code fence is acceptable" — it usually is NOT for strict validators; they want ONLY the JSON document.) Recovery: re-emit the SAME content with zero fence and zero prose, no markdown. If the verification data to report (grep results, build tail) is no longer in context, re-run the gates from disk — grep the sentinels, `npm run build` — and report the FRESH real output; never reconstruct the report from memory. Verified 2026-08-11 (RiderScout carpool-4-tags Phase 2 subagent): first submission rejected for a fence; re-ran greps + build, re-emitted raw JSON, passed.

**Pitfall 13d — You verified the file you ASSUMED it would edit, not the file it actually made (2026-09-17).** I grepped `generate_interview_guide.py` for the new data layers, found none of them, and was about to report "the subagent never wired the new inputs at all" — a total-failure verdict. The child had instead created a SIBLING artifact, `generate_interview_guide_v2.py`, which consumed every one of them. My check was on the wrong path; the work was complete.

**Why it bites:** when you brief a task as "extend X", you picture X being edited. A capable child may judge that X is load-bearing (198 outputs already depend on it) and write a v2 beside it — a *better* engineering decision than the one you implied. Any grep against the assumed path then returns "nothing implemented", and the louder the verdict ("not a single layer is wired"), the more suspicious you should be: a child that produced no work at all is rarer than a child that worked in a place you didn't look.

**Rule — before declaring work absent, search by CONTENT, not by path:**
1. List files by mtime in the target directory, not just the one you expected: `sorted(dir.glob('*.py'), key=lambda p: -p.stat().st_mtime)[:14]`. A file created minutes ago IS the deliverable, whatever it is called.
2. Grep the NEWEST candidates for the distinctive markers, and only then conclude.
3. Treat a 3-referenced-file sweep as insufficient — sweep the directory.

This is the third instance in one session of the checker being the defect rather than the thing checked (the other two: a tool-inference guard that declared a verbatim-evidenced name unsupported; a location gate contradicting the field it reported). **When a verification step returns an implausible, sweeping negative — "none", "zero", "nothing implemented" — suspect the check before the artifact.** An implausibly clean negative is the signature of a broken query, and acting on it means discarding finished work.

## Acting on review subagent findings (fix → verify → deploy cycle)

When REVIEW subagents (spec compliance + code quality) return findings, the parent
agent fixes them directly — do NOT re-delegate fixes to another subagent. The parent
already has full file context and can make surgical patches faster than explaining
the codebase to a fresh child.

**⚠️ Never pre-announce a review verdict before its result has landed (verified
2026-08-01).** Reviewers run as async background delegations. Do NOT summarize,
declare, or act on a review's verdict (APPROVED / PASS / REQUEST_CHANGES) in a turn
where you are merely *anticipating* or *reasoning about* the expected outcome — the
verdict only exists once that delegation's completion message has actually re-entered
the conversation. Real incident (Pampa admin polish): the parent wrote "Wave A fully
approved — no changes needed" while analyzing the review it *expected*, then the real
quality-review result arrived as REQUEST_CHANGES with two Important issues, forcing a
public correction and a re-open of the task. Rule: a review's verdict is unknown until
its result message lands — quote the delivered verdict, never predict it. If you catch
yourself writing a verdict ahead of the result, stop and wait for the notification.
(This is the review-side mirror of Pitfall 7's timing-race guard: there you must not
declare a subagent's *work* absent before its writes flush; here you must not declare a
review's *verdict* before its result arrives. Both are "don't conclude from state that
is still in flight.")

**Workflow:**

1. **Read the FULL findings.** Summaries are often truncated. Use `read_file` on the
   saved summary path (shown in the delegation result footer) to get the complete
   findings table with file:line references.

2. **Triage by severity.** Fix CRITICAL and HIGH immediately. Batch MEDIUMs into the
   same commit. LOWs (code duplication, naming) can be deferred if they don't affect
   correctness — but note them in the commit message.

3. **Fix in the parent session.** Read each affected file, apply targeted patches.
   When multiple files share a pattern (e.g. photo upload validation duplicated in
   3 route files), extract a shared utility FIRST, then update all consumers — this
   is the "fix the class, not the site" principle.

4. **Generate migrations if schema changed.** Run `npx drizzle-kit generate` and
   verify the SQL is correct before proceeding.

5. **Build gate.** `npm run build` must pass clean before any verification.

6. **Targeted re-verification matrix.** Spin up a fresh test environment (Docker
   Postgres + API server) and run curl checks that test EACH fix specifically —
   not just a generic smoke test. Example: if the review flagged an IDOR on a photo
   endpoint, the matrix must include "member A cannot view member B's photo → 403".
   See `references/targeted-fix-verification-matrix.md` for the pattern.

7. **Commit with a descriptive message** listing all fixes by category (security,
   validation, refactoring). Then merge to staging and verify live.

**Parallelism optimization:** dispatch the NEXT phase's implementer while the current
phase's reviews are still running. The implementer works on new files; the reviews
read existing files. No conflict. When reviews report, fix findings in the parent
while the implementer continues. This saved ~10 minutes per phase cycle.

## Pitfall 14 — Parent session died mid-dispatch: results never re-enter, children were mid-work

**The trap (verified 2026-08-07, DesignCanvas 2-stage review):** A delegation batch is dispatched, then the PARENT session hits its tool-call limit / is killed before the children finish. The consolidated results never re-enter the conversation — not because the children failed, but because the parent never received the completion message. If you simply continue (or wait), you never get the reviews.

**Diagnosis:** the live transcripts on disk show real progress but no completion:
```
~/.hermes/cache/delegation/live/<delegation_id>/task-<N>.log   # tail shows read_file/search_files streaming, no 'final' line
~/.hermes/cache/delegation/live/<delegation_id>/manifest.json  # per-task status: 'running'
```
Check the manifest: tasks stuck at `status: running` with a recent `result |` timestamp = the children were mid-work when the parent died and their summaries will never arrive.

**Recovery — re-dispatch the batch with the SAME goals/context:** This is not a child-side failure (Pitfalls 4/5) and not a timeout (Pitfall 2) — the work simply needs to be re-run. Re-issue `delegate_task` with identical `goal`/`context` (a fresh delegation id), then act on the new results. Do NOT try to reconstruct findings from partial transcripts — you'd miss half the review. Confirmed on DesignCanvas: first dispatch (deleg_93417a7e) interrupted at the tool limit and never returned; re-dispatching identical tasks (deleg_b9eac13e) completed cleanly and produced the full reviews.

**Prevention:** if the session is anywhere near its tool-call budget, dispatch review batches EARLY (the reviews are read-only and run while you do other work), and check `process(action='list')` / manifest before ending a turn that depends on delegation results. Same discipline as the "never pre-announce a review verdict" rule — a verdict you can't see hasn't happened.

## Pitfall 15 — Stale duplicate batch: a re-dispatched/second review arrives AFTER you already fixed and shipped

**The trap (verified 2026-08-07, DesignCanvas):** Two review batches get dispatched close together (first at 10:25, a second near-identical re-dispatch at 10:29) against the SAME pre-fix commit. You act on the first batch's findings — fix, commit, deploy. The second batch's consolidated results then re-enter the conversation ~24 minutes later. Both batches reviewed the same `git` state, so most of batch #2's findings are DUPLICATES of findings you already fixed and shipped. The danger is blindly treating the second batch as fresh truth: you'd re-fix already-fixed items, churn the tree, and burn an entire deploy cycle on work that's done.

**Signature that a batch is stale:**
- The subagent's own text anchors it to an OLD state: "prod is still at commit `640f92d`", "the tree was actively mutating mid-review", "the working tree delta is uncommitted" — i.e. it explicitly says it did NOT see your fixes.
- The dispatch timestamp predates (or nearly matches) the batch you already acted on, and the task goals/context are identical.
- The findings' file:line references describe the PRE-fix code (e.g. it flags "no `app/error.tsx`" or "lint fails" when you know you added the file / lint passes).

**Defense — triage the stale batch, don't re-execute it:**
1. **Cross-reference every finding against the fix commit first.** Read the batch's full summaries (they're saved to disk — `read_file` the footer paths), build a checklist of its H1/H2/…/L-items, then check each against the current working tree / `git log -1`. Already-fixed → mark done, move on.
2. **Mine for the ~2-3 genuinely NEW items.** A stale batch still has value: reviewers see things the first batch didn't emphasize. In the DesignCanvas case, the stale batch surfaced: a real click-to-deselect regression risk the spec reviewer flagged, the CSS-injection vector in `injectTweaks`, an autosave race, and the IME/composition guard — none of which the first batch led with.
3. **Verify the new items against live behavior before fixing** — the click-to-deselect "regression" was confirmed real via synthetic DOM events in the browser, not taken on the reviewer's word. (And note the test-targeting trap: synthetic events must dispatch on the SHELL element, not the outer wrapper, or you get a false negative.)
4. **Do NOT re-dispatch the stale batch, and do NOT revert/re-apply its full list.** Fold its new items into the current commit cycle; treat duplicates as confirmation that the first fix was right.

**Prevention:** when re-dispatching a review batch after a parent interruption (Pitfall 14), add an explicit instruction to the re-dispatch: *"If the working tree has already been fixed/deployed since your batch was requested, anchor your review to the CURRENT committed state and say so in your summary."* And before acting on any late-arriving batch, check `git log --oneline -5` + `git status --short` — if the tree moved since dispatch, assume stale and triage.

## Pitfall 19 — Research-paralysis timeout: subagent burns the whole budget READING, writes nothing

**The trap (verified 2026-08-13, a frontend spellcasting task):** A frontend subagent
hit the 1800s wall with 22 API calls and **zero files written**. Its live transcript shows
read-only calls the entire run — `read_file(styles.css)`, `read_file(api.ts)`,
`read_file(tsconfig.json)`, `search_files` for CSS classes and component conventions — but
never a single `write_file` or `patch`. It "completed" the planning in its head, kept
gathering context, and timed out before starting the implementation it was dispatched to
do. The parent had already detected the stall mid-run and implemented the entire frontend
directly, so the timeout was a non-event — but only because the parent didn't wait for it.

**Distinguish from the other failure modes:**
- vs Pitfall 1b (quota wall): that's a 429 error string, low call count; this is a healthy
  call count of pure read-only work.
- vs Pitfall 2 (timeout with 80-90% done): that leaves partial files on disk; this leaves
  **zero files** — the tree is untouched.
- vs Pitfall 7 (hallucination): that reports fabricated success with no files; this reports
  timeout honestly with no files.
- Signature: `status=timeout`, high-but-moderate api_calls (15-30), transcript = reads only,
  `git status` clean of the task's files.

**Why it happens:** the subagent treats the task as a research problem (understand the codebase
thoroughly before writing) and never reaches the writing phase inside its budget. Especially
common for UI tasks in unfamiliar codebases where the model over-invests in "convention
discovery" — reading styles.css, component patterns, and API-client shapes it could have
grokked from the brief.

**Recovery:**
1. **Detect early, don't wait for the wall.** If a transcript is N minutes in, has only
   `read_file`/`search_files` calls, and the task files are untouched on disk — take over
   yourself and implement directly. A well-specified task from a good brief does not need
   20 minutes of context-gathering; the parent already has the context.
2. **Do NOT re-dispatch the same task unchanged** — the same model will repeat the same
   research loop. Implement inline in the parent session (fastest for well-specified work)
   or re-dispatch with a hard write-deadline in the prompt ("start writing files within your
   first 5 tool calls; do not read more than 3 files before your first write").
3. **Verify the tree is truly untouched before treating it as a non-event** — `git status
   --short` should show only the parent's own changes (Pitfall 12's collateral-damage check
   reversed: confirm nothing landed that you need to reconcile).

**Prevention in subagent prompts for implementation tasks:** add an explicit
"WRITE FIRST" instruction for tasks where the deliverable is code: "Begin implementation
within your first few tool calls. Read files only as needed to write correct code; do not
spend more than a few calls on context-gathering before your first `write_file`." This is
the implementation-side mirror of Pitfall 16's "emit intermediate findings as you go" —
both prevent losing all work to the wall.

## Pitfall 16 — Review subagent times out with HIGH api_calls: mine the transcript, sweep the junk files

**The trap (verified 2026-08-08, a graphics-review pass):** A REVIEW subagent hits the 1800s wall with **42 API calls** and no summary (`status=timeout`, `(no summary — ...)`). This is NOT Pitfall 5 (rate-limit pileup — that signature is LOW counts, 7–12) and NOT Pitfall 4 (instant death). It's a **deep-investigation timeout**: the reviewer burned its whole budget on a rabbit hole and died mid-inquiry without ever emitting a verdict.

**What you lose if you just re-dispatch:** the transcript is not empty — it contains the reviewer's *intermediate probe conclusions*, which can be the most valuable findings of the whole review. In that case the timed-out reviewer had written GPU probe harnesses and its tail showed: `REVEAL-ORIENTATION {southWest_alpha: 255, ...}` and a think line *"I've confirmed the reveal mask is Y-mirrored in the actual shader"* — a real MAJOR bug that the parent's own all-revealed E2E could NOT catch (mirror of an all-ones mask is all-ones). Salvaging the transcript turned a "failed" review into a shipped fix.

**Recovery:**

1. **Read the live-transcript tail** (`.../delegation/live/<id>/task-0.log`) — not just the last 20 lines; grep for `think |`, `probe`, `found`, `I've confirmed`, `concluded` to pull out mid-investigation conclusions and probe outputs.
2. **Sweep the repo for probe junk.** Deep-investigation reviewers leave harness files behind (`.p7-flip-check.html`, `p7-raw-check.ts`, `p7-angle-check.html`, …). Run `git status --short | grep "??"` and `ls <repo-root> .p7-* apps/web/p7-* scripts/.p7-*` style globs; `rm` the untracked probes before committing. (This is the reverse of Pitfall 12 — there the subagent deleted YOUR files; here it CREATED junk.)
3. **Do NOT trust the transcript's probe outputs at face value.** The reviewer's own probes were partly unreliable — it wrote "All probes read fogged-everywhere, which suggests the DataTextures may not be sampling correctly" — which CONTRADICTED the live app. Treat transcript probe numbers as *leads*, then re-derive the truth yourself: paper math against the actual source (write convention vs shader UV vs `flipY`), then a live partial-reveal E2E with pixel ground truth.
4. **Re-dispatch only if the transcript has no salvageable signal** (it died on setup, not investigation). If it was mid-investigation, finish the review inline yourself — you now have the leads, and re-dispatch burns another 30 min for findings you can already see.

**Prevention:** for review dispatches, tell the subagent to emit intermediate findings *as it goes* (e.g. "write your probe conclusions to `REVIEW-NOTES.md` incrementally") so a timeout never loses the reasoning. And remember the parent's E2E blind spot: **test-data degeneracy hides bugs** — an E2E that reveals ALL regions can't detect mask orientation errors; verify with a partial pattern.

Full case with transcript excerpts, junk-file list, and the verified partial-reveal fix:
[`references/timed-out-reviewer-transcript-salvage.md`](references/timed-out-reviewer-transcript-salvage.md).

## Pitfall 18 — Self-contradictory delegation spec: resolve toward the normative part, FLAG every deviation

**The trap (verified 2026-08-13, a shared types module):** A delegated task spec can
contradict itself. Two live examples from one task: (1) a spot-check test expectation
("Wizard 20 → 9:{3,0}") contradicted the authoritative PHB table given in the SAME spec
(`20:{...9:1}` — 9th-level slots never exceed 1); (2) a test instruction said to treat
`"Wiz"` as an unknown class while the spec simultaneously REQUIRED `"wiz" → "Wizard"`
normalization. Neither can be implemented literally; a subagent that doesn't notice ships
a failing test suite, and one that "fixes" the spec silently loses a requirement.

**Resolution protocol (implementer side):**

1. **Identify the normative part.** Explicitly-declared authoritative tables, required-
   behavior lists, and exact export names outrank illustrative examples and spot-checks.
2. **Implement toward the normative part.** Adjust the contradictory example/test to a
   consistent interpretation (e.g. swap the "unknown class" test input for a genuinely
   unrecognized string like `"NotAClass"`).
3. **FLAG every deviation in the final summary** — what contradicted what, which side you
   followed, and how you adjusted the test. Never silently pick a side, and don't block
   on the contradiction when the resolution is unambiguous.

**Parent side (spec-writing + intake):**

- Never restate a table's expected values from memory in example assertions — quote the
  exact row you mean, or have tests derive expectations from the declared authoritative
  source.
- When a subagent's summary flags spec deviations, audit each one against the plan before
  merging — a flagged deviation is a signal the PLAN needs amending, not necessarily that
  the subagent went rogue.

## Pitfall 20 — Timeout spent WAITING: the child finished the build, then blocked on its own long job

**The trap:** an implementation subagent builds the deliverable, proves it end to end on a small
sample, and then launches the FULL run **in the foreground** and watches it. Its wall clock is
consumed by waiting, not working, so it hits the timeout with no summary and a moderate-to-high
api_calls count. Read as a failure, this looks like the whole task was lost.

**Distinguish from its neighbours:**
- vs Pitfall 16 (reviewer, mid-investigation): here the child is *idle*, not investigating; its
  tail shows a foreground job streaming progress, not `think`/probe lines.
- vs Pitfall 19 (research paralysis): that writes NOTHING; this one has already written the whole
  deliverable and verified it on a sample.
- vs Pitfall 2 (timeout with partial code): that needs you to finish the remaining 10-20% of the
  code; here the code is COMPLETE and only the batch execution is missing.
- Signature: the transcript contains a successful sample run whose output the child then read and
  judged, followed by one long foreground command and repeated wait/timeout cycles on it.

**Recovery — salvage the build, re-run only the job:**

1. Read the transcript tail. If it shows the child evaluated a sample output and then waited on the
   full run, the deliverable is done and only the run is outstanding.
2. Verify the artifacts on disk (script + sample outputs) before concluding anything. Do NOT
   re-dispatch the build — a re-dispatch re-does finished work and may overwrite verified output.
3. Re-run ONLY the long job, from the parent, as a **tracked background process**. Never foreground,
   and never inside a subagent — a child's wall clock is the wrong place for a job measured in
   tens of minutes.
4. **Before relaunching, prove no instance is already running.** A bare `pgrep -f <name>` run
   inside a shell matches its own wrapper and can read as empty, which is how a second writer gets
   started. Use `ps -eo pid,etime,args | grep <name>` — it lists the real PIDs AND how far along
   each one is, so you can tell a live run from a dead one.
5. If two instances ARE running, kill the LESS ADVANCED one immediately. Two writers on the same
   output paths — and especially on a single JSON index written at the end — interleave their
   results and corrupt the batch.
6. If the job writes its index only at the end, a kill loses the whole run. Per-item artifacts
   (one file per target) are what make a long run salvageable; prefer a design that writes as it
   goes, and say so in the brief.

**Prevention in the delegation brief:** state explicitly that the long batch is NOT the child's to
run — "prove the pipeline on a small sample, print one complete output for review, then hand back
THE EXACT COMMAND for the full run; the parent executes it as a background process." A child that
cannot start a long job cannot block on one.

## Overlap note (for the curator)

Pitfalls 1–2 overlap with `subagent-driven-development`'s existing timeout/quota guidance
and its `references/subagent-verification-pitfalls.md` / `references/delegate-task-failure-catalog.md`.
That skill is manually authored (created_by=None) and could not be patched directly, so the
durable learnings live here. If `subagent-driven-development` becomes editable, fold
Pitfall 1 (403-as-completed) and Pitfall 3 (dist-staleness) into it and consider merging.
