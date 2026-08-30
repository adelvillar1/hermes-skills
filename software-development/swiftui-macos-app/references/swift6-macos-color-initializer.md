# Swift 6 macOS Color Gotchas

## Symptom: "no exact matches in call to initializer"

`Color(nsColor: NSColor { traits in ... })` fails with:
```
error: no exact matches in call to initializer
note: closure passed to parameter of type 'NSImage' that does not accept a closure
```

**Why:** Swift resolves `NSColor { ... }` to `NSColor(patternImage:)`, `NSColor(controlTint:)`, or `NSColor(resource:)` — none accept a trailing closure for dynamic color.

**Correct initializer:** `NSColor(name:dynamicProvider:)`

```swift
// Correct — explicit dynamic provider
Color(nsColor: NSColor(name: nil, dynamicProvider: { appearance in
    if appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua {
        return NSColor(red: 0.20, green: 0.20, blue: 0.21, alpha: 1.0)
    }
    return NSColor(red: 0.96, green: 0.96, blue: 0.97, alpha: 1.0)
}))

// Wrong — picks patternImage or controlTint
Color(nsColor: NSColor { traits in
    traits.isDark ? NSColor.black : NSColor.white
})
```

## Symptom: "Produces result of type 'some ShapeStyle', but context expects 'Color'"

```swift
public static var color: Color { .tertiary }
// Error: produces result of type 'some ShapeStyle', but context expects 'Color'
```

**Why:** `.tertiary` on `Color` resolves to `some ShapeStyle`, which is broader than `Color`.

**Fix:** Use explicit `Color` constructor via `NSColor`:
```swift
public static var textTertiary: Color { Color(nsColor: .tertiaryLabelColor) }
public static var textSecondary: Color { Color(nsColor: .secondaryLabelColor) }
public static var separator: Color { Color(nsColor: .separatorColor) }
```

## Pattern: Full Token File Example

```swift
import SwiftUI
import AppKit

public enum Token {
    public static var bgPrimary: Color { Color(nsColor: .windowBackgroundColor) }
    public static var bgCard: Color { Color(nsColor: .controlBackgroundColor) }
    public static var bgElevated: Color {
        Color(nsColor: NSColor(name: nil, dynamicProvider: { appearance in
            if appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua {
                return NSColor(red: 0.20, green: 0.20, blue: 0.21, alpha: 1.0)
            }
            return NSColor(red: 0.96, green: 0.96, blue: 0.97, alpha: 1.0)
        }))
    }
    public static var separator: Color { Color(nsColor: .separatorColor) }
    public static var border: Color {
        Color(nsColor: NSColor(name: nil, dynamicProvider: { appearance in
            if appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua {
                return NSColor(red: 0.22, green: 0.22, blue: 0.23, alpha: 1.0)
            }
            return NSColor(red: 0.90, green: 0.90, blue: 0.91, alpha: 1.0)
        }))
    }
    public static var textPrimary: Color { .primary }
    public static var textSecondary: Color { .secondary }
    public static var textTertiary: Color { Color(nsColor: .tertiaryLabelColor) }
    public static var accentBlue: Color { .accentColor }
    public static var success: Color { .green }
    public static var warning: Color { .orange }
    public static var danger: Color { .red }
}
```

## Sendable Gotcha: `MutableGlobalVariable` on Static Properties

```
error: static property 'none' is not concurrency-safe because non-'Sendable' type
        'ShadowStyle' may have shared mutable state
```

**Fix:** Add `Sendable` conformance to the struct/enum defining the static:
```swift
public struct ShadowStyle: Sendable { ... }
```
