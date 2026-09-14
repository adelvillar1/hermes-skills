---
name: timeline-verification
description: Use when dating a project milestone for a factual answer.
---

# Timeline Verification — "When did X actually happen?"

Dating a project milestone (first deploy, launch, creation, domain registration) to produce a FACTUAL, often external-facing answer (customer, district, audit, vendor questionnaire). Different deliverable from a retrospective: the output is one defensible date plus confidence and known unknowns, not a narrative.

## When to use

- "When was this site created / first deployed / launched?" for a customer, district, or audit
- User challenges a date you stated ("are you sure it was deployed then?") — re-verify from independent records before answering; never re-assert the nearest record
- Any factual claim about project history that will be quoted outside the team

## Cross-reference the independent records

No single record is complete. Each proves a different thing and has different gaps:

| Record | How to get it | What it proves | Retention / gaps |
|---|---|---|---|
| GitHub repo created_at | `gh api repos/OWNER/REPO --jq .created_at` | Project birth on GitHub | Complete |
| Full commit history | `gh api .../commits?per_page=100 --paginate` | Development activity dates; activity gaps | Complete; but gaps = dormancy, NOT absence of deployment |
| Domain registration | `whois DOMAIN` → Creation Date | When the domain was secured | Complete; registry is authoritative for external answers |
| Session recaps / project docs | `docs/recaps/`, `docs/` | Narrative of provisioning work | Only as old as the methodology — earliest recap ≠ earliest activity |
| Host deploy list | `railway deployment list` | Actual deploys with SHAs | **Retention-limited** — Railway prunes old entries (observed: only ~3 weeks back) |
| Host project JSON | `railway status --json` | Env/service metadata | Scan for old timestamps; not guaranteed present |
| Live DB earliest row | `SELECT MIN(created_at) ...` / earliest audit-log row | Ground truth for "has this ever served anyone" | Usually needs approval (prod-DB rules); the only record that proves USE |

## Distinguish three different questions

Users (and vendors answering districts) conflate these:

1. **When was the CODE created?** → first commit / repo created_at
2. **When was it first DEPLOYED to production?** → host records, deploy recaps
3. **When was it first USED by real users?** → earliest DB row, user records

Answer all three explicitly, or pin which one was actually asked. "The site has been operational since X" requires evidence of *use*, not just commits.

## Integrity checks

- **Author vs committer dates**: divergence reveals rebasing/squashing distortion. `gh api ... --jq '.commit.author.date, .commit.committer.date'` on the earliest commits. If they match, "first commit" is trustworthy as a creation date.
- **Confirm the pagination total**: `--paginate` then count; a missing month in the monthly histogram is either dormancy or a fetch bug — verify which.
- **Two records agreeing** (e.g., commit-per-day counts matching session recaps) is strong evidence; say so when it happens.

## Pitfalls

- **Migrated/shallow repos mislead.** A local clone whose history starts recently does NOT mean the project started then. Always compare local vs remote first.
- **Dormancy ≠ absence of deployment.** Zero commits for months proves nothing was being *developed*; it does not prove the site wasn't *hosted*. Only host records or DB rows prove deployment/use. Phrase negative findings as "no record of", never "never happened".
- **User memory vs registry.** When the user's recalled date differs from the registry (e.g., remembered Sep 21, whois says Aug 21), the registry is authoritative for external answers — state the discrepancy plainly, don't silently pick one.
- **Deploy-list retention.** Absence from `railway deployment list` proves nothing about deploys older than its retention. Pair it with recaps/commits for older claims.
- **Claims must match evidence scope.** "Auth was broken until date X" (from a fix-recap) supports "could not have served users before X" — a strong, scoped inference. Use it; don't overreach past it.
- **Deliverable shape.** Final answer = timeline table (event / date / source) + explicit statement of the remaining unknown and the one check that could close it (e.g., earliest prod DB row, offered but not run without approval).

## Worked example

