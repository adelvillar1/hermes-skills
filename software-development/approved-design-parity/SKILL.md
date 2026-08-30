---
name: approved-design-parity
description: "Use when implementing anything from an approved artifact."
version: 2.0.0
tags: [meta, design-fidelity, delegation, contract, verification, acceptance-criteria]
---

# Approved Design Parity — an approved artifact is a binding contract

When the user has approved a design artifact — a UI prototype, an API contract, a workflow diagram, a process spec, an architecture document, a data model — **the implementation must match that artifact.** This is a non-negotiable acceptance criterion, not a style reference. "Looks reasonable" is not the bar — "matches what was approved" is the bar.

This is a **meta-skill**: the principle applies identically across UI, backend, workflow, process, and architecture. Domain-specific verification guidance is in §Domain playbooks below.

## The mandate

An approved artifact is the most specific expression of the user's intent that exists. It outranks:
- the written task description (which describes intent, not details)
- the implementer's taste or judgment (including yours)
- general best practices or "good design" defaults
- what a subagent thinks would be "cleaner" or "simpler"

If there is a conflict between the artifact and the task description, the artifact wins for everything it covers; the task description wins only for gaps the artifact doesn't address. Surface the conflict — don't silently resolve it by redesigning.

## The failure mode: the invented implementation

The classic failure — especially when delegating to a subagent:

1. User approves an artifact ("looks great," "approved," "go with this").
2. The task spec says "implement X" and *mentions* the artifact, or assumes it's discoverable.
3. The implementer treats the artifact as inspiration, or never opens it, and produces their own version from the task text + their defaults.
4. The result is competent, even good — and wrong. The user opens it and says "that's not what I approved."
5. Full rework: re-implement faithfully, re-verify, re-deploy.

A subagent is the highest-risk actor: it has no memory of the approval moment, no taste context, and defaults to inventing something plausible. "It's in the repo" does not mean the subagent saw it, understood it was binding, or prioritized it over its own defaults.

## When to use

Any implementation work where an approved artifact exists:
- UI: prototype, mockup, Figma frame, screenshot, hosted preview
- Backend/API: OpenAPI spec, endpoint contract, schema definition, architecture doc
- Workflow/process: approved pipeline steps, state machine, approval flow
- Data model: approved ERD, table structure, field naming conventions
- Infrastructure: approved topology diagram, deployment architecture
- Copy/content: approved wording, tone guide, brand voice doc
- Delegating any of the above

## How to enforce it (domain-agnostic)

### 1. Name the artifact as binding, in writing

In the task plan and (critically) the delegation prompt, state explicitly:

> The approved design is at `<exact path or URL>`. It is the BINDING contract. Implement it faithfully. Do NOT redesign, reinterpret, simplify, or "improve" it. If something in it seems wrong, implement it anyway and flag it in your report — do not silently deviate.

Give the exact path/URL. Never say "see the spec in the repo" without a path.

### 2. Enumerate the artifact's distinctive elements as acceptance criteria

Open the artifact and list what makes it *itself* — the things that would be noticed if they vanished or changed. The shape varies by domain (see playbooks below), but the act is the same: extract the concrete, checkable details and paste them into the delegation prompt as acceptance criteria.

A subagent that invents its own version will fail this list; one that implements the artifact will pass.

### 3. Instruct implementation, not "in the spirit of"

The verb matters:
- ✅ "Port the prototype's CSS and markup into the component"
- ✅ "Implement exactly these endpoints with these schemas and status codes"
- ✅ "Follow these pipeline steps in this order with these thresholds"
- ❌ "Build a page matching the brand direction"
- ❌ "Design an API for this domain"
- ❌ "Set up a pipeline that does roughly this"

### 4. Verify against the artifact before shipping

Verification is domain-specific (see playbooks), but the principle is universal: **compare the implementation to the artifact, not to your expectations.** Check that the concrete details from step 2 are present and correct. A wrong implementation passes every functional test — you need artifact-specific verification.

### 5. Allowed deviations — and only these

- Binding live data where the artifact used placeholders
- Accessibility/safety fixes that don't change the contract
- Gaps the artifact genuinely doesn't cover (match its language/patterns, don't invent a new one)
- Anything the user explicitly changed after approval

Aesthetic reinterpretation, architectural "improvement," and process "simplification" are never allowed deviations. If the artifact genuinely has a problem, flag it and let the user decide.

## Domain playbooks

### UI / Visual

**Artifact:** prototype page, mockup, Figma, screenshot, hosted preview.

**Distinctive elements to enumerate:**
- Palette (exact hexes) and tonal mood
- Typefaces (display + body + accent) and scale contrast
- Section order and layout structure
- Signature elements: marquees, hero treatments, specific cards, dividers, badges
- Motion: scroll reveals, hover states, ambient animation
- Imagery treatment (photography-first, duotone, frames)

**Verification:**
- Side-by-side screenshots (artifact vs deployed) compared with vision
- Grep the production CSS for the artifact's hexes/font families — a missing brand color means the wrong design shipped
- Confirm against the PRODUCTION build, not dev mode (bundlers purge/rewrite CSS)
- User views the real deployed page

