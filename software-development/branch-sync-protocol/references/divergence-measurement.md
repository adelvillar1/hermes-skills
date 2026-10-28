# Measuring branch divergence correctly

Use when comparing two branches and reporting what one has that the other lacks. Every rule here exists
because a plausible-looking count produced a wrong conclusion that someone would have acted on.

## 1. Ancestry is not content

`git rev-list --left-right --count A...B` counts **commits**, not changes. A commit absent from a lane
by SHA may be fully present by content — cherry-picks, rebases, and re-applied patches create a new
SHA with the same diff.

Before calling anything "missing from develop":

```bash
# Same change under a different SHA?
git show <missing-sha> | git patch-id --stable | cut -d' ' -f1
git log --format=%H <lane> -n 50 | while read c; do git show $c | git patch-id --stable | cut -d' ' -f1; done | grep <patch-id>

# Same files, same bytes?
git rev-parse <ref-a>:<path>   # blob SHAs equal => identical content

# What actually differs, in files and lines
 git diff --stat <ref-a> <ref-b>
```

A missing-SHA/present-content pair is a duplicate commit, not missing work. Reporting it as missing
sends someone to merge a lane backwards to "close" a gap that does not exist.

## 2. State direction and units

`--left-right --count A...B` prints `LEFT<TAB>RIGHT`, where LEFT is A-only and RIGHT is B-only. Say
which side you are quoting. Never mix units in one list: "+167" beside "+160" reads as comparable,
but one may be a commit count and the other an insertion count (a lane can be 167 commits ahead while
differing by 730,860 insertions across 3,302 files).

## 3. Ahead/behind is inflated by `--no-ff`

Re-run with `--no-merges` before interpreting:

```bash
git rev-list --left-right --count --no-merges origin/staging...origin/main
```

A large ahead count made of merges is release bookkeeping, not unique work. But **name every
non-merge on the ahead side**: a fresh direct commit (an ops or infrastructure commit landing straight
on `main`) is genuine divergence, and "the documented --no-ff pattern" does not explain it. Also check
whether that commit exists on the other lanes — if it does not, the lanes have really diverged and a
future promotion must not clobber its files.

## 4. Containment is a boolean, not an arithmetic judgement

```bash
git merge-base --is-ancestor origin/develop origin/staging && echo contained
```

Exit 0 means the first ref is an ancestor of the second. Use this instead of reasoning about which
of two ahead/behind numbers "means" containment.

## 5. Equal trees are not the same commit

`staging` and `main` can serve identical content from different SHAs (different merge parents).

```bash
git diff --quiet origin/staging origin/main && echo "identical trees"
git rev-parse origin/staging origin/main
```

Report "identical trees, different SHAs" when that is what is true; never write `staging == main
(<main's sha>)`, which reads as one commit.

## 6. Counting table rows

`grep -c '^|' file` counts the header row and the `|---|` separator too. For a markdown table, data
rows are that count minus 2 — or grep the row shape directly. Say which you counted: "20 pipe lines
(header + separator + 18 data rows)" is unambiguous; "20 rows" invites a correction from anyone who
counted rows.

## 7. Do not infer a rewrite from asymmetry

Asymmetry has three ordinary causes — release merges, duplicated commits, genuinely new work. Decide
which one with `--no-merges` plus patch-ids. "Staging was reset/rewritten" is a strong claim that needs
evidence beyond a count, and it sends the reader hunting for a problem that does not exist.

## 8. Re-fetch before measuring

`git log --all` and `git rev-list` only see refs that are already local. Without `git fetch --all
--prune` first, an unfetched remote is invisible and the comparison reports yesterday's world — or
reports "no drift" for a branch that moved.
