# kimi-webbridge Pitfalls and Patterns

## JSON Escaping in evaluate

The `evaluate` action takes a JavaScript code string. Backslashes in regex must be double-escaped in the JSON payload:

```bash
# WRONG — single backslash is invalid JSON
"code": "document.body.innerText.match(/\d+\.\d+/)"

# RIGHT — double-escaped for JSON
"code": "document.body.innerText.match(/\\d+\\.\\d+/)"

# Also RIGHT — use string methods that don't need regex
"code": "document.body.innerText.substring(0, 3000)"
```

When using `curl` with `-d`, the shell also processes backslashes. Use single quotes around the JSON payload to prevent shell interpolation:

```bash
# WRONG — shell may process backslashes before JSON parser sees them
curl -d "{\"code\": \"document.body.innerText.match(/\\d+/)\"}"

# RIGHT — single quotes prevent shell interpolation
curl -d '{"code": "document.body.innerText.match(/\\d+/)"}'
```

## Finding the Right API Endpoint

The daemon only exposes `/command` and `/status`. All other paths return 404:

```bash
# CORRECT
curl -s -X POST http://127.0.0.1:10086/command
curl -s http://127.0.0.1:10086/status

# WRONG — all return 404
http://127.0.0.1:10086/api/command
http://127.0.0.1:10086/api/v1/command
http://127.0.0.1:10086/v1/command
http://127.0.0.1:10086/browser/open
http://127.0.0.1:10086/api/browser/open
```

## Session Lifecycle

Always close sessions when done to avoid accumulating tabs:

```bash
# Close a specific session
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{"action":"close_session","args":{},"session":"port-research"}'

# The response shows how many tabs were closed
{"ok":true,"data":{"success":true,"closed":5}}
```

## Extracting Data from Google Search Results

Google AI Overview often contains coordinates in the first ~1500 characters. Use `substring(0, 1500)` to avoid flooding context:

```bash
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "evaluate",
    "args": {"code": "document.body.innerText.substring(0, 1500)"},
    "session": "port-research"
  }'
```

Look for patterns like:
- "Coordinates: 48.855, 2.290"
- "GPS: 36.3862° N, 25.4303° E"
- "Located at approximately 44.416° N, 8.919° E"

## Cross-Referencing Sources

For critical coordinates, verify with a second source:

1. First search: Google AI Overview for approximate coordinates
2. Second search: CruiseMapper port page for official coordinates
3. Third check: Google Maps satellite view to verify the location shows a cruise terminal

```bash
# Search CruiseMapper for a specific port
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {"url": "https://www.cruisemapper.com/ports/luxor-port", "newTab": true},
    "session": "verify"
  }'

# Extract coordinates from the page
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "evaluate",
    "args": {"code": "document.body.innerText.match(/Coordinates[\\s:]+([\\d.]+)[,\\s]+([\\d.]+)/)?.[0]"},
    "session": "verify"
  }'
```

## Rate Limiting

Don't hammer the daemon with rapid requests. Add small delays between commands:

```bash
# Good: 1-2 second delay between navigation and extraction
navigate → sleep 1 → evaluate → sleep 1 → click → sleep 1 → evaluate

# Bad: Rapid-fire commands may overload the extension
navigate → evaluate → click → evaluate → navigate → evaluate
```

## When Browser Automation is Better Than Nominatim

| Scenario | Nominatim | Browser |
|----------|-----------|---------|
| Major sea ports with dedicated terminals | ✅ Works well | ⚠️ Slower but more accurate |
| River cruise docks | ❌ Rarely in OSM | ✅ Google AI Overview has them |
| Private cruise terminals (Amber Cove, Coco Cay) | ❌ Not in OSM | ✅ Cruise line websites have coordinates |
| Ports with multiple terminals | ⚠️ Returns cargo port | ✅ Can find specific cruise terminal |
| Small islands | ⚠️ May return island center | ✅ Can find actual dock location |

## Extension Connection Issues

If `kimi-webbridge status` shows `extension_connected: false`:

1. Check Chrome extension is installed: chrome://extensions/
2. Look for "Kimi WebBridge" extension
3. If not installed: https://kimi.com/features/webbridge
4. Click the extension icon in Chrome toolbar to connect
5. Restart daemon: `kimi-webbridge restart`
6. Check status again: `kimi-webbridge status`

The extension ID should appear in status: `{"extension_id":"fldmhceldgbpfpkbgopacenieobmligc",...}`

## Batch Research Workflow

For researching many ports efficiently, use a single session and navigate between searches:

```bash
export PATH="$HOME/.kimi-webbridge/bin:$PATH"

# Start session with first search
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {"url": "https://www.google.com/search?q=Port+Name+cruise+terminal+coordinates+GPS", "newTab": true},
    "session": "port-research"
  }'

# Extract coordinates
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "evaluate",
    "args": {"code": "document.body.innerText.substring(0, 1500)"},
    "session": "port-research"
  }'

# Navigate to next port (reuses same session, opens new tab)
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {"url": "https://www.google.com/search?q=Next+Port+cruise+terminal+coordinates+GPS", "newTab": true},
    "session": "port-research"
  }'

# ... repeat for each port

# Close session when done
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{"action":"close_session","args":{},"session":"port-research"}'
```

**Key insight:** Google AI Overview often contains exact coordinates in the first 1500 characters. No need to click into result pages for most ports.

**Proven at scale:** This workflow has been used to research 66+ cruise port coordinates in a single session. Each port takes ~30 seconds: navigate → extract → record → next.

## Coordinate Extraction Patterns

Common coordinate formats found in Google AI Overview:

```bash
# Pattern 1: "Coordinates: 25.691, 32.633"
"code": "document.body.innerText.match(/Coordinates[\\s:]+([\\d.]+)[,\\s]+([\\d.]+)/)"

# Pattern 2: "GPS: 36.3862° N, 25.4303° E"
"code": "document.body.innerText.match(/GPS[\\s:]+([\\d.]+)°\\s*[NS][,\\s]+([\\d.]+)°\\s*[EW]/)"

# Pattern 3: "Located at approximately 44.416° N, 8.919° E"
"code": "document.body.innerText.match(/approximately[\\s]+([\\d.]+)°\\s*[NS][,\\s]+([\\d.]+)°\\s*[EW]/)"

# Pattern 4: Decimal degrees inline "48.855, 2.290"
"code": "document.body.innerText.match(/([\\d]{2}\\.[\\d]{3,})[\\s,]+([\\d]{1,3}\\.[\\d]{3,})/)"
```

**Always verify coordinates make sense:**
- Latitude: -90 to 90 (negative = southern hemisphere)
- Longitude: -180 to 180 (negative = western hemisphere)
- Cruise terminals are always near water
- If coordinates match city center exactly, it's probably not the dock