**Porting shape (static HTML prototype):** lift the `<style>` block into a scoped stylesheet, keep the markup structure, swap hardcoded content for live data bindings. Change structure only where data binding requires it.

### Backend / API

**Artifact:** OpenAPI spec, endpoint contract doc, architecture decision record, schema definition.

**Distinctive elements to enumerate:**
- Exact endpoint paths and HTTP methods
- Request/response schemas (field names, types, required vs optional)
- Status codes for each outcome (200, 201, 400, 404, 409, etc.)
- Auth requirements per endpoint
- Error response shapes
- Pagination/sorting/filtering conventions
- Naming conventions (camelCase vs snake_case, plural vs singular)

**Verification:**
- Curl every endpoint and diff the response shape against the contract
- Check status codes for error cases (not just happy path)
- Confirm field names match exactly (not "close enough")
- Run the contract's example requests if provided

### Workflow / Process

**Artifact:** approved pipeline steps, state machine diagram, approval flow, runbook.

**Distinctive elements to enumerate:**
- Step order and dependencies
- Thresholds, timeouts, retry counts
- State transitions and their triggers
- Gate conditions (what blocks progression)
- Notification/alerting points
- Rollback/failure handling

**Verification:**
- Trace a happy-path execution through every step
- Trigger each failure/gate condition and confirm the specified behavior
- Confirm step order matches (not "roughly the same flow")
- Check that thresholds match exactly (not "similar")

### Data Model / Schema

**Artifact:** ERD, table spec, field naming doc, migration plan.

**Distinctive elements to enumerate:**
- Table names and relationships
- Column names, types, constraints
- Indexes and their targets
- Enum values and their exact strings
- Default values
- Soft-delete vs hard-delete conventions

**Verification:**
- Diff the actual schema (via `\d` or migration SQL) against the artifact
- Confirm FK relationships and cascade behavior
- Check enum values match exactly
- Verify indexes exist on the specified columns

## Anti-patterns

**A. "The spec said 'implement X,' so I designed X."**
The task presupposes the approved artifact. Implementation fills in the artifact's details with working code — it doesn't replace the artifact's decisions with new ones.

**B. "I built something in the spirit of it."**
"In the spirit of" is the sound of the artifact being ignored. The user approved specifics, not a vibe.

**C. Verifying only that it works.**
A wrong implementation passes every functional test. Artifact-specific verification (step 4) is mandatory.

**D. Assuming the subagent discovered the artifact.**
Pass the path, the binding statement, and the acceptance-criteria list in the delegation prompt. Discovery is not a plan.

**E. "I'll fix the deviations in a follow-up."**
Ship parity in the same change. A deployed deviation is a user-visible regression from the moment it goes live.

**F. "My version is simpler/cleaner/better."**
Irrelevant. The user approved *that* version. If the artifact has a genuine problem, flag it — don't silently substitute your judgment.

## Real example (2026-07-31, pampa-wineclub — UI domain)

The user approved a dark, crimson/Playfair, photography-first prototype (`design/prototype/index.html`, hosted at `:8123`) with "the design looks great." The Phase 6b delegation spec said "rewire the public site to the live API" and referenced the prototype — but the subagent shipped an unapproved amber/stone "editorial" design of its own invention. It rendered, it worked, it even looked nice — and it was wrong. The user caught it on staging immediately.

Fix: re-ported the prototype verbatim — lifted its CSS into a scoped `.pampa-home` stylesheet, kept the markup structure (ken-burns fire hero, red marquee, dotted-leader menu rows, region tags, bottle tiers), and bound live menu/event/reservation data into it.

Lesson: the delegation prompt needed the artifact named as binding with its distinctive elements listed as acceptance criteria, and verification needed a side-by-side visual check, not just "the page renders."

## Checklist template

```markdown
## Design parity: [ARTIFACT path/URL] → [TARGET implementation]
Domain: [ UI | API | Workflow | Schema | Infrastructure | Copy ]

### Artifact named as binding in plan + delegation prompt?  [ ]
### Distinctive elements enumerated as acceptance criteria
- [ ] Element 1: <specific>
- [ ] Element 2: <specific>
- [ ] Element 3: <specific>
- [ ] [...domain-specific items...]
### Implementation
- [ ] Implemented the artifact, not a reinterpretation
- [ ] Deviations limited to: data binding / safety / gaps / user-requested
### Verification (domain-specific)
- [ ] <domain verification step 1>
- [ ] <domain verification step 2>
- [ ] User has confirmed the result matches the artifact
```

## Related skills

- **`visual-component-migration-checklist`** — when replacing an existing component, the OLD implementation is the source of truth. Here the APPROVED ARTIFACT is the source of truth. Run both when porting an approved prototype over an existing page.
- **`image-to-code`** — mechanics of turning a mockup/screenshot into code (UI domain).
- **`ui-implementation-review`** — post-build UI audit; use it against the artifact's acceptance criteria.
- **`subagent-driven-development`** — where the delegation-prompt language in steps 1–3 belongs.
- **`spec-compliance-review`** — review an implementation against a plan's acceptance criteria; the review-half of this skill's verify step.
