---
name: audience-portal-build
description: Add a role-facing portal (member/customer) to an admin app.
---

# Audience portal build

Add a **new audience-facing surface** (member portal, customer dashboard, partner area) to an app that already has an admin dashboard, auth, and an API client. The audience portal reuses the session/auth and brand but is a distinct, guarded surface.

## Trigger

User asks to build a member/customer/partner portal, self-registration page, role-based login redirect, or a per-role route guard on top of an existing admin app. Also: "add a <role> view" where a dashboard already exists for another role. **Also: "add a login option visible on the landing page" / "make login discoverable" / "members can't find where to sign in"** — surfacing existing auth entry points on the public marketing site (see "Surfacing auth entry points on the public site" below).

Known-good code for the patterns below (cookie-backed photo modal, scoped brand stylesheet, audience API types + `register()`, audience route guard) is in `references/portal-code-patterns.md`.

## The shape of the work

A portal build is a coordinated set of small changes across the auth/API layer plus one or two new pages. Touch files in this order so each layer compiles as you go:

1. **API client** — add the audience-scoped response types and endpoint methods. The audience's view of a resource is usually a *different shape* than the admin's (see below).
2. **Auth context** — store any extra session payload (e.g. the `member` record), add a `register()`/signup method, and make `login()` return the authenticated user so callers can redirect by role.
3. **Route guard** — add an audience guard alongside the existing admin guard.
4. **Router** — wire the new routes.
5. **Login page** — redirect by role; add a link to the audience signup.
6. **New pages + scoped stylesheet** — the actual portal UI, matching the existing brand.

## Surfacing auth entry points on the public site

A portal is useless if nobody can find it. When the `/login` and `/register` routes exist but aren't linked from the public landing page, the fix is a coordinated set of small changes to the marketing page — not a new route. Four places, in priority order:

1. **Desktop nav** — an auth-aware entry. Use the auth context to pick the target and label: signed-out → `Member Login` → `/login`; signed-in member → `My Portal` → `/portal`; signed-in admin → `Admin` → `/admin`. Compute it once:
   ```tsx
   const { user } = useAuth()
   const authLink = user
     ? { to: user.role === 'admin' ? '/admin' : '/portal',
         label: user.role === 'admin' ? 'Admin' : 'My Portal' }
     : { to: '/login', label: 'Member Login' }
   ```
   Style it as a ghost/outlined button so it's distinct from plain text links and from the primary solid CTA.
2. **Mobile menu** — check whether the burger button is actually wired up. On marketing pages ported from a static prototype the burger is often a dead button (no handler) with the nav hidden by `display:none` under the mobile breakpoint — meaning mobile visitors have *zero* path to login. Wire it: `onClick` toggles state, `aria-expanded` + `aria-label` flip, and a dropdown panel renders the same links (including the auth entry).
3. **The signup/join CTA** — audit where the "Join" button points. A common latent bug: it links to an admin route (e.g. `/club` → redirects to `/admin` → bounces to `/login`), a broken funnel. Point it at `/register` and put a `Member Login` ghost button beside it.
4. **Footer** — a "Members"/"Wine Club" column with Member Login, Join, and an in-page anchor.

Then verify in a real browser (not just a snapshot): the nav button renders and is visually distinct, clicking it lands on the working login page, the burger toggles (`aria-expanded` flips and the panel appears with the `/login` link), and the join/login CTAs point at the right routes.

## Adding self-service features to an existing portal

Extending an already-built portal (self-cancel buttons, contextual status messages, profile tab) is a different shape than building one: the scaffolding exists, so the work is grounding + wiring.

