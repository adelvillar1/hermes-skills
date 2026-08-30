---
name: debug-issue
description: "Use when debugging bugs, regressions, or unexpected behavior in a codebase. Systematically traces issues using the knowledge graph for code navigation."
version: 2.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [debugging, knowledge-graph, code-review, tracing, bug-fix]
    related_skills: [refactor-safely, review-changes]
---

# Debug Issue

Systematically debug issues and regressions using knowledge graph-powered code navigation.

## When to Use

- A bug or regression has been reported and the root cause is unclear
- You need to trace how a piece of code is called or used across the codebase
- Recent changes may have introduced a new issue
- You're investigating unexpected behavior in a specific area

## Tools You'll Need

These steps use the `code-review-graph` MCP tools (see AGENTS.md for project context).

## Workflow

### 0. Check sibling projects for existing solutions FIRST

Before building any new infrastructure, script, rendering pipeline, or integration, search sibling/previous projects in the user's workspace for proven solutions. This is the single highest-leverage debugging step and must come before all others.

```bash
find ~ -maxdepth 5 -name "CLAUDE.md" 2>/dev/null | head -10
# Check each project for relevant scripts, patterns, and approaches
grep -r "<relevant-pattern>" ~/Desktop/<sibling-project>/scripts/ 2>/dev/null
grep -r "<relevant-package>" ~/Desktop/<sibling-project>/package.json 2>/dev/null
```

Common examples:
- **PDF-to-image rendering** → check for `scripts/pdf-to-images.*`, `@napi-rs/canvas`, `pdftoppm` references
- **Vision extraction** → check for `callVisionExtraction`, `kimi` vision, `extractRatingsFromPdf` patterns
- **Batch validation** → check for `partial-submission`, `getValidationErrors`, `batch-operation-ux` patterns

**Why this matters:** The user explicitly expects existing solutions to be reused. Inventing a new approach when a proven one exists in a sibling project wastes time and introduces avoidable errors.

### 1. Find relevant code

Use `semantic_search_nodes` to find code related to the issue. Look for function names, modules, or error messages mentioned in the bug report.

### 2. Trace call chains

Use `query_graph` with patterns like `callers_of` and `callees_of` to trace how the suspected code is connected.

- **callers_of**: Who calls this function? (upstream impact)
- **callees_of**: What does this function call? (dependencies)

### 3. Inspect execution paths

Use `get_affected_flows` to see the full execution paths through suspected areas. This reveals the entry point that triggers the bug.

### 4. Check recent changes

Use `detect_changes` to see if recent modifications caused the issue. Pay attention to risk-scored changes.

### 5. Measure blast radius

Use `get_impact_radius` on suspected files to see what else is affected. This helps avoid fixes that break something else.

## Tips

- Check both callers and callees to understand the full context.
- Look at affected flows to find the entry point that triggers the bug.
- Recent changes are the most common source of new issues.

## Token Efficiency Rules

- ALWAYS start with `get_minimal_context(task="<your task>")` before any other graph tool.
- Use `detail_level="minimal"` on all calls. Only escalate to "standard" when minimal is insufficient.
- Target: complete any review/debug/refactor task in ≤5 tool calls and ≤800 total output tokens.

## Common Pitfalls

1. **Ignoring the terminal tool's error message.** When the terminal tool says *"This foreground command appears to start a long-lived server/watch process. Run it with background=true"*, it is telling you exactly what to do — pass `background=true` in the tool call. Do NOT retry the same command 30+ times hoping it magically works. The `-d` flag on `docker compose up -d` does NOT satisfy this check; the tool detects the intent of the command, not just its process lifetime. The fix is always to use `background=true` for any command that starts a long-running process (Docker containers, dev servers, file watchers, etc.). After starting it in the background, verify readiness with a health check (`curl`, `docker ps`, etc.) in a separate foreground command.

2. **`</script>` in JS template literals inside inline `<script>` tags.** When an HTML file has `<script>...</script>` and the JS code inside contains template literals (backtick strings) that include `</script>`, the browser's HTML parser treats it as closing the outer script tag — even though it's inside a JS string. The entire JS file breaks silently (all functions are undefined). See `references/script-inside-template-literal-bug.md` for diagnosis and fixes.

