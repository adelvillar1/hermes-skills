# Code-Based UX Audit Checklist

Use when auditing UX from source code without rendering the app. Each section maps to a review dimension.

## Information Architecture & Navigation

- [ ] Map screen hierarchy from navigation.js / router files
- [ ] Identify entry points (tabs, deep links, push navigation)
- [ ] Check for dead-end screens (no way to go deeper or back)
- [ ] Verify navigation params match what receiving screens expect
- [ ] Count stack depth (3+ levels deep = wayfinding problem)
- [ ] **Verify every `validViews` / `validRoutes` array includes the actual nav items rendered.** A `<button data-view="users">` paired with `validViews = [..., 'corpus']` (missing 'users') silently redirects on direct URL load — a P0 that code review alone misses. Grep both arrays side-by-side: `grep -E 'data-view=' ui/dashboard.html` vs `grep validViews ui/js/dashboard.js`.
- [ ] **Check init() / bootstrap order for async state.** Look for: `fetchUser().then(setState) {...restOfBootstrap()}` where `restOfBootstrap()` runs synchronously after the `.then()` is registered (not inside it). The bootstrap reads `_user` before the fetch resolves → admin views check `isAdmin()` on a null user and bail. Walk every page-load bootstrap and trace which reads happen inside vs outside the auth promise's `.then()`.

## Interaction Design

- [ ] Every `<View>` that looks interactive should be `<TouchableOpacity>` or `<Pressable>`
- [ ] `activeOpacity` values are consistent (0.7-0.85 range)
- [ ] Touch targets ≥ 44pt (check padding + element size)
- [ ] Feedback on actions: loading indicators, state changes, haptics
- [ ] No `disabled` elements without visual disabled state
- [ ] **For web: every `<th>` styled with `cursor: pointer` must have a click handler.** Dead affordance — users click expecting a sort. Either wire it up or strip the cursor. Same rule for any `cursor: pointer` on elements without handlers.
- [ ] **For web: every icon-only button needs `aria-label`.** Closing X, back arrow, action buttons with no text. The visible-icon-only pattern is a guaranteed accessibility miss.

## Data Flow & Empty States

- [ ] Every API call has loading state
- [ ] Every API call has error state (not just `.catch(console.error)`)
- [ ] Every list has empty state with guidance text
- [ ] Sub-loads (recommendations, related data) have error handling
- [ ] Pagination metadata is used, not discarded
- [ ] **Dedupe by stable identity key in any "list of cards from list of records" aggregator.** Common pattern: `computeAlerts(scenarios, divergence)` — the same team appears in both, gets two cards. Use `Set<key>` with `type:teamId` or `id` as the dedup key. Always check if a single source feeds multiple lists before assuming "N records = N cards."
- [ ] **When the data is a series, group it before rendering.** "Next 3 games" rendered as 3 cards produces visual duplication when all 3 are vs the same opponent. Group by `opponent_id` and show a single "Game N of M" card with all dates concatenated.
- [ ] **Hunt for undefined function references in template literals.** `esc()` called in `renderUsers()` when only `escapeHtml()` exists → silent ReferenceError caught by the loadView error handler, surfaced as generic "Failed to load data." Grep the file for every function name used in a template literal and verify it's defined in scope.

## Visual Hierarchy (from style objects)

- [ ] Typography scale has clear levels (display → heading → body → caption → label)
- [ ] Color contrast: foreground on background ≥ 4.5:1 for WCAG AA
- [ ] Accent color used sparingly (one primary action per screen)
- [ ] Whitespace is systematic (spacing tokens, not magic numbers)
- [ ] Icon usage is consistent (same icon set, no mixing Ionicons + Material)
- [ ] **Single source of truth for numbers that appear in multiple places on one page.** Team-detail hero had narrative "down 60 over the last week" alongside a `-47 7-day` tile and a `-58 30-day` tile — four different values for the same period, eroding trust. When prose numbers a stat: derive the prose from the same data the stat uses, OR strip the prose.
- [ ] **Page title in topbar should be the largest text in the topbar.** If the topbar has filters, logout, and a page title all at the same font size, the page title loses — users can't tell what view they're in. Bump page title to 18-20px or move filters into a sub-row.

## Content Strategy

