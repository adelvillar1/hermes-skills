---
name: ui-implementation-review
description: Use after building a UI feature to systematically audit t.
---

# UI Implementation Review

Systematically audit a recently-implemented UI feature against its plan document, feature docs, and design system. Find bugs, UX gaps, missing wiring, and architecture anti-patterns before the user discovers them. The output is a prioritized report: bugs first, then UX improvements, then architecture debt.

## When to Use

- User says: "review the implementation", "comprehensive review", "audit what was built", "what did we miss", "do a thorough review"
- User says: "review the mobile app", "in-depth review of the app", "full app review", "deep review"
- After completing a feature with 5+ new or changed screen files
- Before shipping a major navigation or layout restructure
- When the user asks "what's left to do" after a feature build

## Preconditions

### Feature audit mode
- A plan document exists (the contract to audit against)
- Feature docs exist for the areas touched
- The design system (theme, tokens, components) is established
- The API layer is implemented alongside the UI

### Full-app review mode
- No plan document required — auditing against correctness and consistency
- Design system (theme.js, shared components) exists
- API client layer exists (for cross-referencing response shapes)
- Navigation config exists (for route-name validation)

## Workflow

### Choosing the right mode

**Feature audit** — use when reviewing a specific feature just built, with a plan document to audit against. Follow steps 1–8 below.

**Full-app review** — use when reviewing an entire app or large section for general health, with no specific plan. Skip step 1 (no plan to load), skip step 4 (no plan to cross-ref), but add the full-app-specific checks from step 2b and step 3b below.

### 1. Load all contract documents (feature audit mode)

Read the plan file, all relevant feature docs, and the design system (theme.js, shared components). This is the baseline you'll audit against.

### 2. Read every screen file in full

Read every new and modified screen file. Do NOT sample — missing one screen means missing a bug pattern that repeats across screens. Pay attention to:

- **Data flow**: what API calls are made, how responses are destructured, what fallbacks exist
- **Component reuse**: are shared components (Card, PillFilter, FavoriteButton, LoadingState) used consistently?
- **Design tokens**: are colors, typography, spacing, radii all from theme.js? Any hardcoded values?
- **State management**: loading, error, empty, and edge-case states
- **Navigation**: screen params passed correctly, back-navigation works, deep links wired

### 2b. Full-app review: additional screen checks

When doing a full-app review (no plan), add these cross-screen checks:

- **Duplicated utility functions**: identical `tierColor()`/`tierLabel()`/formatting functions copied across 2+ screens → extract to shared util
- **Dead styles**: `StyleSheet.create` entries that are never referenced in JSX
- **Navigation route names**: every `navigation.navigate('RouteName')` must match a registered screen in the stack — `QuizHome` navigated to but only `QuizResults` exists is a crash
- **Session lifecycle**: any resource created on mount (API sessions, listeners, subscriptions) must be cleaned up in an unsubscribe/unmount effect
- **Closure staleness**: `useCallback`/`useEffect` with stale dependencies — `isMounted` ref checked after async work may always be `true` at that point, hiding real bugs
- **FlatList index bugs**: `stickyHeaderIndices={[3]}` indexes into the data array, NOT visual position — verify the index is correct for the actual data structure
- **Field name consistency**: API returns `image_url` but screen uses `item.image` (or `passenger_capacity` vs `pax`) — check every destructured field against the actual API response shape
- **N+1 API patterns**: components that fire individual API calls per list item on mount (e.g., FavoriteButton calling `getFavoriteStatus` for every card in a FlatList) — flag for batch endpoint or parent-level prefetch

### 3. Read every API route and the API client

Read the backend routes that serve the screens you audited. Cross-reference every API call from the frontend against the actual route implementation. Key checks:

- **Response shape**: does the frontend destructure the right keys?
- **Field names**: do the API field names match what the frontend expects? (Common bug: API returns `itineraryName` but frontend checks `it.name`)
- **Filter/query params**: does the frontend pass the right params that the backend actually filters on?
- **Active-records enforcement**: are status/active filters applied on every endpoint?

### 3b. Full-app review: API client audit

When reviewing the entire API layer:

- **Endpoint coverage**: list all API client functions and verify each has a corresponding backend route
- **Error handling in the client**: does the client have a central error handler, or does each function handle errors differently?
- **Authentication wiring**: are auth tokens passed consistently, or do some endpoints miss the Authorization header?
- **Inconsistency in response unwrapping**: some endpoints return `response.data.data`, others `response.data` — does the client handle both or assume one shape?

### 4. Cross-reference against the plan

For each acceptance criterion in the plan, determine its actual status by reading the code, not trusting the plan's self-reported status. A criterion marked "done" in a recap may have a bug that makes it non-functional.

### 5. Categorize findings

Group every finding into one of three tiers:

**🔴 Bugs**: behavior that is definitely wrong — wrong response keys, dead UI, broken filters, inaccessible features. These ship today.

**🟡 UX Issues**: behavior that works but degrades the experience — missing interactions, overflow, inconsistent labels, missing states, jargon. These ship next iteration.

**⚪ Architecture Debt**: patterns that work but will cause problems at scale — nested ScrollView+FlatList, silent error handling, inconsistent API shapes. These ship when time allows.

### 6. Assign effort and impact

For each finding, estimate implementation effort (minutes/hours) and user impact (high/medium/low). This lets the user prioritize.

### 7. Present as a structured report

Format:

```
## What's Working Well
(bulleted list of things that are correct and well-implemented)

## Bugs & Defects 🔴
(numbered, with file:line references, root cause, fix suggestion)

## UX Issues 🟡
(numbered, with file references and suggestions)

## Missing Features / Gaps ⚪
(numbered)

## Architecture Issues 🏗️
(numbered)

## Priority Recommendations
(table with issue #, effort, impact, sorted by priority)
```

### 7a. Do live curl/browser QA before declaring the review done

Unit tests + TestClient pass ≠ feature works in production. Before writing the report, run real curl / browser / mobile-curl commands against a running dev server. The two cases where this is mandatory (because TestClient is most likely to lie):

- **Auth-related changes** (login, register, token refresh, logout, multi-source auth). TestClient attaches the cookie + the header simultaneously, so a test asserting `Authorization: Bearer <token>` works can pass when only the cookie works.
- **CORS-related changes**. TestClient doesn't enforce preflight; real browsers will reject missing CORS headers.

**🚨 Do the browser verification yourself — never punt it to the user as "pending manual test."** If browser automation is available (Playwright, your browser tool, etc.), YOU drive the browser to verify login, mutations, WS connections, and UI rendering. Marking an AC as "pending manual browser test" when you have the tools to do it yourself is a workflow failure. The user expects you to close the loop: register → login → perform the action → confirm the result, all via automation. Only defer to the user when the verification genuinely requires human judgment (e.g. "does this animation feel right") or physical hardware (e.g. pinch-zoom on a real phone).

**Include screenshots in the report.** Every finding that has a visual component must include a screenshot captured via `your screenshot tool` or equivalent. Save the `screenshot_path` and reference it with `MEDIA:<path>` in the report. A finding without a screenshot is incomplete — the user explicitly requires visual evidence.

The 30-second version:
```bash
# Start dev server in background
.venv/bin/python -m uvicorn src.api.main:app --port 8765 --log-level warning &

# Real curl
curl -sS -w "\nHTTP %{http_code}\n" http://localhost:8765/api/some-endpoint
curl -sS -w "\nHTTP %{http_code}\n" -H "Authorization: Bearer $TOKEN" http://localhost:8765/api/some-endpoint

# Or use the browser tool to load the page and screenshot
```

If the live QA finds a bug that the tests missed, add it to the report under 🔴 Bugs. Cite the curl command in the bug description so the user can reproduce.

### 7b. Route-by-route auth matrix audit (mandatory on multi-route services)

Multi-route services (Fastify, Express, Rails, Django REST, Next.js route handlers) ship features one route at a time. The `requireSession()` / `requireAuth()` / `requireAdmin()` middleware gets added to new routes but the same coverage is rarely retrofitted to older unprotected routes. A full-app audit MUST check every state-changing route in a single pass, otherwise the entire class slips through.

