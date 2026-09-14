# Coordinate Research Batch Pattern

## Overview

The primary use case for kimi-webbridge in the the cruise-advisor platform project: batch-researching cruise dock coordinates for 3D port map generation. This pattern was refined across 70+ port research sessions.

## When to Use Browser vs Nominatim

| Scenario | Tool | Why |
|----------|------|-----|
| Major city with known landmarks | Nominatim | Faster (~2s), more reliable |
| River cruise dock (not in OSM) | Browser | Nominatim rarely has these |
| Private cruise terminal | Browser | Not in public databases |
| Multiple terminals, need specific one | Browser | Nominatim returns cargo port |
| Batch of 5+ ports | Browser | More efficient than Nominatim loops |
| Verification/cross-reference | Browser | Multiple sources in one search |

## Batch Research Workflow

### 1. Start Daemon

```bash
export PATH="$HOME/.kimi-webbridge/bin:$PATH"
kimi-webbridge status || kimi-webbridge start
```

### 2. Open Research Session

Use a single session name for all searches in a batch. This groups tabs and allows batch close.

```bash
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {
      "url": "https://www.google.com/search?q=PORTNAME+cruise+terminal+coordinates+GPS",
      "newTab": true
    },
    "session": "coord-batch"
  }'
```

**Always use `newTab: true` on first call.**

### 3. Extract Coordinates

Wait 2-3 seconds for page load, then extract the first 1500 characters (captures Google AI Overview):

```bash
sleep 2

curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "evaluate",
    "args": {"code": "document.body.innerText.substring(0, 1500)"},
    "session": "coord-batch"
  }'
```

**Look for these patterns in the output:**
- "Coordinates: 25.691, 32.633"
- "GPS: 36.3862° N, 25.4303° E"
- "Located at approximately 44.416° N, 8.919° E"
- "Primary GPS coordinates of approximately 21.3069° N, -157.8583° W"
- "Decimal: 68.23400° N, 14.56150° E"

**No need to click into results.** The AI Overview is sufficient 90% of the time.

### 4. Navigate to Next Port

```bash
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "navigate",
    "args": {
      "url": "https://www.google.com/search?q=NEXT_PORT+cruise+port+coordinates+GPS",
      "newTab": true
    },
    "session": "coord-batch"
  }'
```

**Reuse the same session name.** Each `newTab: true` opens a new tab within the session.

### 5. Repeat Steps 3-4

Continue until you've researched all ports in the batch.

### 6. Close Session

```bash
curl -s -X POST http://127.0.0.1:10086/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "close_session",
    "args": {},
    "session": "coord-batch"
  }'
```

**Always close when done.** This cleans up browser tabs and frees memory.

## Search Query Templates by Port Type

| Port Type | Query Template | Example |
|-----------|---------------|---------|
| Sea port (major) | `{city} cruise terminal coordinates GPS` | `Miami cruise terminal coordinates GPS` |
| Sea port (Caribbean) | `{city} cruise port dock coordinates` | `Nassau Bahamas cruise port dock coordinates` |
| River port | `{city} river cruise dock coordinates GPS` | `Passau Germany river cruise dock coordinates` |
| Tender port | `{city} cruise ship anchorage coordinates` | `Santorini cruise ship anchorage coordinates` |
| Private island | `{name} private island cruise port coordinates` | `Half Moon Cay Carnival private island coordinates` |
| European port | `{city} cruise terminal GPS decimal` | `Barcelona cruise terminal GPS decimal` |
| Norwegian fjord | `{city} Norway cruise port coordinates` | `Svolvaer Norway cruise port coordinates` |
| Alaska scenic | `{name} Alaska cruise coordinates` | `Hubbard Glacier Alaska cruise coordinates` |
| Asian river | `{city} Mekong cruise dock coordinates` | `Phnom Penh Mekong cruise dock coordinates` |

## Verification Checklist

Before accepting coordinates from any source:

1. **Range check**: Lat -90 to 90, Lon -180 to 180
2. **Hemisphere check**: Negative lat = southern, negative lon = western
3. **Proximity check**: Cruise terminals are always on water (coastline, river, or bay)
4. **Precision check**: If coordinates match city center exactly, it's probably not the dock
5. **Cross-reference**: For critical ports, verify with a second search using different terms

