---
name: saas-starter-bundle
description: "Use when packaging an internal tool into a starter bundle."
version: 1.0.0
metadata:
  hermes:
    tags: [packaging, saas, white-label, distribution, de-personalization, verification]
    related_skills: ["extract-local-package", "credential-hygiene", "env-var-audit"]
---

# Packaging an Internal Tool into a Distributable Starter Bundle

Turn a live, single-tenant, working system into an archive someone else can unzip, configure and run
— and that the owner can build a platform on. The deliverable is a **verified** archive, not a
description of one. Use for "bundle the code so I can build this as a real platform/SaaS", "package
this up so I can download it", or preparing an internal tool for a second user, customer or fork.

## Procedure

### 1. Define the product by ENTRY POINTS, not by directory

Do not dump a working directory. Working trees accumulate scaffolding that is not the product.

- Read the scheduler/cron definitions (or the runbook) and extract **every command and script the
  system actually invokes**. That set is the product's entry points — not what looks important.
- Compute the **import closure**: parse each entry point's `import`/`from` statements, resolve
  against the local module names, and walk transitively. Ship that closure.
- Expect the closure to be a tiny fraction of the tree. A working deployment held **1,239 one-off
  dated scripts out of 2,036 Python files**; the real pipeline was 18 files.
- Include the server and the data layer even if the scheduler never imports them — the API, the
  client and the DB are part of the product surface.

**Pitfall — a script the docs name may not exist at the path the docs imply.** Resolve entry points
against the real filesystem and report misses loudly instead of silently shipping a partial set. A
runbook saying `python fetch_bands.py` when the script lives in `scan/` is the normal case whenever
the runbook also `cd`s first.

### 2. Exclude by CATEGORY, not by file

Everything below is out by default. State the exclusions in the bundle's README so the recipient
knows what is missing and why.

| Category | Examples |
|---|---|
| Credentials | `.env`, API keys, tunnel tokens, cloud account ids |
| Live state | the database, seen-jobs caches, completion markers |
| Generated artifacts | resumes, letters, guides, exports — the personal payload |
| Personal data | the user/candidate profile, truth-base files, contact details |
| Scaffolding | one-off dated scripts, backups, `.bak`, `.venv` |
| Operational history | run logs, run archives, dated incident notes |
| Build artifacts | `__pycache__`, `*.pyc` — see step 8, your own tests create these |

### 3. Ship data files as SHAPE-ONLY examples — plus one runnable minimal file

Replace each excluded data file with an example that keeps the **keys and nesting** and swaps every
value for a type marker (`<string len=42>`, `<number>`, `<bool>`, `[]`). That documents the schema
without transporting anyone's data.

A shape-only file is usually **not runnable**. Also ship one small, fully-populated **minimal**
profile so the README quickstart actually executes. Ship both and say which is which.

### 4. Make paths portable — resolve from an env var, default from `__file__`

Grep for the deployment's absolute path before packaging. One path constant is typically copy-pasted
across a dozen files; in a live system it was hardcoded in **12 files**, which alone made the bundle
undeployable anywhere else.

```python
BASE = pathlib.Path(os.environ.get("APP_HOME", str(pathlib.Path(__file__).resolve().parent)))
```

- Every deployment path becomes an env var with a sane default: home, port, host, env-file path,
  data/attachments dir.
- **The default must be correct for the file's DEPTH.** A top-level module in the app dir wants
  `.parent`; a module in `app/<subdir>/` wants `.parent.parent`. Getting one wrong silently points
  the default at the wrong directory — the app still starts, then reads a database that is not
  there. Decide per file; do not copy one expression everywhere.
- Make the launcher derive its own directory too
  (`HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`) rather than hardcoding a path.

### 5. De-personalize by finding FUNCTIONAL literals, not text hits

A raw grep gives a misleading count — most hits are comments and docstrings. Triage every hit:

- **Functional literal (must fix).** The owner's identity embedded in behavior. Real examples: a
  disqualifier fact hardcoded inside scoring logic, and **document parsers keyed on the literal
  string of the owner's name** (`s.startswith("<Owner Name>")`). These are defects — they silently
  break for any other user.
- **Comment/docstring mention (cosmetic).** Still scrub it — a starter bundle should read as a
  product — but it does not change behavior.

