# Data Source Reconnaissance with Browser Automation

Session: 2026-05-14
Context: Evaluating WhatsInPort.com as a data source for port facility information.

## The Pattern

Before building a scraper for a new data source, use the browser to verify the site is actually accessible and the data exists. This 5-minute check prevents hours of wasted development.

### Step-by-Step Reconnaissance

1. **Navigate to the site's homepage** (browser or curl)
   ```bash
   # Browser approach (may be blocked)
   curl -s -X POST http://127.0.0.1:10086/command \
     -H "Content-Type: application/json" \
     -d '{"action":"navigate","args":{"url":"https://www.whatsinport.com","newTab":true},"session":"recon"}'

   # Fallback: curl with real User-Agent (BROWSER MAY RETURN EMPTY HTML
   # while curl works fine — some sites block browser-instrumentation but
   # allow standard HTTP clients)
   curl -s -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
     'https://www.whatsinport.com' | head -100
   ```

2. **Discover the site's actual URL structure from its own navigation** — DO NOT GUESS.
   ```bash
   # Look at the homepage source for links/navigation patterns
   curl -s -A 'Mozilla/5.0' 'https://www.whatsinport.com' | grep 'option value='
   # → Reveals country pages are .html, not .aspx

   # Follow country pages to discover port URLs
   curl -s -A 'Mozilla/5.0' 'https://www.whatsinport.com/France.html' | grep 'href='
   # → Reveals port pages are .htm (Ajaccio-Corsica.htm), not derived from our slugs
   ```
   
   **Anti-pattern**: Guessing URLs from your own database slugs and adding extensions you assume are correct (e.g., `/{slug}.aspx`, `/{slug}.html`). This is the #1 cause of "page not found" errors. The site's URL naming convention is THEIR choice — discover it from their navigation, don't impose yours.

3. **Test discovered URLs with 3-5 known ports**

3. **Check the page content**
   - Is it the real port page or a security interstitial?
   - Look for: page title, main heading, expected data sections
   - Check HTML length — real pages are 50KB+; blocked pages are ~12KB

4. **Verify data structure**
   - Does the page contain the expected data fields?
   - Is the data in HTML, JSON, or rendered by JavaScript?
   - Can it be extracted with Cheerio or does it need Playwright?

5. **Test from the target environment**
   - If scraping from Railway, test from Railway (different IP = different bot detection)
   - The site may work locally but block datacenter IPs

## WhatsInPort.com Case Study (Updated 2026-05-14)

**What we expected (first attempt):**
- URL pattern: `https://www.whatsinport.com/{slug}.aspx`
- Data: port facilities, terminal info, port authority contact

**What we found initially (wrong conclusion):**
- All URL patterns returned "Sorry page not found!"
- Assumed the site was blocked to automated access
- Scrapped 1,152 ports of garbage data

**Root cause — NOT site blocking, WRONG URLs:**
- The site uses `.html` for country pages, `.htm` for port pages — NOT `.aspx`
- URLs use the site's OWN naming: `Ajaccio-Corsica.htm` not `ajaccio.aspx`
- We were guessing URLs from our database slugs instead of discovering them from the site's navigation

**Correct discovery (2026-05-14):**
```bash
# Step 1: Homepage reveals country structure
curl -s -A 'Mozilla/5.0' 'https://www.whatsinport.com' | grep 'option value='
# → Countries use .html files (France.html, Italy.html, etc.)

# Step 2: Country page reveals port links
curl -s -A 'Mozilla/5.0' 'https://www.whatsinport.com/France.html' | grep 'href='
# → Ports use .htm, named like Ajaccio-Corsica.htm, Antibes.htm, etc.

# Step 3: Extract all 172 countries → 1,287 port URLs
python3 scripts/fetch-wip-ports.py

# Step 4: Match to our port slugs (country-scoped fuzzy matching)
python3 scripts/match-wip-ports.py
# → 660 high-confidence matches (score ≥ 0.93)
```

## Red Flags That Should Have Triggered Earlier Detection

1. **All ports had the same HTML length** (~12KB) — real sites have variance
2. **Port names were generic** (`whatsinport.com`, `403 - Forbidden`) — not actual port names
3. **the LLM provider returned empty JSON for 100% of ports** — a quality check would have caught this
4. **The scraper "succeeded" for 1,152 ports** — success rate too high for a site with missing pages

## Correct Workflow

```
Before building scraper:
  1. Manual browser check (5 min)
  2. Verify 3-5 sample pages have real data
  3. Check HTML length variance
  4. Only THEN write scraper code

After first batch:
  1. Inspect raw HTML for 3-5 ports
  2. Verify data quality heuristics pass
  3. Only THEN run the LLM provider structuring
  4. Inspect structured output for 3-5 ports
  5. Only THEN run full batch
```

## Data Quality Heuristics

Before running batch processing on scraped HTML:

| Heuristic | Pass Threshold | WhatsInPort Result |
|-----------|---------------|-------------------|
| HTML length | >30KB (real pages have content) | ❌ 12KB |
| Page title | Contains port name, not domain | ❌ "whatsinport.com" |
| Expected keywords | "terminal", "dock", "berth", "facilities" | ❌ None |
| Port name extraction | Matches expected port name | ❌ Generic/domain name |
| Variance across ports | Different HTML lengths | ❌ All identical |

If any heuristic fails, STOP and investigate before processing.

## Integration with Scraper Development

Add a `validateHtml()` function to every scraper:

```typescript
function validateHtml(html: string, portSlug: string): { valid: boolean; reason?: string } {
  if (html.length < 15000) {
    return { valid: false, reason: `HTML too short (${html.length} bytes)` };
  }
  if (html.includes('Sorry page not found')) {
    return { valid: false, reason: 'Page not found interstitial' };
  }
  if (html.includes('Checking the site connection security')) {
    return { valid: false, reason: 'Cloudflare/security challenge' };
  }
  const expectedKeywords = ['terminal', 'dock', 'berth', 'facilities', 'port'];
  const hasKeywords = expectedKeywords.some(kw => html.toLowerCase().includes(kw));
  if (!hasKeywords) {
    return { valid: false, reason: 'Missing expected port keywords' };
  }
  return { valid: true };
}
```

Call this BEFORE storing raw HTML and BEFORE calling the LLM provider.

## Lesson

**The WhatsInPort scraper was built backwards:** code first, verification second. The correct order is:
1. Verify site accessibility (browser reconnaissance)
2. Verify data quality (sample HTML inspection)
3. Build scraper
4. Run with validation
5. Process structured output

This would have saved ~2 hours of development + ~$5-10 in the LLM provider quota + the time to clean up 1,152 garbage rows.