**Audit recipe for any `routes/*.ts` (or equivalent) directory:**

```bash
# 1. List every route registration
grep -rhE '(app|router)\.(get|post|patch|delete|put)\(' apps/api/src/routes/

# 2. Check which routes call requireSession / requireAuth / requirePlatformAdmin / isDmOfCampaign
grep -rnE 'requireSession\(|requireAuth\(|requirePlatformAdmin\(|isDmOfCampaign\(' apps/api/src/routes/

# 3. Diff: every (post|patch|delete|put) MUST appear in #2. Anything missing = bug.
```

**Live verification:** hit the suspect route with no auth header / no cookie and confirm it does NOT return `HTTP 200/201/204`. Any successful response on a state-changing route without auth is a 🔴 CRITICAL bug — cite the curl command so the user can reproduce.

**Real failure (the D&D VTT project, 2026-07-18):** `DELETE /saved-encounters/:id` had no `requireSession`, no `isDmOfCampaign`. Live `curl -X DELETE` (no cookie, no auth) returned **HTTP 204** — would have deleted any saved encounter by ID. The audit found 4 routes with the gap (`PATCH/DELETE /content/:id`, `POST /content/:id/duplicate`, `GET /content/:id`) in a 30-minute grep. Report each one with the curl command + observed response.

**Reporting template for this class of bug:**

```
### 🔴 B<N>. <verb> /<resource>/:id accepts unauthenticated requests 🛡️

**File:** apps/api/src/routes/<file>.ts:<line>
**Verify:**
curl -sS -X <METHOD> https://staging.example.com<path>/<fake-uuid> -w '\nHTTP %{http_code}\n'
# Live: HTTP 204 (or 200 — proves the route accepts no-auth requests)

**Fix:** Add requireSession() at the top of the handler; for destructive routes
add isDmOfCampaign(campaignId, accountId) after loading the row.
```

Always cite the curl command. Reproduction recipe is what makes the report actionable.

### 7c. Server-route ↔ UI-feature matrix (the missing CRUD buttons)

UI panels often present Create but omit Edit/Delete, even when the server has the routes. Reverse is also true: UI button implies a route that doesn't exist. Audit both directions:

```bash
# 1. Routes that exist on the server but the UI never calls:
for verb in POST PATCH DELETE; do
  grep -rhE "app.${verb,,}\(" apps/api/src/routes/ \
    | sed -E 's/.*app\.[a-z]+\("([^"]+)".*/\1/' \
    | sort -u
done

# 2. For each route, grep the UI for the corresponding action:
#    POST /foo       → createFoo() in api.ts + <button onClick={create}>
#    PATCH /foo/:id  → updateFoo() + edit button
#    DELETE /foo/:id → deleteFoo() + delete button
```

**Real failure (the D&D VTT project, 2026-07-18):** `DELETE /handouts/:id` and `PATCH/DELETE /journal/:id` exist on the server, but `HandoutPanel.tsx` and `JournalPanel.tsx` have no Edit or Delete buttons — DMs cannot recover from typos. Diagnostic:

```bash
$ grep -nE 'edit|delete|patch' apps/web/src/components/HandoutPanel.tsx
# (exit 1 — zero matches)
$ grep -nE 'edit|delete|patch' apps/web/src/components/JournalPanel.tsx
# (exit 1 — zero matches)
```

Report each missing button as 🟡 UX with the file:line and the existing server route to wire it to. Same pattern catches both directions.

### 7d. Topbar / chrome button density check

When a UI has a header / topbar / toolbar with more than ~8 toggle buttons, the audit should count them explicitly and flag UX density as 🟡:

```bash
# All buttons in a component:
grep -cE '<button' <component.tsx>

# Buttons specifically inside the header chrome:
awk '/<header /,/<\/header>/' <component.tsx> | grep -cE '<button'
```

If the chrome has >8 buttons AND no icons AND no grouping AND no keyboard shortcuts, flag as 🟡 (or 🔴 if at narrow viewports the topbar overflows off-screen without horizontal scroll as a graceful fallback). The fix is usually: group semantically (Map / Combat / Content / Admin / Session), use icons + tooltips, add `Esc` to close topmost panel, add `i` for initiative etc.

**Real failure (the D&D VTT project, 2026-07-18):** 21 toggle buttons in the tabletop topbar — overflows at 1366×768, no grouping, no icons, no keyboard shortcuts. The "Set map" affordance was an `<input type="file">` masquerading as a label; the only way to discover upload was to click the label text.

### 7e. Auth shipped but client never wired it

