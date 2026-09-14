# Dashboard polish primitives — reusable UX patterns

Reusable code-and-CSS primitives that emerged from the 2026-06-10
UX polish sprint on the ELO scenario lab. Each is a one-file addition
that addresses a class of complaint in usability reviews. Use as a
recipe when the next polish sprint surfaces a similar issue.

## 1. `--text-numeric` + `.stat-value` for critical-number contrast

When WCAG AA review flags that critical numerics (Brier scores,
ratings, probabilities) are too low-contrast on dark backgrounds.

**CSS:**
```css
:root {
  --text-numeric: #e2e8f0;  /* between --text-secondary and --text-primary */
}
[data-numeric="1"] {
  color: var(--text-numeric) !important;
  font-variant-numeric: tabular-nums;
}
.stat-value {
  color: var(--text-numeric) !important;
  font-variant-numeric: tabular-nums;
}
```

**JSX usage:**
```html
<!-- Most valuable: tag the cell with data-numeric so any future cell
     uses the stronger color without per-cell work. -->
<td data-numeric="1">${b.model_brier.toFixed(4)}</td>
```

Why this works: opt-in via `data-numeric` keeps the muted color on
descriptive labels (which is correct — labels are intentionally
quieter), and the `.stat-value` class covers all "stat-grid" cells
that already exist in the codebase. `font-variant-numeric:
tabular-nums` aligns decimal points so 0.2341 lines up with 0.2370.

## 2. `copyAnchorLink` + `showToast` for shareable section anchors

For "the X section is great, can I send a link to it?" use cases.

**JS:**
```js
async function copyAnchorLink(anchor, label) {
  const url = `${window.location.origin}${window.location.pathname}#${anchor}`;
  if (window.history?.replaceState) {
    window.history.replaceState(null, '', `#${anchor}`);
  }
  document.getElementById(anchor)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  let copied = false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
      copied = true;
    } else {
      // Fallback for older browsers
      const ta = document.createElement('textarea');
      ta.value = url;
      ta.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(ta);
      ta.select();
      copied = document.execCommand('copy');
      document.body.removeChild(ta);
    }
  } catch (e) { copied = false; }
  showToast(copied ? `Link copied: ${label}` : `Press ⌘C to copy the URL bar`);
}

function showToast(message, kind = 'success') {
  document.getElementById('dashboard-toast')?.remove();
  const t = document.createElement('div');
  t.id = 'dashboard-toast';
  const bg = kind === 'success' ? 'var(--success)' : 'var(--accent)';
  t.style.cssText = `position:fixed;bottom:80px;right:24px;background:${bg};color:#fff;padding:10px 16px;border-radius:6px;font-size:13px;z-index:1500;box-shadow:0 4px 12px rgba(0,0,0,0.3);animation:toast-in 0.2s ease-out`;
  t.textContent = message;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 1600);
}
```

**CSS for the animation:**
```css
@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

**Section markup:**
```html
<div class="today-section" id="top-picks">
  <div class="today-section-title">
    Top Picks
    <button class="icon-btn"
            onclick="dashboard.copyAnchorLink('top-picks', 'Top Picks')"
            title="Copy link to this section"
            style="margin-left:8px;background:transparent;border:1px solid var(--border-standard);border-radius:6px;padding:2px 8px;cursor:pointer;color:var(--text-muted);font-size:11px">#</button>
  </div>
  ...
</div>
```

Pattern: add an `id` to the section + a small `#` button in the
title. Click → updates URL hash, smooth-scrolls, copies to
clipboard, shows toast. Works for any heading-level anchor.

## 3. Vim-style keyboard navigation + `?` help modal

For "users don't know there are keyboard shortcuts" complaints.

**JS:**
```js
const KEYBOARD_CHORDS = {
  t: 'today', r: 'ratings', s: 'scenarios', h: 'schedule',
  a: 'accuracy', p: 'pipeline', l: 'calibration', o: 'domains',
};
function initKeyboardShortcuts() {
  let pendingG = null;
  const G_WINDOW_MS = 1200;
  document.addEventListener('keydown', (e) => {
    // Skip when typing in form fields
    const t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' ||
              t.tagName === 'SELECT' || t.isContentEditable)) return;
    if (e.key === 'Escape') {
      document.getElementById('kbd-help-modal')?.remove();
      return;
    }
    if (e.key === '?') { e.preventDefault(); showKbdHelp(); return; }
    if (e.key === 'g' && !pendingG) { pendingG = Date.now(); return; }
    if (pendingG) {
      if (Date.now() - pendingG > G_WINDOW_MS) { pendingG = null; return; }
      const view = KEYBOARD_CHORDS[e.key];
      if (view) { e.preventDefault(); loadView(view); pendingG = null; }
      else if (e.key === 'g') pendingG = null;
      else pendingG = null;
    }
  });
}
```

