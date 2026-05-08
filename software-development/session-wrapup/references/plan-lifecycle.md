# Plan Staleness Prevention Cycle

Three-layer defense against stale plan files re-surfacing in warmups.

## Layer 1: Completion-time (immediate)

**Rule:** When work is confirmed complete, update the plan file in the SAME TURN.

```bash
# patch status: active → status: completed, bump updated date
```

Do not wait for recap/wrapup. The user says "done" → plan file gets patched immediately.

This is enforced by memory: "Hard rule: when any plan's work is confirmed complete, ALWAYS update the plan file's status from 'active' → 'completed' and bump the updated date immediately."

## Layer 2: Recap-time (cross-reference)

write-session-recap step 4: cross-references commits against previous recap's open items. If a commit resolves an open item, auto-close it.

write-session-recap step 5: checks if commit messages or file changes complete any active plans the prior recap listed. Proposes flipping them.

## Layer 3: Wrapup-time (final gate)

session-wrapup step 5: greps for active/draft plans, cross-references against the latest recap, and checks post-recap git log. Flags any plan with all criteria met but still `status: active`. Auto-resolves open items that were closed by post-recap commits.

## Layer 4: Warmup-time (last resort)

session-warmup step 4: cross-references recaps against plan statuses. If a recap says a plan was completed but the file still shows `status: active`, flags it as stale rather than reporting it as active.

session-warmup item 15: forbids reporting plan statuses from in-session cached memory. Always grep fresh.

## Common failure mode

Plan files are branch-specific. When subagents switch branches (e.g., develop → scraper), plan files that only exist on develop/staging disappear from the working tree. Uncommitted patches are lost. Recovery: `git checkout <branch> -- docs/plans/<file>.md`, then re-apply patches.
