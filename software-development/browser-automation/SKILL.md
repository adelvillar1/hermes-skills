---
name: browser-automation
description: Browser automation for web research, data extraction, and.
---

# Browser Automation with kimi-webbridge

Control the user's real Chrome browser for web research, data extraction, and interactive tasks. The browser runs with the user's actual login sessions — no separate authentication needed.

## When to Use

- **Nominatim/API data is insufficient** — e.g., river cruise docks not in OSM
- **Researching coordinates or locations** — cruise terminals, ports, landmarks
- **Verifying visual information** — checking satellite imagery, maps, photos
- **Extracting data from JavaScript-rendered pages** — SPAs, dynamic content
- **Interacting with websites** — forms, searches, navigation
- **Automated batch research pipelines** — when integrated into TypeScript scripts that run locally (not in CI/pipeline)

## Installation

```bash
curl -fsSL https://kimi-web-img.moonshot.cn/webbridge/install.sh | bash
```

This installs:
- `~/.kimi-webbridge/bin/kimi-webbridge` — daemon binary
- Chrome extension (must be installed manually from Chrome Web Store)
- Skills for Claude, Codex, Kimi CLI, and OpenClaw

## Starting the Daemon

```bash
export PATH="$HOME/.kimi-webbridge/bin:$PATH"
kimi-webbridge start        # Start daemon
kimi-webbridge status       # Check status
kimi-webbridge restart      # Restart if needed
kimi-webbridge logs         # View logs
```

**Status must show:** `extension_connected: true`
If `extension_connected: false`, the Chrome extension isn't installed or connected.

## Basic Commands

All commands go to `http://127.0.0.1:10086/command` via POST:

### Navigate

```bash
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {
      "url": "https://www.google.com/search?q=Paris+Seine+cruise+dock+coordinates",
      "newTab": true
    },
    "session": "port-research"
  }'
```

**Always use `newTab: true` on first call.** Use `session` to group related tabs.

### Read Page Content

```bash
# Get accessibility tree (structured text with element refs)
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{"action":"snapshot","args":{},"session":"port-research"}'

# Get raw page text
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "evaluate",
    "args": {"code": "document.body.innerText.substring(0, 3000)"},
    "session": "port-research"
  }'

# Extract specific data with regex
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "evaluate",
    "args": {"code": "document.body.innerText.match(/Coordinates[\\s:]+([\\d.]+)[,\\s]+([\\d.]+)/)"},
    "session": "port-research"
  }'
```

### Click and Interact

```bash
# Click by accessibility ref (@e1, @e2, etc. from snapshot)
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{"action":"click","args":{"selector":"@e43"},"session":"port-research"}'

# Fill a search box
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "fill",
    "args": {"selector": "input[name=q]", "value": "cruise terminal coordinates"},
    "session": "port-research"
  }'
```

### Screenshot

**Never call screenshot API directly** — returns base64 data that floods context.
Use the helper script instead:

```bash
bash "$(dirname "$SKILL_PATH")/scripts/screenshot.sh"
# or with session:
bash "$(dirname "$SKILL_PATH")/scripts/screenshot.sh" -s port-research
```

### Close Session

```bash
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{"action":"close_session","args":{},"session":"port-research"}'
```

## Research Patterns

### Pattern 1: Coordinate Research (Batch Mode)

For finding GPS coordinates of 5+ locations when Nominatim has poor coverage. This is the primary research method for cruise dock coordinates.

**See `references/coordinate-research-batch-pattern.md` for the complete batch research workflow** — covers search query templates by port type, extracting coordinates from Google AI Overview, verification checklist, batch size guidance, integration with validation scripts, and rate limiting.

### Data Source Reconnaissance

For evaluating a new external data source before planning a feature. Systematic coverage analysis, URL pattern discovery, data structure extraction, and integration feasibility assessment.

**See `references/data-source-reconnaissance.md` for the complete workflow** — covers the 6-step reconnaissance pattern (URL discovery, data extraction, coverage gap analysis, limitation checks, integration feasibility, decision matrix), volume-weighted prioritization, and the river-vs-ocean coverage pitfall.

### Frontend Module-Cache and Dropdown Pitfalls

For debugging UI changes that don't take effect in the browser even though the source file looks correct. Covers stale ES-module cache, `overflow-x: auto` clipping, inline-onclick fragility, CSS syntax errors that silently disable downstream rules, and verifying the executing module rather than just the fetched source.

**See `references/frontend-module-cache-and-dropdown-pitfalls.md`** for the complete checklist and code patterns.

