# OddsPortal Scraper — DOM Structure, Pitfalls & Patterns

## URL Patterns

### League Pages (Football)

League pages are league-specific, NOT date-based (unlike American sports):
- Results: `https://www.oddsportal.com/football/{country}/{league}-{season}/results/`
- Upcoming: `https://www.oddsportal.com/football/{country}/{league}/`

**Season format in URL:** appended to league name with hyphen
- `premier-league-2024-2025/results/` ✅
- `premier-league/results/2024-2025/` ❌ (404)

**League URL slugs (verified 2026-06-03):**
```python
FOOTBALL_LEAGUE_URLS = {
    "football_epl": ("england", "premier-league"),
    "football_laliga": ("spain", "laliga"),
    "football_seriea": ("italy", "serie-a"),
    "football_bundesliga": ("germany", "bundesliga"),
    "football_ligue1": ("france", "ligue-1"),
    "football_championship": ("england", "championship"),
    "football_laliga2": ("spain", "laliga-2"),
    "football_serieb": ("italy", "serie-b"),
    "football_bundesliga2": ("germany", "2-bundesliga"),
    "football_ligue2": ("france", "ligue-2"),
}
```

### Matches Pages (All Sports, Date-Based)

For backfilling completed game odds, use the date-based matches page:
- `https://www.oddsportal.com/matches/{sport}/{YYYYMMDD}/`
- Example: `https://www.oddsportal.com/matches/baseball/20260604/`

**Sport URL slugs:**
```python
SPORT_SLUG_MAP = {
    "mlb": "baseball",
    "nba": "basketball",
    "nhl": "hockey",
    "nfl": "american-football",
    "mls": "soccer",
}
```

---

## DOM Structure — League Pages (Football)

**Game row:** `[data-testid='game-row']`
**Team names:** `.participant-name` — DOM order is **AWAY first, HOME second** (opposite of URL)
**URL pattern:** `/football/{country}/{league}/h2h/{home-slug}/{away-slug}/`

### 3-Way Odds (1X2)

Football has **3 odds per game** (Home/Draw/Away), not 2 like American sports.

**Critical pitfall: responsive duplicates.** Each odds column renders TWO containers:
1. Main container: `class="flex-center border-black-main min-w-[60px]"` — **use this one**
2. Responsive duplicate: `class="height-content !text-black-main"` — **skip this**

Without filtering, you get 6 containers per row instead of 3, and `odds.slice(0,3)` picks up [Home, Home_duplicate, Draw] instead of [Home, Draw, Away].

**Selector to get exactly 3 odds:**
```javascript
r.querySelectorAll(
    "[data-testid='odd-container-default'].border-black-main, " +
    "[data-testid='odd-container-winning'].border-black-main"
)
```

**Odds order:** Home (1) → Draw (X) → Away (2)

### Scores

Scores are NOT in a separate element. They're adjacent to team names inside `[data-testid='event-participants']`.

**DO NOT use regex on row text** — the regex `(\d+)\s*[–\-]\s*(\d+)` matches odds numbers concatenated with scores. Example: "Southampton11–2Arsenal2" matches "11–2" instead of "1–2".

**Correct approach:** Find `div.font-bold` elements inside `event-participants` that contain single digits (0-19):

```javascript
const participants = r.querySelector("[data-testid='event-participants']");
const scoreDivs = participants.querySelectorAll("div.font-bold:not(.participant-name)");
const scores = [];
for (const sd of scoreDivs) {
    const n = parseInt(sd.textContent.trim());
    if (!isNaN(n) && n >= 0 && n < 20 && sd.textContent.trim().length <= 2) {
        scores.push(n);
    }
}
// scores[0] = away score, scores[1] = home score
```

---

## DOM Structure — Matches Pages (All Sports, Completed Games)

**Matches page URL:** `https://www.oddsportal.com/matches/{sport}/{YYYYMMDD}/`
Shows both upcoming and completed games for a given date.

### ⚠️ Team Ordering Differs from League Pages

**This is the #1 cross-page pitfall on OddsPortal:**

| Page Type | `.participant-name` Order |
|-----------|--------------------------|
| Football league pages | AWAY first, HOME second |
| Matches pages (all sports) | **HOME first, AWAY second** |

The URL H2H slug order is consistent: `/h2h/{home-slug}/{away-slug}/`. But the DOM `.participant-name` order **reverses** between league pages and matches pages.

### Game Row Structure (Matches Page)

```
[data-testid='game-row']
├── <a href="/sport/h2h/{home-slug}/{away-slug}/">     ← game link
│   ├── [data-testid='time-item']                       ← "FinishedFIN" for completed
│   ├── [data-testid='event-participants']
│   │   ├── .participant-name                           ← HOME team (1st)
│   │   ├── div.ml-auto                                 ← HOME score
│   │   ├── div.ml-auto                                 ← AWAY score
│   │   └── .participant-name                           ← AWAY team (2nd)
├── [data-testid='odd-container-winning']               ← Winner's closing ML
└── [data-testid='odd-container-default']               ← Loser's closing ML
```

