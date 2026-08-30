---
name: swiftui-macos-design-system
title: macOS SwiftUI Design System
description: Build a centralized token-driven design system for SwiftUI macOS apps — colors, typography, spacing, components, and platform-specific gotchas.
version: 1.0
category: software-development
---

# macOS SwiftUI Design System

## When to use

Building or redesigning a SwiftUI macOS app where consistent visual language matters. This skill covers the token system, component library, and platform-specific macOS SwiftUI 6 quirks.

## Why not just standard tokens?

SwiftUI on macOS has unique constraints: `NSColor` dynamic providers, `Color(nsColor:)` for system colors, `ShapeStyle` vs `Color` type mismatch, and `Sendable` safety for static properties. These are macOS-specific, not iOS.

## Step 1: Centralized Token File

Create a single `DesignTokens.swift`:

```swift
import SwiftUI
import AppKit

public enum Token {
    public static var bgCard: Color { Color(nsColor: .controlBackgroundColor) }
    public static var textTertiary: Color { Color(nsColor: .tertiaryLabelColor) }
    public static var border: Color { ... }
    public static func body() -\u003e Font { .system(size: 13, weight: .regular) }
    public static let space4: CGFloat = 16
}
```

**Rule:** Zero raw colors in view files. All views reference `Token.X`.

### macOS-Specific Color Gotchas

- `Color(nsColor: .tertiaryLabelColor)` ✅ — `.tertiary` returns `ShapeStyle`, not `Color`
- Dynamic dark/light: `NSColor(name: nil, dynamicProvider: { ... })` ✅ — not `NSColor { }` (picks wrong init)

## Step 2: Card Component

Use `RoundedRectangle(cornerRadius:).fill()` as container, NOT `.background().clipShape()` — prevents shadows.

```swift
public struct Card\u003cContent: View\u003e: View {
    public var body: some View {
        content
            .padding(padding)
            .background(RoundedRectangle(cornerRadius: radius).fill(backgroundColor))
    }
}
```

Styles: `.default` (bgCard), `.elevated` (lighter bg + shadow), `.minimal` (transparent + border).

## Step 3: Component Library

Build before screen redesign:
- `Card` — container
- `MeetingRow` / `ListRow` — with hover states
- `IconLabel` — icon+text
- `StatusBadge` — status pill
- `EmptyStateView` — replaces `ContentUnavailableView`
- `AnimatedRecordingIndicator` — replaces raw animation

## Step 4: Screen Migration

1. Replace raw `Color(...)`, `.padding(12)` with `Token.X`
2. Wrap sections in `Card(style: .default, showBorder: true)`
3. Replace `ForEach` in `ScrollView` with `LazyVStack`
4. Add hover: `.onHover { } + background highlight`
5. Section headers: small caps, `tracking(0.5)`, `Token.textTertiary`

## Step 5: Swift 6 Safety

- `struct Foo: Sendable` — avoids `#MutableGlobalVariable` on statics
- `@MainActor` on `ObservableObject` touching `NSApplication`
- `@unchecked Sendable` only for C API wrappers

## Pitfalls

1. `.tertiary` → `ShapeStyle`, not `Color`
2. `NSColor { }` → picks wrong init (`patternImage`)
3. `.background().clipShape()` → loses shadows
4. `ScrollView+ForEach` → use `LazyVStack`
5. Hardcoded colors in views → centralize in `Token`
