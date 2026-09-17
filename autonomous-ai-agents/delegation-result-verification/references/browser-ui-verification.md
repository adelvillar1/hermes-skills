# Browser-Based UI Verification for Frontend Subagent Work

When a subagent builds or rewrites frontend UI (React pages, admin dashboards,
forms), curl smoke tests only prove the SPA fallback works — they don't prove
the UI renders, forms submit, or state updates. Use browser automation tools
for a real verification pass.

## When to use

- Subagent rewrote a page component (admin dashboard, login, public landing)
- Subagent added new interactive flows (forms, dialogs, tab navigation)
- Subagent claims "browser: login page renders, dashboard loads with live data"
  (verify this claim yourself — Pitfall 7 hallucination applies to UI claims too)

## Verification flow (5-10 minutes)

```
# 1. Navigate to the entry page
browser_navigate(url="http://localhost:3000/login")

# 2. Snapshot the accessibility tree — confirm key elements exist
browser_snapshot(full=false)
# Look for: form fields, buttons, headings, navigation elements
# Verify: no error boundaries, no blank page, correct title

# 3. Exercise the primary flow (e.g. login)
browser_type(ref="@e7", text="test@test.com")    # email field
browser_type(ref="@e8", text="testpass123")       # password field
browser_click(ref="@e9")                          # submit button

# 4. Verify navigation happened
browser_snapshot(full=false)
# Expected: redirected to /admin, dashboard tabs visible

# 5. Check rendered data (full snapshot)
browser_snapshot(full=true)
# Verify: stats cards show numbers, tables have headers, empty states render

# 6. Test a mutation through the UI
browser_click(ref="@e17")    # "New member" button
browser_snapshot(full=false) # dialog appeared?
browser_type(ref="@e7", text="Test Member")
browser_click(ref="@e4")     # submit
browser_snapshot(full=false)
# Verify: table updated, count changed ("1 active members"), toast appeared

# 7. Check console for JS errors
browser_console()
# Look for: uncaught exceptions, failed fetch calls, React errors
```

## What to check

| Check | How | Failure looks like |
|-------|-----|--------------------|
| Page renders | browser_snapshot has expected elements | Empty snapshot, error boundary |
| Auth flow works | Login → redirect to protected page | Stays on /login, 401 in console |
| Route guard works | Navigate to /admin without login | Should redirect to /login |
| Data loads from API | Full snapshot shows real data (or correct empty state) | "Loading..." forever, "undefined" |
| Mutations work | Create via dialog → table updates | Dialog closes but table unchanged |
| No console errors | browser_console() | Uncaught TypeError, failed fetch |
| Tabs/navigation | Click each tab → content changes | Tab clicks do nothing |

## Pitfalls & techniques

### Overlays (Sheet/Dialog/Drawer) have their own scroll container — page scroll won't move them

Radix `Sheet`/`Dialog` and similar overlay components render a **portaled panel with its
own internal scrollable region**. `browser_scroll` scrolls the *page*, which does nothing
to the overlay's content — the screenshot looks unchanged and you can't reach sections
below the fold.

**Fix — scroll the overlay's own scrollable element via `browser_console`:**

```javascript
// Find scrollable elements INSIDE the dialog and scroll the largest one
const scrollables = [...document.querySelectorAll('*')].filter(el => {
  const s = getComputedStyle(el);
  return (s.overflowY === 'auto' || s.overflowY === 'scroll')
    && el.scrollHeight > el.clientHeight + 20;
});
const target = scrollables.sort((a, b) => b.scrollHeight - a.scrollHeight)[0];
target.scrollTop = target.scrollHeight;  // jump to bottom
```

**To enumerate an overlay's sections without scrolling through screenshots** (faster and
more reliable than repeated vision checks), query the dialog's headings directly:

```javascript
JSON.stringify([...document.querySelectorAll('[role="dialog"] section')].map(s => {
  const h = s.querySelector('h3,h2,div');
  return h ? h.textContent.trim().slice(0, 30) : '';
}));
// → e.g. ["Save notes","Orders1","Tastings1","Deliveries1","Reservations0"]
```

This confirms every section rendered and shows per-section counts in one call.

### Static screenshots can't reveal hover affordances — trust the accessibility tree, not vision, for interactivity

`browser_vision` on a static screenshot will report a clickable element as "not clickable"
or "styled as plain text" when the affordance is hover-only (e.g. a `<button>` with
`hover:text-primary` and no underline). This is a **false negative** — vision sees one
frame with no hover state.

**The accessibility snapshot is the source of truth for interactivity.** `browser_snapshot`
shows the real element role:

```
- cell "E2E Test Member" [ref=e29]
  - button "E2E Test Member" [ref=e66]   ← IS a button, despite vision saying otherwise
```

**Rule:** if vision says "doesn't look clickable" but the snapshot shows a `button`/`link`
role, the element is interactive — vision just can't see the hover state. Don't file it as
a bug. Conversely, if you need to *prove* a hover affordance, apply the hover via
`browser_console` (`el.dispatchEvent(new MouseEvent('mouseover'))`) and screenshot, or
verify the class (`hover:text-primary`) in the source.

## Tips

- Use `browser_snapshot(full=false)` for interactive elements (compact, shows refs)
- Use `browser_snapshot(full=true)` for verifying rendered data content
- Use `browser_vision` when layout/visual correctness matters (dark theme, spacing)
- The test server must be running (background process) with a seeded DB
- After browser verification, kill the test server and Docker container
- If the subagent claimed "browser verified" but you can't reproduce it, the
  claim may be hallucinated (Pitfall 7) — trust your own browser session
