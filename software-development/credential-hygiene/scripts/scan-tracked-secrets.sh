#!/usr/bin/env bash
# Definitive secret scan: only git-tracked files (ignored/untracked files are skipped,
# so .env / CLAUDE.local.md holding keys by design do NOT cry wolf).
# Usage: cd <repo> && bash scan-tracked-secrets.sh [extra_regex]
# Exit 0 = clean, 1 = hits found.
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not a git repo"; exit 2; }
cd "$ROOT" || exit 2

PAT='github_pat_[A-Za-z0-9_]+|ghp_[A-Za-z0-9]+|sk-ant-api03-[A-Za-z0-9_-]+|sk-proj-[A-Za-z0-9_-]+|sk-kimi-[A-Za-z0-9_-]+|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]+|whsec_[A-Za-z0-9]+|50eb[0-9a-f]{20}\.[A-Za-z0-9]+'
if [ "$#" -ge 1 ] && [ -n "$1" ]; then
  PAT="$PAT|$1"
fi

# Capture hits into a variable — do NOT pipe to head, it masks grep's exit code.
HITS="$(git ls-files -z | xargs -0 grep -lE "$PAT" 2>/dev/null)"

if [ -n "$HITS" ]; then
  echo "!!! FOUND in tracked files:"
  echo "$HITS"
  exit 1
else
  echo "CLEAN — zero matches in git-tracked files"
fi
