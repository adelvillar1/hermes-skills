---
name: design-review
description: "5-dimension design critique framework for reviewing visual designs (prototypes, animations, slides, UI mockups). Scores each dimension 1-10: Philosophy Alignment, Visual Hierarchy, Craft Quality, Functionality, Innovation. Produces a scored review with prioritized fix list. When the user asks for 'thorough' or 'actionable' review, the deliverable is the fixes — the audit is a planning artifact, not an output."
version: 1.1.0
author: Derived from huashu-design (花叔Design) — alchaincyf
license: MIT
metadata:
  hermes:
    tags: [design, "critique", "review", "visual", quality]
    related-skills: [claude-design, "brand-asset-protocol", sketch, "architecture-diagram"]
    category: creative
    requires_toolsets: [vision]
---

# Design Review — 5-Dimension Critique Framework

Use when the user asks for design feedback: "review this design", "how does this look", "critique this", "is this good?", "what would you change?". Analyze the design through 5 dimensions, score each 1-10, and provide a prioritized fix list.

## When to Use

- User wants feedback on a design (HTML page, animation, screenshot, mockup)
- User asks "does this look right?" or "how can I improve this"
- Before finalizing a design deliverable (self-review gate)
- Peer review of another agent's design output

## The 5 Dimensions

### 1. Philosophy Alignment (9-10: Excellent)

| Score | Criteria |
|-------|----------|
| 9-10 | Design perfectly embodies the chosen philosophy — every detail has philosophical justification |
| 7-8 | Direction is correct, core features are in place, minor individual details deviate |
| 5-6 | Intent is visible but execution mixes in elements from other styles, not pure enough |
| 3-4 | Surface-level mimicry only, doesn't understand the philosophy's core |
| 1-2 | Essentially unrelated to the chosen philosophy |

**Checklist:**
- Does it use the designer/studio's signature techniques?
- Are colors, fonts, and layout consistent with the philosophy system?
- Are there self-contradictory elements? (e.g., chosen Kenya Hara minimalism but crammed with content)

### 2. Visual Hierarchy (9-10: Excellent)

| Score | Criteria |
|-------|----------|
| 9-10 | Viewer's eye flows naturally along the intended path — zero friction to find information |
| 7-8 | Primary/secondary relationships are clear, 1-2 spots of ambiguity |
| 5-6 | Headings and body are distinguishable but middle levels are messy |
| 3-4 | Information is flat, no clear visual entry point |
| 1-2 | Chaotic — viewer doesn't know where to look |

**Checklist:**
- Heading to body size contrast: at least 2.5x difference?
- Do color/weight/size establish 3-4 clear levels?
- Does whitespace guide the eye?
- **Squint test**: squint your eyes — is the hierarchy still clear?

### 3. Craft Quality (9-10: Excellent)

| Score | Criteria |
|-------|----------|
| 9-10 | Pixel-perfect — alignment, spacing, colors have zero flaws |
| 7-8 | Generally polished — 1-2 minor alignment/spacing issues |
| 5-6 | Basically aligned but spacing is inconsistent, colors unsystematic |
| 3-4 | Obvious alignment errors, spacing chaos, too many colors |
| 1-2 | Rough, looks like a draft |

**Checklist:**
- Is alignment consistent? (not approximate)
- Is spacing systematic? (same padding for same-level elements)
- Is the color system consistent? (not inventing new hexes per element)
- Is typography clean? (rag, widows, orphans controlled)
- Are edges crisp? (no 1px misalignment, no half-pixels)

### 4. Functionality (9-10: Excellent)

| Score | Criteria |
|-------|----------|
| 9-10 | Every interactive element works as expected — zero broken states |
| 7-8 | Core flow works, edge cases have minor issues |
| 5-6 | Main path works but secondary paths break |
| 3-4 | Core flow has issues — confusing or broken |
| 1-2 | Basically non-functional |

**Checklist:**
- Do all clickable elements respond correctly?
- Are there hover/active/focus states?
- Are loading, empty, error, and edge case states handled?
- Does the flow make logical sense? (no dead ends)

### 5. Innovation (9-10: Excellent)

| Score | Criteria |
|-------|----------|
| 9-10 | Genuinely novel approach — seeing the problem differently |
| 7-8 | Fresh take on a known pattern — meaningful twist |
| 5-6 | Solid execution of standard patterns — safe but not surprising |
| 3-4 | Generic — feels like a template |
| 1-2 | Cliché or copied |

**Checklist:**
- Does it solve the problem in an interesting way?
- Or is it a standard pattern with no original thought?
- Does it have a "signature moment"?

