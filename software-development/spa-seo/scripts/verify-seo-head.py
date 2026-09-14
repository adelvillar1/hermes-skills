#!/usr/bin/env python3
"""Post-build SEO head verification for a client-rendered SPA (Vite/React).

Run from the build root (the dir containing index.html, e.g. `frontend/` after
`npm run build`). Exits nonzero on any failure — run before every deploy.

Usage: python3 verify-seo-head.py [path/to/index.html]
"""
import json
import re
import sys

HTML = sys.argv[1] if len(sys.argv) > 1 else "dist/index.html"

def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))
    return cond

ok = True
html = open(HTML, encoding="utf-8").read()

# 1. Primary meta
ok &= check("title", "<title>" in html)
ok &= check("meta description", 'name="description"' in html)
ok &= check("robots meta", 'name="robots" content="index, follow, max-image-preview:large"' in html)
ok &= check("canonical", 'rel="canonical"' in html)
ok &= check("author", 'name="author"' in html)
ok &= check("theme-color", 'name="theme-color"' in html)

# 2. Open Graph (every og: tag must be present with a value)
og = dict(re.findall(r'property="og:([^"]+)" content="([^"]*)"', html))
for k in ["type", "site_name", "title", "description", "url", "image",
          "image:width", "image:height", "locale"]:
    ok &= check(f"og:{k}", bool(og.get(k)), og.get(k, "MISSING"))

# 3. Twitter
tw = dict(re.findall(r'name="twitter:([^"]+)" content="([^"]*)"', html))
ok &= check("twitter:card", tw.get("card") == "summary_large_image", tw.get("card"))
ok &= check("twitter:image", "og-1200x630.png" in tw.get("image", ""))

# 4. JSON-LD
m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
if not m:
    ok &= check("JSON-LD present", False)
else:
    try:
        data = json.loads(m.group(1))
        graph = data.get("@graph", [])
        types = [n.get("@type") for n in graph]
        ok &= check("JSON-LD @graph >=4 nodes", len(graph) >= 4, str(len(graph)))
        for t in ["WebSite", "Organization", "SoftwareApplication", "FAQPage"]:
            ok &= check(f"JSON-LD {t}", t in types)
        sw = next((n for n in graph if n.get("@type") == "SoftwareApplication"), {})
        ok &= check("SoftwareApplication offers", len(sw.get("offers", [])) >= 1, str(len(sw.get("offers", []))))
        ok &= check("no aggregateRating", "aggregateRating" not in json.dumps(data))
        faq = next((n for n in graph if n.get("@type") == "FAQPage"), {})
        qs = faq.get("mainEntity", [])
        ok &= check("FAQ questions >0", len(qs) > 0, str(len(qs)))
        if qs:
            ok &= check("FAQ grounded (non-empty answer)",
                        len(qs[0].get("acceptedAnswer", {}).get("text", "")) > 20)
    except Exception as e:
        ok &= check("JSON-LD parses", False, str(e))

# 5. noscript fallback: present AND positioned after #root (sibling, not child)
ok &= check("noscript present", "<noscript>" in html)
try:
    ok &= check("noscript outside root", html.index("<noscript>") > html.index('<div id="root">'))
except ValueError:
    ok &= check("noscript outside root", False, "marker not found")

# 6. Analytics / favicon preserved (edit the patterns to match the app)
ok &= check("analytics preserved", "umami" in html or "gtag" in html or "plausible" in html)
ok &= check("favicon preserved", 'rel="icon"' in html)

print("RESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 1)