- [ ] Jargon translated for consumer audience
- [ ] API data that exists but isn't rendered (route maps, metadata, relationships)
- [ ] Default filter states match user intent (current month vs "All")
- [ ] Attribution/authority signals on data-driven content
- [ ] "Coming Soon" or dead-end promotional content removed
- [ ] **"Data freshness" indicator on dashboards.** If the system runs a daily sync, the user has no way to know if they're looking at fresh or stale data. A small "Updated 2h ago" line costs 30 minutes to add and is the single biggest trust signal the product can ship.
- [ ] **No emoji as functional UI icons** (`🔮 💬 🔴 📊 📈`). Anti-ai-slop violation. Replace with Lucide/Heroicons stroke icons. Emoji render fonts differently across macOS/Windows/Linux and carry zero brand identity.
- [ ] **Hunt for dead-tier confidence/categorization gates.** When a system produces tiered labels ("high/medium/low", "critical/warning/info"), verify each tier actually fires. Threshold gates that were set for a hypothetical data distribution often become unreachable once the system produces real distributions (e.g., Glicko-2 phi stuck at 60-90 because the gate was `phi < 50`). Diagnostic: query a sample of records, count how many fall in each tier. If any tier is 0% of the corpus, the threshold is wrong. Fix: re-tune the gate to where the data actually lives, OR explicitly call out the dead tier in the model docs and ask the user if it should be removed entirely.
- [ ] **Ranking UIs: the "alignment is meaningless without decisiveness" principle.** When sorting cards by alignment between two methods (e.g., ELO prediction + MC simulation, or any "two signal sources agree" metric), filter for **decisiveness first** (the prediction is far from the indifferent value, e.g. ≥ 65% probability from the primary signal). Without this, a 51%/53% toss-up is trivially "aligned" because both methods cluster at 50/50 when uncertain. Hierarchy: `decisiveness > alignment > confidence > CI width`. Each layer gates whether the next layer's signal is meaningful. Verified by the "Top Picks surfaced 50-55% coin-flips" feedback loop — user said "I was expecting games with much higher probability in either direction."

## Accessibility

- [ ] Text contrast ratios on canvas/surface backgrounds
- [ ] `accessibilityLabel` on icon-only buttons
- [ ] `accessibilityRole` on interactive elements
- [ ] Keyboard navigation support (web)
- [ ] **Sortable tables need keyboard support too.** Click + Enter/Space on `<th role="button" tabindex="0">` if the headers are clickable.

## Auth & Access Control

- [ ] **Authenticated audits need the test-user recipe.** Most web apps gate at least one surface. Don't ship an audit marked "complete" when you only saw the unauthenticated views. The recipe is in the parent SKILL.md under "Visual Review Protocol" — but read the auth service for a `create_user` factory, pick a syntactically valid email (pydantic `EmailStr` rejects `name@local`, `name@host.test`, `@test.com` — these are reserved TLDs), and use a real-looking domain like `name@yourproject.com`.
- [ ] **Direct-URL nav must work for every nav item.** Click each sidebar/topbar item directly (not from another view), confirm the URL is shareable. Most-rendered-but-route-broken surfaces are a recurring P0.
- [ ] **Catch silent error handlers.** `try { ... } catch (e) { console.error(e) }` in route handlers hides the real failure. A `try/catch` that returns "Failed to load data" is masking a 4-line ReferenceError. Look for: catch blocks with a generic fallback message, no `console.error` or `toast(e.message)` propagation.

## Common Code-Level UX Bugs

| Pattern | Symptom | Detection |
|---------|---------|-----------|
| API response key mismatch | Feature appears implemented but always empty | Grep for `.items` / `.itineraries` / `.results` and verify against API response shape |
| Nested ScrollView + FlatList | Scroll jank, broken virtualization | `grep -r "ScrollView" screens/` then check for FlatList children |
| Silent sub-load failures | Blank sections with no explanation | `grep -r "catch(console.error)" screens/` |
| Discarded pagination | Only first page shows | `grep -r "pagination" screens/` — check if pagination data is used |
| Dead UI elements | Buttons that don't respond | `grep -r "View.*style.*button\|View.*style.*pill" screens/` — should be TouchableOpacity |
| Missing route in `validViews` | Direct URL silently redirects to default | Grep the `validViews` array — every nav item should appear in it |
| Init race: bootstrap reads state before async resolves | Admin views bail with "access required" on direct load | Trace which init functions run inside vs outside the auth promise's `.then()` |
| Undefined function in template literal | Generic "Failed to load data" error | Grep for every function name in `\`\${fn(...)}\`` — verify it's in scope |
| Cursor: pointer on `<th>` with no handler | Click does nothing | `grep "cursor: pointer" ui/css/` then check each match for a JS handler |
| Duplicate cards from multi-list dedup | Same alert / same opponent 3× in a row | Inspect any function that builds an alert/feed list from multiple sources |
| Stat tile values contradict nearby prose | User trust collapse on team detail | Grep for numeric templates near copy that mentions time periods |
| Dead-tier confidence gate (0% of corpus) | A confidence tier never fires | Query sample records, count tier distribution; if any tier is 0%, threshold is wrong |
| "Alignment" sort surfaces 50/50 toss-ups | Users see "agrees" picks at 51%/53% | Add a decisiveness floor (e.g., max(elo, 1-elo) >= 0.65) before alignment matters |
| Badge copy lies about data quality | "✓ agree" tag on a 14.5% delta card | Tier the badge by quality (agree / within X% / hidden), don't soften — filter out |
| Single badge covers heterogeneous data | Same label for Δ=1% and Δ=14% | Three badges (✓ agree / △ within 10% / hidden), each tied to a numeric threshold |
