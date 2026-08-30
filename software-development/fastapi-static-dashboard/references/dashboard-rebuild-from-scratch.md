# Dashboard Rebuild From Scratch — When to Cut Losses

Reference for the decision to scrap a broken dashboard and rebuild clean rather than continue debugging accumulated failures.

## Context

After 4 failed sessions attempting to fix a 1,414-line `dashboard.html` with accumulated bugs (state sync issues, broken scenario cards, mock data leaking through, CSS conflicts, event handlers lost on re-render), the decision was made to cut losses and rebuild.

## The Broken Dashboard's Sins

1. **Single file, 1,414 lines** — HTML, CSS, and JS all crammed together
2. **Accumulated patch-on-patch** — Each session added fixes without removing broken code
3. **State management spaghetti** — Global variables, hardcoded defaults in templates, event handlers attached to destroyed DOM nodes
4. **Mock data fallback never removed** — Real data pipeline existed but endpoints still returned hardcoded samples
5. **CSS specificity wars** — Inline styles fighting with class-based styles, `!important` creeping in
6. **No separation of concerns** — API client, rendering, state, and event handling all interleaved

## The Rebuild Approach

### 1. Preserve What Works

The backend API (`src/api/`) was functional — 8 endpoints serving real data:
- `/api/ratings` — 34 teams from corpus
- `/api/teams` — team listings
- `/api/scenarios` — 830 injury-based scenarios
- `/api/divergence` — computed divergence reports
- `/api/schedule/{sport}` — upcoming games with probabilities
- `/api/pipeline/status` — pipeline state
- `/api/admin/domains` — sport domain configs
- `/api/admin/corpus` — evidence corpus stats

**Decision:** Keep the backend intact. The problem was purely frontend.

### 2. Backup, Don't Delete

```bash
mv ui/dashboard.html ui/dashboard.html.bak.$(date +%s)
```

This preserves the old code for reference without it being served.

### 3. Single-File Architecture (But Clean)

The new dashboard is still a single file (`ui/dashboard.html`) but with strict structure:

```
dashboard.html
├── <head>
│   ├── CSS custom properties (design tokens)
│   ├── Layout styles (grid/flex)
│   ├── Component styles (cards, tables, badges)
│   └── Animation styles (skeleton, toast)
├── <body>
│   ├── Sidebar navigation (7 views)
│   ├── Mobile overlay
│   ├── Topbar (filters)
│   ├── Content area (dynamic)
│   └── Toast container
└── <script>
    ├── State object (single source of truth)
    ├── Navigation handlers
    ├── Filter handlers (with localStorage persistence)
    ├── API client (fetch wrapper + error handling)
    ├── View renderers (one per view)
    ├── Utility functions (escapeHtml, formatDate)
    └── Initialization
```

**Key differences from the broken version:**
- State is a single object, not scattered variables
- All rendering interpolates from state (no hardcoded defaults)
- Each view is a pure function: `async function renderX() { ... }`
- Error handling is centralized (toast system)
- Loading states are uniform (skeleton pattern)
- HTML escaping is mandatory (`escapeHtml` on all dynamic content)

### 4. Verification Strategy

Instead of "looks right in browser," verify programmatically:

```python
# Start server
proc = subprocess.Popen(['python3', '-m', 'uvicorn', 'src.api.main:app', '--host', '127.0.0.1', '--port', '8000'])

# Fetch dashboard HTML
r = urllib.request.urlopen('http://127.0.0.1:8000/dashboard')
html = r.read().decode()

# Structural checks
checks = [
    ('has sidebar', 'class="sidebar"' in html),
    ('has nav items', 'data-view="ratings"' in html),
    ('has content area', 'id="content"' in html),
    ('has league select', 'id="leagueSelect"' in html),
    ('has team filter', 'id="teamFilter"' in html),
    ('has JS app', 'setView' in html),
    ('has ratings view fn', 'renderRatings' in html),
    ('has scenarios view fn', 'renderScenarios' in html),
    ('has divergence view fn', 'renderDivergence' in html),
    ('has schedule view fn', 'renderSchedule' in html),
    ('has pipeline view fn', 'renderPipeline' in html),
    ('has domains view fn', 'renderDomains' in html),
    ('has corpus view fn', 'renderCorpus' in html),
    ('has toast system', 'toast(' in html),
    ('has skeleton loading', 'skeleton' in html),
    ('has API_BASE', "const API_BASE = ''" in html),
    ('has mobile overlay', 'id="overlay"' in html),
    ('has escapeHtml', 'function escapeHtml' in html),
]
```

Also verify JS syntax:
```python
# Balanced braces/parens
open_braces = js.count('{')
close_braces = js.count('}')
open_parens = js.count('(')
close_parens = js.count(')')
# Template literal backticks must be even
backticks = html.count('`')
```

### 5. Size Target

| Metric | Broken | Rebuilt |
|--------|--------|---------|
| Lines | 1,414 | ~500 |
| Script functions | 30+ (interleaved) | 18 (organized) |
| CSS selectors | 80+ (conflicting) | 40 (clean) |
| State variables | 15+ (scattered) | 1 object |

## When to Apply This Pattern

**Cut losses and rebuild when:**
- 3+ consecutive sessions failed to fix the same component
- The file is >1000 lines with no module separation
- Bug fixes introduce new bugs (whack-a-mole)
- You can't explain the state flow in 2 sentences
- Mock data and real data coexist in the same file
- CSS requires `!important` to work

**Don't rebuild when:**
- The bug is isolated and well-understood
- The file is <300 lines with clear structure
- A single fix resolves the issue
- The backend needs changes too (then it's a refactor, not a rebuild)

## Lessons

1. **Single-file dashboards are fine** — but only if the structure is disciplined
2. **State must have a single source of truth** — never hardcode defaults in templates
3. **Verify structure, not just appearance** — programmatic checks catch more than visual inspection
4. **Backup before destroying** — `mv file.bak.$(date +%s)` is cheap insurance
5. **Backend/frontend separation is real** — when the API works, don't touch it
