#!/usr/bin/env python3
"""Audit a BUILT archive for credentials before handing it to anyone.

Two passes, because neither alone works:

  1. BY NAME  — credential/state files (auth.json, .env, *.pem, config.yaml, ...) that should not be
                in a distributable archive at all.
  2. BY SHAPE — opaque secret material: a quoted run of 80+ characters with no whitespace. This is
                the pass that matters most. A credential store nests its secrets under a key like
                `access_token`, and the value matches no keyword pattern: `sk-`, `Bearer` and
                `API_KEY=` all miss it. A token is not a keyword, it is an opaque string.

Run this on the ARCHIVE, not the source tree. Reading the built artifact is the only way to prove
what actually shipped, and re-run it after every change to your exclusion list — an audit that passes
*because* a file was excluded is only valid while the exclusion still holds.

Usage:
    python3 audit_archive_secrets.py <archive.tar.gz|archive.zip> [more...]

Exit codes: 0 = clean, 1 = findings, 2 = bad usage / unreadable archive.
"""

import re
import sys
import tarfile
import zipfile
from pathlib import PurePosixPath

# Files that must never travel. Matched on the basename.
CREDENTIAL_NAME = re.compile(
    r"(^\.env.*|^auth\.(json|lock)$|^credential.*|.*token.*\.json$|^config\.yaml$|^profile\.yaml$|"
    r"^\.netrc$|^\.npmrc$|^\.pypirc$|^\.git-credentials$|.*\.(pem|key|p12|pfx)$|^\.git/config$|"
    r"^\.docker/config\.json$|^id_(rsa|ed25519)$)",
    re.IGNORECASE,
)

# Opaque secret material: a long unbroken string standing alone inside quotes.
OPAQUE = re.compile(r"['\"]([A-Za-z0-9_\-+/=]{80,})['\"]")

# Keyword patterns: weak on their own, but cheap and they name the provider in the report.
KEYWORD = re.compile(
    r"\b(sk-[A-Za-z0-9_\-]{16,}|sk-ant-[A-Za-z0-9_\-]{16,}|AIza[A-Za-z0-9_\-]{20,}|"
    r"ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{12,})\b"
)

# File types worth reading. Skip binaries and anything large: a multi-MB blob is almost always data,
# not a config carrying a token.
TEXT_EXT = (".json", ".yaml", ".yml", ".py", ".js", ".ts", ".sh", ".bash", ".txt", ".md",
            ".html", ".htm", ".cfg", ".ini", ".toml", ".env", ".xml", ".sql", ".conf")
MAX_BYTES = 4_000_000


def members(path):
    """Yield (name, read_callable) for every regular file in the archive."""
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                yield info.filename, info.file_size, z.read(info.filename)
    elif path.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".tar")):
        with tarfile.open(path) as t:
            for m in t.getmembers():
                if not m.isfile():
                    continue
                fh = t.extractfile(m)
                yield m.name, m.size, (fh.read() if fh else b"")
    else:
        raise ValueError(f"unsupported archive type: {path}")


def audit(path):
    findings = {"name": [], "opaque": [], "keyword": []}
    scanned = 0
    total = 0

    for name, size, blob in members(path):
        total += 1
        base = PurePosixPath(name).name
        if CREDENTIAL_NAME.match(base):
            findings["name"].append((name, "credential-shaped filename"))
            continue  # read nothing further from a file we are already rejecting
        if size > MAX_BYTES or not name.lower().endswith(TEXT_EXT):
            continue
        try:
            text = blob.decode("utf8", "replace")
        except Exception:
            continue
        scanned += 1
        for m in OPAQUE.finditer(text):
            findings["opaque"].append((name, f"{len(m.group(1))}-char opaque string: {m.group(1)[:10]}..."))
        for m in KEYWORD.finditer(text):
            findings["keyword"].append((name, m.group(0)[:14] + "..."))

    print(f"\n{path}")
    print(f"  entries: {total:,}   text files scanned: {scanned:,}")
    for label, key, why in (
        ("CREDENTIAL FILES", "name", "must not be in a distributable archive"),
        ("OPAQUE STRINGS", "opaque", "credential-shaped; a keyword scan would miss these"),
        ("KEYWORD HITS", "keyword", "named provider patterns"),
    ):
        hits = findings[key]
        print(f"  {label:<17} {len(hits):>4}  ({why})")
        for f, detail in hits[:12]:
            print(f"      {f}: {detail}")
        if len(hits) > 12:
            print(f"      ... and {len(hits) - 12} more")
    return sum(len(v) for v in findings.values())


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    bad = 0
    for path in argv[1:]:
        try:
            bad += audit(path)
        except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as e:
            print(f"\n{path}: UNREADABLE — {e}")
            return 2
    if bad:
        print(f"\nFAIL: {bad} finding(s). Fix the exclusions and rebuild, then re-run this — the"
              f" archive that ships is the one that passes.")
        return 1
    print("\nCLEAN: no credential files, no opaque secret-shaped strings, no keyword hits.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
