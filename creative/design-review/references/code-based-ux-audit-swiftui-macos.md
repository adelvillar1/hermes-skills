# Code-Based UX Audit — SwiftUI macOS Apps

SwiftUI macOS app-specific checklist for auditing UI quality from source code when the app isn't running.

## What to Read (in order)

1. **DesignTokens.swift (or equivalent)** — the token file. This is the source of truth for visual language. Check: Are spacing values consistent (4pt grid)? Are corner radii systematized (4/6/10/12)? Are colors semantic (textPrimary, bgCard) or hardcoded (Color.red, Color.gray)? Are typography scales defined (7+ levels)?

2. **Every `.swift` in `Sources/ScribeApp/`** — focus on:
   - **Layout:** `ScrollView` vs `List` vs `LazyVStack` — are long lists virtualized?
   - **State containers:** `@State`, `@StateObject`, `@EnvironmentObject` — are they synced correctly?
   - **Empty states:** `ContentUnavailableView` everywhere? Is there a custom `EmptyStateView`?
   - **Interaction:** `onTapGesture(count: 2)` — are double-tap actions discoverable (hover hints, tooltips)?
   - **Toolbars:** Does `MeetingDetailView` use `.toolbar { ... }` for actions?
   - **Sheets:** Is export implemented as `.sheet(isPresented:)` or a full window?

3. **Card/reusable component files** — `Card.swift`, `StatusBadge.swift`, etc. Check: Are view modifiers extracted (`.cardStyle()`, `.statusBadge()`) or is the same pattern copy-pasted?

4. **Navigation structure** — `NavigationStack`, `NavigationSplitView`, `MenuBarExtra`. How deep is the stack? Is there a way back from every detail?

## Code-Level UX Signals (SwiftUI-specific)

| Signal | Check | Why It Matters |
|--------|-------|---------------|
| **Hardcoded colors** | `grep -rn "Color(\(red\|green\|blue\)" Sources/` | Colors should reference DesignTokens, not raw values |
| **Magic spacing** | `grep -rn "\.padding(\d\+)" Sources/` | Should use `.padding(Token.spaceX)` for consistency |
| **Magic corner radii** | `grep -rn "cornerRadius: \d\+" Sources/` | Should use `Token.radiusSmall/Medium/Large` |
| **ScrollView + ForEach** | `grep -B1 -A1 "ScrollView" Sources/ --include="*.swift"` | If content is long, use `LazyVStack` inside `ScrollView` — not bare `ForEach` |
| **Missing hover states** | Any tappable row without `.onHover` or hover background | macOS users expect hover feedback |
| **No-op modifiers** | `func highlight() -> some View { .opacity(1.0) }` | Search/filter UI that appears to work but doesn't is worse than none |
| **Missing keyboard shortcuts** | Only one shortcut in `GlobalHotkeyManager` | Mac apps should have ⌘⇧S (search), ⌘⇧E (export), etc. |
| **MenuBarExtra size** | Hardcoded `frame(width: 280)` — too narrow | 320–340px is comfortable for a popover |
| **Popover border/shadow** | Using `Color(nsColor: .controlBackgroundColor)` for card bg | Gives drab look; should use `Token.bgCard` or custom semantic color |
| **Settings window size** | `frame(width: 450, height: 320)` — will clip | 520×540 is comfortable for a tabbed settings window |
| **ButtonStyle inconsistency** | `.buttonStyle(.plain)` + manual background/clipShape repeated 6+ times | Should be a reusable `PillButton` or similar |
| **Segmented control** | Radio buttons or custom segments with no spacing | macOS `Picker("", selection: $x).pickerStyle(.radioGroup)` is native |
| **Content shape** | Interactive rows without `.contentShape(Rectangle())` | Only the text is tappable, not the whole row |
| **Window background** | No `.background(Token.bgPrimary)` on root view | Shows system background color instead of designed surface |

## Specific SwiftUI Anti-Patterns

- ❌ `Color(nsColor: .controlBackgroundColor)` for card backgrounds — inconsistent between light/dark
- ❌ `.background(Token.bgCard).clipShape(...)` — use `Card(style:)` component instead
- ❌ `ScrollView { ForEach(...) }` for 1000+ items — stutters; use `LazyVStack`
- ❌ `Text("⌘⇧R").font(.caption)` — should be `KeyboardShortcutLabel` or consistent styling
- ❌ `TextField("", text: $x)` with no `.textFieldStyle(.roundedBorder)` — looks unstyled
- ❌ `VStack` of `Button(action:)` with `.plain` style — use `List` or `Form` for grouped actions
- ❌ `NSSavePanel` without `allowedContentTypes` — may crash on newer macOS

## Verification Commands

```bash
# Hardcoded colors (non-Token)
grep -rn "Color(\(red:.*green:.*blue:\|orange\|yellow\|purple\|pink\|gray\|teal\)" Sources/ScribeApp/

# Magic spacing numbers
grep -rn "\.padding(\d\+)" Sources/ScribeApp/ | grep -v "Token.space"

# Magic corner radii
grep -rn "cornerRadius: \d\+" Sources/ScribeApp/ | grep -v "Token.radius"

# ScrollView + ForEach (vs LazyVStack)
grep -B2 -A5 "ScrollView" Sources/ScribeApp/*.swift | grep "ForEach"

# Missing hover states on rows
grep -rn "onTapGesture\|onHover" Sources/ScribeApp/ | wc -l
# Compare to number of interactive rows
grep -rn "NavigationLink\|Button" Sources/ScribeApp/ | wc -l

# Keyboard shortcuts beyond ⌘⇧R
grep -rn "GlobalHotkeyManager\|addGlobalMonitor" Sources/ScribeApp/
```

## Audit Report Template

```markdown
## Code-Based UX Audit: <AppName>

### Score Summary

| Dimension | Score | Notes |
|-----------|-------|-------|
| Philosophy Alignment | X/10 | |
| Visual Hierarchy | X/10 | |
| Craft Quality | X/10 | |
| Functionality | X/10 | |
| Innovation | X/10 | |
| **Overall** | **X.X/10** | |

### Quick Fixes (< 30 min each)
- Fix item 1
- Fix item 2

### Structural Changes (2–4 hrs, bigger impact)
- Change item 1

### Big Bets (1–2 days, signature impact)
- Feature item 1
```
