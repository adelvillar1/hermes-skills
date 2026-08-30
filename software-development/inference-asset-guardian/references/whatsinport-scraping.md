# WhatsInPort.com Scraping Reference

URL patterns, data structure, and coverage analysis for whatsinport.com.

## URL Pattern

`https://www.whatsinport.com/{PortName}.htm`

- **Case-sensitive** — uses display name, not slug
- Examples: `Nassau.htm`, `Cozumel.htm`, `Barcelona.htm`
- **River cruise ports return 404:** `Budapest.htm`, `Vienna.htm`, `Cologne.htm`

## Data Structure (from Nassau sample)

| Section | Content Type |
|---------|-------------|
| Location | Pier details, walking distance to downtown |
| Port description | Welcome center, atmosphere, practical info |
| Tours/Excursions/Transportation | Taxis, ferries, water taxis, tours, rentals |
| Nearby Places | Adjacent destinations (Paradise Island, Atlantis) |
| Shopping and Food | Tips, local specialties, bargaining advice |
| Currency | Converter link |
| Communication | Emergency numbers |
| Opening Hours and Holidays | Holiday links |
| Links | Port Authority, webcam, hotels, printable map, cruise calendar, video, nautical chart, Google Maps, climate averages |

## Notably Absent vs Our Schema

Our `port_guides.cleanedSections` expects:
- `welcome`, `attractions`, `shopping`, `gettingAround`, `safety`, `weather`, `localCurrency`, `portLocation`, `nearbyCities`

WhatsInPort provides narrative prose with headings. Requires Ollama extraction to map to our structured schema.

## Coverage Gap (Active Ports Only)

| Tier | Threshold | Missing Guides | Visit Volume | % of All Visits |
|------|-----------|---------------|-------------|-----------------|
| Tier 1 | 1,000+ visits | 60 | 117,598 | 33.4% |
| Tier 1+2 | 500+ visits | 150 | 179,714 | 51.0% |
| Tier 1+2+3 | 200+ visits | 293 | 224,697 | 63.8% |
| Tier 1+2+3+4 | 100+ visits | 419 | 242,449 | 68.8% |

Current state: 311/1,784 active ports have guides (17.4%).

## Top Missing Tier 1 Ports (River Cruise Heavy)

| Port | Visits | WhatsInPort? |
|------|--------|--------------|
| budapest | 4,859 | ❌ 404 |
| vienna | 4,738 | ❌ 404 |
| cologne | 4,402 | ❌ 404 |
| kehl-strasbourg | 4,264 | ❌ 404 |
| passau | 3,946 | ❌ 404 |
| rudesheim-am-rhein | 3,760 | ❌ 404 |
| koblenz | 3,724 | ❌ 404 |
| porto-leixoes | 3,295 | ✅ Likely |
| breisach-am-rhein | 2,991 | ❌ 404 |
| paris-city | 2,913 | ✅ Likely |

## Scraper Implementation Notes

1. **Name mapping required** — our slugs (`kehl-strasbourg`) ≠ their names (`Kehl` or `Strasbourg` separately)
2. **Retry 404s** — some ports may be under alternate names (e.g., `Strasbourg.htm` instead of `Kehl.htm`)
3. **Rate limit** — unknown; start conservative (~1 req/sec)
4. **HTML parsing** — content is in `<div>` sections with class-based styling; no semantic HTML5 tags
