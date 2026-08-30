---
name: patch-tool-safe-editing
description: Use when patching files. Fuzzy matches can corrupt content.
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [editing, tools, verification]
    related_skills: [post-edit-error-attribution, review-changes]
---

# Patch-Tool Safe Editing

## When to Use

- Any edit via the `patch` tool, especially when `old_string`/`new_string` text was copied from `read_file` output
- Edits to structured text: markdown tables, YAML, JSON
- After a patch reports success but before moving on to the next edit

The `patch` tool is fuzzy (9 matching strategies) — a slightly-wrong `old_string` can still apply, silently producing corrupted content. Several failure modes observed in production sessions (2026-08-29 added two more).

## Pitfall 1 — read_file's line-number separator rides into your patch

`read_file` returns lines as `LINE_NUM|CONTENT` (e.g. `115|| DELETE | /api/...` where content starts with `|`). When copying lines verbatim into `old_string`/`new_string`, it is easy to accidentally include the separator pipe.

Real failure (pampa-wineclub, 2026-08-15): patching a markdown table, the copied `old_string` carried the extra `|`. Fuzzy matching still applied the patch, leaving literal `|| ` at the start of 8 table rows — a broken table that looked plausible as raw text but corrupted the markdown rendering.

**Rule:** when building patch strings from read_file output, strip the `LINE_NUM|` prefix — the separator between line number and content is NOT file content. If the content itself starts with `|`, the displayed line shows a doubled pipe.

## Pitfall 2 — fuzzy match lands in the wrong place

Fuzzy strategies can match a near-identical block in the wrong section of a long file (duplicate headers, repeated boilerplate). The patch reports success while the edit lands somewhere unintended.

## Pitfall 3 — a patch that spans a section boundary eats the sibling section's content

When a patch replaces a list/block that runs up to the next `##` heading, the `old_string` often implicitly spans past the intended section, and the replacement text silently DROPS the sibling list items that sat between them. Real failure (2026-08-27, plan doc): replacing an "Out of Scope" list whose `old_string` accidentally extended through the following "## Verification" heading and its first bullets — the diff applied cleanly, but the Verification section's list items vanished, leaving the section header directly above unrelated content. Discovered only because a post-edit re-read of the file showed the Verification bullets missing.

**Rule:** patch old_strings must start AND end inside the same section. If a fix spans a heading, include BOTH sections' complete content in old_string and new_string (nothing may be elided between them), or do two separate patches. Never replace "from a list item to past the next heading" in one shot unless the diff is re-read line by line.

## Pitfall 4 — V4A multi-hunk patches are all-or-nothing

For the `patch` tool's V4A mode (`mode='patch'`), one hunk's `old_string` not matching refuses the ENTIRE patch (the tool lists "Did you mean one of these sections?" for the missing anchor) — including hunks that would have applied cleanly. Real failure (2026-08-29): a 3-hunk V4A patch adding a docker subcommand family to a Python script; hunk 2's anchor (`-def cmd_register(args):` + `    if args.pid:`) didn't match because the function had gained intervening lines, and all three hunks were dropped. A later single-hunk patch against the same line succeeded, proving hunk 2 was the sole reason.

**Rule:** before firing a multi-hunk V4A patch against functions you edited this session, re-read the current text and use anchors that are still unique-and-current (prefer a longer, more specific context line over a bare function signature). On refusal, either fix that hunk's anchor or split the patch file into per-hunk patches — don't debug all three at once.

## Pitfall 5 — generated insert text can corrupt itself

When assembling a large V4A patch, the text you *generate* (not the target's content) can corrupt the file — two live instances in one session (2026-08-29), both caught quickly because lint/validation ran on the edited file:

- **Placeholder token in a code block** (`else-placeholder:` in Python): immediate SyntaxError, surfaced at patch-report time via built-in lint.
- **Patch-protocol terminator leaking into the file**: a generated `*** End Patch` line landed inside a .md right before the next section — the patch reported success and the line passed unnoticed until the next read of that file. (Same class of bug: emitting a code sample containing your own protocol tokens, or double-including a final `+`/`-` block.)

**Rule:** after any patch whose new_string contains fenced code, generated placeholders, or patch-format lines, (1) run the file's syntax check (`read_file` back through the edited region, or the language's compiler), and (2) `search_files` for leftover terminator tokens (`*** End Patch`, `@@`, `===`) AND for generated placeholder names (`placeholder`, `TODO`, `pass  # ...`) inside the target file — expect zero matches.

## Mandatory verification steps

1. **Read the patch tool's returned diff** — don't just note `success: true`. Check the `+` lines are exactly what you intended, with correct leading characters.
2. **For structured text (markdown tables, YAML, JSON), grep for corruption after patching:**
   - markdown tables: search the file for lines starting with `||` (double pipe) — almost always separator contamination
   - YAML: re-read the patched block and confirm indentation survived
3. **For long files, confirm placement:** the inserted text must be in the intended section, not appended at the end or wedged into a sibling section. Run `git diff -- <file>` and read it yourself — the user will not re-read your diff; if it's wrong it ships wrong.
4. **Two failures on the same region → stop patching.** Re-read the exact region with read_file (mind pagination gaps), then retry with the now-exact text, or rewrite the enclosing block with write_file. Never fire a third fuzzy patch blind.
5. **Partial-read warning = re-read before the next patch.** When the tool returns `_warning: "...last read with offset/limit pagination (partial view)"`, the previous read only covered a window — the old_string may have matched inside a sibling section you never saw. Read the whole file (or the full section) before the next patch against it; do not chain patches from a paginated view.
6. **Section-boundary check for list edits:** after any patch that touches a bulleted list, verify the NEXT heading's content still has all its bullets (count them against the pre-patch state or the returned diff's unchanged lines). The silent-deletion mode of Pitfall 3 shows up here.

## Quick corruption scan after table edits

After any patch touching markdown tables, run a content search for `^\|\|` on the file — zero matches expected. Fix recipe observed working: strip one leading `|` from every line starting with `|| ` via a tiny Python rewrite, then re-verify with the same search.
