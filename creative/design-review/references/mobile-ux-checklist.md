# Mobile UX Deep Dive Checklist

Use when reviewing a mobile app implementation from a UX perspective — not just "does it work" but "does it feel right." Goes deeper than the 5-dimension design critique (which scores visual quality) into interaction patterns, information architecture, and user journey coherence.

## Scoring Dimensions (Mobile-Specific)

### 1. Information Architecture
- Is the primary entry point aligned with the user's mental model? (e.g., "Destination + Date" not "Browse 1,688 ports")
- Does the screen hierarchy match how users think about the domain?
- Are high-cardinality entities (10K+ rows) behind filter axes, not standalone browse surfaces?
- Is there a clear "decision funnel" from browse → compare → act?

### 2. Interaction Patterns & Feedback
- Loading states: consistent component on every async screen?
- Empty states: icon + title + subtitle + guidance (not just "No results")?
- Error states: inline messages with retry, not silent `.catch(console.error)`?
- Pull-to-refresh on browse screens?
- Haptic feedback on key interactions (native only)?
- Touch targets ≥ 44pt?

### 3. Content Density & Cognitive Load
- Does each card/row show enough information for a decision?
- Are there missing data fields that the API already returns but the UI doesn't render?
- Is there information duplication (same description in hero + quote section)?
- Are long text fields truncated with "Read more" toggles?

### 4. Visual Hierarchy (Squint Test)
- Heading-to-body size contrast: ≥ 2.5x?
- Color system: only 1 accent color for CTAs, or is everything coral?
- Typography scale: clear 4-5 level hierarchy?
- WCAG AA contrast ratios on ivory/light canvases? (especially tertiary text)

### 5. Navigation & Wayfinding
- Can users get back to where they came from? (breadcrumbs, context indicators)
- Does the current screen show context from the navigation path? (e.g., "Serving Caribbean" on cruise line detail)
- Are there dead ends? (buttons that lead nowhere, "Coming Soon" cards)
- Tab bar: does each tab have a clear, distinct purpose?

### 6. Trust & Credibility
- Are ratings/source attributed? ("Industry experts" — who?)
- Are data claims verifiable? ("Based on X,XXX+ sailings")
- Is there social proof or authority signaling?
- Are limitations honestly disclosed?

### 7. Missing Signature Moments
- Does the app have any visually distinctive moments that competitors don't?
- Are data-rich assets (maps, charts, images) being fully utilized?
- Is there editorial content (seasonal advice, best months, crowd levels)?
- Does the app feel like a "database browser" or a "travel magazine"?

## Common Silent Bugs to Check

1. **API response key mismatch** — backend returns `{ recommendations: [...] }` but frontend destructures `.itineraries`. Produces empty sections with no error.
2. **Missing data fields in UI** — API joins and returns `miniMapSvg`, `cruise_line`, `tier` but the render function doesn't use them.
3. **Default filter values** — "All" as default month shows unfiltered noise. Current month is better for cruise apps.
4. **Jargon leakage** — "pax", "GT", "berths" in consumer-facing UI. Grep for industry terms.
5. **Dead UI elements** — `<View>` components that look tappable but aren't `<TouchableOpacity>`. Clan pills, tier badges, stat rows.

## Output Format

Structure the review as:
1. **Score Summary** — 7 dimensions, 1-10 each
2. **The User Journey** — where it works, where it breaks
3. **Screen-by-screen issues** — specific, actionable
4. **Prioritized Recommendations** — Quick Wins (<1hr) / Structural (2-4hr) / Big Bets (1-2 days)
5. **Best Thing** — always acknowledge what's working
6. **Biggest Issue** — the one thing to fix first

## Related Skills

- `design-review` — 5-dimension visual critique (parent skill)
- `anti-ai-slop` — what NOT to do in AI-generated designs
- `popular-web-designs` — reference patterns from real apps
- `codebase-survey` — targeted deep dive checklist (code structure, not UX)
