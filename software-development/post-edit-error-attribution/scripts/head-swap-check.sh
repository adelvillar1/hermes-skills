#!/usr/bin/env bash
# head-swap-check.sh — attribute a post-edit error to your change or to HEAD.
#
# Swaps the HEAD version of a file in, runs a check command, restores yours.
# The restore is chained so it can't be forgotten, even if the check exits
# non-zero (which lint/typecheck usually do when they find errors).
#
# Usage:
#   ./head-swap-check.sh <file> <check command...>
#
# Examples:
#   ./head-swap-check.sh web/src/pages/WineClub.tsx npx eslint web/src/pages/WineClub.tsx
#   ./head-swap-check.sh src/foo.py ruff check src/foo.py
#   ./head-swap-check.sh src/bar.ts npx tsc --noEmit
#
# Interpret the output:
#   - HEAD run shows the SAME error(s)  -> pre-existing, not introduced by you
#   - HEAD run is clean                 -> you introduced it; fix it
#   - HEAD run shows different/fewer    -> you introduced the delta
#
# After running, always re-run your normal build/check once more so the final
# verification reflects the exact on-disk state, and confirm with
# `git status --short` that only your intended files are modified.

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <file> <check command...>" >&2
  exit 2
fi

FILE="$1"
shift

if [ ! -f "$FILE" ]; then
  echo "error: '$FILE' not found" >&2
  exit 2
fi

# New files have no HEAD version — the error is necessarily yours.
if ! git cat-file -e "HEAD:$FILE" 2>/dev/null; then
  echo "'$FILE' does not exist at HEAD (new file) — any error in it is yours."
  exit 0
fi

TMP="$(mktemp /tmp/head-swap.XXXXXX)"
trap 'rm -f "$TMP"' EXIT

cp "$FILE" "$TMP"
git show "HEAD:$FILE" > "$FILE"

echo "=== check output against HEAD version of $FILE ==="
# Don't let a non-zero exit (normal for lint/typecheck with findings) abort us
# before the restore.
set +e
"$@"
STATUS=$?
set -e

cp "$TMP" "$FILE"
echo "=== restored your version of $FILE (check exit code: $STATUS) ==="
