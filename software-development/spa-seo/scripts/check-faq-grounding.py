#!/usr/bin/env python3
"""Byte-compare JSON-LD FAQPage answers (built index.html) against the REAL
FAQ copy in the React source (Landing.jsx-style FAQS array).

Why: FAQ answers drift silently — a copy edit on the landing page leaves the
JSON-LD structured data advertising stale text. verify-seo-head.py only
samples the first answer; this checks every pair.

Usage:
    python3 check-faq-grounding.py <index.html> <Landing.jsx> [--json-ld-only]

Assumes the source FAQ array uses this exact shape (matches Landing.jsx):
    { q: 'Question?', a: 'Answer text.' },
and the JSON-LD FAQPage entries:
    {"@type":"Question","name":"Q","acceptedAnswer":{"@type":"Answer","text":"A"}}

The JSX regex is single-quote based; if the project uses double quotes or
template literals, adjust JSX_FAQ_RE. Unescapes \u2019/\u201c/\u201d escapes.

Exit code 0 = all answers byte-match; 1 = count mismatch or any mismatch.
"""
import html as h
import json
import re
import sys

JSX_FAQ_RE = re.compile(r"\{ q: '([^']+)', a: '((?:[^'\\]|\\.)*)' \}")
LD_JSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def load_jsx_faqs(path):
    src = open(path, encoding="utf-8").read()
    pairs = []
    for q, a in JSX_FAQ_RE.findall(src):
        # JSX string-literal escapes: unicode escapes the source uses
        norm = (a.replace("\\u2019", "\u2019").replace("\\u201c", "\u201c")
                 .replace("\\u201d", "\u201d").replace("\\'", "'"))
        pairs.append((q, norm))
    return pairs


def load_ld_faqs(path):
    idx = open(path, encoding="utf-8").read()
    m = LD_JSON_RE.search(idx)
    if not m:
        sys.exit("FAIL: no application/ld+json script found in " + path)
    data = json.loads(m.group(1))
    graph = data.get("@graph", [])
    faq = next((n for n in graph if n.get("@type") == "FAQPage"), None)
    if not faq:
        sys.exit("FAIL: no FAQPage node in JSON-LD @graph")
    return {q["name"]: h.unescape(q["acceptedAnswer"]["text"]) for q in faq["mainEntity"]}


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    idx_path, jsx_path = sys.argv[1], sys.argv[2]
    js_faqs = load_jsx_faqs(jsx_path)
    ld_faqs = load_ld_faqs(idx_path)
    ok = True
    print(f"JSX FAQ count: {len(js_faqs)} | JSON-LD count: {len(ld_faqs)}")
    if len(js_faqs) != len(ld_faqs):
        print("FAIL: question count mismatch")
        ok = False
    for q, a in js_faqs:
        match = ld_faqs.get(q) == a
        print(("PASS " if match else "FAIL ") + f"[{q}]" + ("" if match else
              f"\n  LD: {ld_faqs.get(q)!r}\n  JS: {a!r}"))
        ok = ok and match
    print("RESULT:", "ALL FAQ ANSWERS BYTE-MATCH" if ok else "MISMATCHES PRESENT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