3. **Skipping the sibling-project check.** Before building anything new — especially rendering pipelines, extraction approaches, or validation patterns — search sibling projects for existing proven solutions. The user will ask "why aren't we reusing that?" if you don't. This applies to EVERY new approach, not just the first time.
2. **Searching too broadly.** Start with the specific function or error message rather than broad keyword searches.
3. **Ignoring callers.** A bug in a leaf function may be caused by bad input from a caller three levels up.
4. **Skipping recent changes.** If the issue is new, the fix is almost always in the last few commits.
5. **Fixing symptoms instead of root causes.** Always trace to the entry point before proposing a fix.
6. **All-or-nothing batch validation.** When a user reports "I filled in the fields but it still says missing fields," the hidden cause is often that the client-side validation aborts the ENTIRE batch when a single entry fails. One incomplete row blocks every other row from submitting — even though those other rows are fine. Before digging into code, ask: "does this UI process batch items individually or as a group?" The fix is partial-success submission (process valid, keep invalid with field-level highlighting).

## Edge Case: Cross-Source ID Format Mismatch

When a feature silently degrades because two data sources use different ID formats for the same entity (e.g., schedule uses `"669432"`, ratings use `"mlb-669432"`, probability function uses `"trevor-rogers"`). The lookup returns nothing, system falls back to default with no error. See `references/cross-source-id-mismatch.md` for detection, common patterns, and a real MLB pitcher example.

## Edge Case: Prisma Empty `_count.select`

When a Prisma query includes `_count: { select: {} }` (empty select), Prisma throws a validation error at runtime:
```
The `select` statement for type ShipsCountOutputType must not be empty.
```
This surfaces as a 400 error to the client. The fix is to populate the select with actual relation fields:
```typescript
_count: {
  select: {
    diningVenues: true,
    barsLounges: true,
    cabins: true,
  },
},
```

Check all `_count.select` blocks in the affected router file — the empty one is usually an oversight when copy-pasting a query template.

## Edge Case: Prisma Raw SQL Type Cast Mismatch (`text = uuid`)

When using `prisma.$queryRaw` with `ANY()` array comparisons, the DB column type must match the cast:

```typescript
// ❌ WRONG — shipId column is TEXT but ::uuid[] casts the array to UUID
WHERE si."shipId" = ANY(${shipIds}::uuid[])

// ✅ CORRECT — both sides are TEXT, no cast needed
WHERE si."shipId" = ANY(${shipIds})
```

**Root cause:** Prisma `String` fields map to `text` in PostgreSQL, not `uuid`. The `::uuid[]` cast converts the JS array to UUID-typed array, but PG won't auto-cast the column from text to uuid. Result: `operator does not exist: text = uuid` (PG error code 42883).

**Debugging flow:**
1. tRPC resolver returns 500 (INTERNAL_SERVER_ERROR) — no stack in browser console
2. Direct curl to the tRPC endpoint reveals: `ERROR: operator does not exist: text = uuid`
3. Search the resolver for `::uuid[]`, `::text[]`, or similar explicit casts in raw SQL
4. Check Prisma schema to confirm column type (`String` → text, not `@db.Uuid` → uuid)
5. Remove the cast: `ANY(${arrayVar})` instead of `ANY(${arrayVar}::uuid[])`

**Cross-environment symptom:** Always fails everywhere (unlike `_count.select: {}` which is masked by Redis on production). It's a schema-level type mismatch, not a data difference.

**Prevention:** When writing `prisma.$queryRaw` with `ANY()` array params, verify the column's PG type via `information_schema.columns` before adding a cast. Prisma `String` is TEXT unless explicitly annotated with `@db.Uuid`.

## Edge Case: Next.js Image Optimization + API Routes

When `next/image` `<Image>` components use `src` pointing to same-origin API routes (e.g., `/api/ship-image/{id}`), the Next.js image optimizer (`/_next/image`) fails with 400. See `references/nextjs-image-optimization-api-route-pitfall.md`.

The browser console shows:
```
image?url=%2Fapi%2Fship-image%2F{uuid}&w=2048&q=75  Failed to load resource: 400
```

Fix: add `unoptimized` prop to the `<Image>` component when src is a same-origin API route.

## Edge Case: tRPC Resolver ↔ UI Component Data Contract Mismatch

When a UI surface shows "nothing" or an empty state after data loads successfully (no errors in console, the query returns data, but the component renders blank), check whether the resolver output shape matches what the component expects.

**Symptom:** A persona insight panel, detail card, or results list renders an empty container after the data fetches. No errors in the network tab. The tRPC response has the right status code.

**Root cause:** The component checks for specific property names (e.g., `insights.description`, `insights.strengths`) that the resolver doesn't produce. The resolvers return structured nested objects (e.g., `{ shipCorridor: { narration: "..." } }`) but the panel expects flat arrays.

**Debugging flow:**