## Review Format

### Output Skeleton (use this for full-app audits)

```markdown
# Design Review: <name/description>

**Method:** visual+code | code-only | visual-only — note how you actually saw it
**Source artifacts:** N HTML pages, M CSS files, K JS files, J screenshots

## Score Summary
| Dimension | Score | Verdict |
|---|---|---|
| Philosophy Alignment | X/10 | … |
| … | … | … |
| **Overall** | **X.X/10** | <one-line summary> |

## Dimension Breakdown
(per dimension: what's working, what's not, with line-number evidence)

## Anti-AI-Slop Audit
(table form, ✓/❌ per trap from the checklist below)

## Surface Inventory
(one row per surface, with verdict)

## Prioritized Recommendations

### P0 — Fix This Session (data correctness / broken features)
| # | Issue | Where | Effort |
|---|---|---|---|

### P1 — Fix This Quarter (real UX gaps)
…

### P2 — Structural Improvements (2-4 hrs each)
…

### P3 — Big Bets (1-2 days)
…

## Sign-Off
The single biggest gap + the single biggest strength + 2-3 next-action options for the user.
```

**Why this shape:** the P0/P1/P2/P3 + effort columns is the part users actually act on. Dimension scores are interesting; the prioritized table is the deliverable. Don't ship the review without it.

### Quick Review (lightweight version)

```markdown
## Quick Review

**Score:** 7/10 — Strong, <2-word verdict>

**Best thing:** <one sentence>

**Biggest issue:** <one sentence>

**Quick fixes:**
- <item>
- <item>
```

## Using with Vision

When the user asks for a design review, use vision_analyze on the design screenshot/output to understand the visual elements. Then produce the structured review.

### Visual Review Protocol (with screenshots + access to the live app)

The agent who only sees screenshots audits the surface, not the system. To audit a *live* app, you need to render it. For modern web apps that means you need to be authenticated. Three patterns, in order of preference:

1. **Production with your own credentials.** Acceptable for read-only viewing; never write.
2. **Local stack with a seed test user.** The right default for any project that has a "develop locally first, never touch remote DBs" rule (most do). Find the user-seeding path (CLI command, factory function, fixture script), create a non-real test user against the local DB, run the dev server on a free port, screenshot the auth-gated surfaces.
3. **Public/staging if it exists.** Often has demo accounts documented.

**For pattern 2, the recipe is:** read the auth service for a `create_user(email, password, role, display_name)` function (or equivalent factory). Use a syntactically valid email — pydantic `EmailStr` rejects `name@local`, `name@host.test`, and other reserved TLDs. Use `name@yourproject.com` style. Spin up the dev server (`uvicorn ...:app --port XXXX`) in the background, not in a foreground process. Log in via curl with a cookie jar: `curl -c cookies.txt -X POST /api/auth/login -d '{"email":"...","password":"..."}'`. Verify with `curl -b cookies.txt /api/auth/me`. Drive the browser through the login form, then navigate to each surface via direct URL/hash.

### Multi-Frame Capture for Animations

For 3D scenes, motion design, or any artifact that changes meaningfully over time, **a single screenshot is structurally incomplete** — you can't audit motion, transitions, state-machine outputs, or the difference between an "intact" frame and a "replication in progress" frame. Capture 5-8 frames at deliberate points in the cycle:

- **Pre-animation / resting state** — baseline
- **Just past the trigger event** — captures the entry into a new state
- **Mid-cycle** — peak activity, all elements visible
- **Near the end of the cycle** — completion / crowding behavior
- **Right before reset / loop** — the "look at all of this" moment where everything is at peak

Use Playwright with timed `wait_for_timeout()` calls between `page.screenshot()` calls. Track frame count vs time so you know what phase each screenshot represents. See `references/multi-frame-capture-protocol.md` for the full pattern + script template.

### Vision-Aided Debugging Pitfalls (3D scenes)

Vision models describe what they *see*, not what you *coded*. When a vision model says "I see a label that reads 'Sun'" in a 3D scene you know is about DNA, it's hallucinating — the text is too small or blurry to actually read, and vision fills the gap with plausible-but-wrong guesses. Two debugging techniques:

1. **Increase size until unambiguous.** If a sprite label might be there but vision can't read it, scale the label 2-3× larger. If the label was rendering correctly, the larger version will be obviously readable. If it wasn't rendering, the larger version still won't appear.
2. **Add a debug fallback.** A label pinned to a fixed NDC coordinate (e.g., `(-0.6, 0.4)`) that *should* always be visible is the canonical "is the sprite pipeline working at all?" test. If the debug label doesn't appear, the bug is in the sprite/render setup, not the positioning logic.

