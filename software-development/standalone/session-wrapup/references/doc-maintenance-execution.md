# Doc Maintenance Execution - Update needed

Worked example of executing deferred doc-update debt — the "update the documents as needed" flow.

## When This Applies

When the user says "update the documents as needed" or "address the doc debt" in response to a recap that listed deferred updates. This is the **execution** side — the recap identified what needs changing; this covers the how.

## Steps

### 1. Identify all deferred updates from the recap

Read `docs/daily-recaps/<latest>.md` and extract every bullet under "Doc updates deferred". Also check the "Doc updates applied" section to avoid re-applying already-done work.

### 2. Map each deferral to its target doc

Use CLAUDE.md's "Where to find things" map:

| Deferral mention | Likely target |
|------------------|---------------|
| New API route | `docs/technical-documentation.md` → API Routes table |
| New business rule | `docs/functional-specifications.md` → the relevant feature section |
| New feature behavior | `docs/feature-<slug>.md` or create one |
| Schema change | `docs/technical-documentation.md` → Database Schema section |
| Stale CLAUDE.md bullets | `CLAUDE.md` → "Today's state" |

### 3. Read the target doc

```bash
grep -n "pattern-to-find" <doc>.md  # locate the right insertion point
```
Read at least 10 lines of context around the insertion point so the patch matches exactly.

### 4. Apply edits (pitfalls below)

Use `patch` for targeted edits. Verify with a follow-up read.

### 5. Patch tool pitfalls with markdown tables

**The `patch` tool can mangle markdown table rows that start with `||`.** This is the standard pipe-table prefix:

```
|| Route | Method | Access | Description |
||-------|--------|--------|-------------|
|| `/api/bookings` | GET/POST | Owner/Agent | List/create bookings |
```

When `patch` matches a row that starts with `||` and replaces it with a row starting with `|`, the diff can produce **triple-pipe artifacts** (`|||`) or **double-pipe** (`||`) that break the table. The corruption pattern:

- **Triple pipe `|||`**: occurs when the patch tool's diff logic adds an extra `|` prefix
- **Mangled leading pipe**: `|` becomes `||` or vice versa

**Fix strategies:**
1. **Include enough context in old_string** — match at least 3-4 consecutive lines to give the diff a stable anchor
2. **Use single-pipe syntax throughout** — even if the existing table uses double-pipe `||`, use single `|` in both old_string and new_string. The patch is character-level text replacement, it doesn't understand table syntax.
3. **Fix the broader block** — if one row gets corrupted, fix the entire block (5-10 lines) in one `patch` call rather than chasing individual lines
4. **If patch keeps failing** — restore the file from git (`git checkout -- <file>`) and retry with a larger context block

**Known failure mode (discovered 2026-04-30):** Even a clean patch match can produce `|||` artifacts. When this happens, the triple-pipe prefix causes subsequent patch calls on nearby lines to ALSO fail (the `old_string` no longer matches because the leading pipe count changed). The fix is to restore from git and retry with a broader context block that catches ALL affected rows in a single call, including the unaffected rows between them. A single sed-like Python script (via `execute_code`) could also be used for bulk replacement of `|||` → `||` when chasing individual lines becomes untenable.

### 6. Verify table rendering

After patching any table, read the 10 lines around the edit and visually check:
- All rows start with the same pipe-count (`|` or `||`, consistent)
- No row has `|||` (triple pipe)
- No rows are missing (duplicates, or lines that got dropped)
- All pipe-separated values are present

### 7. Run the drift check

Required after any doc maintenance session:

```bash
wc -l CLAUDE.md
# Should be ≤ 300 lines

# Check CLAUDE.local.md is gitignored
git check-ignore -v CLAUDE.local.md 2>/dev/null && echo "OK" || echo "WARN: not gitignored"

# Check all doc pointers in CLAUDE.md resolve
for f in $(grep -oE 'docs/[a-zA-Z0-9_/.-]+\.md' CLAUDE.md); do
  [ -e "$f" ] || echo "MISS: $f referenced but does not exist"
done

git status --short
# Should show only the files you intentionally changed
```

### 8. Confirm all deferred items were addressed

Check off each bullet from step 1. If something must be deferred again, note it in the session output as an explicit carry-forward.
