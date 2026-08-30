---
name: namethatui
version: 0.1.0
author: Hermes
description: Look up real UI element names for coding agent prompts.
metadata:
  hermes.tags:
    - UI
    - Design
    - Reference
    - macOS
    - Web
---

# NameThatUI — Visual Dictionary of UI Components

NameThatUI (https://namethatui.com/) is a visual reference that maps UI elements to their real framework-specific names. It covers 54 components: 31 macOS (AppKit/SwiftUI) and 23 Web (HTML/ARIA/shadcn/Radix). Each entry includes a live interactive demo, anatomy labels, a ready-to-paste agent prompt, and a framework code-reference table. Use it when you need the precise name of a UI element to communicate accurately with coding agents or in design specs.

## When to Use

- You're building a UI component and need its real name for the target framework
- You're writing a prompt for a coding agent and want to specify the exact component
- A user describes a UI element in plain English ("the dark see-through layer behind a popup") and you need to identify it
- You need to translate between AppKit and SwiftUI names for the same Mac element
- You need to distinguish similar components (badge vs chip vs pill vs tag; popover vs dropdown vs tooltip)
- You're writing design specs or documentation and need correct terminology

## Prerequisites

- No dependencies. The site is a public webpage at https://namethatui.com/
- Use `browser_navigate` to access it (not `web_extract` — the site relies on JavaScript for interactivity)

## How to Run

1. **Browse the catalog**: Navigate to `https://namethatui.com/` — the homepage shows all 54 components as interactive cards with live demos. Filter by platform with the "macOS" or "Web" buttons.
2. **Reverse lookup (describe → name)**: Click "Describe the thing…" (or press ⌘K) to open the search dialog. Type a plain-English description of what you see. The site suggests matching components.
3. **Read a component page**: Click any card to open its detail page (e.g., `/web/command-palette`). Each page has: live demo, anatomy labels, agent-ready prompt, framework code table, and "See also" cross-references.
4. **Check the translation table**: Navigate to `https://namethatui.com/translate` for a searchable table mapping 60+ plain-English UI terms to AppKit and SwiftUI equivalents. See `references/translation-table.md` in this skill for the full table.
5. **Framework decision guides**: `/appkit-vs-swiftui` explains which name to use in prompts. `/swift-vs-electron` covers native vs web shell.

## Quick Reference

### Component Catalog (54 total)

**macOS (31):**

| Name | Framework Ref | Description |
|------|--------------|-------------|
| Menu Bar | `NSApp.mainMenu` | The strip along the top of the Mac screen |
| Context Menu | `NSMenu` | Menu opened at the pointer by right-clicking |
| Disclosure Triangle | `NSOutlineView` | Small rotating control that reveals/hides nested content |
| Dock Badge | `NSDockTile.badgeLabel` | Red count or status label on an app's Dock icon |
| Focus Ring | `NSView.focusRingType` | Accent-colored glow identifying the focused control |
| Inspector | `View.inspector(isPresented:content:)` | Right-hand panel for editing current selection |
| Menu Bar Extra | `NSStatusItem` | Icon on the right side of the macOS menu bar |
| Panel (Floating Window/HUD) | `NSPanel` | Auxiliary window floating above document windows |
| Popover | `NSPopover` | Floating bubble whose arrow points to the opening control |
| Pop-Up vs Pull-Down vs Combo Box | `NSPopUpButton` | Three similar macOS controls for choosing a value |
| Segmented Control | `NSSegmentedControl` | Row of connected choices, one visibly selected |
| Sheet | `NSWindow.beginSheet` | Modal dialog attached to a window's title bar |
| Sidebar (Source List) | `NSSplitView` | Left-hand navigation panel |
| Stepper | `NSStepper` | Compact up/down arrow pair for incrementing values |
| Toolbar (Unified Title Bar) | `NSToolbar` | Row of window actions in the modern title bar |
| Traffic Lights | `NSWindow.standardWindowButton(_:)` | Red, yellow, green controls at top-left of a window |
| Visual Effect Material | `NSVisualEffectView` | Frosted material where wallpaper bleeds through |
| Mac Window | `NSWindow` | The movable Mac app frame |
| Split View | `NSSplitView` | Two or more panes divided by a draggable divider |
| Scroll View (Scroller) | `NSScrollView` | Viewport with AppKit scrollbar (called a "scroller") |
| Search Field | `NSSearchField` | Text input with magnifying glass and clear button |
| Save Panel | `NSSavePanel` | Standard dialog for naming a file and choosing location |
| Token Field | `NSTokenField` | Text input that turns values into removable rounded tokens |
| Combo Button | `NSComboButton` | Primary action joined to a separate arrow for related actions |
| Level Indicator | `NSLevelIndicator` | Gauge as capacity bar, rating stars, or relevance meter |
| Column View (Browser) | `NSBrowser` | Finder-style columns revealing successive hierarchy levels |
| Outline View | `NSOutlineView` | Hierarchical list with expandable/collapsible rows |
| Pointer (Cursor) | `NSCursor` | Every shape the mouse pointer takes |
| Alert | `NSAlert` | Modal warning dialog with buttons |
| Slider | `NSSlider` | Round knob dragged along a track to pick a value |
| Color Well | `NSColorWell` | Swatch button showing current color, opens picker |

**Web (23):**

| Name | Framework Ref | Description |
|------|--------------|-------------|
| Three Dots (Overflow Menu) | — | The ⋯ button that opens a menu of secondary actions |
| Drag & Drop | — | Visual feedback for dragging items between drop zones |
| Divider vs Separator vs Rule | `<hr>` | Thin line marking topic break, separating controls, or decoration |
| Progress Ring vs Spinner vs Bar | `<progress>` | Spinner = wait; ring or bar = shows progress amount |
| Toast (Snackbar) | `role="status"` | Brief non-blocking message after an action |
| Modal Dialog vs Drawer vs Sheet | — | Overlays that block some or all of the page |
| Popover vs Dropdown vs Tooltip | — | Three anchored overlays with different triggers and content |
| Scrim (Backdrop/Overlay) | `::backdrop` | Translucent layer behind a modal or popup |
| Skeleton vs Spinner | — | Skeleton = placeholder for loading content; spinner = generic wait |
| Combobox (Autocomplete/Typeahead) | `role="combobox"` | Text input paired with a filtered suggestion list |
| Command Palette | `role="dialog"` | Keyboard-first overlay searching actions, ⌘K |
| Accordion (Disclosure) | — | Collapsible sections that expand/collapse content |
| Tabs | — | Row of labels switching between content panels |
| Badge vs Chip vs Pill vs Tag | — | Compact labels distinguished by meaning and interactivity |
| Breadcrumbs | `<nav>` | Hierarchy trail from current page to ancestors |
| Sticky vs Fixed Positioning | — | Element stays visible during scroll (sticky) or pinned (fixed) |
| Focus Ring (`:focus-visible`) | `:focus-visible` | Outline showing keyboard-focused element |
| Empty State | `<section>` | Purposeful guidance shown when a view has no content |
| Hover Card | — | Floating preview appearing on hover over a trigger |
| Switch vs Checkbox vs Radio | `<input>` | On/off toggle, independent choices, or one-from-group |
| Toggle Group (Segmented Control) | — | Connected button group for single or multiple selection |
| Form Field | `<label for>` | Label + input with help text and validation |
| Truncation (Ellipsis & Line Clamp) | `text-overflow` | CSS for cutting text with visual ellipsis |

### Detail Page Structure

Every component detail page follows this structure:
1. **Live interactive demo** — a working example you can click/interact with
2. **Title + framework reference** — e.g., `/ Command · role="dialog" /`
3. **Also called** — alternative names (e.g., "command menu, quick actions, launcher")
4. **Description** — what it is, how it works, and how it differs from similar components
5. **ANATOMY — EVERY PART, NAMED** — numbered annotations on the demo, each with a "Copy prompt" button
6. **PROMPT — PASTE INTO YOUR AGENT** — ready-to-paste description for coding agents
7. **IN CODE** — table mapping the component to exact names in each framework
8. **SEE ALSO** — cross-references to related components (often cross-platform)

## Procedure

### 1. Identify a component by description

```
browser_navigate → https://namethatui.com/
browser_click → "Describe the thing… ⌘ K" button
browser_type → plain-English description into the search combobox
browser_snapshot → read suggestions (name, framework ref, description, platform tag)
browser_press → Enter on the matching result to open its detail page
```

### 2. Get the agent-ready prompt for a component

```
browser_navigate → https://namethatui.com/{platform}/{component-slug}
browser_snapshot full=true → capture the full page content
```

The "PROMPT — PASTE INTO YOUR AGENT" section contains a ready-to-use paragraph. The "IN CODE" table lists the exact framework identifier (shadcn/ui, ARIA, Radix, AppKit, SwiftUI, HTML).

### 3. Translate between AppKit and SwiftUI

Navigate to `https://namethatui.com/translate` or consult `references/translation-table.md` in this skill — it contains all 60+ entries mapping plain English → AppKit → SwiftUI.

### 4. Extract all component data programmatically

From any page, use `browser_console` with a JavaScript expression to extract structured data:

```javascript
// On the homepage: extract all component cards
(() => {
  const links = document.querySelectorAll('main a');
  return Array.from(links).map(l => {
    const h3 = l.querySelector('h3');
    const ps = l.querySelectorAll('p');
    return {
      name: h3?.textContent?.trim(),
      framework: ps[0]?.textContent?.trim(),
      description: ps[1]?.textContent?.trim(),
      href: l.getAttribute('href')
    };
  }).filter(c => c.name);
})()
```

```javascript
// On a detail page: extract all paragraphs (description + prompt + anatomy)
(() => {
  const art = document.querySelector('article');
  return Array.from(art.querySelectorAll('p')).map(p => p.textContent.trim());
})()
```

```javascript
// On a detail page: extract the IN CODE framework table
(() => {
  const rows = document.querySelectorAll('article table tr');
  return Array.from(rows).map(r => 
    Array.from(r.querySelectorAll('td')).map(c => c.textContent.trim())
  );
})()
```

## Pitfalls

- **Don't use `web_extract`** — the site is a JavaScript SPA. Use `browser_navigate` + `browser_snapshot` or `browser_console` for data extraction.
- **Framework refs in the homepage cards can be noisy** — the card's first `<p>` sometimes captures demo text rather than the framework reference. Use the detail page's "IN CODE" table for authoritative framework names.
- **The search is fuzzy, not exact** — typing "the small x button to close a tab" won't find a "close button" because the site doesn't have one. It matches against component names, descriptions, and alternative names.
- **Slug pattern**: macOS components are at `/macos/{slug}`, Web components at `/web/{slug}`, guides at `/{slug}` (e.g., `/translate`, `/appkit-vs-swiftui`).
- **The translation table** is the most complete reference for macOS — 60+ entries vs 31 detail pages. Use it for anything not covered by a standalone component page.

## Verification

Navigate to any component detail page and confirm the "PROMPT" section and "IN CODE" table are present:

```
browser_navigate → https://namethatui.com/web/command-palette
browser_snapshot full=true
```

The snapshot should contain headings: "ANATOMY — EVERY PART, NAMED", "PROMPT — PASTE INTO YOUR AGENT", "IN CODE", and "SEE ALSO".