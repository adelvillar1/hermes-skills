#!/usr/bin/env bash
# history_report.sh — pull FULL commit history from GitHub and print the
# standard analytics dimensions. Avoids the shallow-local-clone trap by going
# straight to the remote via `gh api`.
#
# Usage:
#   history_report.sh <owner/repo> [branch]
#   history_report.sh adelvillar1/cruise-intelligence main
#
# Requires: gh (authenticated), standard POSIX tools.
set -euo pipefail

REPO="${1:?usage: history_report.sh <owner/repo> [branch]}"
BRANCH="${2:-main}"
OUT="$(mktemp /tmp/gh_commits.XXXXXX.txt)"

echo "==> Counting commits on $REPO @ $BRANCH (via Link header)..."
TOTAL=$(gh api "repos/$REPO/commits?sha=$BRANCH&per_page=1" -i 2>/dev/null \
  | grep -i '^link:' | grep -oE 'page=[0-9]+>; rel="last"' | grep -oE '[0-9]+' || echo "?")
echo "    total commits: $TOTAL"

echo "==> Pulling full history (paginated)..."
gh api "repos/$REPO/commits?sha=$BRANCH&per_page=100" --paginate \
  -q '.[] | "\(.commit.author.date)|\(.commit.author.name)|\(.commit.message | split("\n")[0])"' \
  > "$OUT"
echo "    fetched: $(wc -l < "$OUT") lines -> $OUT"
echo

echo "=== DATE RANGE ==="
echo "First: $(tail -1 "$OUT" | cut -d'|' -f1)"
echo "Last:  $(head -1 "$OUT" | cut -d'|' -f1)"
echo

echo "=== COMMITS BY MONTH ==="
cut -d'|' -f1 "$OUT" | cut -dT -f1 | cut -d'-' -f1,2 | sort | uniq -c | sort -k2
echo

echo "=== COMMIT TYPE DISTRIBUTION ==="
cut -d'|' -f3 "$OUT" | sed -E 's/^([a-z]+)(\(.*)?[!:].*/\1/' | sort | uniq -c | sort -rn | head -15
echo

echo "=== COMMITS BY HOUR (UTC — convert to user TZ before narrating) ==="
cut -d'|' -f1 "$OUT" | cut -dT -f2 | cut -d: -f1 | sort | uniq -c | sort -k2n
echo

echo "=== COMMITS BY DAY OF WEEK (1=Mon..7=Sun) ==="
cut -d'|' -f1 "$OUT" | cut -dT -f1 | while read -r d; do
  date -j -f "%Y-%m-%d" "$d" "+%u" 2>/dev/null || date -d "$d" "+%u" 2>/dev/null || true
done | sort | uniq -c | sort -k2n
echo

echo "=== TOP 10 BUSIEST DAYS ==="
cut -d'|' -f1 "$OUT" | cut -dT -f1 | sort | uniq -c | sort -rn | head -10
echo

echo "=== AUTHORS (human vs agent) ==="
cut -d'|' -f2 "$OUT" | sort | uniq -c | sort -rn | head -15
echo

echo "=== FIX:FEAT MATURITY CURVE (by month) ==="
for m in $(cut -d'|' -f1 "$OUT" | cut -dT -f1 | cut -d'-' -f1,2 | sort -u); do
  f=$(grep "^$m" "$OUT" | cut -d'|' -f3 | grep -c '^fix' || true)
  ft=$(grep "^$m" "$OUT" | cut -d'|' -f3 | grep -c '^feat' || true)
  echo "$m: fix=$f feat=$ft"
done
echo

echo "=== DEPLOY CADENCE ==="
echo "staging merges: $(grep -c 'into staging' "$OUT" || true)"
echo "prod (main) merges: $(grep -c "Merge branch 'staging'" "$OUT" || true)"
echo

echo "Full log saved at: $OUT"
echo "Run references/recipes.md §4/§5 against it for fix attribution + file churn."
