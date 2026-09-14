# UI Implementation Review Checklist

Ordered checklist. Run every step — skipping one means missing a bug pattern.

## 1. Load Contracts
- [ ] Read plan document (acceptance criteria, approach, files to be touched)
- [ ] Read all feature docs for areas touched
- [ ] Read design system (theme.js, shared components)

## 2. Read Every Screen (in full, no sampling)
- [ ] New screens (read entire file)
- [ ] Modified screens (read entire file, focus on changed areas)
- [ ] Check: every API call has error handling (not just `.catch(console.error)`)
- [ ] Check: response destructuring matches API response shape
- [ ] Check: all design values from theme.js (no hardcoded colors/spacing/fonts)
- [ ] Check: empty state rendered for every list (icon + title + subtitle pattern)
- [ ] Check: LoadingState used for async loads
- [ ] Check: design tokens applied consistently (no "pax" on one screen but "guests" on another)

## 3. Read Every API Route + API Client
- [ ] Read backend routes for every endpoint the screens call
- [ ] Cross-reference: API response keys ↔ frontend destructuring
- [ ] Cross-reference: query params passed ↔ query params filtered on
- [ ] Check: active-records filter (`status='active'`, `itinerary_count > 0`) on every endpoint
- [ ] Check: API client function signatures match route definitions

## 4. Cross-Reference Against Plan
- [ ] For each acceptance criterion: verify by reading code, not trusting status
- [ ] Flag any criterion that's marked "done" but code shows it's broken
- [ ] Note any criterion that's implemented beyond what the plan requires

## 5. Navigation Audit
- [ ] Read navigation.js — every stack, every screen registration
- [ ] Verify: any screen navigated to from a tab is registered in that tab's stack
- [ ] Check: duplicate/missing options keys
- [ ] Check: header titles are meaningful (not "Destination" for every screen)

## 6. Shared Component Audit
- [ ] FavoriteButton: used on all detail screens? initialSaved passed?
- [ ] PillFilter: secondary row wired correctly? onSelect triggers re-fetch?
- [ ] Card/SectionHeader: used consistently for card sections?
- [ ] LoadingState: used on every screen with async data?

## 7. Categorize & Prioritize
- [ ] 🔴 Bugs: definitely wrong behavior (response keys, dead UI, broken filters)
- [ ] 🟡 UX: works but degraded (missing interactions, overflow, inconsistent labels, jargon)
- [ ] ⚪ Architecture: works now but won't scale (nested ScrollViews, silent errors, inconsistent API shapes)
- [ ] For each: estimate effort (minutes/hours) and user impact (high/medium/low)
