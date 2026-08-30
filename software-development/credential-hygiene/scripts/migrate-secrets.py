#!/usr/bin/env python3
"""Move plaintext credential lines out of a source file into a gitignored
destination store (e.g. CLAUDE.local.md). Values are read from the source at
runtime and NEVER printed raw — stdout shows [REDACTED] only.

Usage:
  python3 migrate-secrets.py <source> <destination>

Behavior:
  - Lines matching SECRET_RE under the marker header are moved.
  - The header in the source is replaced with a pointer note.
  - Non-secret lines inside the section (e.g. "- Default git user: ...") stay.
  - Prints the count moved and redacted previews; aborts if nothing found.
"""
import os
import re
import sys

SECRET_RE = re.compile(
    r"(github_pat_[A-Za-z0-9_]+|ghp_[A-Za-z0-9]+|sk-kimi-[A-Za-z0-9_-]+|"
    r"sk-ant-api03-[A-Za-z0-9_-]+|sk-proj-[A-Za-z0-9_-]+|"
    r"AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]+|whsec_[A-Za-z0-9]+|"
    r"50eb[0-9a-f]{20}\.[A-Za-z0-9]+)"
)
HEADER = "## Credentials (Global)"  # section marker; adjust per source file


def redact(line: str) -> str:
    return SECRET_RE.sub("[REDACTED]", line)


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    src, dst = os.path.expanduser(sys.argv[1]), os.path.expanduser(sys.argv[2])

    with open(src, encoding="utf-8") as f:
        lines = f.readlines()

    moved: list[str] = []
    kept: list[str] = []
    in_creds = False
    for ln in lines:
        stripped = ln.strip()
        if stripped == HEADER:
            in_creds = True
            kept.append("## Credentials (Global) — values MOVED to gitignored "
                        "store (see %s)\n" % dst)
            continue
        if in_creds and stripped.startswith("## "):
            in_creds = False
        if in_creds:
            if SECRET_RE.search(ln):
                moved.append(ln)
            else:
                kept.append(ln)
        else:
            kept.append(ln)

    if not moved:
        print("NO SECRET LINES FOUND — nothing to move; aborting.")
        sys.exit(1)

    with open(src, "w", encoding="utf-8") as f:
        f.writelines(kept)

    with open(dst, "a", encoding="utf-8") as f:
        f.write("\n## Credentials (moved from %s — %s)\n" % (src, __import__("datetime").date.today()))
        f.writelines(moved)

    print(f"MOVED {len(moved)} credential line(s):")
    for ln in moved:
        print("  " + redact(ln).strip())


if __name__ == "__main__":
    main()
