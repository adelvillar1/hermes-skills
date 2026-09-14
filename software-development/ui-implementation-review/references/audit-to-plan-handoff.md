# Audit-to-Plan Handoff

The skill's Step 8 says: "Offer to create a fix plan." This reference codifies the conversion when the user says yes — how to take a 30-finding numbered report (🔴 / 🟡 / ⚪) and turn it into an executable, phased plan.

## When to load

- The user has just received the full-app audit report and answered "yes, make a plan."
- The audit produced ≥10 findings, or any 🔴-level findings exist.
- The conversion needs to preserve every finding ID (B1, B2, U1, etc.) and produce a plan with concrete ACs.

## The conversion recipe (4 steps)

### Step 1: Build a findings inventory

Open the audit report and produce a table:

| ID | Tier | Title | Files | Effort | Impact |
|----|------|-------|-------|--------|--------|

The IDs are whatever the audit used. Effort + Impact come from the audit's priority-recommendations section. If the audit didn't assign effort/impact, estimate based on file-touchpoint count (single file = S, 1-3 files = M, 4+ files = L).

Then sort by tier (🔴 first, 🟡 second, ⚪ last) within the table. This becomes the input to phase assignment.

### Step 2: Cluster findings into shippable phases

Group findings into 2-4 phases. Use the **🔴 → 🟡 → ⚪ ordering principle** from `draft-feature-plan/references/phase-implementation-ordering.md`. Each phase should have:

- One reason to ship (e.g., "Phase 2 restores session on page load").
- Clustered file touchpoints (Phase 1 hits 3 files, not 30).
- Tests that pass after Phase N (don't break tests in later phases).

Common clusterings for a usability audit:

| If the audit has... | Phase structure... |
|---|---|
| Any unverified-by-curl security findings | Phase 1 = security gates (always first) |
| Session/auth flow problems | Phase 2 = session/auth |
| Many panel CRUD gaps | Phase 3 = component completeness (group by panel type) |
| Single-file refactors (Tabletop.tsx too big, etc.) | Phase 4 = refactor (always last) |

**Avoid the mistake of one finding per phase.** A 30-finding plan with 30 single-item phases is unmaintainable. Cluster by *concern* not by *finding*.

### Step 3: Write phase ACs that close multiple findings

For each phase, write ACs that match the **specific observable outcomes** of the findings being closed. The pattern:

```
### Phase 2 — Session + DM role detection

- [ ] <closing AC for A1/B3>: Loading `/` while authenticated → user lands in tabletop without re-login (your browser tool verification)
- [ ] <closing AC for A1 specifically>: `grep -r "auth/me" apps/web/src/` returns exactly 1 hit (the new useSession call site)
- [ ] <closing AC for B9>: `grep -n "dmMode" apps/web/src/components/Tabletop.tsx` returns 0 hits (the client toggle is gone)
```

Each AC must:

- Be **independently verifiable** (a single command or visual check)
- Cite a **specific file path or grep target**
- Close **at least one audit finding** (referenced by ID in parens)
- Be achievable with **one or two file edits** (per the skill's "single observable outcome" rule)

### Step 4: Map every audit finding to exactly one phase

Use this verification before saving the plan:

```markdown
| Audit finding | Closes in phase | AC #
|---------------|----------------|-----|
| B1 (DELETE /saved-encounters accepts no auth) | Phase 1 | AC 1 |
| A1/B3 (/auth/me never called) | Phase 2 | AC 8 |
| U2 (CharacterSheet JSON textarea) | OUT OF SCOPE — follow-on plan |
| ... | ... | ... |
```

**Every finding must appear** in this table — either in a phase's AC or in the "Out of Scope" section with rationale. An audit finding that disappears during plan conversion is the #1 signal that the conversion was sloppy.

## Real-world conversion (the D&D VTT project, 2026-07-18)

The audit produced 31 findings. The plan covered them in 4 phases:

| Audit category | Coverage | Out of scope (rationale) |
|---|---|---|
| 🔴 Bugs (9) | 9/9 — every bug in a phase | none |
| 🟡 UX (14) | 10/14 — Phase 2, 3, 4 | U2 (typed character sheet — too large), U9 (markdown — needs new dep), U4 partial (click-to-place), U7 (PC/NPC) — each with one-paragraph rationale |
| ⚪ Architecture (8) | 3/8 — A2 (WS reconnect), A6 (ErrorBoundary), A4 (refactor) | A1 (shipped as a bug fix in Phase 2), A3 (shipped in Phase 4 as op TTL), A5 (shipped in Phase 1 as CSRF), A7/A8 (not addressed) |

Critically: the plan's "Out of Scope" section enumerated every deferred finding with a sentence of rationale. A reader of the plan knows exactly which audit findings are unaddressed and why. No finding silently disappeared.

## The "Suggested split for subagent dispatch" section

The plan body needs an explicit section specifying how each phase can be `subagent dispatch`'d. The pattern:

```markdown
**Suggested split for `subagent dispatch`:**

- **Phase 1** as a single subagent (security fixes are concentrated in 3 files; spec-compliance + code-quality review).
- **Phase 2** as a single subagent (session + role is a coherent change).
- **Phase 3** split into 2-3 subagents: (a) routes + HandoutPanel + JournalPanel + CharacterSheet; (b) ChatPanel + DicePanel + displayName joins; (c) topbar grouping + ErrorBoundary + confirm-dialogs sweep.
- **Phase 4** as a single subagent (refactor is hard to split; needs the whole tabletop context).

Each subagent gets the relevant subset of this plan's Acceptance Criteria as the verifiable spec.
```

See `draft-feature-plan/references/phase-implementation-ordering.md` for why this section belongs in the plan body.

## What NOT to do during the conversion

- **Don't re-rank the audit findings' severity.** The audit's triage is the user's accepted input; the plan respects it.
- **Don't drop "low impact" findings silently.** If a finding doesn't justify a phase, put it in Out of Scope with a one-sentence rationale.
- **Don't invent new findings.** If a finding emerges during planning, it's a new audit-iteration outcome — not part of this plan.
- **Don't write ACs that map to multiple files.** If an AC requires editing 5 files, it's a phase summary, not an AC. Break it down.
- **Don't forget the verification step that **every** 🔴 from the audit gets re-checked at production URLs.** The plan's Verification section should include the exact curl commands from the audit's 🔴 findings.

## The verification checklist before saving the plan

- [ ] Every audit finding appears in either a phase AC or the Out of Scope section.
- [ ] Every AC has a specific verification method (curl, grep, your browser tool, visual check).
- [ ] Phase ordering follows 🔴 → 🟡 → ⚪.
- [ ] Each phase has 5-25 ACs (not too few to be meaningful, not too many to be reviewable).
- [ ] "Suggested split for `subagent dispatch`" section exists if phases will be dispatched to subagents.
- [ ] Every file path the plan references is verified to exist (`ls` or equivalent) before saving.
- [ ] Type-check passes (`npx tsc --noEmit`) per the skill's `pre-flight-verification` rule.
- [ ] Plan is staged (added to git) but not committed — `git status` shows the new file as untracked or modified-not-staged.

The plan is now ready for the user to review and mark `status: active`.