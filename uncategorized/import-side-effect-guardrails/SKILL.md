---
name: import-side-effect-guardrails
description: "Importing a script can execute it — guard sys.path."
version: 1.0.0
tags: [python, imports, sys.path, side-effects, guardrails]
related_skills: [verifying-failures-before-acting, patch-tool-safe-editing]
metadata:
  hermes:
    tags: [python, imports, sys.path, side-effects, guardrails]
    related_skills: [verifying-failures-before-acting, patch-tool-safe-editing]
---

# Import Side-Effect Guardrails

Importing a Python module EXECUTES its top level. In a repo of runnable scripts — as opposed to a
library — "import it to reuse one helper" can run a job, write files, or mutate a database. The
mechanism is dull and the damage is not: an unintended run can overwrite artifacts you cannot
regenerate, before you have looked at anything.

## When to Use

- About to `import` a project module to reuse a function or constant from it.
- Setting up `sys.path` to reach a helper in a sibling directory.
- A run behaves inexplicably: files appear you did not ask for, a "dry run" seems to hang, a table
gains rows after a test, a script prints its banner and then just sits there.
- A repo holds same-named files at more than one depth.

## Rule 1 — Never `sys.path.insert(0, '.')` before importing a helper

`'.'` is the process CWD, so a stale namesake anywhere in the working directory shadows the real
module. Insert the SPECIFIC directory that holds the module (`scan/`), never the repo root and never
CWD, or load the file directly:

```python
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("gen", pathlib.Path("scan/generate_materials.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
```

## Rule 2 — Verify which file you actually imported

Print `mod.__file__` for every project module you import intending to call. If it is not the path you
meant, you are holding a different program — and it may already have run (Rule 3).

## Rule 3 — Every executable module carries a `__main__` guard

`if __name__ == "__main__": main()` — no exceptions, for anything that does work at top level. A
script that runs its job at module scope is a landmine: any importer, in any `sys.path` order, that
merely wants one helper sets it off. Before importing a module you did not write, grep it for the
guard; if it is absent, do not import it — load it by path (Rule 1) after confirming what its top
level does, or refactor the helper out.

## Rule 4 — Quarantine a stale duplicate, do not delete it

A superseded namesake (older copy, no guard) should be MOVED to a dated backup directory, not
removed: reversible, and it leaves the tree one import away from being dangerous again. Before
moving, grep for the module name across scripts, cron/job config, and docs to confirm nothing live
resolves to it.

## Rule 4b — Sweep for the namesake, not just for the missing guard

The vector is a NAME COLLISION, and a missing guard on its own is usually harmless: a helper only
explodes when something imports it. So sweep in two passes and treat the intersection as the
finding:

1. every executable `.py` that lacks `if __name__ == "__main__": main()` (grep it, do not eyeball);
2. every one of those whose BASENAME matches a module another script imports — especially when a
   canonical copy lives in a subdirectory (`scan/`, `app/`, `src/`) and a stale copy sits at the
   repo root, where `sys.path.insert(0, '.')` puts it first.

Pass 2 is the dangerous set. A dated one-off migration script with no guard is inert; a stale
`generate_*.py` at the root that shadows the live generator is a loaded gun. When you find one,
quarantine it and add the guard lesson to the tree's conventions — the next copy is usually added by
someone reaching for a quick script.

### Find them by basename collision, not by eye

Sweep every executable file in the tree for the guard, then intersect with the module names that
scripts actually import:

```bash
for f in $(find . -name '*.py' -not -path './.venv/*'); do
  grep -q '__name__ == "__main__"' "$f" || echo "NO GUARD  $f"
done
```

The dangerous entries are the NO-GUARD ones whose **basename** matches a module another script
imports. A stale `generate_materials.py` at the repo root shadows `scan/generate_materials.py` for
anything that puts the root on `sys.path`, and quietly runs the OLD generator. What hides it is that
the correct copy is guarded, the names differ only by directory depth, and a missing guard reads as
harmless in review when the file "isn't the one you run". Before quarantining, check the tree for a
canonical copy of that name — if one exists, the duplicate is dead weight by definition.

## Rule 5 — Validate at import; fail loudly. Never fail silently at use