Fix functional literals by reading from the profile/config, not by swapping one string for another.
Verify the app still boots afterwards.

**When a value is rendered in a template, inject it at serve time** (read the HTML, substitute the
profile value, return it) rather than shipping client-side JS that fetches it — one build, any user,
no client state.

### 6. Generate the schema from the live DB, then EXECUTE it

Dump `sqlite_master` / `pg_dump --schema-only`, then make it idempotent
(`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).

**Pitfall — a dumped schema is frequently invalid SQL.** A `sqlite_master` dump has **no terminating
semicolons**, and joining statements with a separator yields `near "CREATE": syntax error`. Run it
from an empty database **twice** and confirm the column count is identical both times. Never ship a
schema you have not executed.

### 7. Verify by EXTRACTING ELSEWHERE and booting it

Compiling in place proves nothing about the archive. The real check:

1. Create a fresh empty directory **outside** the bundle.
2. Extract the archive into it.
3. Follow the bundle's own README steps verbatim: venv, install, apply schema, copy the minimal
   config, start the server.
4. Hit the endpoints and assert on **content**, not just status — e.g. that the page renders the name
   read from the config file, which proves the profile wiring works rather than that a page exists.
5. Only then hand over that exact archive.

### 8. Scan the ARTIFACT for secrets and personal data — after your own test runs

Run the scanner on the bundle directory as the final step, because your verification runs leave
`__pycache__` directories containing the pre-scrub bytecode. Use separate pattern sets for
credentials and for personal data, and treat any remaining credential hit as a hard stop.

`scripts/verify_bundle.py` in this skill does both scans plus a real compile check; run it against
the bundle before packaging and again after extracting.

### 9. Package and hand over

- Produce **both** `tar.gz` and `.zip` — recipients differ.
- Report absolute paths and the uncompressed file count.
- **Ask before exposing the archive on a public URL.** Serving a download from an existing public
  tunnel publishes the source to anyone with the link. State the tradeoff and let the owner choose;
  never do it unprompted.

## Pitfalls

**A verification command whose exit code you did not check is not verification.** `cmd | head && echo OK`
reports the status of `head`, which is always 0 — the check prints OK for a file that failed to
compile. Assert on the real command: `py_compile.compile(path, doraise=True)`, `set -o pipefail`, or
read `$?` directly. This masked a genuine syntax error in a shipped bundle.

**Automated edits break syntax in ways a replace never shows you.** Inserting a line before the
first matching import can land it **above `from __future__ import annotations`**, which is a
SyntaxError. After every scripted edit pass, re-compile every file with real exit codes before
trusting any later result.

**Enumerate your download/exposure surface BEFORE putting anything on a public URL.** A tunnel
publishes every route. Test the document endpoints unauthenticated: a live "internal" dashboard
served a resume `.docx` — containing a phone number, personal email and home city — to a plain
`curl` with no credentials, keyed only by a guessable record id. Any internal tool being exposed or
productized needs its `FileResponse`/download routes auth-gated first.

**A starter bundle must not hardcode one tenant.** If the code cannot serve a different user without
editing code, it is a snapshot, not a platform. Steps 4 and 5 are that difference.

**Text substitution mangles as easily as it fixes.** A broad "replace this name" pass can land
inside an unrelated absolute path and produce nonsense (`/Users/<name>/` → `/Users/the user/`). After
scrubbing, re-read the changed lines instead of trusting the replacement count.

**A guard that fails is not proof the work failed.** If a reconciliation reports an implausible
result for the bundle ("no files found" across the whole tree), suspect the path construction in the
checker before the data — the correct files are frequently present under a differently-composed name.

## Checklist

- [ ] Product = import closure of the real entry points; scaffolding excluded
- [ ] No credentials, database, generated artifacts, or personal data in the bundle
- [ ] Data files shipped as shape-only examples **plus** one runnable minimal config
- [ ] Every deployment path overridable by env var, default derived from `__file__` at the correct depth
- [ ] Functional owner-identity literals replaced with config reads; app verified to boot
- [ ] Schema executed from empty, twice, with matching column counts
- [ ] Archive extracted elsewhere and booted following its own README
- [ ] Final secret/PII scan run on the artifact after all test runs (no `__pycache__`)
- [ ] Both `tar.gz` and `.zip` produced; public-URL exposure offered, never assumed
