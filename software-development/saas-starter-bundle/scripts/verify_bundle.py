#!/usr/bin/env python3
"""Pre-flight check for a distributable bundle.

Run against the bundle directory BEFORE packaging and again AFTER extracting it elsewhere. It does
three things a "did it build?" glance does not:

  1. compiles every Python file and reports REAL exit codes (never `cmd | head && echo OK`)
  2. scans for credential patterns (hard stop)
  3. scans for personal-data patterns (triage: comments are cosmetic, logic is a defect)

Usage:
    python3 verify_bundle.py /path/to/bundle
    python3 verify_bundle.py /path/to/bundle --allow-pattern "+1-555"   # known-safe leftover

Exit 1 if compilation fails, a build artifact is present, or a credential pattern matches.
Personal-data hits are printed but do not fail the run -- triage them by hand.
"""
import argparse
import pathlib
import py_compile
import re
import sys

CREDENTIALS = {
    "api-key": re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,}|sk-ant-[A-Za-z0-9_\-]{16,}|AIza[A-Za-z0-9_\-]{20,})\b"),
    "bearer-token": re.compile(r"(?i)\b(bearer\s+[A-Za-z0-9_\-\.]{20,}|token\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{20,})"),
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "long-hex-id": re.compile(r"\b[0-9a-f]{32,}\b"),
}

PERSONAL = {
    "email": re.compile(r"\b[\w\.\-\+]+@[\w\-]+\.[\w\.\-]+\b"),
    "phone": re.compile(r"\b\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}\b"),
    "home-dir": re.compile(r"/(?:Users|home)/[A-Za-z0-9._\-]+"),
    "deployment-path": re.compile(r"/(?:opt|srv|var)/[\w\.\-/]*\b(?:profiles|attachments|deploy)\b"),
}

BUILD_ARTIFACTS = ("__pycache__", ".pyc", ".pyo")
TEXT_SUFFIXES = (".py", ".js", ".ts", ".html", ".md", ".json", ".sh", ".yml", ".yaml",
                 ".sql", ".toml", ".example")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="bundle directory to verify")
    ap.add_argument("--allow-pattern", action="append", default=[],
                    help="literal string that may legitimately remain (repeatable)")
    a = ap.parse_args()

    root = pathlib.Path(a.root).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}")
        return 1

    files = [p for p in root.rglob("*") if p.is_file()]
    print(f"bundle: {root}\nfiles:  {len(files)}\n")
    failed = False

    # 1. build artifacts -- these leak the PRE-scrub bytecode and must never ship
    artifacts = [str(p.relative_to(root)) for p in files
                 if any(tok in p.name or tok in str(p) for tok in BUILD_ARTIFACTS)]
    if artifacts:
        failed = True
        print(f"BUILD ARTIFACTS present ({len(artifacts)}) -- remove before packaging:")
        for x in artifacts[:10]:
            print(f"   {x}")
    else:
        print("build artifacts : none")

    # 2. compile check with real exit codes
    py = [p for p in files if p.suffix == ".py"]
    bad = []
    for p in py:
        try:
            py_compile.compile(str(p), doraise=True, cfile="/tmp/_vb.pyc")
        except py_compile.PyCompileError as e:
            bad.append((str(p.relative_to(root)), str(e).splitlines()[-1][:140]))
    if bad:
        failed = True
        print(f"\nCOMPILE FAILURES ({len(bad)} of {len(py)}):")
        for f, e in bad:
            print(f"   {f}: {e}")
    else:
        print(f"compile         : {len(py)} files OK")

    # 3. scans
    def scan(patterns, label):
        hits = {k: [] for k in patterns}
        for p in files:
            if p.suffix.lower() not in TEXT_SUFFIXES and p.name not in (".env.example", ".gitignore"):
                continue
            try:
                t = p.read_text(errors="replace")
            except Exception:
                continue
            for allow in a.allow_pattern:
                t = t.replace(allow, "")
            for k, rx in patterns.items():
                for m in rx.finditer(t):
                    hits[k].append((str(p.relative_to(root)), m.group(0)[:60]))
        total = sum(len(v) for v in hits.values())
        print(f"\n{label}: {total} hit(s)")
        for k, v in hits.items():
            if not v:
                continue
            files_hit = sorted({f for f, _ in v})
            print(f"   {k:16} {len(v):4} across {len(files_hit)} file(s)")
            for f in files_hit[:5]:
                print(f"        {f}: {[s for ff, s in v if ff == f][:2]}")
        return total

    cred = scan(CREDENTIALS, "CREDENTIAL SCAN")
    pers = scan(PERSONAL, "PERSONAL-DATA SCAN (triage: comments are cosmetic, logic is a defect)")
    if cred:
        failed = True
        print("\nSTOP: credential-shaped string in the bundle. Do not ship.")

    print(f"\n{'FAIL' if failed else 'PASS'}  (personal-data hits: {pers} -- triage before shipping)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
