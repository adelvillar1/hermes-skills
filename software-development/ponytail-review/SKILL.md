---
name: ponytail-review
description: >
  Code review focused exclusively on over-engineering. Finds what to delete:
  reinvented standard library, unneeded dependencies, speculative abstractions,
  dead flexibility. One line per finding: location, what to cut, what replaces
  it. Use when the user says "review for over-engineering", "what can we
  delete", "is this over-engineered", "simplify review", or invokes
  /ponytail-review. Complements correctness-focused review, this one only
  hunts complexity.
license: MIT
source: https://github.com/DietrichGebert/ponytail
---

Review for unnecessary complexity. One line per finding: location, what
to cut, what replaces it. The code's best outcome is getting shorter.

**Scope flexibility.** The skill originated as a diff reviewer ("Review diffs")
but the user often asks for a whole-codebase review ("ponytail review the
codebase", "review for over-engineering", "what can we delete"). When they do,
expand the scope: hit the biggest files, the most-recently-changed areas, and
known hot paths (per CLAUDE.md "Today's state"). State the scope at the top of
the review ("Reviewed 6 high-traffic files in src/ and ui/js/, plus a
spot-check on the rest"). Don't pretend to have read the whole codebase —
flag the scope honestly.

**The review→ship flow.** A standalone review the user has to act on later
is half a deliverable. When the user asks for a ponytail review and the
review surfaces a high-leverage finding (e.g. a 100-line block duplicated
across two routes), the default next step is to ask: "proceed?" then ship
the fix in the same session. Lean reviews pair naturally with the user's
"ship early" preference — they want the diff to be shorter, not just
described as shorter. End the review with `net: -N lines possible.`
followed by a one-line "Want me to do the X extraction?" prompt.

**Always end with a recommendation order, not a flat list.** The user
prefers to skim-and-pick. Format the closing block as a numbered list of
the top 2-3 findings ordered by leverage (lines saved × blast-radius
reduction), each with: which files, what the extraction looks like in one
line, and the lines-saved estimate. The user picks one and you ship it.

## Format

`L<line>: <tag> <what>. <replacement>.`, or `<file>:L<line>: ...` for
multi-file diffs.

Tags:

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

## Examples

❌ "This EmailValidator class might be more complex than necessary, have you
considered whether all these validation rules are needed at this stage?"

✅ `L12-38: stdlib: 27-line validator class. "@" in email, 1 line, real validation is the confirmation mail.`

✅ `L4: native: moment.js imported for one format call. Intl.DateTimeFormat, 0 deps.`

✅ `repo.py:L88: yagni: AbstractRepository with one implementation. Inline it until a second one exists.`

✅ `L52-71: delete: retry wrapper around an idempotent local call. Nothing replaces it.`

✅ `L30-44: shrink: manual loop builds dict. dict(zip(keys, values)), 1 line.`

## Scoring

End with the only metric that matters: `net: -<N> lines possible.`

If there is nothing to cut, say `Lean already. Ship.` and stop.

## Boundaries

Complexity only, correctness bugs, security holes, and performance go to a
normal review pass, not this one. A single smoke test or `assert`-based
self-check is the ponytail minimum, not bloat, never flag it for deletion.
Does not apply the fixes, only lists them.

**Distinguish "big file" from "over-engineered."** A 3,000-line file with
15 small classes can be justified (5 mixin classes × signal-aware engines is
a real fan-out, not YAGNI). A 947-line file with 1 function and 900 lines of
static lookup tables is data, not code. **Always state why a large file is
OK before moving on** — silence on the big files reads as if you didn't
look at them. Quick justification: "15 classes = 5 mixins × 5 concrete
engines, real fan-out, keep" or "1 function + 900 lines of static maps,
data not code, keep."
"stop ponytail-review" or "normal mode": revert to verbose review style.