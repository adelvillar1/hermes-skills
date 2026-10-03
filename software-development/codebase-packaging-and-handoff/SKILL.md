---
name: codebase-packaging-and-handoff
description: "Use when packaging a codebase into a deliverable archive."
version: 1.0.0
---

# Codebase Packaging and Handoff

Turning a working system into something another machine can receive: a starter bundle, a full project
snapshot, a portability export, or the input to building a product. The work is not `tar` — it is
deciding what the project IS, removing what must not travel, making it runnable elsewhere, documenting
it from evidence, and proving the delivered artifact works.

## Step 1 — Decide which artifact the user actually asked for

Users conflate these; state your read before building:

- **A curated starter** — the canonical pipeline only, cleaned and de-personalized, ready to fork into
  a product. Small (hundreds of KB).
- **A full snapshot** — every source file, all data, all documents. Large (tens of MB).

Build whichever they asked for, and say plainly which one it is. When they ask for "the whole
codebase," that is the snapshot — do not hand them the curated subset and call it complete.

## Step 2 — Find the project by import closure, not by eye

For a starter, do not guess which files matter. Extract the entry points from the scheduler/job
definitions (the commands those jobs actually invoke), then walk the import graph:

```python
# parse Import/ImportFrom via ast; resolve bare module names against local .py stems; recurse
```

This reliably reduces thousands of files to the working set and, more importantly, proves what the
system runs. It also surfaces broken references — a "canonical script" named in a job prompt that no
longer exists at that path is a real finding worth reporting.

## Step 3 — Draw the boundary from evidence

**A working directory is not a project.** A profile/repo root accumulates the harness's own runtime
side by side with the code: virtualenvs, session stores, caches, sandboxes, binaries, shared skill
libraries. In one case these outweighed the real content three to one.

Measure before deciding (`du -sh */`, plus a file-type histogram), then exclude:

- environment/dependency dirs (`.venv`, `node_modules`), build artifacts (`__pycache__`, `*.pyc`)
- runtime state (`sessions/`, `memories/`, caches, sandboxes, workspaces, logs)
- machine/site-specific binaries and any bundled tool runtimes not belonging to the project
- editor/OS debris, lock files, and database `-wal`/`-journal` sidecars

Keep the project's own data deliberately (database, generated documents, configs) when it is a
snapshot — but see Step 10 for the warning that must accompany it.

## Step 4 — Exclude credentials BY NAME, then sweep for shape

Run **both** passes; neither alone is sufficient. The full rules live in `credential-hygiene` — the
short version:

1. Exclude credential and state files by filename (`auth.json`, `auth.lock`, `credential*`,
   `*token*.json`, `config.yaml`, `profile.yaml`, `.env*`, `.netrc`, `*.pem`, `*.key`, `.git/config`).
2. Sweep the **finished archive** (not the source dir) for credential-SHAPED strings — a quoted run of
   80+ chars with no spaces. Keyword patterns (`sk-`, `Bearer`, `API_KEY=`) find nothing, because a
   token is not a keyword: it is an opaque string.

Use `scripts/audit_archive_secrets.py` for pass 2 — it reads the built tarball/zip, reports hits by
file, and flags any credential file that slipped through. Run it after every change to the exclusion
list: an audit that passes *because* a file was excluded is only valid while the exclusion holds.

## Step 5 — Make it runnable elsewhere

A snapshot that only runs on the original host is not a handoff. Find and fix every absolute path:

- Replace hardcoded roots with an env-overridable constant defaulting to the app's own directory:
  `BASE = Path(os.environ.get("APP_HOME", str(Path(__file__).resolve().parent)))`.
- **Mind the depth.** A file at the tree root needs `.parent`; a file one level down needs
  `.parent.parent`. Getting this wrong silently points the app at the wrong directory — verify by
  resolving both from their real locations.
- Also parameterize port, host, the `.env` path, and any attachments/assets directory.
- Make the DB schema executable and **idempotent** (`CREATE TABLE IF NOT EXISTS`), and ship an
  `.env.example` with keys only, never values.

## Step 6 — De-personalize, then declare what remains

**Hardcoded identity is a defect when it is load-bearing, not just when it is ugly.** Three shapes to
hunt, in priority order:

1. **Facts inside logic** — a candidate/target constraint written as a literal in a scoring or
   filtering branch. Move it to configuration read from the profile/record.
2. **Parsers keyed on a literal name** — code that recognises a document header by comparing to a
   person's name breaks for every other user. Resolve the name from data at call time.
3. **Prompt text carrying identity** ("you are rewriting <name>'s resume"). Drive it from the profile.

Cosmetic occurrences (page titles, docstrings, comments) matter less, but scrub them in a starter —
they signal an unmaintained fork. Then rerun the sweeps and report the residue honestly.

