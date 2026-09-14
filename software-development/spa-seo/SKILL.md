---
name: spa-seo
description: Use when improving SEO on a client-rendered SPA static site.
---

# SPA SEO — technical SEO for client-rendered single-page apps

Audit + improvement workflow for SPAs (Vite/React etc.) where the landing is client-rendered and hosting is a static file server (e.g. `serve -s dist`, nginx SPA fallback). The marketing/content side (keywords, AI-citation strategy) lives in `marketing/seo-audit` and `marketing/ai-seo`; this skill is the ENGINEERING of making the SPA visible.

## Audit checklist (run before changing anything)

1. **Curl the live head**: `curl -s <url>/ | grep -o '<title>[^<]*</title>'` and grep for `og:title|twitter:card|rel="canonical"|application/ld+json|meta name="description"`. A bare SPA almost always has only a `<title>` — that's the gap.
2. **Curl robots.txt AND check who serves it.** If the first lines say `# As a condition of accessing this website...` or contain `BEGIN Cloudflare Managed content`, it's the **Cloudflare managed robots.txt** served at the edge — the origin/repo file is shadowed and will NOT take effect until a dashboard change (zone → Scrape Shield / Managed robots.txt → disable). Cloudflare's managed file blocks all AI bots (GPTBot, ClaudeBot, Google-Extended, CCBot, Bytespider) with `ai-train=no` — kills AI-citation SEO by default.
3. **Curl sitemap.xml and check the Content-Type/body.** `serve -s dist` (and most SPA fallbacks) returns **index.html with HTTP 200 for ANY unknown path** — so a missing sitemap.xml soft-404s to the HTML shell. Googlebot fetches it expecting XML. Same trap applies to robots.txt if the origin doesn't serve one.
4. **Check the router**: no router / path routes mean the landing `/` is the only real public surface; everything else is auth-gated. Don't invent sitemap URLs for auth pages.
5. **Check non-JS crawlability**: the static HTML has `<div id="root"></div>` and nothing else → AI crawlers that don't execute JS see a blank page.

## The fix (in order of value)

### 1. Full head in the static `index.html` (template: `templates/spa-head.html`)
- Keyword-rich `<title>` + `meta name="description"` (~155 chars)
- `link rel="canonical"`, `meta name="robots" content="index, follow, max-image-preview:large"`, `theme-color`
- Open Graph: `og:type/site_name/title/description/url/image` (+ `og:image:width/height/alt`, `og:locale`)
- Twitter: `summary_large_image` card
- JSON-LD `@graph` with WebSite + Organization + SoftwareApplication + FAQPage (FAQ answers must be grounded in REAL page copy — never invent capabilities; user rule). Validate with python `re.search` + `json.loads` after build.
- Vite copies `public/` → `dist/`, so static assets live there; `index.html` at app root is the build template.

### 2. `<noscript>` fallback mirroring the landing (non-JS crawlers)
Place it OUTSIDE `<div id="root">` (sibling after it) so React's `createRoot().render()` never wipes it. Mirror the landing's real structure: h1, tagline, feature list, pricing. This is legitimate (only non-JS clients see it), not hidden-text spam. Googlebot renders JS and sees the real app; the noscript serves AI/no-JS crawlers.

### 3. Real `sitemap.xml` in `public/`
Single `<url>` for the landing, `weekly`, priority 1.0. Only list genuinely public URLs. This fixes the soft-404 trap (static files take priority over the SPA fallback in `serve -s`).

### 4. Repo `robots.txt` in `public/`
`User-agent: * / Allow: /` plus explicit allows for GPTBot, ClaudeBot, PerplexityBot, Google-Extended (AI citation), and a `Sitemap:` line. Flag to the user that Cloudflare managed robots shadows it until the dashboard change.