**Critical rule: ALWAYS verify site accessibility with browser automation BEFORE building a scraper.** The WhatsInPort.com case (2026-05-14) shows what happens when this step is skipped: 1,152 ports of garbage data, wasted the LLM provider quota, and 2+ hours of cleanup. See `references/data-source-reconnaissance.md` for the full post-mortem and the `validateHtml()` pattern.

### Pattern 3: Data Verification

**For OddsPortal scraping (Playwright-based), see `references/oddsportal-football.md`** — covers ALL OddsPortal page types (football league pages, date-based matches pages for all sports). Key topics: responsive duplicate containers (6 odds per row, need 3), URL season format, **cross-page team ordering pitfall** (matches pages: HOME first; league pages: AWAY first), score extraction from DOM (never regex on row text), closing ML extraction from matches-page odds containers (winning/default → map to home/away based on who won), **fast path pattern** (skip per-game H2H visits — matches page already has closing MLs), team name aliases, American odds format conversion, and JS selector verification before implementation.

1. Research 5-10 ports per batch (opens tabs in single session)
2. Compile findings into table format for user review
3. Patch all into source file in one commit
4. Push immediately — don't let validated coordinates sit uncommitted
5. Re-run validation to confirm overrides are detected

**Anti-pattern to avoid:** Researching ports one-at-a-time with individual commits. This creates noisy commit history and increases risk of losing work if the session ends unexpectedly.

**Commit-after-each-batch rule:** When batch-researching 20+ ports, commit after every 5-7 ports (one batch), not at the end. If the session ends early, uncommitted coordinates are lost. The JSON report is overwritten on each validation run.

### Pattern 2: Data Verification

For verifying information across multiple sources:

```bash
# Search source 1
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {"url": "https://www.cruisemapper.com/ports/luxor-port", "newTab": true},
    "session": "verify"
  }'

# Extract coordinates
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "evaluate",
    "args": {"code": "document.body.innerText.match(/Coordinates[\\s:]+([\\d.]+)[,\\s]+([\\d.]+)/)?.[0]"},
    "session": "verify"
  }'

# Search source 2 for cross-reference
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {"url": "https://www.google.com/search?q=Luxor+Nile+cruise+dock+GPS", "newTab": true},
    "session": "verify"
  }'
```

### Pattern 3: Visual Verification

For checking maps, satellite imagery, or visual content:

```bash
# Navigate to Google Maps
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {"url": "https://www.google.com/maps/search/Port+of+Miami", "newTab": true},
    "session": "maps"
  }'

# Take screenshot (use helper script)
bash "$(dirname "$SKILL_PATH")/scripts/screenshot.sh" -s maps -o /tmp/miami_port.png

# Read image to verify
# (Use image reading tool to view /tmp/miami_port.png)
```

## Common Pitfalls

### Letting Validated Coordinates Sit Uncommitted

**When batch-researching coordinates, commit immediately after each batch.** Do not accumulate findings across multiple batches without committing. The validation script's JSON report is overwritten on each run — if coordinates are found but not committed to the source file, they are lost and the next validation run will re-research the same ports.

**Correct workflow:**
1. Research batch of 5-10 ports
2. Patch into source file immediately
3. Commit with descriptive message listing all ports
4. Push to staging
5. Only then start the next batch

**Anti-pattern:** Research 20 ports, then try to patch all at once. If the session ends or a tool fails, the findings are lost.

### Health Check

The webbridge `/command` endpoint only accepts POST — HEAD requests will fail. Use a lightweight navigate call for health checks:

```bash
# Correct health check (must use POST, not HEAD)
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{"action":"navigate","args":{"url":"https://www.google.com","newTab":true},"session":"health-check"}'

# Wrong — HEAD not supported
curl -s -I http://127.0.0.1:10086/command  # Returns 404 or error
```

**In TypeScript scripts, always use POST for health checks:**
```typescript
const check = await fetch(webbridgeUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    action: 'navigate', 
    args: { url: 'https://www.google.com', newTab: true }, 
    session: 'health-check' 
  }),
  signal: AbortSignal.timeout(5000)
});
const checkData = await check.json() as { ok?: boolean };
if (!checkData.ok) throw new Error('Webbridge not responding');
```

### "extension_connected: false"

The Chrome extension isn't installed or connected:
1. Install from Chrome Web Store: https://kimi.com/features/webbridge
2. Pin the extension to toolbar
3. Click the extension icon to connect
4. Restart daemon: `kimi-webbridge restart`

### "404 page not found"

The API endpoint is wrong. Use `/command` not `/api/command`:
```bash
curl -s -X POST http://127.0.0.1:10086/command  # Correct
curl -s -X POST http://127.0.0.1:10086/api/command  # Wrong
```

