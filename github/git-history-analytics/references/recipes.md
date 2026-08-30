# Git History Analytics — Command Recipes

Copy-paste building blocks. All assume `gh` is authenticated (`gh auth status`)
and you're in the repo. Replace `{owner}/{repo}` and `{branch}` as needed.

## §1. Pull the full history into a flat file

`gh api --paginate` walks every page. Output one `date|author|subject` per line
(subject = first line of the message, so multiline bodies don't break parsing):

```bash
gh api "repos/{owner}/{repo}/commits?sha={branch}&per_page=100" --paginate \
  -q '.[] | "\(.commit.author.date)|\(.commit.author.name)|\(.commit.message | split("\n")[0])"' \
  > /tmp/gh_commits.txt
wc -l /tmp/gh_commits.txt   # sanity check vs the rel="last" count
```

If the repo is large and you only need the local view, `git log --all
--format='%ai|%an|%s'` works — but only AFTER confirming the clone is full
(see SKILL.md CRITICAL).

## §2. Standard dimensions

Run against `/tmp/gh_commits.txt` (fields: 1=date, 2=author, 3=subject).

```bash
F=/tmp/gh_commits.txt

# Date range
echo "First: $(tail -1 $F | cut -d'|' -f1)"
echo "Last:  $(head -1 $F | cut -d'|' -f1)"

# Commits by month
cut -d'|' -f1 $F | cut -dT -f1 | cut -d'-' -f1,2 | sort | uniq -c | sort -k2

# Commit-type distribution (conventional-commit prefix)
cut -d'|' -f3 $F | sed -E 's/^([a-z]+)(\(.*)?[!:].*/\1/' | sort | uniq -c | sort -rn | head -15

# Commits by hour (UTC — convert to user TZ before narrating!)
cut -d'|' -f1 $F | cut -dT -f2 | cut -d: -f1 | sort | uniq -c | sort -k2n

# Commits by day of week (1=Mon .. 7=Sun; macOS date)
cut -d'|' -f1 $F | cut -dT -f1 | while read d; do
  date -j -f "%Y-%m-%d" "$d" "+%u" 2>/dev/null
done | sort | uniq -c | sort -k2n
# Linux: date -d "$d" "+%u"

# Top busiest days
cut -d'|' -f1 $F | cut -dT -f1 | sort | uniq -c | sort -rn | head -10

# Authorship split (human vs agent)
cut -d'|' -f2 $F | sort | uniq -c | sort -rn | head -15

# Deploy cadence — staging gate ratio
grep -c "into staging" $F          # staging deploys
grep -c "Merge branch 'staging'" $F # prod (main) merges
# staging:prod ratio ~5:1 = healthy validate-before-prod discipline
```

## §3. Maturity curve — fix:feat ratio per month

```bash
for m in 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07; do
  f=$(grep "^$m" $F | cut -d'|' -f3 | grep -c '^fix')
  ft=$(grep "^$m" $F | cut -d'|' -f3 | grep -c '^feat')
  echo "$m: fix=$f feat=$ft"
done
```

Interpret with the SKILL.md table. A month holding ~half the lifetime fix count
is the "wall" — connect it to the volume spike.

## §4. Fix attribution by category (strict buckets)

Extract fixes first, then bucket with ANCHORED patterns. Loose words (`port`,
`ship`, `map`) cross-cut pipeline and UI — keep patterns specific and always
spot-check.

```bash
cut -d'|' -f3 $F | grep '^fix' > /tmp/fixes.txt

# Data pipeline (strict)
grep -icE 'scrap|pipeline|junction|coherence|enrich|ingest|harvest|corridor|falkor|precompute|insight|materialized|redis|cache|worker|job|cron|dedup|upsert|prisma|jsonb|embedding|graph|signature|stale|drift|backfill|orphan|run_log|batch|delta|port.visit|port_visit|visit.*match|river.*(seg|snap|chain)|leg.*(speed|dist)' /tmp/fixes.txt

# UI / frontend (strict)
grep -icE '\bui\b|button|modal|layout|css|style|render|component|sidebar|nav\b|header|footer|responsive|mobile|viewport|scroll|font|color|theme|dark mode|icon|loading|spinner|tooltip|dropdown|form.*(field|input|valid)|placeholder|tailwind|className|z-index|overflow|tab\b|card\b|badge|pill|drawer|toast|hero|landing|screenshot|label.*(size|read)|contained=' /tmp/fixes.txt

# Build / import / type errors (refactor fallout)
grep -icE 'import|build error|type|typescript|\btsc\b|undefined|export.*(missing|shared|from)|duplicate defin|wrong import|sed|refactor|missing.*import|conflicting' /tmp/fixes.txt

# Auth / infra / deploy
grep -icE 'auth|login|session|csrf|token|webhook|deploy|railway|env|nextauth|middleware|401|403|404|500|email|resend|smtp|stripe|billing|subscription' /tmp/fixes.txt
```

Buckets overlap and won't sum to 100% — that's fine; report each as a share of
the total fix count and name the caveat. Spot-check `head -30` of the largest
bucket to confirm the patterns aren't sweeping in the wrong class.

## §5. Per-file fix churn (precision cross-check)

Needs full local history. Top files absorbing fix commits:

```bash
git log --all --grep='^fix' --format='%H' | while read h; do
  git show --stat --format='' "$h" 2>/dev/null | grep -oE '^ [^|]+\|'
done | sed 's/|//;s/^ //' | sort | uniq -c | sort -rn | head -20
```

Narrow to a subsystem by adding a pathspec, e.g.
`git log --all --grep='^fix' -- scraper-worker/ pipeline-worker/ scripts/insights/`.
