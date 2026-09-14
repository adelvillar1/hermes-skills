# Surface Checklist Library (checklist.design distilled)

Source: https://www.checklist.design — 110 design checklists across mobile app / web app / website / design system / flows.
Each checklist = 5–8 items, each item = title + one-line definition + "why it matters" tip.
URL pattern: `/mobile/{surface}`, `/web-app/{surface}`, `/website/{surface}`, `/design-system/{surface}`, `/flows/{surface}`.

Use: when auditing a feature, pull the matching checklist(s), audit item-by-item, cite the checklist URL in any 🟡/🔴 finding.

## Mobile Paywall (`/mobile/paywall`) — 6 items
1. **Locked feature context and breakdown** — clear statement/list of which specific feature/s the user is blocked from. Be specific: "Unlock unlimited projects" or "Access full library", not "Go premium".
2. **Upgrade CTA** — primary action to start subscription or free trial, prominent.
3. **Free trial offer** — clear trial statement. Tip: "Try free for 7 days" framed as low-commitment is consistently one of the highest-converting messages on a paywall.
4. **Dismiss action** — clear, neutral way to close and return to free experience. Must be obvious and accessible.
5. **Restore purchases** — way for existing subscribers to recover access after reinstall/sign-in on a new device.
6. **No guilt language** — dismiss/decline in neutral language. "'No thanks, I don't want to save money' is manipulative and unnecessary."

## Mobile Onboarding (`/mobile/onboarding`) — 7 items
1. **Steps** — limited to what is genuinely required before the app can be used. "Steps that can be deferred without preventing the app from functioning on day one consistently belong later, not in onboarding."
2. **Progress indicator** — how many steps remain + where the user is. "Users who can see the end of onboarding are significantly less likely to abandon it than those who feel they are in a tunnel."
3. **Step navigation** — next button or horizontal swipe.
4. **Contextual permissions** — surfaced at the contextually relevant moment, NOT grouped at the start. "Grouping all permission requests at the beginning can lead to denials given lack of context."
5. **Skip option** — visible way to exit early and explore; setup available later. "Users who skip and explore freely often complete setup voluntarily once they understand the value."
6. **Personalisation step** — one or two choices that make the app feel tailored (name, interests, key product-relevant info).
7. **Keyboard handling** — views adjust when keyboard appears, appropriate keyboard types per field, Next advances to following input.

## Web App Empty State (`/web-app/empty-state`) — 6 items
1. **Illustration or icon** — signals the empty state, gives personality. "Visual should be contextual e.g. empty inbox and a deleted account shouldn't be the same."
2. **Clear heading** — short, plain-language title naming what's missing. "'It's empty' isn't helpful while 'No projects yet' is clear."
3. **Supporting description** — brief explanation of what belongs in this space, most useful for first-time users.
4. **Primary action** — CTA toward the next step (create, import, connect). "It should create the first item, not just link somewhere generic."
5. **Zero state vs. no-results state** — distinction between empty-because-nothing-created vs empty-because-search/filter returned nothing. "A no-results state without a way to reset or broaden the search is a dead end — always provide an escape route."
6. **Error state variant** — separate variant for content that FAILED to load vs genuinely empty. "Showing an empty state when the real issue is a loading error causes users to assume they have lost their data."

## Web App Pricing (`/web-app/pricing`) — 7 items
1. **Plan names, prices and frequency** — name + cost of each plan, billing frequency clearly stated.
2. **Billing period toggle** — monthly/annual switch, annual discount shown if applicable.
3. **Feature comparison (if price options)** — side-by-side of what each plan includes/excludes.
4. **Call to action** — button per plan: start trial, subscribe, or contact sales.
5. **Free tier or trial details** — what's included, how long, what happens when it ends. "State clearly whether the account downgrades or charges automatically once the trial ends."
6. **FAQ section** — billing, plan limits, cancellation, payment.
7. **Enterprise option** — prompt for orgs needing custom arrangement beyond standard plans.

## Mobile Login (`/mobile/login`) — 8 items
1. **Social sign-in** — Apple or Google, bypassing manual entry. "On iOS, Apple Sign In is required by App Store guidelines if any other social provider is offered."
2. **Email field** — input for account email.
3. **Password field** — masked input with reveal option.
4. **Biometric authentication** — Face ID / fingerprint for returning users. "Encouraged to suggest after initial login so it's a faster experience in the future."
5. **Credential autofill** — system-level prefill. "textContentType on iOS and autoComplete on Android are the attributes that trigger native autofill."
6. **Forgot password link** — leading into the reset flow.
7. **Error states** — distinguish unrecognised email vs incorrect password. "Generic 'incorrect credentials' gives users no useful signal — knowing whether the email or password is wrong helps them recover without guessing."
8. **Passwordless sign-in (magic link)** — one-time link to email. "Useful for infrequent-use apps where remembering a password between sessions is difficult."

## Other surfaces on the site (checklist titles — pull the page for items)
- Mobile: action-sheet, account, cart, search, splash-screen, in-app-browser, invite, billing
- Web app: admin-panel, billing, onboarding, settings, notifications, login, 2FA
- Website: features, blog-post, contact-us, pricing, 404, team, careers, FAQ, legal-privacy, compare-page, cart
- Design system: typography, tokens, accordion, banner, radio, tooltip, modal, input-field, button, toggle, toast, card, badge
- Flows: adding-to-cart, uploading-media, canceling-subscription, filtering-items, resetting-password, submitting-a-form, contacting-support, making-a-payment, verifying-account

## Method notes
- Check the Related checklists on each page — they flag adjacent surfaces the feature likely also touches (login → resetting-password → 2FA → verify-account).
- Cross-platform variants differ meaningfully (mobile paywall: restore-purchases; web pricing: billing-period toggle). Pull the variant matching the platform under audit.
- The site also offers: AI-powered review via a Figma plugin, and one-click export of any checklist to Confluence / Notion / Linear / GitHub / Jira / Google Docs / Asana / ClickUp / Trello / Slack ("Copy as plain text" or per-tool copy).
- These items are the floor, not the ceiling — project-specific pitfalls (ui-implementation-review sections 1–43) still apply.
