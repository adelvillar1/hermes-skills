---
name: credential-hygiene
description: Move/redact secrets; scan tracked files for leaks.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [security, secrets, git, credentials, redaction]
    related_skills: [credential-safe-api-scripting, cross-boundary-evidence-tracing, aes-256-gcm-encryption]
---

# Credential Hygiene

A repo is only as leak-proof as its tracked files. Plaintext secrets surface in config files, recap docs, test fixtures, and agent tool output; the job is to get them into a gitignored store, prove nothing sensitive is tracked, and never echo a value while doing it.

## When to use

- Tool output surfaced a plaintext key/PAT — treat that as a signal to remediate, and keep the value out of your message text.
- User asks to relocate secrets out of a config file (e.g. "put into a git ignored CLAUDE.local.md").
- Audit a repo for committed secrets before a push, share, or handoff.
- A tracked file needs redaction because a token prefix leaked into git history.

## Detect: where secrets hide

Search patterns worth scanning for:

```text
github_pat_[A-Za-z0-9_]+   ghp_[A-Za-z0-9]+   sk-ant-api03-  sk-proj-  sk-kimi-
AKIA[0-9A-Z]{16}           xox[baprs]-[A-Za-z0-9-]+   whsec_[A-Za-z0-9]+
50eb[0-9a-f]{20}\.[A-Za-z0-9]+   postgres://user:pass@   redis://:pass@
```

Hideouts: `CLAUDE.md` / global agent configs, `docs/recaps/*.md`, `.env` files that got committed, test fixtures, shell scripts with hardcoded tokens. Grep the repo (`search_files`), and remember tool output reading those files is itself a leak vector — the value ends up in a transcript.

## Map the landscape before touching anything

1. `git -C <dir> rev-parse --is-inside-work-tree` — the file may not even be in a repo (`~/.claude/CLAUDE.md` typically isn't; "git ignored" then only means something inside a repo).
2. Find the existing gitignored store: `git check-ignore -v CLAUDE.local.md` proves the convention exists and where the rule lives (e.g. `.gitignore:9`).
3. Check the tracked `CLAUDE.md` for real VALUES vs env-var NAMES only — names are fine, values are not.

## Migrate safely — values never pass through your message text

Write a Python script that READS the values from the source file at runtime. Your command/script text contains only regex patterns; the secret values exist only in file I/O and are redacted before printing.

- `scripts/migrate-secrets.py` is the reference implementation (source file → gitignored destination, redacted stdout, count verification).
- Verify by count after the move: `grep -cE '<patterns>' <source>` must be `0`, the destination must hold `N` moved lines.
- Confirm the destination is ignored: `git check-ignore -v <dest>` and `git status --short` must NOT list it.

## The definitive scan: tracked files only

A working-tree grep finds secrets in IGNORED files (e.g. `CLAUDE.local.md` holds keys by design) and cries wolf. The only check that answers "would this leak via git" scans tracked files:

```sh
git ls-files -z | xargs -0 grep -lE '<patterns>'
```

Use `scripts/scan-tracked-secrets.sh` — it scopes to the repo root, accepts an extra pattern, and exits 1 on hits.

**Pipeline exit-code trap:** truncating a grep pipeline with a line limit (e.g. `grep ... | head -5`) masks grep's exit status, so `&& echo CLEAN || echo DIRTY` silently never fires the DIRTY branch even on empty grep. Capture hits into a variable and test it instead.

## Triage a found token: full or truncated?

Compare lengths against the known value in the gitignored store: `len(found)` vs `len(known)`. A short prefix plus a literal `...` (e.g. 21 chars of a 93-char PAT) is a partial disclosure — not directly usable, but still worth redacting and mentioning.

A prefix in git history is PERMANENT on shared branches (rewriting history is destructive). Redact the working file, commit the fix, and recommend rotation — do not attempt history rewrites for it.

## Redact & commit

- Replace the value with a neutral reference ("a `github_pat_` token, prefix only ever referenced here").
- Commit on the development branch (docs/recap convention), never directly on staging/main.
- Re-run the definitive tracked scan after the fix; expect CLEAN.

## Rotation

If a full value was read by any agent, sat in plaintext on disk, or a prefix entered git history, say plainly: **the agent cannot rotate the credential** — give the exact URL (github.com/settings/tokens, provider console) and let the user decide. Only a prefix leaked → moderate risk, still recommend rotation.

## How to Run

1. `bash scripts/scan-tracked-secrets.sh` inside the repo → expect `CLEAN — zero matches`.
2. `git check-ignore -v CLAUDE.local.md` → shows the `.gitignore` rule proving the store is ignored.
3. `grep -cE '<patterns>'` counts to prove migration (0 in source / N in destination).
4. `read the SKILL.md for '`credential-hygiene`' via your harness's skill loader` to load this skill.

## Extract one credential into a shell variable (no bulk echo)

Scripts sometimes need a single credential from the gitignored store (e.g. `STAGING_PG_PASSWORD` for a drift script). Extract it in ONE tight pass into a shell var; never print it:

```sh
# Markdown-table env-var reference inside CLAUDE.local.md ("| `VAR` | value | …"):
PW=$(awk -F'|' '/`STAGING_DB_PW`/ {gsub(/[ `]/,"",$3); print $3; exit}' CLAUDE.local.md)
# Plain KEY=VALUE lines:
PW=$(grep -m1 '^STAGING_DB_PW=' CLAUDE.local.md | cut -d= -f2-)
# Use it without storing or echoing:
STAGING_PG_PASSWORD="$PW" python3 scripts/detect-schema-drift.py --cron
```

Print only a confirmation like "creds extracted (pw hidden)". If extraction fails, check the field position (`awk -F'|'` numbering, surrounding backticks) — do NOT fall back to grep/sed line iteration over the file: **bulk line-scanning a secrets file echoes the whole file to the terminal** (one session printed ~26k chars of live credentials that way).

## Pitfalls

- **Never echo secret values into tool output.** Redact with `re.sub(..., '[REDACTED]', line)` before any print; a migration script that prints raw lines leaks the secret into the transcript you're trying to protect.
- **Bulk line-scanning a secrets file dumps the entire file into the transcript.** Pipes like `grep -n 'VAR=' file | sed -n "Np"` / any shim that prints whole lines or whole-file content defeat redaction in one shot. Single tight extraction (awk field / grep -m1 | cut), value into a shell var, nothing printed.
- Working-tree grep flags ignored files → false positives. Tracked-only scan is the real gate.
- A truncated grep pipeline masks the exit code — test the captured variable, not the pipeline status.
- A hit in `.env` / `CLAUDE.local.md` is NOT a leak — those are ignored by design; only tracked-file hits matter.
- Don't rewrite git history for a token prefix on shared branches — rotate instead.
- Partial prefixes live in `git log` forever; say so, then move on.