### 5. OG image + favicon
- OG image: **use a real screenshot of the live landing** (user rejects AI mockups for product visuals). Capture via browser, then crop with `sips -c 630 1200 --cropOffset 0 40 <in> --out <out>` (offset x=40 centers the 1200-wide crop in a 1280 screenshot). Verify not-blank with `scripts/check-og-image.py` (vision analysis may be unavailable — don't block on it).
- **Capture pitfall (2026-08-10):** `wait_until="networkidle"` times out on pages with third-party analytics (Umami etc.) — the tracker keeps connections open. Use `wait_until="load"` + a fixed `wait_for_timeout(2500)` before screenshotting. For a 1440-wide viewport the crop offset is `--cropOffset 60 120` (y 60 skips the nav bar, x 120 centers 1200 in 1440). Confirm the result with `sips -g pixelWidth -g pixelHeight` (expect 1200 × 630) and file size ≥80KB (blank/grey screenshots come in far smaller).
- Favicon: reuse existing brand SVG geometry if the app has one (e.g. a logo component) on the brand's dark background.

### 6. Per-route meta for auth-gated surfaces (noindex)
A client-rendered SPA serves ONE index.html for every route, so the static head's `robots: index` would apply to login/register and tenant pages too. Add a small `RouteMeta` component rendered once inside the router (uses `useLocation` + a path map): sets `document.title` per route and **upserts a single `<meta name="robots">` node in `<head>`** — `index, follow, max-image-preview:large` on the landing only; `noindex, nofollow` on utility routes (login/register) and on tenant/subdomain surfaces (auth-gated apps: never index tenant pages). Create the meta node once (module-level ref or querySelector) and update `content` in place — never append duplicates. This is the client-side counterpart to `seo-auth-gated-saas`'s sitemap rule: keep noindex surfaces out of the sitemap AND mark them noindex in the head.

## Verification (always run these — "it works" needs real output)

1. `npm run build` (or package's build; NOT a bare `vite build` — the the harness terminal guard may flag it as a watch process).
2. Local smoke: `npx serve -s dist -l <PORT>` as a **background** process. **Check the port is free first** (`lsof -i :<port>`) — other projects' vite dev servers commonly squat on common ports and silently shadow yours.
3. Curl every artifact: `/` (title + og hit count), `/robots.txt`, `/sitemap.xml`, `/favicon.svg`, `/og-image.png` (expect 200 + correct content-type) AND an unknown route (expect 200 = SPA fallback intact).
4. Live production checks after deploy — **use a browser User-Agent** for python/curl fetches: Cloudflare 403s default python `urllib` UAs (HTTP 403 Forbidden). `python3` fetch with `headers={"User-Agent": "Mozilla/5.0 ... Chrome/126..."}` or just `curl -s` (curl's UA passes).
5. Validate prod JSON-LD parses and the noscript block is present.
6. Confirm branches sync + drift checks before wrap-up.

Automate the post-build head validation with `scripts/verify-seo-head.py` (run from the build root): asserts title/description/canonical/robots meta/theme-color, every og: tag, twitter:card, JSON-LD `@graph` node types (WebSite/Organization/SoftwareApplication/FAQPage), the $500-style Offer shape, NO `aggregateRating`, FAQ question count + grounding of the first answer, noscript present and positioned AFTER `<div id="root">`, and that analytics/favicon tags survived. It exits nonzero on any failure — run it before every deploy, not just the first. verify-seo-head.py samples ONLY the first FAQ answer; after any landing-copy edit run `scripts/check-faq-grounding.py` (built HTML vs JSX FAQ source) for the full byte-for-byte 6-pair comparison — FAQ answers drift silently when the landing text changes.

## Pitfalls
- `serve -s` SPA fallback returns 200 + HTML for ANY missing file — sitemap/robots "existed" in the sense of returning 200, but were soft-404s. Always check body/content-type, not status code.
- **Vite local preview of a main-domain landing: use `vite dev`, not `vite preview`.** Preview serves a PRODUCTION build where `import.meta.env.DEV` is false — any `.localhost`-host preview branch gated on `import.meta.env.DEV` never fires and the page silently renders the school/login route instead of the landing. Only `npm run dev` (DEV=true) triggers it. (Real failure 2026-08-10: 4 screenshot attempts returned the login page.) Also check the hostname predicate actually matches: `hostname === 'localhost'` does NOT match `the school-dismissal SaaS.localhost` — `endsWith('.localhost')` is the correct test. And if the project delegates detection to a `mainDomain.js`-style module, patch the fix THERE — the inline copy can look fixed while the live module still gates on DEV.
- Cloudflare managed robots.txt: origin file is shadowed until dashboard change — tell the user it's a one-time dashboard action, not a repo fix.
- Cloudflare 403s non-browser UAs — always spoof a browser UA for prod fetches.
- Port conflicts on local smoke tests — verify `lsof` before starting the server.
- Don't add auth-gated pages to the sitemap — they 401/403 to crawlers.
- The 1.48 MB JS bundle chunk warning is common for Three.js SPAs — note it as a follow-up, don't fix it in an SEO pass.
