# Ref arithmetic for PR / branch status claims

Commands for turning "is it stale / merged / missing?" into a number with a direction, without checking out the branch.

## Staleness

```bash
git fetch --all --prune
git rev-list --count origin/<base> --not origin/<head>       # commits the head lacks
git log -1 --format='%h %cI %s' origin/<head>                # what the tip actually is
```

A `Merge origin/<base> … (refresh #N)` commit at the tip is the *last* refresh, not currency. If the count is > 0 the PR is behind by that many; report the count and the refresh date together, and never write "not stale".

## Containment / promotion

```bash
git rev-list --left-right --count origin/<lane>...origin/<work>
# LEFT = lane-only, RIGHT = work-only
git merge-base --is-ancestor origin/<work> origin/<lane> && echo contained
```

| Output | Meaning | Report as |
|---|---|---|
| `188 0` | work fully contained in lane | promoted to that lane |
| `188 4` | 4 work commits absent from lane | 4 commits pending promotion, named |
| `0 156` | lane-only history, work is an ancestor | work is a strict ancestor; a branch cut from it cannot host new product work |

Direction matters: the same pair reversed swaps LEFT and RIGHT. Beware importing a sibling repo's numbers — check `pwd` before quoting a count.

## Merge-only asymmetry (is a rewrite real?)

```bash
git rev-list --count --no-merges origin/A..origin/B
git log --no-merges --oneline origin/A..origin/B
```

With `--no-merges`, an asymmetry that collapses to 0 means every commit one side "lacks" is a merge — the documented `--no-ff` release pattern, not a reset. Never infer "rewritten" from raw ahead/behind.

## Duplicate commits (ancestry gap without a content gap)

```bash
git show <sha> | git patch-id --stable          # compare two candidates by patch
git rev-parse <ref>:<path>                      # compare the blobs they touched
git diff --stat origin/A origin/B               # the actual content delta
```

A cherry-pick/rebase leaves the same change under two SHAs. Equal `patch-id` + equal file blobs = the change is present; only the commit object is absent. Report it as a duplicate, and never propose merging a lane back to "close" it.

## What changed between two refs

```bash
git diff --stat A B        # never assert "content-identical" without this
git diff --name-only A B | wc -l
git log --oneline A..B -- <path>
```

Quote the file and the line delta. "Diff is empty" is a measurement others will act on, so it needs its command output — an unmeasured "identical" is how a real 160-line pending promotion gets reported as nothing to chase.

## Counting rows in a markdown table

```bash
git show <ref>:path | grep -c '^|'          # header + separator + data rows
git show <ref>:path | grep -c '^| \`'       # data rows only (cells opening with a code span)
```

`20` leading-pipe lines is not "20 rows"; state the arithmetic you used (20 = header + separator + 18 rows) so the next run cannot read a different number into it.

## Test / assertion counts

```bash
git show <ref>:<testfile> | grep -cE '^\s*(it|test)\('
git show <ref>:<testfile> | grep -c 'it\.each'
```

Blocks ≠ executed tests: each `it.each(table)` row becomes its own test. A PR claiming "86 tests" over 49 blocks plus three tables is consistent; check the tables before disputing it.