## Batch Size Guidance

| Batch Size | Use When | Notes |
|-----------|----------|-------|
| 5-10 ports | Standard session | Comfortable pace, easy to track |
| 15-20 ports | Longer session | Maximum before tab clutter |
| 50+ ports | Scripted loop | Use TypeScript script with curl calls |

## Common Pitfalls

### "Coordinates not found in page text"

Google AI Overview doesn't always include coordinates. Try:
1. Different search terms (add "GPS", "decimal", "latitude longitude")
2. Navigate to first result page instead of search results
3. Search for the specific terminal name if known

### Wrong coordinates (city center, not dock)

Signs the coordinate is wrong:
- Matches city center exactly (check with Nominatim)
- Not on water (inland, no river/coastline nearby)
- Too precise to be a dock (e.g., 48.8566, 2.3522 for Paris — that's the city center, not a dock)

**Fix:** Try more specific search terms:
- `{city} cruise ship terminal pier coordinates`
- `{terminal name} {city} GPS`
- `{city} port authority cruise terminal`

### Multiple terminals

Major ports have multiple terminals. Use the primary one or specify the cruise line:
- `Port of Miami Terminal B coordinates`
- `Barcelona Moll Adossat cruise terminal`
- `Seattle Smith Cove Cruise Terminal`

### Private islands / small ports

These are often not in standard databases. Try:
- Cruise line websites (Carnival, Royal Caribbean, NCL)
- Specialized port guides (CruiseMapper, CruiseCritic)
- Satellite imagery (Google Maps, OpenStreetMap)

## Integration with Validation Script

The `validate-coordinates.ts` script can call webbridge automatically for ports with no data:

```bash
# Automated mode only (fast, no webbridge)
DATABASE_URL="..." npx tsx scripts/port-map3d/validate-coordinates.ts --dry-run --tier=high --limit=100

# With webbridge (slower, researches "no data" ports)
DATABASE_URL="..." npx tsx scripts/port-map3d/validate-coordinates.ts --dry-run --tier=high --limit=50 --webbridge
```

**Webbridge integration in TypeScript:**
```typescript
const webbridgeUrl = 'http://127.0.0.1:10086/command';

// Health check — MUST use POST, not HEAD
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
if (!checkData.ok) {
  console.log('⚠️  kimi-webbridge not running — skipping webbridge research');
  return null;
}

// Research a port
await fetch(webbridgeUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    action: 'navigate',
    args: { 
      url: `https://www.google.com/search?q=${encodeURIComponent(portName)}+cruise+port+coordinates+GPS`, 
      newTab: true 
    },
    session: 'batch-research',
  }),
});

// Wait for page load
await new Promise(r => setTimeout(r, 3000));

// Extract text
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
  // Parse coordinates from text using regex
  const coordRegex = /(-?\d{1,2}\.\d{3,})\s*°?\s*[NS]?[,\s]+(-?\d{1,3}\.\d{3,})\s*°?\s*[EW]?/;
  const match = text.match(coordRegex);
  if (match) {
    const lat = parseFloat(match[1]);
    const lon = parseFloat(match[2]);
    // Validate ranges
    if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
      return [lat, lon];
    }
  }
}
```

## Rate Limiting

Google search has implicit rate limits. For batch research:
- Wait 2-3 seconds between navigations
- Don't exceed 20 searches per minute
- If you hit a CAPTCHA, stop and wait 5 minutes

## Output Format

When batch-researching, compile findings into a table for the user:

```
| Port | Type | Dock Coordinates | Notes |
|------|------|-----------------|-------|
| Miami | Sea | 25.7781, -80.1791 | Dodge Island, Pier B |
| Vienna | River | 48.2108, 16.3695 | Reichsbrücke Danube dock |
```

Then patch `MANUAL_OVERRIDES` in `generate-port-glbs.ts` with all findings.

## Remember

**Coordinate overrides ONLY affect 3D map generation — NEVER modify the port table coordinates.** The `cruisemapper_ports` table coordinates are used for itinerary routing, corridor computation, and other features. Changing them would trigger a hashing cascade. The `MANUAL_OVERRIDES` map is the only place for 3D map coordinate corrections.
