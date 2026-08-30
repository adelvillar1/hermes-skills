# Command Recipes — Commit History Analysis

Exact slicing commands operating on the pipe-delimited `/tmp/gh_commits.txt`
(`date|author|subject`, produced by the `gh api` pull in SKILL.md step 1).

## Pull full history from GitHub

```bash
gh api "repos/<owner>/<repo>/commits?sha=main&per_page=100" --paginate \
  -q '.[] | "\(.commit.author.date)|\(.commit.author.name)|\(.commit.message | split("\n")[0])"' \
  > /tmp/gh_commits.txt
wc -l /tmp/gh_commits.txt
```

## Date range + totals

```bash
echo "First: $(tail -1 /tmp/gh_commits.txt | cut -d'|' -f1)"
echo "Last:  $(head -1 /tmp/gh_commits.txt | cut -d'|' -f1)"
```

## Commit type distribution

```bash
cut -d'|' -f3 /tmp/gh_commits.txt \
  | sed -E 's/^([a-z]+)(\(.*)?[!:].*/\1/' | sort | uniq -c | sort -rn | head -15
```

## Commits by month

```bash
cut -d'|' -f1 /tmp/gh_commits.txt | cut -dT -f1 | cut -d'-' -f1,2 | sort | uniq -c | sort -k2
```

## Commits by hour (UTC) and day of week

```bash
# hour
cut -d'|' -f1 /tmp/gh_commits.txt | cut -dT -f2 | cut -d: -f1 | sort | uniq -c | sort -k2n
# day of week (1=Mon..7=Sun) — macOS date syntax
cut -d'|' -f1 /tmp/gh_commits.txt | cut -dT -f1 | while read d; do
  date -j -f "%Y-%m-%d" "$d" "+%u" 2>/dev/null
done | sort | uniq -c | sort -k2n
```

## fix:feat ratio by month

```bash
for m in 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07; do
  f=$(grep "^$m" /tmp/gh_commits.txt | cut -d'|' -f3 | grep -c '^fix')
  ft=$(grep "^$m" /tmp/gh_commits.txt | cut -d'|' -f3 | grep -c '^feat')
  echo "$m: fix=$f feat=$ft"
done
```

## Busiest days

```bash
cut -d'|' -f1 /tmp/gh_commits.txt | cut -dT -f1 | sort | uniq -c | sort -rn | head -10
```

## Authors (human vs AI agents)

```bash
cut -d'|' -f2 /tmp/gh_commits.txt | sort | uniq -c | sort -rn | head -15
```

## Per-workstream bucket (template)

Define a strict regex for the domain, then count total + fixes + monthly split.
Run for EACH workstream with its own pattern.

```bash
PAT='corridor|family|families|clan|topology|signature|hierarchy'   # example
total=$(grep -iE "$PAT" /tmp/gh_commits.txt | wc -l | tr -d ' ')
fixes=$(grep -iE "$PAT" /tmp/gh_commits.txt | grep -c '|fix')
echo "$fixes / $total = $(( fixes * 100 / total ))% fix rate"

# monthly split
for m in 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07; do
  n=$(grep "^$m" /tmp/gh_commits.txt | grep -icE "$PAT")
  echo "$m: $n"
done
```

## Chronological narrative for a workstream (oldest first)

macOS has no `tac` — use `tail -r` to reverse:

```bash
grep -iE "$PAT" /tmp/gh_commits.txt | tail -r \
  | cut -d'|' -f1,3 | sed 's/T.*Z|/ | /'
```

Page through long lists with `| head -80` then `| tail -n +81`.

## Sample spot-check (validate a loose bucket)

Always eyeball 20-30 matches before trusting a count:

```bash
grep -iE "$PAT" /tmp/gh_commits.txt | head -30 | cut -d'|' -f3
```

## Deploy cadence (staging vs prod gates)

```bash
grep -c "into staging" /tmp/gh_commits.txt        # staging deploys
grep -c "Merge branch 'staging'" /tmp/gh_commits.txt  # prod merges
```

## Largest commits by churn (needs local repo, not the API file)

```bash
git log --all --format='%H %s' | while read hash msg; do
  churn=$(git show --stat "$hash" 2>/dev/null | tail -1 | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+')
  echo "${churn:-0} | $msg"
done | sort -rn | head -10
```