1. **Check the component's expected interface** — read the first 20-30 lines of the component to see what props/fields it accesses
2. **Check the resolver's output type** — read the resolver's interface to see what fields it actually returns
3. **Compare the shapes** — the component likely expects `description: string` but the resolver returns `corridorBestFit: { narration: string }`

**Fix options (choose one):**
- **Rewrite the component** to render the resolver's actual output format (recursively extract `.narration` fields, render typed sub-sections). This is better when the resolver has rich structured data.
- **Add a mapper** in the tRPC router that transforms resolver output to the component's expected shape. This is better when you can't change the component.

**Prevention:** When wiring a new resolver to an existing UI component, always read the component's expected prop types first. Don't assume the resolver output format matches what the component renders.

**Example from this project:** `PersonaInsightPanel` expected `insights.description`, `insights.strengths[]`, `insights.weaknesses[]`, `insights.bestForPersona[]` — but the ship/cruise-line/itinerary/region resolvers all return nested objects with `.narration` fields. All four surfaces showed empty panels after loading. Fix: rewrote the panel to recursively extract `.narration` text and typed stats chips from the actual resolver format.

## Edge Case: Data Property Path Bug (Nested API Response)

When debugging why a client-side tRPC query is sending `undefined` for a required parameter:

**Symptom:** A page loads, user interacts (e.g., clicks a persona badge), a tRPC query fires with one or more params that result in a 400 error or silently fail. No errors visible in the UI, but the expected data never shows.

**Root cause:** The page passes the full API response as `data` to the component, but the API response nests the ID under a sub-object:

```
getBySlug returns: { cruiseLine: { id: "...", name: "..." }, regions: [...], fleetStats: {...} }
Component uses:     data.id                              ← undefined!
Should use:         data.cruiseLine.id                    ← correct
```

**Debugging flow:**

1. **Read the server-side resolver** — what shape does `getBySlug` (or whatever fetcher) return? Look at the `const result = { ... }` block or the `return` statement.

2. **Read the component's tRPC call** — what does it pass as input? Check the `useQuery` call for the parameter being sent.

3. **Check if the path is wrong** — `data.propertyId` vs `data.nested.propertyId`. Use `console.log(data)` or look at how the page.tsx passes props.

4. **Check all surfaces** — the same pattern may be broken on similar pages (cruise line, ship, itinerary, region all use similar data structures).

**Prevention:** When wiring a new component to an API response, always read the resolver output type/interface first. Don't assume top-level fields exist — the API may nest the entity under a wrapper key.

**Example from this project:** `HarborCruiseLineDetailTabs` used `data.id` as the `cruiseLineId` for the persona insights query, but `getBySlug` returns `{ cruiseLine: { id, name, ... }, regions, ... }`. Fixed by changing to `data.cruiseLine.id`.

## Edge Case: Client-Side API Fallback for Missing Precomputed Content

When a component receives precomputed data from a server-side query (e.g., SVG mini-map, AI cache, image binary) and the value is null, the component should attempt to generate/cache it on-demand via an API endpoint rather than just showing a fallback.

**Symptom:** The page loads, cards show fallback content (ship photo instead of route map, placeholder icon instead of hero image) even though an API endpoint exists that can generate the missing content.

**Root cause:** The component only renders whatever the server query returned. If the precomputed value isn't in the DB (yet), the server returns null, and the component shows the fallback without trying the API.

**Fix (3-layer pattern):**

```tsx
function MyCard({ precomputedSvg, itineraryId, shipId, heroImage }) {
  const [generated, setGenerated] = useState(null);
  const [loading, setLoading] = useState(false);

  // Layer 1: Use precomputed data if available
  const resolvedSvg = precomputedSvg || generated;

  // Layer 2: Fetch and generate on-demand via API
  useEffect(() => {
    if (resolvedSvg || loading || !itineraryId) return;
    setLoading(true);
    fetch(`/api/generate-svg?id=${itineraryId}`)
      .then(r => r.text())
      .then(setGenerated)
      .catch(() => setShowFallback(true))
      .finally(() => setLoading(false));
  }, [itineraryId, resolvedSvg, loading]);

  // Layer 3: UI with toggle between generated map and fallback
  return (
    <div>
      {resolvedSvg ? renderInlineSvg(resolvedSvg) : (
        <Image
          src={getProxiedImageUrl(heroImage, shipId) || '/placeholder.png'}
          onError={handleFallbackChain}  // cascade on image error
        />
      )}
    </div>
  );
}
```

**Key patterns to apply consistently:**
- Any `<Image>` or `<img>` loading from an API route should have an `onError` handler
- The fallback chain for images should be: API route → external URL → built-in placeholder
- Any content that could be precomputed (SVG maps, cached AI responses, etc.) should fall back to an API endpoint that generates on-demand
- Store the generated result locally (React state) so it persists during the session

