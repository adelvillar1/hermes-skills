# GRDB + SwiftUI ForEach Overload Collision

## The Problem

When GRDB.swift is a dependency, its `Array` extension (`init(_ cursor: some Cursor<Element>) throws`) collides with Swift's standard `Array.init` in SwiftUI `@ViewBuilder` contexts. The type checker resolves the wrong overload, producing errors that look nonsensical.

## Error Progression (real errors from Scribe session)

### Attempt 1: `Array(events.prefix(3))`
```
error: initializer 'init(_:)' requires that 'PrefixSequence<[UpcomingMeetingEvent]>' conform to 'Cursor'
```
GRDB's `Array.init(_ cursor:)` wins over Swift's `Array.init<S>(_ elements: S)`.

### Attempt 2: `Array(events[..<3])`
Same error — `ArraySlice` also triggers the Cursor overload.

### Attempt 3: `ForEach(events, id: \.id)` where events comes from `@StateObject`
```
error: cannot convert value of type '[UpcomingMeetingEvent]' to expected argument type 'Binding<C>'
```
SwiftUI's `ForEach.init<C>(_ data: Binding<C>, ...)` overload wins because the data originates from an `@StateObject`'s published property, and the type checker infers a Binding context.

### Attempt 4: Index-based ForEach
```swift
ForEach(0..<count, id: \.self) { index in ... }
```
```
error: cannot convert value of type 'Range<Int>' to expected argument type 'Binding<C>'
```
Same Binding overload wins — the `@StateObject` context poisons inference for the entire view body. **Even an integer range is not immune** when the surrounding view has `@StateObject` properties.

## Root Cause

Two independent overload resolution failures:
1. **GRDB pollution**: GRDB adds `Array.init(_ cursor:)` which matches any sequence-like argument when Swift's type checker is stressed.
2. **Binding inference**: SwiftUI has both `ForEach(data: RandomAccessCollection)` and `ForEach(data: Binding<C>)`. When data traces back to an `@StateObject`, the type checker can prefer the Binding variant in `@ViewBuilder` contexts.

## Solutions (ranked by reliability)

### 1. Manual rendering (most reliable)
```swift
if !events.isEmpty { eventRow(for: 0) }
if events.count > 1 { eventRow(for: 1) }
if events.count > 2 { eventRow(for: 2) }

@ViewBuilder
private func eventRow(for index: Int) -> some View {
    let event = events[index]
    HStack { /* ... */ }
}
```
No `ForEach`, no `Array()` constructor, no overload ambiguity.

### 2. @State copy pattern
```swift
@StateObject private var manager = SomeManager()
@State private var items: [Item] = []

// Sync on appear + change
.onAppear { items = manager.items }
.onChange(of: manager.items) { _, new in items = new }
// ⚠️ Element type must conform to Equatable for .onChange(of:) on arrays

// ForEach on the @State copy
ForEach(items, id: \.id) { item in ... }
```
Breaks the Binding inference chain by copying into a plain `@State`. **Caveat:** `onChange(of:)` on an array requires the element type to conform to `Equatable`. Add `Equatable` conformance if needed.

### 3. Index mapping (avoids Array constructor)
```swift
let top3: [Item] = {
    let n = min(3, items.count)
    return (0..<n).map { items[$0] }
}()
ForEach(top3, id: \.id) { item in ... }
```
Avoids calling `Array()` explicit constructor. The `(0..<n).map` produces a plain `[Item]` that doesn't trigger GRDB's Cursor overload.

## When It Bites

- GRDB is a dependency (via SPM)
- Using SwiftUI `ForEach` inside `@ViewBuilder` contexts
- Data originates from `@StateObject` published properties
- Using `Array()` constructor on slices/prefixes of GRDB-adjacent types

## Prevention

If you see "does not conform to Cursor" or "cannot convert to Binding<C>" in a SwiftUI ForEach context with GRDB:
1. Stop trying different `Array()` / `ForEach()` overloads — they'll all resolve wrong
2. Switch to manual rendering or @State copy pattern immediately
3. Do NOT waste 6+ build attempts trying minor syntax variations