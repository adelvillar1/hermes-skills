# Swift 6 Build Error Cookbook — Session 2026-05-30

Quick-reference of build errors encountered during the Scribe UI redesign and their exact fixes.

## Error: `no exact matches in call to initializer` on NSColor

**Trigger:** Attempting to create a color that adapts to light/dark mode using a closure:
```swift
Color(nsColor: NSColor { traits in
    traits.isDark ? NSColor(...) : NSColor(...)
})
```

**Root cause:** `NSColor { ... }` resolves to `NSColor(patternImage:)` or other init that doesn't accept closures. There is no `NSColor` initializer that takes a closure directly.

**Fix:** Use the explicit `dynamicProvider:` initializer:
```swift
Color(nsColor: NSColor(name: nil, dynamicProvider: { appearance in
    if appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua {
        return NSColor(red: 0.20, green: 0.20, blue: 0.21, alpha: 1.0)
    }
    return NSColor(red: 0.96, green: 0.96, blue: 0.97, alpha: 1.0)
}))
```

**Prevention:** Never use `NSColor { traits in ... }`. Always use `NSColor(name: nil, dynamicProvider: ...)`.

---

## Error: `ShapeStyle` vs `Color` type mismatch

**Trigger:** Using `.tertiary`, `.primary`, etc. where `Color` is expected:
```swift
public static var textTertiary: Color { .tertiary }  // ❌
```

**Root cause:** On `Color`, `.tertiary` returns `some ShapeStyle`, not `Color`. Cannot assign to a `Color`-typed property.

**Fix:** Use `Color(nsColor:)` for explicit `Color` construction:
```swift
public static var textTertiary: Color { Color(nsColor: .tertiaryLabelColor) }  // ✅
```

**Related:** Same issue affects `.primary` and `.secondary` in some SwiftUI contexts, but `Color` itself conforms to `ShapeStyle` so `.primary` works as `Color` initializer. `.tertiary` specifically does not.

---

## Error: `#MutableGlobalVariable` on static property in non-Sendable type

**Trigger:** Defining a static `let` inside a struct that doesn't conform to `Sendable`:
```swift
public struct ShadowStyle {
    public static let none = ShadowStyle(...)
}
```

**Root cause:** Swift 6 treats non-Sendable types with static storage as potentially shared mutable state.

**Fix:** Add `Sendable` conformance:
```swift
public struct ShadowStyle: Sendable {
    public static let none = ShadowStyle(...)
}
```

---

## Error: `Sendable` conformance required for enum with static computed properties

**Trigger:** Static computed `Color` properties inside a plain `enum Token`:
```swift
public enum Token {
    public static var bgPrimary: Color { ... }
}
```

**Fix:** Add `: Sendable` to the enum if it defines any static stored/computed properties that cross concurrency boundaries:
```swift
public enum Token: Sendable {
    public static var bgPrimary: Color { ... }
}
```

**Note:** If the enum is purely value-based with no static properties, `Sendable` is implicit. Static properties change the analysis.
