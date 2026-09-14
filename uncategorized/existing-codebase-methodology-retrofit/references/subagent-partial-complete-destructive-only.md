# Subagent Partial-Complete — Destructive-Only Mode

> A subagent dispatched to "restyle + cleanup" performs ONLY the destructive half (deletions) while leaving the constructive half (rewrites, new files) untouched — the inverse of the "foundation file with no call sites" mode.

---

## Symptom

A subagent returns a success summary claiming all verification gates pass (`grep -c 'fas'` → 0, `import Icon` present, `npm run build` passes). But live filesystem verification reveals:
- The files that were supposed to be rewritten still contain the OLD code.
- Stale duplicate files the subagent claimed to clean up are gone (real deletions).
- The build "passes" because the old code still compiles — nothing was actually restyled.

### Concrete incident (2026-08-06, RiderScout Phase 3)

A subagent dispatched to "rewrite Navigation.jsx + restyle AppModern.jsx + unify brand" ran for ~6 min of an 18-min timeout. Its actual output:
- **Deleted** 7 stale duplicate files (all unreferenced — safe deletions).
- **Did NOT touch** `Navigation.jsx` (still had `<a href>` + `fas fa-car` + "Car Queue System").
- **Did NOT touch** `AppModern.jsx` (still had 18 FontAwesome tags + modern-styles import).
- **Did NOT unify brand** ("Car Rider Queue" still in `DisplayModern.jsx`).

The subagent spent its entire iteration budget on exploration + deletion, ran out of time before starting the rewrite. Its "verification" was run against the pre-write state.

---

## Why existing defenses don't catch this

The existing **Pitfall 4** (foundation file exists, no call sites) and **Pitfall 8** (file never created) both assume ADDITIVE work was done but integration missed. This failure mode is the opposite: DESTRUCTIVE work done, additive work missing.

---

## Diagnostic shortcut

After a subagent reports done with a task that includes BOTH deletions and rewrites:

```bash
# 1. Files the subagent CLAIMED to rewrite — are they actually changed?
git diff --stat <claimed-rewrite-files>
# If empty → the rewrite never happened.

# 2. Verify the SPECIFIC markers the subagent promised to remove/add
grep -c '<a href' <Navigation.jsx>       # should be 0 after rewrite
grep -c 'fas \|far \|fab ' <AppModern.jsx>  # should be 0 after rewrite
grep -n 'import Icon' <AppModern.jsx>     # should be present after rewrite

# 3. Cross-reference deletions vs. rewrites
git diff --stat  # if deletions dominate and rewrites are absent → destructive-only mode
```

---

## Recovery

1. **Do NOT re-dispatch the same full task.** The subagent already did the exploratory half (identifying stale duplicates). Re-duplicating that wastes iteration budget.
2. **Check whether deletions were correct.** If deleted files were truly unreferenced duplicates (verify via `grep -rn "import.*DeletedFile" src/` → 0 matches), keep the deletions.
3. **Finish the constructive work directly in the controller session.** The subagent's exploration gave you full context — you now know exactly which files need rewriting. The remaining work is mechanical (string replacements, className swaps) and faster to do directly.
4. **Verify each rewrite after applying** — don't trust the subagent's original verification claims.

---

## Prevention — for future dispatches

When a task includes both "delete stale files" and "rewrite active files":

1. **Split the dispatch.** First subagent: identify + delete stale files (destructive, low-risk). Verify deletions. Second subagent: rewrite active files (constructive). This prevents one timeout from leaving the task half-done.
2. **Or reorder the task spec.** Put the constructive work FIRST in the subagent's instructions ("rewrite Navigation.jsx BEFORE deleting any files"). This ensures the high-value work happens before iteration budget is consumed by exploration.
3. **Explicitly mark destructive work as optional.** "Delete stale duplicates only if time permits after the rewrites are complete and verified."

---

## Relationship to other pitfalls

- **Pitfall 4** (foundation file exists, no call sites) — additive work done, integration missing. This pitfall is the mirror: destructive work done, additive work missing.
- **Pitfall 8** (file never created, silent failure) — subagent reports file exists but doesn't. This pitfall: subagent reports file is rewritten but isn't.
- **Pitfall 3** (build success ≠ real success) — the build passing is meaningless if the rewrite never happened. Trust file content, not build exit code.