### Completed Game Detection

```javascript
const timeItem = link.querySelector("[data-testid='time-item']");
const isCompleted = timeItem ? timeItem.textContent.includes("Finished") : false;
```

### Score Extraction

```javascript
const participants = link.querySelector("[data-testid='event-participants']");
const scoreDivs = participants ? participants.querySelectorAll("div.ml-auto") : [];
const homeScore = scoreDivs[0] ? scoreDivs[0].textContent.trim() : null;  // HOME first
const awayScore = scoreDivs[1] ? scoreDivs[1].textContent.trim() : null;  // AWAY second
```

Note: On matches pages, scores are in `div.ml-auto`, NOT `div.font-bold` (which is the league page pattern).

### Closing Money Lines

The matches page shows closing MLs as **sibling elements** of the game link, not inside it:

```javascript
const winOddsEl = r.querySelector("[data-testid='odd-container-winning']");
const defOddsEl = r.querySelector("[data-testid='odd-container-default']");
```

**⚠️ Mapping to home/away requires checking who won:**
- `odd-container-winning` = winner's ML (who literally won the game)
- `odd-container-default` = loser's ML

```javascript
let home_ml, away_ml;
if (parseInt(homeScore) > parseInt(awayScore)) {
    home_ml = winOddsEl.textContent.trim();   // Home won → winning = home
    away_ml = defOddsEl.textContent.trim();
} else {
    home_ml = defOddsEl.textContent.trim();    // Away won → winning = away
    away_ml = winOddsEl.textContent.trim();
}
```

---

## Fast Path Pattern: Extract Odds from Listing Pages

**Key insight (verified 2026-06-05):** The OddsPortal matches page already displays closing MLs for completed games alongside the scores. There is **no need to visit each game's individual H2H page** to get closing odds.

| Approach | Pages Loaded | Time for 3 dates (37 games) |
|----------|--------------|-----------------------------|
| H2H per-game (original) | 37 pages + 3 matches | ~3-5 minutes |
| Matches page only (fast path) | 3 pages only | ~37 seconds |

**When to use the fast path:**
- You need closing MLs only (no opening lines, no spread, no O/U)
- The matches page shows odds for your sport (MLB, NBA, NHL, NFL confirmed)
- You're backfilling completed game data

**When you still need H2H pages:**
- You need opening lines (to track line movement open→close)
- You need spread or over/under data
- The matches page doesn't show odds for a completed game (rare but possible)

---

## Pagination

Results pages are paginated. Look for numbered page links or a "Next" link:
```javascript
const links = await page.query_selector_all("a");
for (const link of links) {
    const text = (await link.text_content()).trim();
    if (text === String(nextPageNum)) { /* found it */ }
}
```

---

## Odds Format

OddsPortal US view shows **American moneyline format** (+320, -114, etc.), NOT decimal.

Convert to implied probability:
```python
def american_to_implied(american_odds):
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)
```

Remove overround (devig):
```python
def devig(home_p, draw_p, away_p):
    total = home_p + draw_p + away_p
    return home_p/total, draw_p/total, away_p/total
```

---

## Team Name Aliases

OddsPortal uses short names that differ from common usage. Key aliases to add:
- "Nottingham" → Nottingham Forest (NFO)
- "Man Utd" / "Manchester Utd" / "Manchester United" → MUN
- "Man City" / "Manchester City" → MCI
- "Nottm Forest" → Nottingham Forest (NFO)
- "Spurs" → Tottenham (TOT)
- "Wolves" → Wolverhampton Wanderers (WOL)
- "Sunderland" → SUN (may appear in EPL after promotion)

---

## Playwright Requirements

- Install: `pip install playwright && python -m playwright install chromium`
- Use `wait_until="networkidle"` — odds load via XHR after initial HTML
- Add 1500ms delay after networkidle for odds to populate
- Politeness: 2000ms between page loads

---

## Critical Pitfall: Verify JS Selectors Against Real DOM

**Never write scraper JS selectors based on assumptions about the DOM.** The OddsPortal DOM has changed multiple times and differs between page types (league vs matches). The pattern that broke the H2H backfill (2026-06-05):

1. Wrote JS looking for `.score, [data-testid='score'], .result` — **none of these exist** on the matches page. Result: 0 rows extracted, silent failure.
2. Used browser `console.evaluate()` to inspect the actual DOM structure.
3. Discovered real selectors: `[data-testid='time-item']` + `div.ml-auto` + `odd-container-winning/default`.

**Always verify before implementing:**
```javascript
// Use browser console to check real DOM before writing extraction JS
document.querySelectorAll("[data-testid='game-row']")[0].innerHTML.substring(0, 2000);
```

This single check would have caught the 0-row extraction immediately.