### Code-Based UX Audit (no screenshots available)

When you can't render the app but need to audit UX (e.g., reviewing a codebase before implementation, or when the app isn't running), audit from code. This produces a review that's 80% as accurate as a visual review and catches structural issues screenshots miss.

**Platform-specific checklists:**
- **SwiftUI macOS apps:** See `references/code-based-ux-audit-swiftui-macos.md` for SwiftUI-specific checks (DesignTokens.swift audit, ScrollView+ForEach virtualization, hover states, keyboard shortcuts, verification commands).
- **Ranking UIs ("Top N" surfaces, "watchlist" widgets, recommendation lists):** See `references/ranking-hierarchy-pattern.md` for the 4-layer filter/sort hierarchy, badge-copy tiering, and the "alignment is meaningless without decisiveness" principle.
- **Data-dense dashboards (team detail, analytics overview, portfolio summary):** See `references/dashboard-real-estate-patterns.md` for hero density, chart hygiene, card-vs-list layout, gauge over-engineering, tab design, scenario surfaces, and navigation structure.

**What to read:**
1. **Design system / theme file** — tokens, typography scale, color palette, spacing system, shadows. This tells you the visual language.
2. **Every screen file** — focus on layout structure (ScrollView vs FlatList vs SectionList), state management (loading/error/empty states), interaction handlers (onPress, onLongPress), style objects.
3. **Navigation structure** — screen hierarchy, stack depth, tab configuration, header options.
4. **API client** — what data is requested, what's returned, what's rendered vs discarded.
5. **Shared components** — which patterns are reused (cards, pills, buttons, loading states).

**What to look for (code-level UX signals):**
- **Dead UI**: `<View>` where `<TouchableOpacity>` should be (non-interactive elements that look interactive)
- **Silent failures**: `.catch(console.error)` on sub-loads (data fails but no user-facing error state)
- **Response key mismatches**: API returns `{ results: [...] }` but code checks `.items` — produces empty arrays silently
- **Data wastage**: API joins and returns fields (route maps, metadata, relationships) that the UI never renders
- **Nested scroll anti-patterns**: `<ScrollView><FlatList scrollEnabled={false}>` disables virtualization
- **Missing pagination**: `limit: 20` with discarded `pagination` metadata means only first page shows
- **Contrast failures**: foreground color on canvas background below 4.5:1 WCAG AA ratio
- **Default state problems**: filters defaulting to "All" when domain knowledge says users want current month/year

**Audit structure for code-based review:**
1. Score the 5 dimensions (Philosophy, Hierarchy, Craft, Functionality, Innovation) from code analysis
2. Map the user journey through navigation structure
3. Identify "signature moments" that are present vs missing
4. Prioritize findings by user impact (not code complexity)
5. Produce recommendations grouped into Quick Wins (< 1 hr), Structural Changes (2-4 hrs), and Big Bets (1-2 days)

**When to use this vs visual review:**
- **Code-based**: pre-implementation audit, codebase review, planning phase
- **Visual**: post-implementation audit, design QA, final polish
- **Both**: when you have screenshots AND code access (code reveals what screenshots hide)

## Anti-Patterns to Flag

From the anti-AI-slop checklist — if you see these in a design, flag them regardless of scoring:

- ❌ Radical purple gradient backgrounds
- ❌ Rounded cards with left border accent color
- ❌ Emoji as UI icons (🚀 ⚡️ ✨ 🎯 💡 before headings)
- ❌ SVG hand-drawn imagery (people, scenes, objects)
- ❌ Excessive iconography (every item gets an icon)
- ❌ "Data slop" — fake stats as decoration ("10,000+ happy customers")
- ❌ Inter/Roboto/Arial as display font without brand spec justification
- ❌ Cyber neon / dark blue #0D1117 — overused GitHub dark mode clone

## Post-Audit Workflow (Full App Redesign)

When the review covers an entire app (not just one page), the audit is the starting point — not the deliverable. Follow this sequence:

### 1. Audit (this skill)
Produce the 5-dimension review. Be brutally honest. A 3/10 overall is fine — that's the baseline.

### 2. Present findings + direction alignment
Present the audit, then **immediately ask the user to choose a design direction.** Offer 3-4 concrete directions with evocative descriptions (not just style names). Each should name a recognizable reference:
- "Warm & editorial — Airbnb meets a travel magazine"
- "Clean & premium — Apple Maps meets a luxury hotel app"
- "Dark & immersive — Spotify meets a cruise ship evening app"