## Edge Case: AI Extraction / PDF Import Issues

When the bug involves **AI extraction from PDF documents** (booking confirmations, invoices, etc.) — poor field extraction, bad supplier matching, or "missing fields" errors during import — the knowledge graph tools alone won't help. The PDF text is opaque to source code analysis.

Use the dedicated workflow in `references/debugging-ai-extraction.md`:

1. **Phase 1** — Extract raw PDF text with pdfplumber to see what the AI actually receives (vs what a human sees rendered)
2. **Phase 2** — Trace the extraction pipeline: upload route → text extractor → AI prompt → response parser → supplier matcher → duplicate check
3. **Phase 3** — Trace the client-side and server-side validation that fires on "Create"

Four root causes dominate this class of bug: (a) the supplier isn't in the DB, (b) the PDF is noise-heavy (Viator/aggregator layouts), (c) the file isn't a booking confirmation at all (hotel list, itinerary reference), or (d) the batch validation is all-or-nothing — one missing field blocks every selected entry.

### Fix pattern for (d): all-or-nothing batch validation

When the client-side validation fires for multiple selected entries and rejects the entire batch because one has a missing field, the fix is:

1. **Separate valid from invalid per-entry.** Compute a `getValidationErrors()` function that returns per-field error map or null.
2. **Process valid entries.** Send only the entries that pass to the API.
3. **Keep invalid entries in the review table** with `validationErrors` set, so the user can fix and retry without re-entering everything.
4. **Add field-level red highlighting** (`ring-2 ring-destructive`) on invalid inputs, clearing on edit.
5. **Toast distinct messages** for created count, rejected count, and skipped-with-errors count.

See the reference file for the exact validation pattern and state management approach.

## Edge Case: Prisma Field Does Not Exist on Model (Wrong Model Query)

When a Prisma `findMany()` or `findFirst()` throws `Unknown field 'X' for select statement on model 'Y'`:

**Symptom:** Script crashes with `PrismaClientValidationError: Invalid prisma.<model>.findMany() invocation: Unknown field 'fieldName'`. The field exists in the schema — but on a **different model** than the one being queried.

**Root cause:** The script selects fields that belong to a different table. Common cases in this project:
- `familyFriendly`, `adultOnly`, `soloFriendly` → on `ships` model, NOT `cruise_lines`
- `inclusionScore` → on `route_corridors` model, NOT `cruise_lines`
- `overallRating` → on `ship_cruise_critic_ratings` model, NOT `cruise_lines`
- `serviceQuality` → renamed to `avgServiceRating` on `cruise_lines`

**Debugging flow:**
1. Read the exact Prisma error — it tells you which field AND which model
2. Search the schema for the field: `grep -n 'fieldName' prisma/schema.prisma`
3. Check which `model <name> {` block the field lives in — it's likely on a different model
4. Either remove the field from the select, or add a relation include + nested select if the data is needed

**Prevention:** When writing a Prisma select for a model, verify every field exists on THAT model specifically. Don't copy-paste fields from queries against other models.

## Edge Case: Line-by-Line DB Writes Inside Loops (Should Be Batched)

When a script does individual `prisma.<model>.update()` or `.create()` calls inside a `for`/`forEach`/`while` loop, each iteration is a separate DB round-trip. For scripts processing hundreds or thousands of rows, this adds minutes of unnecessary latency.

**Detection:**
```bash
# Find all write calls and check if they're inside loops
for script in scripts/*.ts; do
  grep -n '\.update(\|\.create(' "$script" | while read line; do
    lineno=$(echo "$line" | cut -d: -f1)
    sed -n "$((lineno-8)),$((lineno-1))p" "$script" | grep -q 'for\b\|forEach\|\.map\|while\b' && \
      echo "⚠️  $(basename $script):$lineno — inside loop"
  done
done
```

**Fix pattern — collect then batch:**
```typescript
// ❌ Line-by-line: N round-trips for N corridors
for (const corridor of corridors) {
  await prisma.route_corridors.update({
    where: { id: corridor.id },
    data: { score: computeScore(corridor) },
  });
}

// ✅ Collect updates, then Promise.all
const updates = corridors.map(corridor =>
  prisma.route_corridors.update({
    where: { id: corridor.id },
    data: { score: computeScore(corridor) },
  })
);
await Promise.all(updates);

// ✅ Even better: single SQL UPDATE when possible
await prisma.$executeRaw`UPDATE route_corridors SET score = ... WHERE ...`;
```

