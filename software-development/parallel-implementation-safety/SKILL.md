---
name: parallel-implementation-safety
description: Keep parent and subagent writers from race-corrupting sha.
---

# Parallel Implementation Safety

## When to load
- Multi-phase plans (admin console, auth expansions, shared routers)
- Any background `subagent dispatch` while the parent keeps working
- Live transcript frozen / "sibling subagent modified file" warnings
- Corrupted files with duplicated blocks or orphan braces after parallel work

## Core rule
**One writer per path until commit.** A background child and the parent must not both edit the same file.

## Ownership matrix

| Work shape | Who owns it |
|---|---|
| Shared router / auth / session / schema migration | **Parent only** until committed |
| Disjoint **new** leaf files (`FooPanel.tsx`, pure helpers) | Subagent OK in parallel |
| Same file, different sections | **Serialize** — never parallel |
| Child exited (terminal transcript line), or stalled ≫ timeout | Parent takes over; do not dual-write |
| Child silent but transcript last line is a normal tool/result line | **Throttled, not dead** — wait; do NOT take over |

## Stall detection

**⚠️ Do NOT use "no new transcript lines for N minutes" alone as the dead signal.** This heuristic false-alarms when children are rate-limit-queued rather than dead (observed 2026-07-21: three concurrent children on one provider key were silent ~9 min during their read phase, then resumed and wrote all their files correctly). Silence is ambiguous; discriminate on the transcript's LAST LINE and the disk state:

1. Read live transcript path from dispatch response.
2. **Definitively dead:** the transcript's last line is a `final` / `status=timeout` / `status=completed` / `error:` line. The child has exited. Safe to take over its files.
3. **Alive but throttled:** the transcript's last line is a normal `tool` / `result` / `assistant` line, even if many minutes old. The child is mid-execution but its LLM calls are queued. **Do NOT declare dead, do NOT write to its files.** Check `git status` for partial writes; then wait. Concurrent children sharing one provider key divide throughput (~1/N each), so read phases can be silent for many minutes — scale your patience by concurrency.
4. Only treat as dead-and-take-over when you see a terminal transcript line, OR silence is so extreme (≫ the child timeout) that the scheduler must have already killed it. When in doubt, wait one more cycle.
5. Never "help" a possibly-alive child by patching its target files — a throttled child that wakes up will race you.

## Recovery from race corruption
1. **Stop patching.** More fuzzy patches worsen half-merged files.
2. Rewrite each corrupted file as one **complete known-good write** (Python/heredoc full replace is fine).
3. Immediately run project typecheck + targeted tests.
4. Commit the phase before the next multi-file wave.

## Repo-wide git operations in a shared working tree

In a repo where sibling subagents work concurrently, **repo-wide git operations are blast-radius events**: `git stash`, `git checkout .`, `git reset --hard`, and unscoped `git clean` affect *every* uncommitted file — including a sibling's in-flight WIP you cannot see from your task scope.

**Prevention:**
- Never use repo-wide stash/reset to "temporarily check the pre-change state." Use non-destructive comparison instead: `git show HEAD:<path>` / `git diff HEAD -- <path>` against the baseline, or copy the file to /tmp before editing.
- If a stash is truly required, scope it to your own paths only: `git stash push -- <your-paths>`.
- "Was this lint/type error pre-existing?" is answerable from the reported line number (usually far from your edits) or `git show HEAD:<file> | npx eslint --stdin` — never by stashing the world.

**Recovery when a repo-wide stash already happened and the pop conflicts** (the sibling rewrote a file while the stash was open, so `git stash pop` aborts with "would be overwritten by merge"):
1. **Do not force anything.** The stash is intact — `git stash show --name-status stash@{0}` lists what's inside.
2. Extract every stashed file (`git show stash@{0}:<f> > /tmp/<f>`) and compare against the working tree.
3. **Per-file superset check:** strip whitespace and compare line sets — lines present in the stash but absent from the working tree are lost content that must be restored.
4. If the working tree is a *superset* of the stash for a file (the sibling rewrote it during the stash window and re-integrated everything plus new work), keep the working-tree version.
5. For files whose content vanished from the working tree, restore them: `git checkout stash@{0} -- <paths>`, then immediately `git restore --staged <paths>` so the sibling's WIP stays unstaged as it was.
6. Final verification: every unique non-empty line of every stashed file exists in the working tree. Only then `git stash drop`.
7. Re-run typecheck across all affected packages after restoration.

