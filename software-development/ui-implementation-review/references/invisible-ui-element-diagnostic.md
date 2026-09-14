# Invisible UI Element Diagnostic — "User says it's not there"

When a user reports a UI element is missing after implementation, the debugging
path must start with "which component is the user actually viewing?" — NOT with
CSS positioning, token names, or z-index. This reference documents the full
diagnostic chain that prevents wasted debugging cycles.

## The diagnostic hierarchy (in order)

### Step 1: Which component is the user viewing?

**This is the #1 most common root cause and should be checked FIRST.**

When a project has a feature-flagged dual UI (Harbor vs legacy, new vs old,
mobile vs desktop), the same user-visible surface may be served by completely
different components. Adding UI to component A is invisible if the user is
viewing component B.

```bash
# Find the feature flag that gates the UI path
grep -rn "isHarborEnabled\|USE_HARBOR\|featureFlag" app/app/itineraries/page.tsx

# Trace which component the page renders on each path
grep -n "HarborItinerariesContent\|ItinerariesContent" app/app/itineraries/page.tsx

# Check if the target component is used on the user's path
grep -rn "ItineraryDetailModal" app/app/itineraries/HarborItinerariesContent.tsx
# If 0 results → the modal is NOT used in Harbor mode → UI added to it is invisible
```

**Real failure (2026-06-27):** Toggle button added to `ItineraryDetailModal.tsx`.
User was viewing `HarborItineraryDetail.tsx`. Four rounds of CSS/positioning/token
debugging were wasted before this was checked.

### Step 2: Is the CSS rule in the deployed bundle?

Tailwind arbitrary-value classes with CSS variables (`bg-[var(--bg-glass)]`)
can be silently purged from the production CSS bundle. The class is in the HTML
but no CSS rule exists — `background: unset` = transparent = invisible.

```bash
# After building locally
grep -c "bg-\[var" .next/static/css/*.css
# If 0, arbitrary-value classes were purged

# On staging, curl the deployed CSS
curl -sS "https://staging-url/_next/static/css/HASH.css" | grep "bg-glass"
# If the pre-defined utility class IS there but your arbitrary-value class is NOT,
# switch to the utility class
```

### Step 3: Is the element in the DOM?

```javascript
// browser_console
document.querySelector('button[aria-label*="3D"]')
// null → component never rendered (wrong component path, conditional gate, error)
// element → continue to step 4
```

### Step 4: Is the element visible?

```javascript
// browser_console
const el = document.querySelector('button[aria-label*="3D"]');
const cs = getComputedStyle(el);
console.log({
  display: cs.display,        // 'none' = hidden
  visibility: cs.visibility,  // 'hidden' = hidden
  opacity: cs.opacity,        // '0' = transparent
  position: cs.position,      // 'static' when it should be 'absolute'
  background: cs.background,  // 'unset' or 'transparent' = no bg (purged CSS)
  color: cs.color,            // 'unset' = no text color (purged CSS)
});
```

### Step 5: Is the element positioned correctly?

```javascript
const rect = el.getBoundingClientRect();
console.log({ top: rect.top, left: rect.left, width: rect.width, height: rect.height });
// width=0 or height=0 → CSS not applied
// top/left way outside viewport → positioning context wrong
```

## The anti-pattern: debugging CSS before checking the component path

The most expensive debugging pattern is: user says "it's not there" → agent
assumes the CSS is wrong → iterates on positioning, token names, z-index,
backdrop-filter → 4+ rounds later, discovers the UI was added to the wrong
component entirely. The user never saw the code because it was in a component
that doesn't render on their current UI path.

**The rule:** When a user says "it's not there" or "it's not visible," the first
diagnostic question is "which component is the user actually viewing?" — not
"what's wrong with the CSS?" Check the feature flag path FIRST, then CSS, then
DOM, then positioning.