## Step 7 — Make the archive self-consistent

A README that references a file the archive does not contain is a first-run failure. Derive the
missing pieces or stop referencing them — and prefer generating the missing file over deleting the
line, since both a schema and an env template are genuinely useful to a recipient.

Generate the documentation FROM the tree so it cannot drift:

| Document | Derivation |
|---|---|
| Directory/file map | walk the staged set; count files per directory and per extension |
| Script inventory | non-dated scripts in the pipeline dirs, each with its own docstring/first line |
| Scheduler spec | the job definitions **verbatim** — prompts are the executable specification |
| Operations | ports, services, external access, model routing, known landmines |
| Manifest | full file listing with sizes |

Prefer including scheduler prompts verbatim over paraphrasing them; they describe the pipeline more
accurately than any summary.

## Step 8 — Verify by extracting and running it

The build succeeding proves nothing. Extract the artifact to a **clean directory** and run its own
documented quickstart: create the database, copy the example config, boot the service, hit its
endpoints. Report what the run returned.

If the app hardcodes a port another instance already holds, do not stop production to test. Import the
archived module and drive its app object on a free port instead — same code, no conflict:

```python
sys.path.insert(0, extracted_root)
import server                       # module level only; the __main__ guard prevents binding
uvicorn.run(server.app, host="127.0.0.1", port=<free>)
```

### A check that cannot fail is worse than no check

Each of these produced a green result while the artifact was broken:

- **The exit code you tested was not the command's.** `cmd 2>&1 | head -3 && echo OK` binds `&&` to
  `head`, which always succeeds — so a file with a `SyntaxError` printed `OK`. A pipe discards the
  exit status of everything upstream: never let a pass/fail decision rest on the last stage of a
  pipeline. Test the command's own status explicitly.
- **Building is not running.** A schema assembled by string-joining looked right and was invalid the
  moment anything consumed it (statement list joined without terminating semicolons). Execute every
  generated artifact once, from empty, before shipping it.
- **A check that derives the target differently from the writer lies.** A verification loop that
  rebuilt a filename by prefixing an id that already carried the prefix reported "no file" for files
  present the whole time. **An implausibly sweeping negative — everything missing, a whole batch
  failing — means suspect the check first.** Build the path the way the writer does, or read it back
  from the record of truth.
- **A generated script bakes in the authoring machine.** An unquoted heredoc expands `$(...)` and
  `$VAR` at *creation* time, so a helper meant for someone else's machine pointed at a path only the
  author had. Quote the heredoc (`<<'EOF'`) when the body must survive verbatim, and test generated
  scripts where the authoring paths do not exist.

**Prove each check can fail** by running it once against a known-bad input before trusting it. A check
you have only ever seen pass is untested — the same rule as "a guard you have not watched fire is not a
guard," applied to your own verification tooling.

## Step 9 — Deliver it to the recipient

A hosted agent container usually has **no inbound port**, so a file on disk is unreachable from the
user's machine. If the host already runs a public service (tunnel, reverse proxy), add a token-gated
route to that app rather than standing up a new listener.

- Gate on a token **file** so enabling is writing it and disabling is deleting it — a one-command off
  switch the user controls.
- Return **404, not 403**, on a bad token, so a prober cannot confirm the route exists.
- Guard path traversal on the **resolved parent**, not by matching `..` in the raw string.
- Compare tokens with a constant-time function.
- Many edges (Cloudflare included) 403 a non-browser `User-Agent`; tell the user to pass one, and do
  not read that 403 as the route being broken.
- **Publish `sha256sum` values** and verify the route end to end yourself: download it, `cmp` the
  bytes against the file on disk, confirm they match, and give the recipient the exact command.
- Expect the route addition to require a service restart — say so, because the dashboard may be down
  for a minute and the user may be looking at it.
- State the exposure plainly: the archive is reachable by anyone holding the URL. Offer to remove the
  token when they are done.

## Step 10 — Warn about what the snapshot contains

A full snapshot carries real personal data: a live database, a real profile, and often thousands of
generated documents with contact details. Say so before they share it, and keep the curated starter
available as the shareable alternative.

## Pitfalls

- **Do not archive a working directory wholesale.** Decide the boundary from measurements.
- **Do not ship the harness's credentials with the project.** Filename exclusion first, shape sweep
  second, both every time.
- **Do not keep per-session run-logs and dated one-off scripts in a curated starter.** They are
  operational history, not product. Keep them in the full snapshot if one is being built.
- **Do not claim "it works" because it built.** Extract it, run the documented quickstart, report the
  actual output.
- **Clean up artifacts your own verification created** inside the thing you are packaging — test runs
  leave `__pycache__` and `.pyc` files carrying the exact strings you just scrubbed.
