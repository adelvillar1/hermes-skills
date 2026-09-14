# Stale-base trap: "honest but stale" cloud gate reports

From the mahjong VTT PR #2, 2026-08-17.

## The failure mode

The PR body's claimed gates were run against the cloud clone's base
(`origin/<base>`). If local `<base>` is AHEAD of origin with unpushed commits
touching the PR's subject area, a green self-report can be true for the old code
and false for the current one.

Concrete case: cloud's claims tests claimed 57/57 ✅ against `origin/develop`.
Materialized onto local develop (10 unpushed commits ahead, including a new
claim-window kernel), 3 of 30 failed — the tests encoded the old direct-claim
API (`applyAction({type:'claim'})` without an open `pendingClaim` window). The
kernel was right; the tests were written against a superseded contract. Merging
as-is would have turned develop's suite red.

## Defense, in order

1. `git log origin/<base>..HEAD --oneline` BEFORE reviewing — if local is ahead
   in the PR's subject area, materialize-and-run against the LOCAL tree (the
   future shared base), not just the PR's merge base.
2. When a revision needs the newer code: **push `<base>` first** (plain push,
   never force — force-push breaks the cloud clone) so the cloud instance can
   fetch what its fix must target. Then post the changes-requested comment.
3. In the comment, name exact failing lines AND the current source locations
   (file:line, e.g. `turn.ts:301 'no claim window open'`) plus a pointer to
   reference tests showing the new flow. The cloud agent cannot see your local
   state; precise citations are what make its one-shot revision land green
   (it did — revised PR passed 101/101).
4. On re-review, verify the revision drives the REAL current flow end-to-end
   (e.g. discard → window → claim recorded → passes → tick resolves), not just
   that assertions were reworded to pass.