`?` modal is dynamically created — no HTML markup needed. Use a
`g`+letter chord for navigation; the 1.2s window between keys
gives fast typists natural flow without trapping slow typists.

## 4. Distinguishing "Last Successful Run" vs "Last Attempted Run"

When the user reports "pipeline status is misleading — it says
'Last Run: 5 min ago' but the run actually failed".

**Backend (Pydantic model):**
```python
class PipelineStatus(BaseModel):
    status: str
    last_run: str | None = None           # legacy back-compat
    last_successful_run: str | None = None
    last_attempted_run: str | None = None
```

**Backend (state transitions):**
```python
# In trigger handler: mark as attempted immediately
_pipeline_state["last_attempted_run"] = datetime.now(timezone.utc).isoformat()

# In success handler: also update last_successful_run
now = datetime.now(timezone.utc).isoformat()
_pipeline_state["last_run"] = now
_pipeline_state["last_successful_run"] = now

# In failure handler: do NOT touch last_successful_run
```

**Frontend display:**
- "Last Successful Run" colored green if recent / red if stale
- "Last Attempted Run" colored neutral with absolute timestamp in tooltip
- Use `timeAgo()` for relative, `absoluteTimestamp()` for tooltip

## 5. Empty-state copy that explains WHY

When a metric shows zeros and the user reads it as a bug.

**JSX template:**
```js
if (isEmpty) {
  const ranges = {
    '50-65%': 'no games fell into the coin-flip range (50-65% model confidence) in the analyzed period',
    '65-80%': 'no games fell into the moderate-favorite range (65-80% model confidence) in the analyzed period',
    '80%+':   'no games crossed 80% model confidence in the analyzed period — try extending the date range or check the Calibration view for high-confidence calibration on completed games',
  };
  const msg = ranges[b.range] || `no games in the ${b.range} range in the analyzed period`;
  return `<div style="opacity:0.85">
    <div style="font-size:24px;color:var(--text-muted)">0 <span>games</span></div>
    <div style="color:var(--text-secondary)">${msg}</div>
  </div>`;
}
```

Anti-pattern: showing "0 games" with no explanation. The user
wonders "is this a bug? should I run the pipeline? is this sport
broken?" — all of which require a support ticket. The fix is a
5-line message that explains the data and suggests a remediation.

## 6. `format=csv` on a cached endpoint

See `ui-implementation-review/SKILL.md` pitfall #15 for the cache
poisoning pitfall. The pattern:

```python
@router.get("/{sport}", response_model=AccuracyReport)
async def get_accuracy(
    sport: SportPath,
    format: str = Query(None, description="Response format: 'csv' for download"),
    user: dict = Depends(get_current_user),
):
    if format != "csv":  # BYPASS the cache for non-default formats
        cached = _accuracy_cache.get(sport_lower)
        if cached is not None:
            return cached
    # ... compute ...
    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([...header row...])
        for p in report.predictions:
            writer.writerow([...])
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="accuracy_{sport}.csv"'},
        )
    return report
```

UI side: simple `<a href="/api/accuracy/mlb?format=csv" download>`.

## 7. Series detection for repeating game cards

For "the scenarios page has two cards that look identical" complaints.

```js
const matchupKey = (g) => g.teams.map(t => t.team_id).filter(Boolean).sort().join('|');
const matchupCounts = {};
games.forEach(g => { const k = matchupKey(g); matchupCounts[k] = (matchupCounts[k] || 0) + 1; });
const matchupSeen = {};
games.forEach(g => {
  const k = matchupKey(g);
  const total = matchupCounts[k] || 1;
  if (total > 1) {
    matchupSeen[k] = (matchupSeen[k] || 0) + 1;
    g.seriesIdx = matchupSeen[k];
    g.seriesTotal = total;
  }
});
// Render: ${g.seriesTotal > 1 ? ` <span>Game ${g.seriesIdx} of ${g.seriesTotal}</span>` : ''}
```

The sort-then-join of team IDs gives a stable matchup key regardless
of home/away. Use `matchupSeen` for stable numbering — order is
preserved by the input list.

## 8. Filter-active indicator in section headers

For "I typed in the filter and the count changed — did the data
drift or did my filter do that?" complaints.

```js
const filterActive = !!state.teamFilter;
const headerHtml = `
  <div class="league-count">
    ${totalCount} games · ${dateKeys.length} days${filterActive
      ? ` · <span style="color:var(--accent)">filtered by "${escapeHtml(state.teamFilter)}"</span>`
      : ''
    }
  </div>
`;
```