Do NOT start designing until the user picks a direction. The direction locks the color palette, typography, and component patterns.

### 3. Write an implementation plan
Use `draft-feature-plan` to create a plan with:
- **Design tokens** section: exact color palette, typography scale, spacing system, shadow levels, border radius scale
- **Shared components** task first (theme.js + reusable components)
- **Screen-by-screen tasks** after, each referencing the shared components
- **Verification** that includes `grep` for hardcoded colors and emoji
- **UI constraints** section listing what stays the same (data logic, API client, navigation structure)

See `references/mobile-app-redesign-pattern.md` for the concrete pattern (theme.js structure, shared component library, verification commands, design direction catalog with token signatures).

### 4. Execute via subagent-driven-development
Each screen becomes a task. Shared components must be Task 1 — every subsequent task imports from them.

## Pitfalls

1. **Be specific, not vague.** "The typography could be better" is useless. "Heading size should be 2.5x body for stronger hierarchy" is actionable.
2. **Always prioritize.** Rank issues by impact. Don't present a flat list of 20 problems.
3. **Separate quick fixes from structural changes.** A 2-minute CSS tweak is different from a layout rethink.
4. **Dimension scores should be justified.** If you give a 6, explain why it's not a 7.
5. **Never skip the "best thing"** — the review should acknowledge what's working, not just critique.
6. **Don't audit and design in one step.** Audit → direction choice → plan → implement. Mixing these produces mediocre results because the direction isn't locked.
7. **Code review alone is structurally incomplete for modern web apps.** You will not catch duplicate-list bugs (same alert appearing twice, same opponent in 3 sequential "Up Next" cards) by reading JS — both look fine syntactically. You catch them by *seeing* the rendered page. For any audit of a live app, render the screens you audit, even if you also read the code.
8. **The auth wall will stop you before you can audit.** Most modern web apps have at least one auth-gated surface. If you can't render authenticated views, your audit is incomplete and you should say so explicitly in the sign-off — don't pretend the unauthenticated review is the whole story.
9. **Audit findings come with implied fixes — don't ship a review and stop.** When the user asks for a "thorough" or "actionable" review, they expect the fixes to follow in the same session (or a tight follow-up). Find the 5 P0 items, fix them, commit, recap. A review without execution is a journal entry, not a deliverable. If the audit is huge and they want it staged, ask which P0s to ship now — don't assume "review = done."

   **The implicit contract when the user says "thorough review with actionable recommendations":** the deliverable is the fixes, not the audit document. Default to executing P0+P1 in the same session. Treat the audit as a planning artifact, not an output. If you produce a 6,000-word audit and then idle waiting for direction, you have failed the contract — the user has to prompt you to do the work you already catalogued. The right rhythm: audit (output is the prioritized table), ask one clarifying question if scope is genuinely unclear, then go. A "do you want me to fix these now?" question is fine ONCE; a second one is friction.

   **"Don't go silent after the audit" is the user-visible failure mode.** A review that ends with "What do you want to do next?" and then no movement until the user pokes you is the same failure as idling on an empty todo list. Plan your next action into the audit itself: "I can ship all 5 P0s + the 9 P1s in ~4-6 hours. Want me to start with P0-1, P0-2, P0-3 now, or stage them?" — then start the highest-impact one immediately after delivering the plan, unless the user explicitly says stop.

   **"Fix them all" / "ship everything" / "no time pressure" is an explicit green light to execute the full audit, not a request for another round of planning questions.** When the user removes the only constraint (time), the remaining decisions are *sequencing* (which P0 first) and *implementation choices* (rewrite vs patch-stack), not *scope*. Use a todo list, not a clarifying question. Phrasings to watch for: "time is of no concern to me", "fix them all", "ship everything", "no time pressure", "I don't care about the timeline, just do it", "do the full list", "go through them all". When you hear one, the audit→execution rhythm changes: deliver the audit, write a todo list, then start on the highest-impact P0 immediately. Asking "do you want me to stage this?" after they removed the time constraint is friction, not helpful clarification. The legitimate remaining question is sequencing (dependency chains, rewrite-vs-patch-stack tradeoffs), and you answer that with a todo list the user can scan in 10 seconds — not with a back-and-forth.
