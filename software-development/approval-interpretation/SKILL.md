---
name: approval-interpretation
title: Approval Interpretation for Guarded Operations
description: Distinguish between guardrails that require user initiative vs. commands that are themselves explicit approval. Prevents bureaucratic friction.
triggers:
  - User gives a command involving production, destructive ops, or hard-rule-guarded resources
  - About to ask "are you sure?" after user already said "do X"
  - User says "push to production" or similar explicit action on guarded resource
---

# Approval Interpretation for Guarded Operations

## The rule

Guarded operations (production deploys, destructive DB ops, force-pushes, etc.) require **explicit user approval**.

**Explicit approval can be:**
- A direct command: "push to production", "deploy to prod", "drop the table"
- A confirmation in response to a warning: "yes, do it anyway"
- A pre-authorized plan step: "step 3: merge to main" where the user approved the plan

**Explicit approval is NOT:**
- Silence after a warning
- A general discussion about production
- Approval for staging that implicitly might include production

## When to NOT ask for confirmation

| User said | Your response |
|-----------|--------------|
| "push to production" | Execute immediately |
| "deploy to prod" | Execute immediately |
| "merge staging to main" | Execute immediately |
| "yes, do it" (after warning) | Execute immediately |
| "run the migration on prod" | Execute immediately |

The user knows the rules. They are overriding the guardrail with their explicit command. Your job is to execute, not to re-guard.

## When to ask for confirmation

| Situation | Your response |
|-----------|--------------|
| You are about to push to production on your own initiative | Stop and ask |
| The user said "that looks good" but didn't say "ship it" | Ask: "ship to production?" |
| The user approved staging deploy but production was not discussed | Ask separately for production |
| A plan says "step 5: deploy to prod" but user only approved step 1-3 | Ask before step 5 |

## Anti-pattern: bureaucratic loop

**Wrong:**
> User: "push to production"
> You: "I need explicit approval to push to production. Do you want me to push to production?"

**Right:**
> User: "push to production"
> You: [executes immediately]

## Anti-pattern: verification loop on non-existent resources

**Wrong:**
> User: "use the repo https://github.com/user/repo.git"
> You: [fetches, finds repo doesn't exist, asks user "are you sure?" or suggests alternatives]

**Right:**
> User: "use the repo https://github.com/user/repo.git"
> You: [attempts to use it; if it doesn't exist, reports the fact and asks for the correct URL OR proceeds with local git init if the context supports it]

The user gave you a command. Your job is to execute it or report the blocker, not to second-guess their intent. If the repo doesn't exist, state that clearly and ask what they'd like to do next — but don't treat "repo not found" as a reason to question whether they meant it.

## Anti-pattern: implicit extension

**Wrong:**
> User: "ship the fix to staging"
> You: [ships to staging AND production because "it's just a small fix"]

**Right:**
> User: "ship the fix to staging"
> You: [ships to staging only, reports status, asks separately about production]

## Anti-pattern: committing on the wrong branch

**Wrong:**
> User: "commit and push to staging"
> You: [currently on `main`] → commits on `main`, then cherry-picks to `staging`, then pushes `staging`
> User: "why did you push to main without my approval?"
> You: "I didn't push to main, I only committed locally" ← this is still a violation

**Right:**
> User: "commit and push to staging"
> You: [currently on `main`] → `git checkout staging` FIRST, then commit, then push `origin/staging`
> `main` is never touched — not even for a local commit that you plan to cherry-pick away.

**Why this matters:** The user said "staging" — that word scopes the entire operation. Committing on `main` even temporarily (even without pushing) violates branch flow rules and creates a dirty production branch. The fix is simple: **switch to the target branch before committing.** If you discover changes on the wrong branch after committing, reset that branch back before doing anything else. The user's correction ("why did you push to main without my approval?") is a first-class signal — encode it.

**General rule:** When the user names a target branch ("push to staging", "commit to development"), the ENTIRE git operation (commit + push) happens on that branch. Switch to it before staging files. Never commit on a branch the user didn't name.

## Hard rules vs. user commands

Hard rules in project context (CLAUDE.md, etc.) are **defaults**. They protect against *agent initiative*. They do not override *user commands*.

Think of it like sudo:
- `rm -rf /` → blocked by default (guardrail)
- `sudo rm -rf /` → executed (user override)
- "delete everything" → executed (explicit user command = sudo)

## Examples from this project

**Production push (2026-05-14)**
- Wrong: User said "push to production" → I responded with "I need explicit approval" and asked them to choose between waiting for staging or pushing now
- Right: User said "push to production" → execute immediately, report result

**Port selection (2026-05-14)**
- User said: "just pick a port that's not used"
- Right: Immediately check `lsof`, pick an unused port (8080/8081), update docker-compose.yml, commit, push — no clarifying questions
- The user explicitly delegated the decision. Asking "what about 8080?" would be bureaucratic friction.

**Docker deployment decision (2026-05-14)**
- User said: "so, why don't we put this behind a proper web server?"
- Right: Offered Railway (simplest) and Docker+nginx (alternative), then immediately started building Docker config when user didn't object — action-first, not analysis-paralysis

## Verification checklist

Before asking for confirmation on a guarded operation:
- [ ] Did the user use the exact name of the guarded resource? ("production", "main", "drop", "delete")
- [ ] Was it a command/imperative, not a description? ("push" vs. "I see it's on staging")
- [ ] Have they already been warned about this operation in this conversation?
- [ ] If yes to all three: execute, do not ask