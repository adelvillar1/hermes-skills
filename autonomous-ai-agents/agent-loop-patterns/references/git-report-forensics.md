# Verifying git-state claims in a monitor's report

Scope: you are reviewing a recurring job's report about branches, PRs, plan indexes, deploys or test
gates. Each claim below has a cheap command that confirms or refutes it. Run it and quote the output —
a number that reproduces is evidence the run measured; one that does not is a guess dressed as a finding.

## Branches and divergence

| Claim in the report | Command | Trap |
|---|---|---|
| "N commits behind" | `git rev-list --count origin/<base> --not origin/<head>` | A `Merge <base> … (refresh #N)` commit in the head does **not** reduce the count. Carrying a refresh ≠ current. |
| "A is behind B" / "B is ahead" | `git rev-list --left-right --count A...B` | LEFT = only-A, RIGHT = only-B. A lane that contains the other is never "behind": report RIGHT=0 as contained/promoted. Quote the direction you measured. |
| "The extra commits are release merges" | `git rev-list --count --no-merges A..B` and `git log --no-merges --oneline A..B` | Name **every** non-merge commit. One fresh direct commit on a production branch is a bypass of the promotion flow, not the `--no-ff` pattern. This is the difference between bookkeeping and genuine lane divergence. |
| "A lane was reset / rewritten" | `--no-merges` on the same range | Never infer a rewrite from ahead/behind asymmetry. A `--no-ff` release flow permanently leaves release merges on the production branch; that is the normal shape. |
| "These refs are identical" | `git diff --stat A B` (plus `--name-only`) | Never assert equality without the diff. A single docs-file delta is still a real difference, and the direction matters (which side holds the file). |
| "The checkout is behind" | `git rev-list --count HEAD..@{upstream}` vs `git rev-parse --abbrev-ref HEAD` | Compare against the branch's **own upstream**, not the newest commit anywhere. A clone deliberately parked on the work branch while a deploy branch carries newer work is not stale — and calling it stale every run hides the real case. |

## Is a commit actually missing?

An ancestry gap is not a content gap. Cherry-picks, rebases and duplicated commits leave a SHA absent
while its change is fully present:

```bash
git show <sha> | git patch-id --stable            # compare with the candidate on the other branch
git rev-parse <ref>:<path>                        # and compare blobs of the files it touched
```

- Identical patch-id (or identical blobs) ⇒ "the change is present under another SHA", not "missing work".
- Distinct patch-id ⇒ a genuine content gap; report it as one.
- Consequence: **never** recommend merging a deploy lane back into the work branch to "close" an
  ancestry gap. That manufactures ancestry churn and can drag deletions into the work branch.
- The inverse also matters: a commit can exist on the deploy lanes and not on the work branch while its
  content is on all three. Say "SHA absent, content present" — do not let one phrase stand for the other.

## Markdown / index counts

- Data rows = lines matching `^|` **minus header and separator** when the table has both. State the rule
  you used; when precision matters, count rows with the stricter pattern (pipe, space, backticked slug)
  and say which rule produced the number.
- Re-measure every run. A count pinned into a prompt ("the index has N rows and never mentions X") is a
  standing falsehood the moment the subject changes; pin the *command*, date any remembered value, and
  mark it historical.
- A row can contradict the branch it lives on (status says "uncommitted" while the commits exist). Quote
  the row, then check the branch history before repeating it.

## Deploy status

- Commit statuses and check runs may come from a platform that has been **retired** under the job. Read
  the branch's own deploy documentation for the current platform before calling anything green.
- Measure the live surface directly and quote it: HTTP status, page title or asset hash, health endpoint,
  host/IP, certificate dates. `curl -sS -o /dev/null -w '%{http_code}' <url>` plus the health route is
  usually enough.
- A status context that stops updating (`inactive`) is evidence of stand-down, not health.
- If the current platform posts no status at all, say exactly that — "no platform-side signal; measured
  live at <time>" — instead of borrowing an old platform's green.
- Docs naming a public URL are not proof the URL serves: verify the host, and compare it with the app's
  own allowlist (CORS origins often record the real origin).

## Test gates

- Run the suite in a **scratch copy** of the PR head, never in the shared clone; end with the shared
  clone's `git status --short` empty.
- A runner's results cache (`node_modules/.vite/vitest/results.json` and friends) can be copied between
  scratch checkouts. Identical cached durations across two copies are not evidence that both suites ran.
  Re-run in the copy that holds the code under test and quote the runner's own pass count.
- Treat self-reported gate numbers as unverified until reproduced, and say which you did.

## Before contradicting a report

Re-measure like-for-like: same ref (local branch vs `origin/*`), same unit (commit count vs insertions),
same counting rule, same path depth. A nested install directory (e.g. `skills/skills/<name>`) is not a
missing install, and branch arithmetic from a sibling repository is not a contradiction. If the numbers
differ, check what you measured before concluding the report was wrong — a false correction costs more
trust than the error it corrects.