Distinct from the TestClient pitfall (#14): this is a *client-side missing call*, not a server-side multi-source auth confusion. The server has `/auth/me` (or `/auth/refresh`, `/auth/profile`), but the web app's root component has no `useEffect` calling it. Symptom: every page reload forces re-login even though the cookie is still valid.

Diagnostic:

```bash
# Replace /auth/me with whichever session-restore endpoint the project exposes
grep -rn "auth/me" apps/web/src
# 0 hits on a project whose docs claim "session restored on page reload" = bug
```

**Real failure (the D&D VTT project, 2026-07-18):** `/auth/me` endpoint exists and is documented; zero hits anywhere in `apps/web/src`. `App.tsx` has no `useEffect` calling it. Every page reload = forced re-login. Report as 🔴 with the missing call site (root component file + line).

### 7f. User-facing UI showing dev jargon

When a page tagline, hero text, or button label was copy-pasted from a PR title, component spec, or migration commit message, look for dev-facing artifacts that survived into user copy. Concrete failure (the D&D VTT project, 2026-07-18): the `<Landing>` page showed `<p className="tagline">Session cookie + WS ticket auth</p>` as the user-facing tagline — that's a developer-facing artifact (auth mechanism), not a value proposition for a D&D player.

Diagnostic grep for landing / hero / first-impression components:

```bash
grep -rnE 'TODO|FIXME|XXX' apps/web/src/components/Landing.tsx apps/web/src/components/Hero.tsx
grep -rnE 'stub|WS|ticket|hash|cookie' apps/web/src/components/Landing.tsx
```

Anything matching on a player-facing page is 🟡 UX at minimum.

### 7g. Cite live verification in every 🔴 finding

Every 🔴 Bug in the final report should include BOTH the file:line AND a curl command + observed output that proves the bug. Reproduction recipe is what makes the report actionable — when a reader says "is this really a bug?", they should be able to copy/paste the curl and verify themselves. Abstract descriptions ("the route accepts unauthenticated requests") are weaker than reproducible evidence (`curl -X DELETE ... returned HTTP 204`). Treat the report as a QA artifact that should survive the reader's first skeptical read.

### 7h. Per-surface UX checklist audit (checklist.design pattern)

Before writing the report, run the feature's surface against its **canonical design checklist**. Source: https://www.checklist.design — 110 checklists across mobile app / web app / website / design system / flows. Each checklist is 5–8 items, each item = a title + one-line definition + a "why it matters" tip. The value is the **rationale attached to every item** — these are field-tested observations, not surface checks.

**How to use it during a review:**
1. Identify the surface(s) the feature touches: paywall, onboarding, empty-state, pricing, login, settings, notifications, splash screen, admin panel, input field, modal, button, tooltip, toast, adding-to-cart, canceling-subscription, etc.
2. Pull the matching checklist(s) from the site (URL pattern: `/mobile/{surface}`, `/web-app/{surface}`, `/website/{surface}`, `/design-system/{surface}`, `/flows/{surface}`). The "browse" page lists all 110.
3. Audit the implementation item-by-item. For each missed item, write a 🟡/🔴 finding citing the checklist item + the checklist URL so the reader can see the expectation.
4. Check the cross-platform variant when relevant — mobile vs web-app checklists differ (e.g. mobile paywall needs restore-purchases; web-app pricing needs billing-period toggle).
5. Check the Related checklists on the page — they flag adjacent surfaces the feature probably also touches (login → resetting-password → 2FA).

**Sharpest distilled items (proven non-obvious, from the sampled set — full list in `references/surface-checklist-library.md`):**
- **Empty state**: zero state ≠ no-results state ≠ error state. "A no-results state without a way to reset or broaden the search is a dead end." "Showing an empty state when the real issue is a loading error causes users to assume they've lost their data."
- **Paywall**: dismiss/decline copy must be neutral — "'No thanks, I don't want to save money' is manipulative and unnecessary." Frame trials as low-commitment ("Try free for 7 days" = highest-converting message). Restore purchases is a checklist item.
- **Login**: error states must distinguish "unrecognised email" vs "incorrect password" — "Generic 'incorrect credentials' gives users no useful signal." If any social provider is offered on iOS, Apple Sign In is required (App Store guideline). Passwordless/magic-link is a listed alternative.
- **Onboarding**: keep steps to what's genuinely required day-one ("Steps that can be deferred consistently belong later"). Progress indicator reduces abandonment ("Users who can see the end of onboarding are significantly less likely to abandon it"). Contextual permissions, not grouped at start. Skip option must exist.
- **Pricing**: billing-period toggle with annual discount; trial-end behavior must state whether the account downgrades or charges automatically; FAQ for billing/cancellation; enterprise option.

**Do NOT treat these as exhaustive.** The site's items are the floor, not the ceiling — your per-project pitfalls (sections 1–43 above) still apply. Use the checklist to catch what a code-grep audit structurally can't: copy tone, state coverage, platform conventions, and conversion-science details.

### 8. Offer to create a fix plan

After presenting findings, ask if the user wants a plan document to address them all. If yes, load `draft-feature-plan` and create one.

## Common Pitfalls

1. **Skipping screens because they seem fine.** Read every one. A "pax" bug on CruiseLineDetail was missed because ShipDetail was already fixed — the same mistake repeats unless you read both.

37. **🚨 Adding UI to the wrong component — Harbor vs non-Harbor dual-path.** When a project has a feature-flagged dual UI (e.g., Harbor mode vs legacy mode), the same user-visible feature may be served by completely different components on each path. Adding a toggle button to `ItineraryDetailModal.tsx` (the legacy modal) is useless if the user is viewing `HarborItineraryDetail.tsx` (the Harbor detail page) — a different file that uses `HarborItineraryDetailSvgMap` directly, with no modal at all. **Before implementing any UI element, verify which component the user is actually viewing.** The diagnostic: (1) check if a feature flag gates the UI path (`isHarborEnabled()`), (2) trace which component the user's current page renders, (3) confirm the target component is on that path. If the project has a Harbor/legacy split, UI elements must be added to BOTH paths or explicitly scoped to one in the plan.

    **Audit recipe:**
    ```bash
    # Find the feature flag that gates the UI path
    grep -rn "isHarborEnabled\|USE_HARBOR\|featureFlag" app/app/itineraries/page.tsx
    # Trace which component the page renders on each path
    grep -n "HarborItinerariesContent\|ItinerariesContent" app/app/itineraries/page.tsx
    # Check if the target component is used on the Harbor path
    grep -rn "ItineraryDetailModal" app/app/itineraries/HarborItinerariesContent.tsx
    # If 0 results, the modal is NOT used in Harbor mode — UI added to it is invisible
    ```

    **Real failure (2026-06-27):** The 3D map toggle was added to `ItineraryDetailModal.tsx`. The user reported "the toggle is not there" after 4+ rounds of CSS/positioning fixes. Root cause: Harbor was enabled, so the itinerary listing page rendered `HarborItinerariesContent`, which linked to `/app/itineraries/[id]` (the `HarborItineraryDetail.tsx` page) — NOT the modal. The toggle button code was correct but mounted in a component the user never saw. Fix: add the same toggle to `HarborItineraryDetail.tsx`. The lesson: when a user says "it's not there," verify which component they're looking at BEFORE debugging CSS, positioning, or token names.

38. **🚨 Tailwind arbitrary-value CSS variable classes are silently purged from production bundles.** `bg-[var(--bg-glass)]` may not generate a CSS rule in the production bundle even though the variable exists in `globals.css` and the class is in the source code. The element renders with `background: unset` (transparent) — invisible. `tsc` and `next build` do not catch this. The only verification that catches it: grep the built/deployed CSS file for the class name. If the rule doesn't exist, switch to a pre-defined utility class (`bg-glass`, `text-white`, `border-white/10`) or add the class to the Tailwind safelist. See `nextjs-build-pitfalls` Pitfall 8 for the full pattern.

    **Audit recipe:**
    ```bash
    # After building, check if the class was generated
    grep -c "bg-\[var" .next/static/css/*.css
    # If 0, arbitrary-value classes were purged — switch to utility classes
    # On staging, curl the deployed CSS
    curl -sS "https://staging-url/_next/static/css/HASH.css" | grep "bg-glass"
    ```
2. **Trusting the plan's self-reported criteria status.** The plan may say "✅ done" but the code may have a response-key mismatch that makes the feature non-functional. Verify by reading the code.
3. **Not cross-referencing API response shapes against frontend destructuring.** The recommendations bug (API returns `recommendations`, frontend checks `itineraries`) is invisible in isolation — only visible when you compare route file against screen file.
4. **Treating design inconsistencies as minor.** "pax" vs "guests" on different screens erodes trust. Audit every screen for the same label.
5. **Not checking navigation.js for stack completeness.** A new screen may be navigable from one tab but not registered in that tab's stack navigator (clan pills → ItineraryBrowser needed DestinationStack registration).
6. **Presenting findings without prioritization.** A list of 19 issues without triage is overwhelming. Always bucket into bugs/UX/architecture and sort by priority.
7. **Missing navigation route-name mismatches.** `navigation.navigate('QuizHome')` when only `QuizResults` is registered causes an immediate crash. Grep for every `navigate(` call and verify each route name exists in the stack.
8. **Overlooking stale closure patterns in useEffect/useCallback.** An `isMounted` ref checked after an async call often becomes meaningless — the component may have already unmounted and remounted. Flag these for proper cleanup patterns.
9. **Ignoring N+1 API call patterns in list items.** FavoriteButton firing `getFavoriteStatus` per item in a FlatList means 20 items = 20 API calls on mount. Flag for batch endpoint or parent-level prefetch.
10. **Not flagging duplicated utility functions.** If `tierColor()` and `tierLabel()` appear in 3+ screens identically, they should be extracted to a shared module. This is architecture debt that compounds.
11. **🚨 Classifying broken rendering as "polish" or "UI tweaks."** When a section renders `undefined` because JSONB destructuring is wrong, or when an API returns camelCase but the frontend reads snake_case, these are **bugs** — not polish, not UX improvements, not "minor visual issues." Incorrect data rendering means the feature is broken. Categorize these as 🔴 Bugs in the report, never as 🟡 UX Issues. The user explicitly corrects this: "in reality it's broken functionality, not polish." If a section shows nothing or shows `[object Object]`, it's a bug.
12. **🚨 Missing "stringly-typed display path" audit.** A whole class of bugs hides in code that takes a string ID / enum / name and uses it directly in display logic without normalization. The high-leverage check on any UI audit:
    ```bash
    # Grep for the suspicious patterns
    grep -n "name.split\|.toLowerCase()\|.toUpperCase()\|.replace(" ui/js/*.js
    grep -n "/api/auth/login\|/api/auth/register" src/api/routes/auth.py
    ```
    Concrete examples that ship to users:
    - `team.name.split(' ').pop()` for short names → "Boston Red Sox" becomes "Sox", "FC Bayern Munich" becomes "Munich". Use a per-sport alias table or fall back to `team.id` (abbreviation).
    - State stored as one string (e.g. `FOOTBALL_EPL`) but displayed as another (e.g. `Premier League`) with no canonical mapping → same league appears under 3 different names on the same page (chips, dropdown, URL).
    - Login endpoint sets httpOnly cookie but doesn't return `access_token` in response body → CLI / mobile / API-tool clients can't authenticate even though browsers can.
    Audit the data flow for every string field that gets shown to the user. The bug pattern is: API returns string X, state stores X, but display layer expects Y. If the mapping is done ad-hoc in 3+ places, it will diverge.
13. **Treating inconsistency as "polish" instead of a class of bug.** When the same concept has 2+ names on the same page (FOOTBALL_EPL vs EPL, "All Leagues" vs "All", or team names with mixed Title Case / UPPER), the user reads it as "unfinished." Count the variants of each key label across the dashboard before deciding severity: if a label has 3+ forms, the issue is at least 🟡 Medium regardless of how minor each variant looks in isolation. The user explicitly spots these ("you always do Y and I hate it" / "be consistent") and will surface them in the next session if you don't.

    **Audit extension (2026-06-10):** When applying the "stringly-typed display path" check, **list every view that displays the entity type**, not just the ones the user mentioned. In a recent review, Home / Ratings / Team Detail / Match Modal were fixed for `name.split(' ').pop()` but **Schedule was missed** because the audit grepped by call site pattern, not by view. The bug only manifested when the user actually clicked the Schedule view. Audit recipe: after finding one occurrence of a broken display path, grep for the entity's name field across the entire frontend (not just the call site) and verify EVERY render path is fixed. `grep -rn "team\.name\|home_team\.name\|away_team\.name" ui/js/` should produce a finite list. Cross-reference that list against the alias/helper function — any call site that uses the raw name field directly is a missed fix.

14. **🚨 TestClient is a false-positive factory for multi-source auth.** When the security boundary accepts the same identity from multiple sources (httpOnly cookie + `Authorization: Bearer` header, or session cookie + API key, or form login + OAuth), TestClient tests can pass while the real-CLI path is broken. The mechanism: TestClient attaches whatever cookies the response set, AND forwards whatever headers the test passed — so a test that says "register a user (cookie set), then GET /me with the Bearer header" actually sends BOTH the cookie and the header. The endpoint returns 200 via the cookie path; the test author concludes "Bearer works" and ships. Production CLI clients (curl, scripts, mobile apps) don't have the cookie, so they get 401.

    **The fix is to add live-curl QA to the post-implementation checklist.** A 30-second `curl -s -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" $URL` against a real uvicorn server catches what TestClient hides. The test that would have caught this is also easy: `client.cookies.clear()` + `headers={"Authorization": f"Bearer {token}"}` — the cookies.clear() call is critical; without it, the cookie is still attached and the test passes for the wrong reason.

    **When the checklist must include live curl/browser QA:**
    - Auth-related changes (login, register, token refresh, logout)
    - Any new auth path is being added (e.g. "now also accept Bearer")
    - Any multi-source auth (cookie + header, or cookie + API key)
    - Anything that previously had a single auth source that's being extended

    **Other "TestClient lies" patterns to watch for:**
    - CORS: TestClient doesn't enforce CORS preflight; real browsers will reject responses missing CORS headers.
    - Cookie domain/path attributes: TestClient ignores them; production browsers respect them.
    - HTTPS-only cookies / Secure flag: TestClient accepts them on http://localhost; production browsers reject them on http.
    - `X-Forwarded-*` headers (proxies, rate limits): TestClient doesn't simulate the proxy chain; production behavior may differ.
    - 401 vs 403 distinction: a test asserting "401 returned" passes when the endpoint is 401, but a real client might need the WWW-Authenticate header that TestClient doesn't validate.

    **Case study (2026-06-10):** Added `access_token` to login response body so CLI clients could use it. Updated `get_current_user` to accept the Bearer header. Wrote a TestClient test that registered a user, cleared cookies, and asserted `/me` with `Authorization: Bearer <token>` returned 200. **Test passed.** Shipped. Two hours later, did live curl QA at the end of the sprint — `curl -H "Authorization: Bearer ..."` against the running server returned **401**. TestClient had been silently passing the cookie even after `cookies.clear()`. The actual fix was one line in `dependencies.py`, but the test had given a false green.

15. **🚨 Cached endpoint + new response format = silent cache poisoning.** When a route caches its JSON response and you add a new `?format=csv` (or any non-JSON) branch, the cache **returns the cached JSON object even when the caller asked for CSV**. FastAPI will try to serialize a `dict` as a `StreamingResponse` and either crash with `TypeError` or return the wrong content type. The failure mode is silent because the cache is only populated by the JSON path — adding the CSV branch doesn't invalidate it. Symptom: the new format works on the first call (when nothing is cached) and breaks on every subsequent call. The test passes in isolation but fails in the full suite when other tests have warmed the cache.

    **Fix: bypass the cache for the non-default format branch:**
    ```python
    if format != "csv":
        cached = _accuracy_cache.get(sport_lower)
        if cached is not None:
            return cached
    # else: recompute (cheap, and the cached AccuracyReport object
    # is not serializable to CSV anyway)
    ```
    Equivalent pattern: cache key includes the format, OR the format-specific branch recomputes without reading the cache. General rule: **if a request format is response-shape-changing, the cache key must include the format, or the format branch must bypass the cache entirely.**

16. **🚨 Deferred-item reviews rot. Always verify the finding before coding.** When picking up a list of deferred polish items (e.g. "5 medium + 15 low items from the usability review"), the items were identified at a point in time. As the project evolved, the underlying issue may have been addressed by another change. The discipline: before writing code for a deferred item, **read the current code to confirm the issue still exists**. Concrete case (2026-06-10): deferred item L11 was "Calibration view has no inline help — straight to the table." When the second sprint opened up `renderCalibration()`, the explainer card was already there (added implicitly by an earlier change). The right move was to mark it "already done, no change needed" — not invent a fake improvement to justify the ticket. Anti-pattern: coding up a "fix" for a non-existent problem because it's on the list. The list is a backlog, not a contract; each item needs verification on its own merits.

17. **🚨 Multi-view display-path audits must enumerate EVERY view, not grep the call sites.** When the first polish sprint fixed `team.name.split(' ').pop()` for the "Sox" disambiguation, the fix targeted the call sites in Home/Ratings/Team Detail/Match Modal. The Schedule view still had the bug because the original audit grepped by call-site pattern (`renderMatchCard`, `renderRatingsTable`) rather than by entity type. The user caught it: *"the only issue I see is the schedule page still showing sox for both chicago white sox and boston red sox"*. The fix was a 4-line patch in `getShortName()` + 1 line in the schedule call site. Audit recipe when fixing a display-path bug:

    ```bash
    # Don't grep by the helper function — grep by the entity type's name field
    grep -rn "team\.name\|home_team\.name\|away_team\.name\|g\.home_team\|g\.away_team" ui/js/
    # → finite list. Cross-reference each against the alias/canonicalization helper.
    # Every entry that uses the raw .name field directly is a missed fix.
    ```
    The same applies to any "fix display logic" change: a single missing view will look fine in the diff but burn a 30-second user report. The general rule: **after fixing a display-path bug in N places, search for the entity's data field, not the function that did the fix.** A helper function added to one view doesn't migrate other views automatically.

18. **🚨 Inline comparison text in narrow stat cards is a wrap-trap.** When a stat card needs to display two values side by side (Model vs Market, Actual vs Expected, Before vs After), inline text at 20px+ font **always** overflows a ~200px-wide card. Symptoms the user reports: "bunched up", "doesn't look good", "wrapped wrong", "stranded text". Concrete failure modes:
    - `"Model 0.2438 vs Market 0.2598"` (~280px at 20px) wraps mid-value: `0.2438 vs` stranded on its own line, `Model` splits from its value, three different text sizes jammed into one card.
    - Hint copy like `"+4.2pp vs market (985 games)"` wraps the parenthetical to a second line, orphaning `(985 games)`.
    - The user's eye reads it as "broken" or "unfinished".

    **The fix is to restructure the layout, not shrink the font.** A stat card is the wrong primitive for a comparison — it's designed for one value with a label. The recipe (full code in `dashboard-polish-primitives.md` section 9):
    1. Add `stat-card-compare` variant: 2 stacked rows (Model, Market) + one hint line.
    2. Use flex `justify-content: space-between` so the label sits left, value sits right.
    3. Hint copy ≤ 25 chars at 11px to fit one line; drop redundant counts (`(985 games)` — already in the next-door "Games Analyzed" card); use `white-space: nowrap` on the hint div to prevent future wrap regressions.
    4. Don't pad simple single-value cards to match compare-card height — the asymmetry is fine, padding the simple ones makes them look empty.

    **Audit recipe:** when reviewing a dashboard, grep for any stat card with two data values in the same `.stat-value` div:
    ```bash
    # Find any stat-value that contains "vs" or multiple span children
    grep -rn "stat-value" ui/js/ | grep -i "vs\|model\|market\|actual\|expected\|baseline"
    ```
    Each hit is a candidate for the stacked-rows refactor. **Don't just measure font size and call it fine** — measure total text width against the card's actual rendered width. If text width > card width at the design font, it'll wrap on the user's screen.

19. **🚨 Redundancy across adjacent sections and blind component reuse.** When consolidating UI (e.g., densifying a page), audit for information duplication across *adjacent* sections. Example: A "Form & Momentum" card showing 7d/30d trends and a sparkline when those exact metrics already exist in the Hero card. The fix is merging the novel data (e.g., 5-game W/L pills) directly into the existing Hero stats row, eliminating the redundant card entirely.
    Similarly, when asked to "reuse the component from page X", don't blindly copy it. Evaluate context. A full `.schedule-card` showing "Home Team 55% @ Away Team 45%" on a Team Detail page duplicates the team name on every row, wasting horizontal space. The correct approach is a *context-optimized variant* (e.g., `.schedule-row`) that reuses the same design tokens (bars, badges, typography) but strips redundant elements (the known team) to maximize information density. 
    **Audit recipe:** when reviewing a dense view, ask "What does the user *already know* from the page title/hero, and does this component repeat it unnecessarily?" If so, strip the redundancy rather than expanding the footprint.

20. **🚨 Don't ship HTML template patches without a live render check when HTML is constructed as a JavaScript string.** When a frontend view builds DOM by interpolating HTML strings (`return \`<div class="foo">...\``), a patch can accidentally double-escape angle brackets or quote characters. The lint passes, the unit test passes, and the browser silently displays raw tags as text (e.g., `&lt;div class="today-section"&gt;`). The bug is invisible in code review because the patch *looks* like HTML; only a live render exposes it.

    **Why this happens during patch:** find-and-replace tools often XML-escape `<` and `>` inside the matched `old_string`/`new_string` to stay safe in patch metadata. When the target file is a JavaScript template literal, those escaped characters get written into the source as `&lt;` and `&gt;`, producing literal text in the browser.

    **Catch it before the user does:**
    - After any patch to a function that returns HTML strings, run the app in a browser and screenshot the affected section. If you see raw tags, the string was escaped during patch.
    - If you must use `.innerHTML =`, verify the assigned string starts with `<` characters, not `&lt;`, before you even reload the browser.

    **Audit recipe:**
    ```bash
    grep -n "&lt;\|&gt;" ui/js/views/*.js
    # Any hit in a template literal is a likely regression.
    ```

21. **🚨 Swapping a skeleton wrapper for real content with `.innerHTML =` nests containers and breaks styling/anchors.** A common dashboard pattern is to render a shell like `<div class="today-section" data-section="top-picks">...</div>` and later replace it with the real markup returned by a render helper. If the helper itself returns a `<div class="today-section">`, using `wrapper.innerHTML = htmlString` leaves the outer `data-section` wrapper in the DOM and nests the real section inside it. This breaks CSS selectors, section anchors, and section-specific styling. It also makes future `querySelector('[data-section="top-picks"]')` lookups return the old wrapper instead of the live content.

    **Fix: replace the wrapper, not its contents.** Use a `DocumentFragment` and `replaceWith`:

    ```javascript
    const topPicksSection = els.content.querySelector('[data-section="top-picks"]');
    if (topPicksSection) {
      const frag = document.createRange().createContextualFragment(topPicksHtml);
      topPicksSection.replaceWith(frag);
    }
    ```

    This removes the skeleton wrapper entirely and inserts the real markup in its place. Always use this pattern when the render helper returns its own root element with the same semantic role as the wrapper.

    **When `.innerHTML =` is fine:** when the wrapper is a generic container (e.g., `<div id="content">`) and the assigned HTML is its children, not a replacement for the wrapper itself.

    **Reference:** `references/html-template-regression-recipe.md` — before/after code and a verification script.

21. **🚨 Inline CSS patch insertions can introduce brace-balance syntax errors that silently break the rest of the stylesheet.** When using find-and-replace to insert a new CSS block between two existing rules, a common failure mode is pasting after a rule declaration but before its closing `}`. The browser then ignores the new selector and every subsequent rule in the file. Symptom: your new styles don't apply, and unrelated styles below the error also vanish. Catch it by running a CSS parser or at least a brace-balance check after the patch:

    ```bash
    # Quick brace-balance sanity check
    python3 -c "
    import sys
    src = sys.stdin.read()
    balance = 0
    for ch in src:
      if ch == '{': balance += 1
      elif ch == '}': balance -= 1
      if balance < 0:
        print('ERROR: extra closing brace')
        sys.exit(1)
    print('OK' if balance == 0 else f'ERROR: {balance} unclosed braces')
    " < ui/css/dashboard.css
    ```

    Better: use a real CSS parser (e.g. `npx csstree-validator` or `postcss-safe-parser`). Verify that the selector you intended to add actually appears in the computed stylesheet and that its rules are not crossed out in DevTools.

22. **🚨 Browser module cache hides view-module fixes during live QA.** In a modular SPA where view files are loaded via `import()`, the browser caches the resolved module record. After editing a view file, a normal reload may still run the old module. If your CSS/JS fix "doesn't work" in the browser, check the cache before redesigning the fix:
    - Confirm via DevTools Network that the view file request includes the cache-buster query string (e.g. `today.js?cb=...`).
    - If not, add `?cb=${Date.now()}` to the router's dynamic import path.
    - As a one-shot verification, open the page in an incognito/private window or hard-reload with cache disabled (`Cmd+Shift+R` / `Ctrl+Shift+R`).
    - If the live DOM still shows an old attribute (e.g. an old `onclick` value), the module cache is the culprit.

23. **🚨 Truncated `read_file` output can be accidentally written back into a file as literal `...[truncated]` text.** When a `read_file` response shows a line ending in `...[truncated]`, a subsequent patch that uses that exact text may write the literal truncation marker into the source. The file parses successfully, but template literals containing `...[truncated]` produce broken HTML/JSON strings at runtime. Symptom: module loads, no syntax error, but rendered content is missing items or shows malformed markup. After any edit where truncation appeared, verify the exact bytes with `python3 -c "..."` or `sed -n`, not just another `read_file` call.

24. **High information density is not the same as "cram more in" — it's removing redundancy.** When a user asks for denser UI, the first move is to audit adjacent sections for duplicated information and strip the redundant container, then tighten padding and font sizes. Don't add new widgets to increase density; remove empty/duplicate space first.

    **Concrete recipe (web dashboards):**
    1. Remove placeholder/empty-state cards when a section has no data instead of showing a large explanation banner.
    2. Collapse multi-row filter strips into a single row with an overflow control ("More ▾").
    3. Merge comparison stats into stacked rows rather than inline text in narrow cards.
    4. Reduce section title font size and margin before shrinking content.
    5. Use visible card borders and subtle shadows so denser layouts remain scannable.

    **Anti-pattern:** leaving empty skeleton cards visible because "they might fill later." A blank card in a dense layout is more glaring than a missing section.

25. **🚨 Hover-only buttons are invisible on touch devices.** `opacity-0 group-hover:opacity-100` hides action buttons (delete, remove, edit) on mobile/tablet where there's no hover state. Users on touch devices cannot access these actions at all. Fix: use `md:opacity-0 md:group-hover:opacity-100` so buttons are always visible on mobile and only hide-on-hover on desktop. Also add `aria-label` to icon-only buttons for screen reader accessibility. Common locations: list item delete buttons, card action buttons, row-level edit/remove controls.

26. **🚨 `<a href>` instead of `<Link>` in Next.js causes full page reloads.** When a component already imports `Link` from `next/link` but uses `<a href="/some-route">` for a button, clicking it triggers a full page reload instead of client-side navigation. This is a performance and UX regression that's invisible in code review — the page loads fine, just slower. Audit recipe: grep for `<a href="/` in files that also import `Link`. Every hit should use `<Link href=...>` instead. Pay special attention to toolbar/action buttons in `HarborShell` `tools` prop — these are frequently written as `<a>` because they're passed as JSX props.

27. **🚨 Missing debounce on search inputs floods the API.** When `onChange` calls an async fetch function directly, every keystroke triggers a network request. For a 10-character search query, that's 10 requests in ~2 seconds. Fix: use a `useRef<ReturnType<typeof setTimeout>>` + 300ms debounce:
    ```typescript
    const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const handleSearch = useCallback((query: string) => {
      setSearchQuery(query);
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
      searchTimeoutRef.current = setTimeout(() => {
        fetchResults({ search: query });
      }, 300);
    }, [fetchResults]);
    ```
    Don't forget to add `useRef` to the React imports.

28. **🚨 `try/finally` without `catch` silently swallows errors.** When an async fetch uses `try { ... } finally { setIsLoading(false) }` but no `catch` block, errors are swallowed — the loading spinner stops but no error is shown to the user. The UI looks like it loaded successfully with zero results. Fix: add a `catch` block that sets an error state, and render the error message to the user:
    ```typescript
    const [error, setError] = useState<string | null>(null);
    // In fetch:
    setIsLoading(true); setError(null);
    try { ... } catch (err: any) { setError(err?.message || 'Failed to load'); }
    finally { setIsLoading(false); }
    // In render:
    {error && <div className="text-red-600 p-4">{error}</div>}
    ```

29. **🚨 List item ID vs slug mismatch breaks saved list links.** When "Add to List" stores entity UUIDs (`entityId={ship.id}`) but detail pages use slugs in URLs (`/app/ships/[slug]`), clicking a list item produces a 404 or "not found" error. The UUID is passed as the slug parameter but `getBySlug({ slug })` queries `where: { slug: input.slug }` which doesn't match. Fix: add a fallback in `getBySlug` — if the slug lookup returns null, try looking up by `id`, get the actual slug, then re-fetch:
    ```typescript
    let entity = await prisma.ships.findUnique({ where: { slug: input.slug }, include: {...} });
    if (!entity) {
      const byId = await prisma.ships.findUnique({ where: { id: input.slug }, select: { slug: true } });
      if (byId) entity = await prisma.ships.findUnique({ where: { slug: byId.slug }, include: {...} });
    }
    ```
    Audit recipe: grep for `entityType` and `entityId` in AddToListButton usage, then verify the route function in ListDetailContent uses the same identifier type as the detail page expects.

30. **🚨 Public nav links to auth-gated routes.** When routes are moved behind authentication (e.g., `/pricing`, `/cruise-lines`, `/sailings` added to middleware's `isPremiumRoute`), the public navigation component must be updated to point to public marketing pages instead. Otherwise, unauthenticated visitors clicking nav links get silently redirected to login — a confusing UX that looks like the site is broken. Audit recipe: for every `<Link href="/some-route">` in the public nav component, curl the route without auth and verify it doesn't redirect to `/login`. Common fix: point nav links to `/features/*` marketing pages instead of the actual app pages.

39. **🚨 Hardcoded literals inside live-data components drift from the source of truth.** When a component pulls most of its numbers from a live query (e.g. `trpc.health.check()` → `dashboard_stats`) but embeds a few hardcoded strings for decoration, those literals silently rot. Concrete case (2026-07-08 landing-page deep dive): the `CompassIllustration` SVG footer hardcodes `49 lines · 23 regions · 4 seasons` while the live `health.database.regions` is **24** — so the caption is wrong on every render. Same class: `|| 23` / `|| '1,700+'` fallbacks that no longer match reality, and marketing copy (`Basic $20` in docs) that diverged from the real `$15`. Audit recipe: when a screen mixes `health.*` / API values with string literals, grep the file for hardcoded numbers/region-counts/price strings and cross-check each against the live query result or the source-of-truth doc. Flag every literal that has drifted; prefer deriving it from the live data (or removing the literal) so it can't rot. Also watch for **copy drift between two surfaces that display the same data** — the landing pricing band said Basic = "full tools" while `/pricing` shows Basic as feature-limited; reconcile both to one source of truth.

40. **🚨 Custom `<div>` sliders are invisible to keyboard and screen-reader users unless ARIA is wired.** A range slider built from two `<div>` thumbs is not announced as a slider and cannot be operated with a keyboard. The fix is mechanical: each thumb gets `role="slider"`, `tabIndex={0}`, `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, and an `aria-label`; the group gets `role="group"` with an `aria-label`; and keyboard handlers support ArrowRight/ArrowUp, ArrowLeft/ArrowDown, Home, End, PageUp, and PageDown. Also add a visible `:focus-visible` ring. See `wcag-accessibility/references/custom-slider-accessibility.md` for the full working pattern. This is a common gap in design systems that move from native `<input type="range">` to custom-styled dual-thumb controls.

41. **🚨 An empty `grep '^\+'` on a diff does NOT mean "no matches" — the anchor may not match the diff's actual prefix format.** When auditing a commit for hardcoded values (hex colors, secrets, debug statements) by grepping the *added* lines of a diff, the standard anchor is `grep '^\+'`. But if the diff output is piped through a wrapper/formatter that re-indents prefixes (e.g. `rtk` rewrites `+` to `  +` and compacts/truncates the output), `grep '^\+'` returns nothing and `grep -c '^+'` returns 0 — even on hundreds of added lines. You then report a false "clean / no violations."

    **The discipline:** before trusting an empty grep on a diff, confirm the anchor matches the actual format. Either use a lenient anchor (`grep -cE '^\s*\+'`) or, better, read the changed file directly with `read_file` and grep the real source. Concrete case (2026-07-21, the D&D VTT project pricing review): `git show da12743 -- apps/web/src/styles.css | grep -c '^+'` returned 0 on a 432-line CSS addition, and the hex-literal grep appeared to find "NONE" — only because the wrapper had reformatted `+` to `  +`. Reading the file directly confirmed the CSS was genuinely token-clean, but the empty grep alone would have been a false negative. Never sign off on "no hardcoded values" from an empty diff grep you haven't sanity-checked.

 42. **🚨 Dark-mode redesigns leak on portaled overlays — Radix renders dialogs/dropdowns into `document.body`, outside any scoped `.dark` wrapper.** When an app themes dark by putting a `dark` class on a wrapper `<div>` (instead of `<html>`), every Radix-portaled component — `Dialog`, `AlertDialog`, `Select`, `Sheet`, `Drawer`, `Popover`, `Tooltip`, `Command` — renders into `document.body` and falls back to the light `:root` tokens. Result: white dialogs and dropdowns on an otherwise dark console. **Static screenshots and page-level reviews never catch this, because nothing opens an overlay.** Concrete case (2026-08-01, the wine-club app dark admin): 20 static screenshots + a full design review verified a dark redesign as clean; every dialog/select/alert was actually a white box. Only found by explicitly opening each overlay type.

 **Audit recipe (mandatory on any theming / dark-mode / token change):**
 ```bash
 # 1. Where do the dark tokens live?
 grep -n "\.dark\s*{\|:root\s*{" web/src/index.css
 # 2. Which components portal to body?
 grep -rln "Portal" web/src/components/ui/
 # 3. If dark tokens are scoped to a class on a div (not :root / <html>),
 #    every portaled overlay is rendering LIGHT. That's a 🔴 bug.
 ```
 **Live verification:** open a dialog, a `Select` dropdown, and an `AlertDialog`; screenshot each; confirm they render dark, not white.

 **Fix:** put the dark token block on `:root` (single-theme app) or add `class="dark"` to `<html>`/`<body>` — never only on a scoped div. For one app serving both a light public site and a dark console, set the class on `<html>` per route, or define dark tokens on `:root` and let the console's own surface classes carry the look. Full recipe + before/after: `references/radix-portal-dark-mode-leak.md`.

43. **🚨 Operational / throughput-critical UIs: extract the domain workflow model BEFORE flagging "friction."** When reviewing a live-operations tool (dismissal queues, dispatch boards, checkout lines, event intake), the operator workflow is a set of *designed constraints*, not bugs. In a 600-rider school-dismissal review (2026-08-06), the first review pass flagged four things as friction — every one was by design:
    - "Pagination is a problem" → NO: teachers move the queue in 24-car page batches (12 per color). Pagination IS the mechanism that advances the display.
    - "Removal is a bottleneck (confirm dialog per car)" → NO: cars are never removed. The queue is append-only; pagination moves the view forward. Remove buttons exist only for admin error-correction.
    - "5s display poll lags the 4s car cycle" → NO: cars already in queue don't need fast refresh; new cars go to the back and pagination shows them at their turn.
    - "Rejected entries need an admin error surface" → NO: entry is fire-and-forget by design; invalid numbers are silently ignored, admin cleans up later.

    **Before writing ANY finding:** ask the user (or read the domain docs) — what is the operator model, who does what, what's the throughput target, which behaviors are deliberate? Then *measure, don't assume*: compute the per-item budget (600 riders / 40 min = 1 every 4s), time the critical path with a real scripted load (append latency 195ms → 20× headroom), and seed live data to confirm queue behavior at scale. **State the model back to the user first** ("I understand: X is by design, Y is the flow, Z is where admin fixes errors") — they will correct you mid-report otherwise, and every finding built on the wrong model wastes a round-trip.

    **The real risk class in fire-and-forget entry is silent data loss**, and the audit should focus there: (a) payload contract mismatch — mobile screen sent camelCase `primaryNumber` to a snake_case endpoint → 422 swallowed by `.catch(() => {})` → operator sees success, zero entries land (verify by calling the endpoint with the exact payload the frontend builds, not the correct one); (b) `{status: 'ignored'}` response never read — frontend only checks `response.ok`, so a rejected number flashes green + beeps and shows in "recent entries" but never enters the queue; (c) flag fields that never render — dashboard read `item.isDuplicate`, API returned `is_duplicate`, so the duplicate warning + count were invisible (normalize in the fetch layer, then verify visually with seeded duplicates); (d) inconsistent roster gates between entry paths — one endpoint validates students, the other accepts any number → phantom "Unknown" rows on the public display (make both paths silently ignore non-roster numbers).

    See `references/operational-throughput-review.md` for the full recipe (timed simulation script shape, silent-loss audit checklist, live verification steps, and the exact user corrections to internalize).

 44. **🚨 A wrapper-mangled grep can report "0 matches" for markers that ARE present — verify with `read_file`, not a second grep.** When terminal output is reformatted/truncated by a wrapper, grep results can come back as `37:0:number;` (line:0:content) or even **"0 matches" for a string that is demonstrably in the file**. Real case (2026-08-08, the design-tool web app Motion Craft Doctrine verification): `grep -n "cubic-bezier(0.23, 1, 0.32, 1)" lib/llm.ts` returned "0 matches" and `grep -n "clampScore(obj.scores?.motion)"` also returned "0 matches", yet `tsc --noEmit` was clean and `read_file` showed both lines verbatim in place. The wrapper had mangled the output; the code was correct. **Rule: when grep output disagrees with a clean type-check or with a subagent's claimed insertions, re-read the file with `read_file` before flagging work as missing or re-dispatching.** A false "missing marker" burns a re-dispatch and erodes trust in a correct implementation; the file is usually fine. This is the reverse of Pitfall 41 (empty grep falsely implying "no violations") — the same lesson in the opposite direction: verify actual file bytes, never trust the grep rendering.

45. **🚨 New optional field with a fallback — EVERY read site needs the fallback, not just the one the implementer noticed.** When a feature adds an optional field to a persisted object that existing rows lack (e.g. a new review score dimension stored in a JSON column), every consumer of that field must normalize with `?? fallback` (or `Number(x ?? 0)`). The failure mode is **partial normalization**: one read path gets the fallback, a sibling path reads the field raw and renders `undefined` (often styled as a red/error value) until the row is rewritten. Real failure (2026-08-08, the design-tool web app motion score): the API history strip was normalized (`Number(s.motion ?? 0)` in the route) but the main score grid read `frame.review!.scores[key]` raw — old reviews showed "Motion undefined/10" in danger-red until re-reviewed. **Audit recipe (same shape as Pitfall 17 but for READS, not writes):** grep the sibling fields (e.g. `scores.polish` / `.polish`) across every render + API read site, and add the fallback to each — do not trust that the implementer found them all, and do not rely on `tsc` alone (an `?? 0` on one path typechecks fine while another path is still raw).

    **Related (prompt-doctrine systems):** when the "new field" is a scoring dimension added to an LLM reviewer, reconcile the reviewer's escalation triggers with the doctrine's own allowances in the SAME change — a reviewer told to "flag durations over 300ms" while the doctrine permits modals 200–500ms contradicts itself and produces incoherent scores. And verify the reviewer actually enforces the new dimension on live output (generate a frame with a deliberate violation; confirm the score + flag appear), not just that the schema hint includes the key.

46. **🚨 A "pick exactly N" multi-select built as a SET cannot express every legal combination — and deadlocks the modal.** When a picker lets the user choose N items to satisfy a quota (discard N cards, assign N tokens), a toggle implemented as `idx !== -1 ? prev.filter(...)` **deselects** on re-click. That makes the selection a set of distinct *kinds*, so any combination needing two of the same kind is unexpressable: a hand of `{wood:2, ore:6}` told to "discard 4" can select at most 2 items, so `picked.length === count` is unreachable and Submit stays disabled FOREVER. If the modal has no close/cancel affordance, the user is hard-stuck. **Audit recipe:** for every picker gated on a count, enumerate the legal multisets the backend can demand and confirm the UI can express each one; verify the disable-condition is reachable from the worst-case inventory. Fix as a pure function (e.g. `togglePick(picked, kind, available, count)`) with explicit rules — click adds; clicking a picked entry hands it back only when the owed count is already reached; identity otherwise — and unit-test the multiset case in a node-env test (no DOM needed). Report as 🔴: a permanent deadlock is a bug, not polish.

47. **🚨 A transient refusal/error note that only clears on the next *success* of the same kind persists as a false failure.** When a client projection/reducer spreads previous state (`...prev`) into the update case without clearing `error`, a one-shot refusal (not-host, wrong-phase) stays on screen indefinitely — the user reads a permanent failure from a single declined click. **But** clearing unconditionally is equally wrong: real connection/auth errors must survive state updates and clear only on an explicit reconnect/ack. Fix by clearing **only** errors whose code is in an explicit transient set (e.g. `notHost`, `badPhase`) on every projection, and leaving all others to clear on welcome/connect. **Audit recipe:** in the state reducer, find the update/projection case and confirm it clears transient codes by name; then pin BOTH directions with tests — transient clears on the next projection, non-transient (e.g. `badToken`) still forces the error status.

## Feature Audit Spreadsheet Pattern

When doing a full-app QA pass, create a canonical tracking CSV with these columns:

```
ID,Section,Feature,Route,User Story,Expected Behavior,Status,Errors Found,Notes
```

- **Status**: `not_tested`, `pass`, `fail`, `fixed`
- Write user stories in standard format: "As a [user type], I can [action] so that [benefit]"
- Group by section (AUTH, MARKETING, DASHBOARD, SHIPS, PORTS, etc.)
- Update status as you test each feature
- Use `subagent dispatch` with a subagent to create the initial spreadsheet — it can read all page files and generate user stories in parallel
- Test public pages first (curl for HTTP status codes, browser for visual), then authenticated pages (need credentials)
- Code-level review with `subagent dispatch` can find bugs in authenticated pages without credentials

31. **🚨 `[object Object]` stringified in database text columns.** Scrapers or pipeline scripts can accidentally assign JavaScript objects to string fields, which get stored as the literal string `"[object Object]"` in PostgreSQL. This renders as `[object Object]` in the UI — confusing and unprofessional. During a feature audit, check for this pattern:
    ```sql
    SELECT COUNT(*) FROM ships WHERE "homePort" = '[object Object]';
    -- Check all text columns that display in the UI
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'ships' AND data_type = 'text' OR data_type = 'character varying';
    ```
    Fix: set affected rows to NULL (the UI should show '—' for null values). Then trace the scraper/pipeline code that writes the field and add `String(value)` or a null check. Common locations: `homePort`, `flag`, `registry`, any field populated from a nested JSON response where the scraper assigns an object instead of a primitive.

32. **🚨 JWT session caches user role — DB changes require re-login.** When testing admin pages, changing a user's `role` in the database (e.g., `UPDATE users SET role = 'super_admin'`) does NOT take effect in the current browser session. The role is baked into the JWT session token at login time. The user will still see `unauthorized` redirects until they sign out and sign back in. Testing technique: sign out via `/api/auth/signout`, then log in again to get a fresh JWT with the updated role. This applies to any JWT-based auth system (NextAuth, custom JWT, etc.), not just NextAuth.

33. **🚨 `Promise.all` with placeholder slots causes silent variable misalignment.** When a `Promise.all` array has placeholder `Promise.resolve(0)` entries to "skip" a position, the destructured variables shift silently. Example:
    ```typescript
    // BUG: placeholder at index 1 and 3 shift all subsequent variables
    const [regions, , shipCount, , dataPoints, itineraries, ratings] = await Promise.all([
      fetchRegions(),        // index 0 → regions
      Promise.resolve(0),    // index 1 → DISCARDED
      fetchShipCount(),      // index 2 → shipCount
      prisma.categories.count(), // index 3 → DISCARDED (wasted DB call!)
      fetchDataPoints(),     // index 4 → dataPoints
      fetchItineraries(),    // index 5 → itineraries
      fetchRatings(),        // index 6 → ratings
    ]);
    ```
    Audit recipe: grep for `Promise.resolve(0)` in `Promise.all` arrays. Every hit is either a placeholder (remove it) or a wasted computation (the result is discarded but the DB query still runs). Also check that variable names match what the function actually returns — `expertRatingsCount` that actually counts `ship_cruise_critic_ratings` is a misnomer that misleads future readers.

34. **🚨 Raw SQL queries against dropped tables silently produce empty data.** When code uses `$queryRaw` against a table that was later dropped (e.g., `itinerary_ports` from an early scraping approach), the query throws, but if it's wrapped in `try { ... } catch { }` with an empty catch block, the error is silently swallowed. The page renders with empty data for that section — no error, no log, no indication anything is wrong. The feature "works" but shows nothing. Audit recipe:
    ```sql
    -- Check if tables referenced in raw SQL actually exist
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name IN ('itinerary_ports', 'mv_region_active_months');
    ```
    Then grep for every `$queryRaw` or `$executeRaw` call and verify the table exists:
    ```bash
    grep -rn '\$queryRaw\|\$executeRaw' app/ | grep -i 'FROM\|INSERT INTO\|UPDATE\|DELETE FROM'
    ```
    Each hit should reference a table that exists in PG. If the table was dropped as dead code, replace the query with one against the live table (e.g., `port_visit_itineraries` instead of `itinerary_ports`), or remove the query entirely if the data is no longer needed. The try/catch pattern is dangerous here because it masks the problem — consider logging in the catch block even if you don't show the error to the user.

35. **🚨 Creating test accounts for QA via direct DB password hash.** When testing authenticated pages during a feature audit, you often need a test account with specific roles (admin, super_admin, subscribed). Instead of going through the signup flow, set the password directly in the DB:
    ```bash
    # Generate bcrypt hash
    node -e "const bcrypt = require('bcryptjs'); console.log(bcrypt.hashSync('TestPass123!', 12));"
    
    # Set password and role on existing test user
    PGPASSWORD="$STAGING_PG_PASSWORD" psql -h $HOST -p $PORT -U postgres -d railway -c \
      "UPDATE users SET \"passwordHash\" = '\$2b\$12\$...', \"emailVerified\" = NOW(), role = 'super_admin', \"subscriptionStatus\" = 'subscribed' WHERE email = 'test@example.com';"
    ```
    Then log in via the browser with the test email and password. Remember: the JWT session caches the role at login time — if you change the role in the DB, the user must sign out and sign back in to get a fresh JWT with the updated role.

36. **🚨 Python CSV writer fails on malformed rows with None keys.** When updating a CSV file that was originally written by a subagent (which may produce rows with extra fields or None keys), `csv.DictWriter.writerows()` throws `ValueError: dict contains fields not in fieldnames`. Use `csv.reader`/`csv.writer` instead of `csv.DictReader`/`csv.DictWriter` for malformed CSVs:
    ```python
    import csv
    # Read with csv.reader (handles arbitrary column counts)
    with open('audit.csv', 'r', newline='') as f:
        lines = list(csv.reader(f))
    # Update specific rows by index
    lines[57][6] = 'pass'  # column 6 = Status
    # Write back with csv.writer
    with open('audit.csv', 'w', newline='') as f:
        csv.writer(f, quoting=csv.QUOTE_MINIMAL).writerows(lines)
    ```

## References

- `references/review-checklist.md` — ordered checklist for running a UI implementation review
- `references/audit-to-plan-handoff.md` — converting a 30-finding audit report into a phased, shippable plan: build findings inventory → cluster by concern into 🔴 → 🟡 → ⚪ phases → write ACs that close multiple findings → map every audit finding to exactly one phase (or to Out of Scope with rationale).
- `references/react-native-review-checks.md` — React Native–specific checks for full-app reviews (stale closures, FlatList indices, session leaks, N+1 patterns)
- `references/dashboard-polish-primitives.md` — reusable UX primitives (numeric contrast, anchor+toast, keyboard chords, series detection, ETA hints, filter-active indicators, **stacked compare rows for narrow stat cards**) emerged from 2026-06-10 polish sprint
- `references/html-template-regression-recipe.md` — escaped HTML and nested skeleton-wrapper regressions in JavaScript template-literal UIs; before/after code and verification script (2026-07-14)
- `references/invisible-ui-element-diagnostic.md` — the diagnostic hierarchy for "user says it's not there": check component path FIRST (Harbor vs legacy dual-path), then CSS bundle purging (Tailwind arbitrary-value classes), then DOM existence, then visibility, then positioning (2026-06-27)
- `references/route-auth-matrix-audit.md` — step 7b recipe: how to compute auth coverage over every mutating route in a multi-route service, with the live curl verification template that the 🔴 reports cite (2026-07-18)
- `references/design-token-compliance-audit.md` — audit a frontend commit against a token-based design system (DESIGN.md + tokens.css): read the docs first, negative-grep for hardcoded hex/rgb/hsl, positive-grep for correct per-surface token usage, audit structural rules (typography/buttons/cards/surface modes/motion), report PASS/FAIL per rule (2026-07-21)
- `references/operational-throughput-review.md` — recipe for reviewing live-operations tools (dismissal queues, dispatch boards, checkout lines): extract the operator model FIRST, time the critical path with a scripted load, audit the silent-loss paths in fire-and-forget entry, verify with seeded live data + browser (2026-08-06)
- `references/surface-checklist-library.md` — step 7h companion: distilled per-surface checklists from checklist.design (paywall, onboarding, empty-state, pricing, login + all other surface names) with the "why it matters" tips; the site's 110 checklists are the floor, not the ceiling
- For **live-UI reviews of a running web app** (not just code audit), use the `dogfood` skill as the entry point. In particular, `dogfood/references/authenticated-qa.md` has the cookie-jar + bearer-token recipe for getting past login walls without depending on a static-server fallback.
- **Mid-session 403/401 during live QA** ("works after login, every mutation fails once the WebSocket connects / a token-refresh fires"): this is a client CSRF-token rotation desync, not a server bug. See the `client-csrf-token-store` skill — it has the fetch-instrumentation probe (log sent-vs-minted token) and the core-wrapper fix.