### "invalid JSON" in evaluate

Escape backslashes in regex patterns:
```bash
# Wrong: "code": "document.body.innerText.match(/\d+\.\d+/)"
# Right:  "code": "document.body.innerText.match(/\\d+\\.\\d+/)"
```

### Page content is truncated

Google search results are often truncated. Try:
1. Click "Show more" or expand AI Overview
2. Navigate to a specific result page instead of search results
3. Use `document.body.innerText` with a larger substring

## Security Notes

- The browser runs with the user's real login sessions
- Be careful with sensitive sites (banking, email)
- Don't screenshot or extract sensitive information
- The extension only works on the local machine

## Comparison with Other Tools

| Tool | Use When | Limitation |
|------|----------|------------|
| Nominatim API | Fast coordinate lookup | Limited coverage for private terminals |
| kimi-webbridge | Complex research, verification | Requires Chrome extension |
| curl + grep | Simple HTML scraping | Fails on JavaScript-rendered pages |
| subagent dispatch | Parallel research | Subagents may fail on complex queries |

## Scripting with TypeScript

When integrating webbridge into TypeScript scripts (e.g., batch validation pipelines), use `fetch()` with proper typing:

```typescript
const webbridgeUrl = 'http://127.0.0.1:10086/command';

// Health check — must use POST, not HEAD
const check = await fetch(webbridgeUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    action: 'navigate', 
    args: { url: 'https://www.google.com', newTab: true }, 
    session: 'health-check' 
  }),
  signal: AbortSignal.timeout(5000)
});
const checkData = await check.json() as { ok?: boolean };
if (!checkData.ok) throw new Error('Webbridge not responding');

// Navigate with session
await fetch(webbridgeUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    action: 'navigate',
    args: { url: 'https://www.google.com/search?q=...', newTab: true },
    session: 'batch-research',
  }),
});

// Extract text — wait for page load first
await new Promise(r => setTimeout(r, 3000));
const textRes = await fetch(webbridgeUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    action: 'evaluate',
    args: { code: 'document.body.innerText.substring(0, 1500)' },
    session: 'batch-research',
  }),
});
const textData = await textRes.json() as { ok: boolean; data?: { value?: string } };
if (textData.ok && textData.data?.value) {
  const text = textData.data.value;
  // Parse coordinates, extract data, etc.
}

// Close session when done
await fetch(webbridgeUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ action: 'close_session', args: {}, session: 'batch-research' }),
});
```

**Key TypeScript patterns:**
- Response type: `{ ok: boolean; data?: { value?: string } }` for evaluate
- Response type: `{ ok: boolean; data?: { success: boolean; url: string; tabId: number } }` for navigate
- Always `newTab: true` on first navigate in a session
- Always wait 2-3s after navigate before extracting text
- Always close session when done (cleans up browser tabs)
- Use `AbortSignal.timeout()` for health checks to avoid hanging

## Examples

### Research Cruise Port Coordinates

See `references/coordinate-research-batch-pattern.md` for the complete batch research workflow developed during 70+ port coordinate override sessions. Covers:
- Search query templates by port type (sea, river, tender, private island, Norwegian fjord, Alaska scenic, Asian river)
- Extracting coordinates from Google AI Overview
- Verification checklist (range, hemisphere, proximity, precision, cross-reference)
- Batch size guidance (5-10 standard, 15-20 max, 50+ scripted)
- Integration with 3D map generation pipelines
- Rate limiting and anti-CAPTCHA practices
- TypeScript integration with validation scripts

### Common Pitfalls

See `references/kimi-webbridge-pitfalls.md` for detailed patterns on:
- JSON escaping in evaluate commands
- Finding correct API endpoints
- Session lifecycle management
- Extracting data from Google search results
- Cross-referencing sources
- Rate limiting
- When browser automation beats Nominatim
- Extension connection troubleshooting

### Extract Data from a Table

```bash
# Navigate to page with table
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {"url": "https://example.com/data", "newTab": true},
    "session": "data"
  }'

# Extract table data as JSON
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "evaluate",
    "args": {"code": "JSON.stringify(Array.from(document.querySelectorAll('table tr')).map(r => Array.from(r.querySelectorAll('td')).map(c => c.innerText)))"},
    "session": "data"
  }'
```

### Fill and Submit a Form

```bash
# Fill search box
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "fill",
    "args": {"selector": "input[name=search]", "value": "cruise terminal"},
    "session": "form"
  }'

# Click submit button
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "click",
    "args": {"selector": "button[type=submit]"},
    "session": "form"
  }'
```