1. **Read the plan doc first.** Feature additions usually trace to a gap-audit plan (`docs/plans/YYYY-MM-DD-*.md`) with exact acceptance criteria and a files-to-touch list. Match its wording in UI copy (e.g. "Your August allotment is ready — pick it up at the restaurant").
2. **Backend-first grounding.** Before writing self-service UI, read the backend routes. The endpoints usually already exist, and the server encodes gating rules (which statuses are cancellable, ownership scoping). Mirror those rules in UI *visibility*: only render the action when the server would accept it (hide cancel for `seated`/`cancelled`/`no_show` reservations or past/completed events) so you never surface a button that always fails.
3. **Grep the API client before adding methods.** In multi-agent builds a sibling may have already added the endpoint methods to the shared client — reuse them rather than duplicating.
4. **Confirm → busy → retry → inline error.** For destructive self-service: `window.confirm` first, track a `busyId` per row so only that button disables/spins, call `retry()` (refetch) on success, and show a `role="alert"` inline error on failure instead of swallowing it.
5. **Refresh the auth context after self-edit.** After a self-update PATCH (e.g. `/members/me`), call the auth context's `refresh()` before closing the form — otherwise the portal header keeps showing the stale member name.
6. **Hooks at the top, always.** Don't call context-reading helper hooks inside map/conditional JSX; destructure everything a component needs from the context hook in one place (caught fast by LSP diagnostics). While wiring a new panel, TS 6133 "declared but never read" on fresh imports is expected noise that clears as the panel gets added.
7. **Read conditional copy out loud.** Singular/plural ternaries easily drop a verb ("Your August allotment is ready" vs. the broken "Your August ready"). Self-review generated copy before declaring done.

Concrete code for all seven (self-cancel buttons, pickup-ready callout, profile tab with self-edit) is in `references/portal-code-patterns.md` §5.

## Pitfalls

- **Audience response shapes differ from admin shapes.** The same table returned to the member vs. the admin usually omits other users' names and exposes raw paths instead of computed flags. Define *separate* types for the audience view (e.g. `MemberDelivery` with `proofPhotoPath` and no `hasPhoto`, vs. admin `Delivery` with `hasPhoto` + `memberName`) rather than reusing the admin type. Compute derived flags client-side from the raw path (`hasPhoto = !!row.proofPhotoPath`).
- **Self-registration is an auth endpoint, not a members endpoint.** `POST /auth/register` returns the new session's user + record and sets the cookie — so the auth context can auto-log-in from the response. Don't create the member separately and then log in.
- **`login()` must return the user for role-based redirect.** If it currently returns `void`, change the signature to return the authenticated user (check there are no other callers first). The login page then does `navigate(user.role === 'admin' ? '/admin' : '/portal')`.
- **The audience guard redirects admins away.** Admins use the dashboard, not the portal — the audience guard should send `role === 'admin'` to the admin route, not show them the portal. Anonymous → login.
- **Match the existing brand with a scoped stylesheet, don't invent one.** If the app already has a scoped brand CSS (e.g. `.pampa-home { --crimson: …; --serif: 'Playfair Display'… }`), create a sibling file scoped under a new root class (`.pampa-portal`) that re-declares the *same* token block. Copy the palette, fonts, grain/glow effects, and button styles so the portal feels like the same product. Keep every rule prefixed with the scope class so nothing leaks.
- **Don't use arbitrary-value Tailwind for brand tokens.** In a scoped-stylesheet design system, `text-[var(--gold)]` / `align-[-2px]` break the convention. Put icon sizing/color/alignment in the scoped CSS instead (e.g. `.pampa-portal .type-tile b svg { width:15px; color:var(--gold); }`).
- **Proof/attachment photos sit behind the HttpOnly session cookie.** A plain `<img src>` won't carry credentials. Fetch the blob with `credentials:'include'`, mint a `URL.createObjectURL`, render that, and revoke it on close/unmount.

## Verification

- Run the project's real build (`tsc -b && vite build` or equivalent) and lint; report actual output.
- **Attribute lint/test failures before fixing them.** If a linter flags an error in a file you modified, prove whether your change caused it: `git stash push -- <file>`, re-run the check on the pristine file, `git stash pop`. If the pristine file fails the same rule it's pre-existing — report it, don't "fix" unrelated code.
- Re-read/grep the new files on disk to confirm the content actually landed (guards against silent write failures).
- Confirm `git status` shows only the intended files; no stray lockfile/tsbuildinfo/dist artifacts.

## No-commit delegated builds

When the task says "do NOT commit / leave changes uncommitted for review":
- Touch **only** the files the task enumerates. Leave pre-existing unrelated modifications (other phases' backend work, design assets, plan docs) untouched.
- Do **not** `git add` or `git commit`.
- In the report: list exactly which files changed vs. which were pre-existing, give real build/lint output, and call out any signature/behavior deviation (e.g. "`login()` now returns the user — no other callers existed").