Module scope is the right place to catch drifting inputs. Validate at import that every name in a
hardcoded table exists in the data file it refers to, and raise with the actionable message:

```python
_UNKNOWN = sorted({n for _d, _p, names in TABLE for n in names if n not in _BY_NAME})
if _UNKNOWN:
    raise RuntimeError(
        f"{_UNKNOWN} are named in TABLE but absent from {DATA}. Either they were renamed "
        "(update TABLE) or dropped (remove them from TABLE).")
```

A renamed product/column/feature then stops the run at startup with a message naming the fix,
instead of silently degrading every document it produces.

## Rule 6 — A lookup that can raise inside a sort key makes the guard below it dead code

```python
ranked = sorted(score.items(), key=lambda kv: (-kv[1], NAMES.index(kv[0])))  # raises here
for name, sc in ranked[:max_n]:
    p = next((x for x in data if x["name"] == name), None)
    if not p:
        continue          # DEAD: unreachable, the sort already raised
```

`list.index` raises `ValueError` inside the sort when the name is missing, so the guard written for
exactly that case never runs. The error then surfaces far from its cause, and any `except` in the
caller collapses it into a silent fallback — a whole batch degrades to low-quality output while
looking clean.

- Sort keys must be total and non-raising: precompute `_ORDER = {n: i for i, n in enumerate(NAMES)}`
  and use `_ORDER.get(name, len(_ORDER))`.
- Fix membership ONCE, loudly, at import (Rule 5) rather than defending at every call.
- Prefer truncating by walking the ranking until N keepers are collected, so a filtered-out
  candidate backfills instead of silently shrinking the result.

## Rule 7 — After any accidental import, inventory before re-running

If an import may have executed work: list artifacts by mtime, count the rows, read the newest files,
and check the class you must never touch (rows already committed to the outside world — sent,
published, applied). Then decide. Re-running a job whose state you have not established is how one
accidental execution becomes several.

TWO TRAPS IN THAT INVENTORY, both of which produce alarming false conclusions:

- **Count ROWS, not files.** A writer that emits each artifact under two names (a canonical
  filename and a prefixed alias, say) makes `glob` report double the rows — so progress looks twice
  as fast, or a batch looks twice as large. Resolve filenames back to their row identity before you
  count anything.
- **Use a window narrower than the thing you are measuring.** A run that wrote 129 artifacts two
  and a half hours ago sits INSIDE a "last three hours" window, so its output is attributed to the
  run you are actually inspecting. Time the window from the run's own start, not from "recently".
  A contaminated window is how a 99%-correct generator gets mistaken for a 71%-correct one.

Three ways this inventory lies to you:

- **Bound the window by the RUN's start time, not by a convenient "last N hours".** A broad window
  sweeps in a PREVIOUS run's output and you read its artifacts as the new run's. That produces
  false conclusions in both directions — phantom failures (a prior run's lower-quality output counted
  as this run's) and phantom successes. Anchor on when the suspected run started; when a harness
  prints its own starting count, that number is your baseline.
- **Count ROWS, not files.** A writer that emits each artifact under two names (a prefixed and an
  unprefixed form) doubles the file count: 174 files is 87 rows. Reconcile files to rows through the
  database's stored filename column, not by dividing or eyeballing.
- **A row count that will not fall to zero needs a reason.** If the queue shrinks by less than the
  number of rows you processed, either new rows entered the set or rows silently failed — find out
  which before launching another pass, or you will relaunch a run that cannot converge.

When a queue is refreshed on every pass, bound the retry: count attempts per row and stop after a
small number, or a single row that can never succeed re-spends a full call every pass and keeps the
remaining count permanently above zero.

## Rule 8 — "It printed a banner and kept running" is not a hang

A script that reports its plan and then continues is usually working. Establish its outcome from the
artifacts it produces and its real exit status before calling it stuck, killing it, or launching it
again — and never read that status through a pipe (see `verifying-failures-before-acting`).

## Rule 9 — Importing a CLI to reuse one helper is the anti-pattern

The fix is structural, not defensive: extract the helper into a module with no top-level work, or
load the file by path and call the function (Rule 1). Reaching into a script's namespace is a
standing invitation to execute it by accident.