**Key insight:** the stash captured *your* edits and the *sibling's* uncommitted work together. Your recovery obligation covers both — restoring only your own files strands the sibling's WIP inside a stash you're about to drop. Full incident + superset-check script: `references/repo-wide-stash-sibling-recovery-2026-08-05.md`.

## Commit cadence
After recovering a shared router/auth file (or finishing a phase the child was supposed to own):
**typecheck + targeted tests + commit before the next multi-file wave.** Uncommitted good state is still race food if another writer wakes up.

## Late timeout arrivals
When a background task eventually returns `status=timeout` (or empty summary) **after** you finished and committed its work: **do nothing to the tree.** Acknowledge and move on — never merge the child's half-done transcript into code.

**Verified 2026-07-21:** Phase-1 admin subagent returned `ASYNC DELEGATION BATCH COMPLETE` with `status=timeout` ~10 minutes after parent had already shipped Phases 0–8 and committed. Correct response is a one-line acknowledgment only — no re-open of `admin.ts`.

**Verified 2026-08-08 (the D&D VTT project P1 audio) — timeout ≠ broken code; the subagent can reconcile your collision and win.** The parent misread a long-silent-but-alive subagent as stalled, started writing the SAME files (`audioManager.ts`, `cues.ts`, `useAudio.ts`), and collided. The subagent noticed ("A sibling subagent was working on the same P1 task concurrently — I've overwritten…"), rewrote the files coherently with its own design (different exported type unions than the parent's draft → type errors that were collision residue, not real bugs), finished, and then returned `status=timeout` before the final verify/commit.

Correct parent response in that situation (differs from the dead-child "rewrite as known-good write" recovery):
1. **Stop editing the subagent's files the moment you see it is alive and reconciling** — let its rewrite stand. The parent's second copy of the same module is a distraction, not a safety net.
2. When the subagent returns `status=timeout`, do NOT assume the work is broken. **Verify the tree first**: read the files, run the tests from the correct workspace cwd (see `monorepo-typescript-verification` — vitest run from repo root false-fails happy-dom tests with `window is not defined`), then commit the subagent's completed work with a normal message.
3. The eventual timeout cost is fine: the code was complete and correct; the only loss was the subagent not writing the final commit message.

**Key distinction:** "late timeout arrival after parent shipped" (2026-07-21 → do nothing) vs "first signal that the child is done is a timeout" (2026-08-08 → verify + commit its tree). A timeout is a wall, not a verdict on the code.

**Resurrection clobber — a wall-crossing subagent can still write over parent-committed files (2026-08-09).** Observed: an admin-UI subagent went silent ~16 min (past its 600s wall, zero tool calls); the parent finished the 6 pages itself, committed them, and browser-verified. The subagent then RESUMED and, at its end, wrote its own unverified versions over the parent's committed `app/admin/*.tsx` (missing the parent's fixes: a subscription.id field the API returns, a DELETE route that doesn't exist). The parent restored with `git checkout app/admin/` — its committed versions were the verified baseline; tsc re-checked clean.

Defenses:
1. **Commit parent-verified versions immediately after taking over** a long-silent subagent — a committed version is the recoverable baseline; uncommitted good state is race food.
2. **Detect resurrection:** post-commit `git status --short` showing modifications to parent-owned files with no parent action, plus the transcript mtime advancing again, means the "dead" subagent woke up. Check `git status` + transcript before every commit AND after unexpected modifications appear.
3. **`git checkout <path>` restores the parent's committed version** — the subagent's late output is unverified by definition, the parent's was verified (tsc/lint/browser). Don't diff-merge the late version "to be fair"; it lost the verification race.
4. Never `git add -A` while a late subagent might still write — explicit paths only.

This extends "Late timeout arrivals": the arrival is not only a summary to acknowledge — it can be a write burst that lands minutes after the timeout notification.

## Phase sequencing (multi-phase monorepo features)
1. Parent: migration + schema + audit/helpers (foundation).
2. Commit.
3. Parent: expand shared router/auth gates (or one exclusive subagent).
4. Commit.
5. Parallel OK: leaf UI panels that only import stable `api.ts` helpers.
6. Commit; parent wires nav once.

## Sibling already committed your assigned task

When you're dispatched to implement a task on a file and discover (via "modified by sibling subagent" warnings or `git log`) that a sibling already implemented and committed the bulk of it:

1. **Stop and re-read the file.** Your earlier reads are stale — the sibling's changes shifted line numbers and may have restructured the code.
2. **Revert any field/variable renames you made** that conflict with the sibling's committed naming. Your uncommitted edits are now the delta, not the base.
3. **Audit the sibling's implementation against the spec.** They may have used different values (e.g. intensity 2.2 vs spec's 1.5, shadow far ×3 vs spec's ×2). Fix deviations.
4. **Selectively stage only your corrections** with `git add -p` — do NOT `git add -A`, which would sweep in the sibling's uncommitted Phase 2+ work that's sitting in the same file.
5. **Commit with a descriptive message** that names what you corrected (e.g. "fix: Phase 1 spec corrections — sun intensity 1.5, shadow far boardSize×2").
6. **Verify typecheck passes** after your corrections.

**Key insight:** When multiple subagents work on the same file in sequence, the later agent's job often shrinks from "implement feature" to "verify + fix spec deviations." The `git add -p` selective staging is critical — a blanket `git add` would commit another sibling's in-progress work under your message.

### Variant: sibling edits the shared file MID-TASK (uncommitted)

The patch/replace tool may return a `_warning` like *"file was modified by sibling subagent 'sa-X' … re-read the file before writing"* right after your edit lands. That means a sibling is *concurrently* editing a shared dependency (typically the API client) while you work. Correct response:

1. **Stop and re-read the whole file** before your next patch — your earlier reads are stale.
2. **Grep for what you were about to add.** Often the sibling already added exactly the helpers you planned (e.g. they added `signups.cancel` / `reservations.cancel` / `members.selfUpdate` to `api.ts` while you were building the UI that calls them). **Reuse their methods — do not duplicate.** Duplicate client methods with different names for the same endpoint create confusion for everyone downstream.
3. **Anchor later patches to current content**, not to what you read 10 minutes ago. If a planned `old_string` no longer matches, that's your signal the file moved.
4. Proceed with your own file (the leaf UI) freely — only the shared file needs re-reads before each write.
5. Note the division of labor in your final report ("sibling X added the API methods; I consumed them") so the parent agent knows nothing was double-worked.

This is the benign side of parallel work: no corruption, just a re-read-and-adapt. It is NOT the race-corruption case — the tool warning did its job and both writers' edits survived.

### Variant: EXTERNAL writer (not a subagent) mutating the tree mid-session

Observed 2026-08-09 (the design-tool web app billing): the tree changed hands while the parent worked — UI files (`UpgradeModal.tsx`, `useSubscription.ts`) appeared with mtimes during the session, the patch tool returned `_warning: "file was modified since you last read on disk (external edit or unrecorded writer)"` mid-edit, and `git log` showed a commit (`c61b711`) the parent never made. The writer was the user in their editor (or another session), not a delegated subagent — but the same rules apply.

1. **Inventory before acting:** `git status --short` + file mtimes + `git log` recent commits. Distinguish "genuinely concurrent writer" from "stale session-start snapshot" (the workspace snapshot at session start can be outdated — re-derive from git, don't trust it).
2. **Re-read the file fresh before EVERY patch.** Your earlier reads are stale; anchors stop matching; the other writer's changes may already implement what you planned (they often pick different prop names — e.g. `onPremiumRequired` vs your `onPaywall`).
3. **Adopt their approach when it's better, don't duplicate.** The writer had replaced bare `useState` with the full `useSubscription()` hook (correct subscribed status + checkout-return detection). Rename your additions to their names, delete your duplicate modal renders, keep their version. Fighting a better design to preserve your own is how you end up with two modals and a broken prop chain.
4. **Commit with EXPLICIT paths only** (`git add <paths>`, never `git add -A`) while another writer is in flight, and re-check `git status` + mtimes immediately before committing. Expect and absorb their commits in the log; your explicit-path commits land cleanly on top.
5. **Rapid-fire patches on a contested file are dangerous.** A wrong `old_string` + replacement sequence on the workspace page mangled the JSX (leftover `);` fragments, an extra `</div>`, `EmptyState` nested inside the component). The LSP diagnostics after the FIRST patch were stale (computed pre-patch) and useless; only re-reading the actual region showed the truth. Read the region before AND after each patch; repair with one precise patch per defect.
6. **Suspected file corruption must be confirmed with `read_file` before rewriting.** The terminal wrapper mangled the refund route's tail output (`}\n  }\n  }\n}` looked like orphan braces); `read_file` showed a clean 56-line file. Mangled terminal output ≠ corrupted file — check before "recovering".

## Second full the harness session on the same repo (sibling session, NOT a subagent)

The EXTERNAL-writer variant above assumes one-off edits. The escalation: the user runs a **second complete the harness TUI session** on the same repo with its own goals (e.g. running the rest of a plan while you handle one phase). Verified 2026-08-09 (the design-tool web app): the user confirmed "yes, I have a separate session" after commits appeared that neither the parent nor its subagent made.

**Detection (before assuming corruption):**
1. `git reflog --date=iso` shows commits at timestamps where you made none — a sibling committed. `git show --stat <sha>` on an unexpected commit lists YOUR uncommitted files — proof of the sweep.
2. `ps aux | grep the harness` shows a SECOND `node --expose-gc` + `python -m tui_gateway.entry` pair with a different start time than your session. A subagent's processes die with its transcript; a full second session stays alive (it can outlive your whole turn).
3. `git log --oneline -5` shows commits from *other* phases of the plan (e.g. "Phase 2 collab UI") landing while you work Phase 0-1.

**The sweep failure mode:** a sibling session committing with `git add -A && git commit` absorbs your parent-written files AND an in-flight subagent's files into ITS commit message. Files stay tracked and present — **mislabeled, not lost**. The sibling may also commit your subagent's work as its own. Don't rewrite history; verify integrity and move on.

**Subagent timeout against sibling WIP:** a child that times out while the sibling is mid-refactor may report a tsc error that is TRANSIENT sibling WIP. Observed: the child's final check failed `Cannot find name 'loadOwnedFrame'` because the sibling had just renamed it to `loadFrame` across routes — minutes later tsc was green. A timeout is a wall, not a verdict: re-run `tsc --noEmit` yourself after the tree stabilizes before declaring breakage.

**Correct response (stand down, don't race):**
1. Confirm the tree is stable: `stat -f "%m" <file>` twice 6-8s apart — unchanged mtime means the sibling is between writes (not necessarily done).
2. Verify YOUR scope survived intact via grep markers (e.g. `grep -l requirePaid app/api/.../route.ts`), NOT by re-reading everything.
3. Do NOT touch the sibling's uncommitted WIP, do NOT bulk-commit, do NOT take over its phases. Report the collision, name what your scope shipped, and list deploy-time shared resources (webhook endpoint registration, env vars, key flips) as coordination points so both sessions don't double-handle them.
4. `git stash` / `checkout .` / `reset --hard` on such a tree is catastrophic — the sibling's WIP is invisible to you; scoped `git stash push -- <your-paths>` only.

## Anti-patterns
- Parent implements Phase 1 on `admin.ts` while a child is also assigned `admin.ts`
- Layering `patch` after "modified by sibling subagent" warnings
- Trusting a stalled child's eventual async completion notice after you already rewrote its files
- Dispatching Phase 2 on the same router before Phase 1 is committed
- Re-applying a late `ASYNC DELEGATION BATCH COMPLETE` timeout result after parent already shipped that phase
- **Repo-wide `git stash` (or `checkout .` / `reset --hard` / unscoped `clean`) while a sibling subagent has uncommitted WIP.** The stash silently captures the sibling's in-flight work alongside yours; if the sibling keeps writing, `git stash pop` aborts with "would be overwritten by merge" and the sibling's files vanish from the working tree — now recoverable only from the stash. Verified 2026-08-05. Use `git show HEAD:<path>` for baseline comparison instead; see "Repo-wide git operations in a shared working tree" above.
- **A subagent's blanket `git add -A` sweeps in a parent-authored file.** When the parent writes a file while a child is in flight, and the child commits with `git add -A && git commit`, the parent's file lands under the CHILD's commit message — tracked and present (no data loss), but mislabeled and missing from the parent's later targeted `git add <that-file>` (it's already committed). Defenses: (a) don't write parent deliverables into the tree while an `add -A` child is in flight; (b) instruct children to stage explicit paths, not `git add -A`, when the parent is concurrently writing; (c) after any child commit, `git show --stat <sha>` and confirm the file list matches ONLY that child's scope — a surprise extra file means a parent/sibling write got swept in. Benign when it happens: note it, fix forward only if the mislabel matters; not worth a history rewrite.

## Support
- `references/parent-child-file-race-2026-07-21.md` — concrete admin-surfaces incident + recovery recipe
- `references/repo-wide-stash-sibling-recovery-2026-08-05.md` — repo-wide stash swept a sibling's uncommitted WIP; superset-check recovery script