10. **Multi-frame capture is mandatory for animations.** A single screenshot of a 3D scene, motion graphic, or state-machine-driven UI tells you almost nothing. The DNA-replication scene in the project that motivated this pitfall had 4 distinct visible states (intact helix, fork opening, mid-replication with Okazaki cluster, near-complete) and a single screenshot at t=3s caught it in the *transition* between fork-opening and mid-replication, missing both the cluster and the cleanup behavior. Capture 5-8 frames at deliberate cycle points: pre-animation baseline, just past the trigger, mid-cycle, near the end, just before reset. See `references/multi-frame-capture-protocol.md` for the Playwright recipe. **Single-screenshot animation audits are structurally incomplete and will miss both state-machine bugs and visual regressions that only manifest at specific cycle points.**
11. **Vision models hallucinate to fill unreadable text.** When you ask `vision_analyze` to "read the text in this label" and the label is small enough that vision can't actually read the pixels, vision will *guess* — confidently. In one session a vision model said a DNA scene's tiny label "appears to read 'Sun'" when the actual code said something completely different, and only admitted uncertainty when pressed. Two debugging techniques when verifying in-scene text: (a) **scale the label 2-3× larger** — if it was rendering, the larger version will be obviously readable; if it wasn't, the larger version still won't appear. (b) **add a debug fallback** — a label pinned to a fixed NDC coordinate (e.g., top-left corner) that should always be visible. If the debug label doesn't show, the bug is in the sprite/render setup, not the positioning logic. Don't trust vision OCR on tiny 3D-scene text.
12. **The pydantic `EmailStr` reserved-TLD trap.** When seeding a test user via the local auth service, `name@local`, `name@host.test`, and `name@test.com` all fail validation. Use a real-looking domain (`name@yourproject.com`). The skill already notes this in the test-user recipe — keep it.
13. **"Alignment" without "decisiveness" is a coin-flip trap.** When a UI surface sorts by "two methods agree" (e.g., ELO+MC, deterministic+simulation, intent+outcome), the aligned toss-up is the worst-case pick — both methods cluster at 50/50 when uncertain, so their agreement is meaningless. A user looking at "Top Picks: 51% / 53% (Δ 2%)" will correctly point out: that's not a pick, that's a coin-flip. The fix is a hierarchy: `decisiveness > alignment > confidence > spread`. Filter for the favored side being ≥ 65% (or whatever your domain's decisiveness floor is) BEFORE alignment is even considered. Tier the badge copy by data quality (✓ agree / △ within X% / hidden) — never let "✓ agree" label a 14.5%-delta card. See `references/ranking-hierarchy-pattern.md`.
14. **The dead-tier confidence bug.** A confidence/categorization model with tiered labels (high/medium/low, critical/warning/info) is structurally susceptible to a class of bug: thresholds tuned for a hypothetical data distribution that the real system never produces. Symptom: 0% of records fall in the "highest" tier, even when the model is producing confident predictions. Diagnostic: query a sample, count tier distribution, and if any tier is at 0%, the threshold is wrong. Two interpretations: the data drifted (system got worse) or the thresholds were tuned for a state the system never reaches. Either way, the fix is re-tuning gates to where the data actually lives. Write a regression test that pins "a record at the realistic data values MUST classify as the highest tier when the score is also high" — locks the contract. See `dead-tier-classifier-audit` skill for the full pattern.
15. **"Don't ship a top-N section that's actually all tier 2."** A "Top Picks" surface that, on visual review, turns out to be 51%-53% games is a semantic failure — the section title is the contract. After building the section, do a visual review: do these *actually look like picks*? If a child could read them and ask "wait, why is this a top pick?", the section isn't done. Two ways this manifests and how to fix: (a) the filter is too loose — add the missing gate (decisiveness, freshness, etc.); (b) the data isn't there — render the empty state explicitly and tell the user why. Don't ship a sparse section that misleads.

## When to skip Pitfall 9's "default to executing P0+P1" rule

There ARE legitimate times to stop after the audit. The user might:
- Be in an exploratory / discussion mode and explicitly wants just feedback, not changes
- Be working on a codebase shared with other people who need to review the audit before action
- Have constraints the agent doesn't know about (a code freeze, a stakeholder veto)
- Want to discuss direction BEFORE committing to the fix list

The signal that says "ship it all": the user removes the only remaining constraint (time) and explicitly green-lights full execution. Phrasings to watch for:
- "time is of no concern to me"
- "fix them all" / "ship everything"
- "no time pressure"
- "I don't care about the timeline, just do it"
- "do the full list"

When you hear one of these, the audit→execution rhythm changes: deliver the audit, then plan the work into a todo list, then execute. Don't ask "do you want me to stage this?" — the staging question was answered when they removed the time constraint. Do ask if you genuinely don't know *order* (e.g., when an audit mixes P0 dependency chains with independent fixes), but solve that with a todo list, not a question.