**Known offenders in this project (2026-05-07):**
- `compute-corridor-families.ts` — nested loop, ~2,360 families × N members
- `reclassify-corridor-regions.ts` — loop over misclassified corridors
- `enrich-corridor-cabins.ts` — ~443 corridors individual updates
- `enrich-corridor-venues.ts` — ~476 corridors individual updates
- `enrich-corridor-port-costs.ts` — per-corridor individual updates

## Edge Case: React Hydration Errors (#422/#425) from Timezone-Dependent Formatting

When a `'use client'` component renders dates with `toLocaleDateString()` without specifying `timeZone`, the server (UTC) and browser (user's local timezone) can produce different text for dates near midnight UTC.

**Symptoms:**
- Minified React error #425: "Text content does not match server-rendered HTML"
- Minified React error #422: "Hydration failed because initial UI does not match"
- The error may cascade and prevent OTHER components in the tree from rendering
- The date itself may appear correct on screen, but the page is partially broken

**Diagnosis:**
```bash
grep -rn 'toLocaleDateString\|toLocaleTimeString' app/<affected-page>/
```

**Fix:**
```typescript
// ❌ Server says "Jul 4", browser says "Jul 3" → hydration error
d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })

// ✅ Same on both server and client
d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' })
```

**Safe alternatives:** Number formatting with `toLocaleString()` does NOT depend on timezone. ISO string formatting (`toISOString().split('T')[0]`) is also safe. See `systematic-debugging` skill pitfalls #14-15 for related patterns.

## Edge Case: Frontend 404 After Modular Refactor — Route Drift

When a frontend view reports a 404 for an API call after a modular refactor or router reorganization, the endpoint often still exists — just under a different path or router prefix.

**Symptom:** A view that worked before extraction/refactor now shows "Failed to load X: 404". The backend route file is unchanged in substance but was moved into a different `APIRouter` with a new prefix (e.g., from `/api/pipeline/*` to `/api/admin/*`).

**Root cause:** The frontend view module was extracted or copied during the refactor and still points at the old URL. Static-string URLs are easy to miss because they don't raise compile-time errors.

**Detection recipe:** See `references/route-drift-404-refactor-recipe.md` for copy/paste commands, a TestClient snippet, and the response-shape gotchas. The key commands are:

```bash
# Find every API call string in the affected view and related views
grep -nE "api\('/api/" ui/js/views/*.js

# Confirm the backend router paths and prefixes
grep -nE "router\.(get|post|put|delete)\(|APIRouter\(prefix" src/api/routes/*.py

# Confirm how routers are mounted in main.py
grep -nE "include_router|prefix" src/api/main.py
```

**Fix pattern:**
1. Update the frontend URL to the current backend path.
2. Run the backend with a TestClient (or curl) to verify the response **shape** as well as the status — a route move often coincides with a shape change (e.g., backend now returns a list directly instead of `{items: [...]}`).
3. Adapt the frontend to consume the actual shape; don't assume the old wrapper key exists.
4. Check that the backend returns the full canonical entity set. If it only returns a subset (e.g., 5 of 15 sports), synthesize or extend the response to match `VALID_SPORTS`/canonical constants.
5. Add/update a frontend test that asserts the URL string or the rendered output when the mocked endpoint returns the new shape. Update backend tests to assert the full canonical count.

**Prevention:** During modular frontend refactors, include a "URL audit" step: grep all `api('/api/...` calls after extraction and compare them against the mounted backend routes. Keep endpoint paths in a shared constants module when multiple views hit the same resource.

**Example from this project:** `ui/js/views/domains.js` and `ui/js/views/corpus.js` were extracted during the 2026-06-10 modular refactor. They called `/api/pipeline/domains`, `/api/pipeline/corpus`, and `/api/pipeline/corpus/{table}/sample`. The actual endpoints had been placed in `src/api/routes/admin.py` with prefix `/admin`. The fix updated the URLs to `/api/admin/...`, adapted the views to the list-shaped responses, and expanded the backend to return all 15 `VALID_SPORTS` by synthesizing football-league configs. See `references/route-drift-404-refactor-recipe.md`.

## Verification Checklist

- [ ] The bug's entry point has been identified via `get_affected_flows` (or via raw PDF text extraction for document-based bugs)
- [ ] Recent changes near the bug have been inspected with `detect_changes`
- [ ] Impact radius of any proposed fix has been checked with `get_impact_radius`
- [ ] For 404 regressions after refactor: all `api('/api/...` URLs in affected view files have been cross-checked against the mounted backend routes in `src/api/main.py`
- [ ] For 404 regressions after refactor: the backend response shape and coverage have been verified with a TestClient/curl call, not just the status code