The accent-colored "filtered by X" is the signal: the count
difference is from the filter, not from data drift. Cheap to
implement, prevents a class of "is this a bug?" support questions.

## 9. Stacked compare rows for narrow stat cards

For "the Model-vs-Market stat cards look bunched up / wrapped wrong" complaints.
The anti-pattern is inline comparison text in a ~200px-wide card:

```html
<!-- BAD: "Model 0.2438 vs Market 0.2598" at 20px font is ~280px wide.
     It overflows a 200px card and wraps mid-value: "0.2438 vs" stranded,
     "Model" splits from its value, three different text sizes jammed in. -->
<div class="stat-value" style="font-size:20px">
  Model <span>0.2438</span>
  <span> vs Market </span>
  <span>0.2598</span>
</div>
```

The fix is to **stop trying to put "Model X vs Market Y" on one line in a
stat card**. The card is the wrong primitive for a comparison — it's
designed for one value with a label. The recipe: stack as 2 compact rows
with label-left, value-right, then a one-line hint below.

**HTML:**
```html
<div class="stat-card stat-card-compare">
  <div class="stat-label">Brier Score</div>
  <div class="stat-compare-row">
    <span class="stat-compare-label">Model</span>
    <span class="stat-compare-value" style="color:var(--success)">0.2438</span>
  </div>
  <div class="stat-compare-row">
    <span class="stat-compare-label">Market</span>
    <span class="stat-compare-value" style="color:var(--text-secondary)">0.2598</span>
  </div>
  <div class="stat-hint" style="white-space:nowrap">-0.0160 · beats market</div>
</div>
```

**CSS:**
```css
.stat-card-compare {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-compare-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  line-height: 1.25;
}
.stat-compare-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-weight: 500;
}
.stat-compare-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-numeric);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
```

**Hint copy guidelines** (the hint is a one-liner so it must fit at 11px
in a 200px card — ~25 chars max):
- Lead with the delta value: `+4.2pp vs market`, `-0.0160 · beats market`.
- Drop the parenthesized count (`(985 games)`) — the next-door
  "Games Analyzed" card already shows it. Redundant counts are a
  common wrap cause.
- Use `white-space: nowrap` on the hint div so a future longer value
  (e.g. `-0.01604`) can't cause a wrap regression.
- Use direction-agnostic phrasing: `beats market` / `behind market`
  instead of `model beats market` / `market beats model` (saves 6 chars).

**Don't do this:**
- Don't shrink the font to fit ("Model 0.2438 vs Market 0.2598" at 12px
  is illegible on a dark background). Shrinking fonts to make bad
  layouts fit is the standard anti-pattern. Restructure the layout.
- Don't pad simple single-value cards to match the height of compare
  cards — the asymmetry is fine. Padding the simple ones to match
  makes them look empty. The eye reads the compare cards as "richer
  data here" and that's actually correct.
- Don't try `text-overflow: ellipsis` — that hides data, which is worse
  than ugly wrapping.

**Verification recipe** when the fix is CSS/JSX-only and you don't have a
live API:
1. Build a static HTML snippet with the production CSS link
2. Copy it into the directory served by `python -m http.server` (the
   server's root may not be `/tmp` — copy into `ui/_preview.html`)
3. `your browser tool` to it, `your screenshot tool` to screenshot, iterate
4. Clean up the preview file before commit

The visual review should call out: (a) is the wrapping fixed, (b) do
subtitles fit on one line, (c) is the height difference between simple
and compare cards acceptable or jarring. "Noticeable but acceptable,
not jarring" is the bar.

## 10. ETA hint on expensive buttons

For "I clicked Run and I have no idea if it's working" complaints.

```js
function estimateMCDuration(iterations) {
  const SECONDS_PER_ITER = 0.001;  // calibrate for your workload
  const total = Math.max(1, iterations) * SECONDS_PER_ITER;
  if (total < 1) return '< 1s';
  if (total < 60) return `~${Math.round(total)}s`;
  const mins = total / 60;
  if (mins < 5) return `~${Math.round(mins)} min`;
  return `~${Math.round(mins)} min (long)`;
}

function updateMCEtaHint() {
  const iter = parseInt(document.getElementById('mc-iterations')?.value || '1000', 10);
  document.getElementById('mc-eta-hint').textContent = `(${estimateMCDuration(iter)})`;
}

// Bind once, update on input change
const iterInput = document.getElementById('mc-iterations');
iterInput?.addEventListener('input', updateMCEtaHint);
```

Calibrate `SECONDS_PER_ITER` from production observations. Update
the hint when the input changes so the user sees the impact of
their choice (e.g. `1000 → 1s`, `10000 → 10s`, `50000 → 50s`).
