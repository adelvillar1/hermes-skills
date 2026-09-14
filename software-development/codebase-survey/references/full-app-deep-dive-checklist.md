# Full App Deep Dive — Comprehensive Domain Survey Checklist

Use when the user asks for a "deep dive of the app" without naming a specific domain — they want the full picture of what the application does, its major features, data flows, and architecture.

## Precondition
- [ ] CLAUDE.md read (project memory, hard rules, today's state)
- [ ] CLAUDE.local.md — **only read with explicit user approval in the current turn** (ask before reading)
- [ ] Latest 1-3 recaps read (last session context)
- [ ] Active plans identified and read

## Step 1: Schema Audit
- [ ] Read the full Prisma schema (or equivalent ORM/schema file)
- [ ] For each model, note: purpose, key fields, relations, indexes, soft-delete status
- [ ] Group models by domain: auth, core business, payments, CRM, AI pipeline, admin, operational
- [ ] Identify the central entity (usually `Booking` or equivalent) and how everything orbits it
- [ ] Note multi-tenancy fields (`agency_id`, `organization_id`, etc.)
- [ ] Note audit tables (no soft delete) vs business tables (soft delete)

## Step 2: Route Inventory
- [ ] List all API routes: `find src/app/api -type f | sort`
- [ ] Count total routes
- [ ] Group by domain/feature area
- [ ] For each major domain, read the main CRUD route
- [ ] Note auth guards, role restrictions, feature-flag gates
- [ ] Note any special routes: extract, import, upload, reprocess, reports, webhooks

## Step 3: Page Inventory
- [ ] List all dashboard pages: `find src/app/(dashboard) -type f | sort`
- [ ] Group by domain/feature area
- [ ] For each major domain, read the list page
- [ ] Note: filters, bulk actions, mobile/desktop split, CSV export, pagination
- [ ] Note shared layout components (sidebar, header, navigation)

## Step 4: Key Feature Deep Dives (Lightweight)
For each major feature area, do a condensed version of the targeted deep dive:

### Per feature:
- [ ] Read the feature doc if it exists (`docs/feature-<slug>.md`)
- [ ] Read the main API route(s) for that feature
- [ ] Read the page component(s)
- [ ] Note the data flow: input → processing → persistence → display
- [ ] Note any special patterns: AI extraction, file upload, batch import, matching algorithms
- [ ] Note dormant/hidden features (UI buttons hidden, endpoints not wired)

### Typical feature areas to cover:
- [ ] AI extraction / document processing
- [ ] Core CRUD (bookings, orders, transactions)
- [ ] Financial (commissions, payments, payroll)
- [ ] CRM (customers, contacts, communication)
- [ ] Reporting / analytics
- [ ] Admin / user management
- [ ] Settings / configuration

## Step 5: Shared Infrastructure
- [ ] Auth system (`src/lib/auth.ts` or equivalent): strategy, session/JWT, refresh tokens
- [ ] Database client (`src/lib/prisma.ts` or equivalent): extensions, soft delete middleware
- [ ] Multi-tenancy helper (`src/lib/agency-scope.ts` or equivalent): how isolation works
- [ ] AI pipeline (`src/lib/ai/` or equivalent): clients, extractors, prompt patterns
- [ ] Validation layer (`src/lib/validations/` or equivalent): schemas, type safety
- [ ] Shared UI components: sidebar, tables, forms, modals, cards

## Step 6: Testing & Deployment
- [ ] List test files: `find tests -type f | sort` or equivalent
- [ ] Note test count, frameworks (Vitest, Jest, Playwright, etc.)
- [ ] Read Dockerfile if present
- [ ] Note deployment platform, branch → environment mapping
- [ ] Note CI/CD config if present

## Step 7: Synthesize Report

### Structure:
1. **Overview** — what the app does, target users, production URL
2. **Tech stack** — concise bullet list (framework, ORM, auth, UI library, AI provider, hosting)
3. **Architecture** — multi-tenancy, auth flow, soft deletes, role hierarchy
4. **Database** — model count, central entities, notable patterns
5. **API surface** — total route count, grouped by domain
6. **Key features** — for each major feature: what it does, how it works, special patterns
7. **Frontend** — route groups, shared components, responsive patterns
8. **Shared infrastructure** — AI pipeline, extraction patterns, matching algorithms
9. **Testing** — unit + E2E coverage, frameworks
10. **Deployment** — environments, branch flow, auto-deploy
11. **Current state** — what's shipped, what's deferred, recent activity
12. **Notable patterns** — idioms that show up repeatedly across the codebase

### Quality checks:
- [ ] Report is readable in 3-5 minutes (not a raw file dump)
- [ ] Every major domain is covered (no missing feature areas)
- [ ] Data flows are traceable from input to persistence to display
- [ ] Contradictions between docs and implementation are surfaced explicitly
- [ ] Dormant/hidden features are documented
- [ ] File counts and scale metrics are included

## Key Difference from Targeted Deep Dive

| Aspect | Targeted deep dive | Full app deep dive |
|--------|-------------------|-------------------|
| Scope | One domain/feature | All domains |
| Depth | Full (every file in domain) | Moderate (key files per domain) |
| Reading pattern | Every route, lib, UI file | Representative files per domain |
| Output | Domain architecture + data flow | App-wide capabilities + architecture |
| Time | 15-25 min | 25-40 min |
| Use case | "How does booking import work?" | "What does this app do?" |

## Key Difference from Full Codebase Survey

| Aspect | Full codebase survey | Full app deep dive |
|--------|---------------------|-------------------|
| Focus | Structure, maintainability, maturity | Features, data flows, capabilities |
| Output | File counts, grades, refactor targets | What the app does and how |
| Tests | Run test suite, count coverage | Note frameworks and coverage |
| Git history | Analyze commit patterns | Note recent activity |
| Use case | "Can I work with this?" | "What are we building?" |
