---
name: swiftui-macos-app
version: 1.0.0
description: Build macOS apps with SwiftUI, GRDB.swift, ScreenCaptureKit, CoreAudio, and EventKit. Covers Swift 6 concurrency strictness, GRDB+SwiftUI overload collisions, CoreAudio C-bridge patterns, and menu bar app architecture.
triggers:
  - swift build
  - swiftui
  - macos app
  - menu bar
  - grdb
  - CoreAudio
  - ScreenCaptureKit
  - EventKit
  - swift 6
---

# SwiftUI macOS App Development

Build local macOS apps with SwiftUI, GRDB.swift for persistence, CoreAudio/ScreenCaptureKit for capture, and EventKit for calendar integration. Swift 6 strict concurrency is the default — every closure, every generic, every `@StateObject` interaction needs explicit Sendable handling.

## When to Load

- Building or debugging a Swift macOS app (menu bar, accessory, or full app)
- Using GRDB with SwiftUI views (ForEach, Query, etc.)
- Integrating CoreAudio device enumeration or ScreenCaptureKit
- Hitting Swift 6 Sendable/concurrency errors
- Working with EventKit calendar integration

## Critical Pitfalls

### 1. GRDB + SwiftUI `ForEach` Overload Collision

GRDB extends Swift's `Array` with `init(_ cursor: some Cursor<Element>)` which Swift's type checker can resolve **instead of** the standard `Array.init` when constructing arrays inside SwiftUI `@ViewBuilder` contexts. This produces nonsensical errors like "PrefixSequence does not conform to Cursor".

**Bad** — GRDB's Array init wins:
```swift
ForEach(Array(events.prefix(3)), id: \.id) { event in ... }
ForEach(Array(upcomingEvents.prefix(3))) { event in ... }
```

**Good** — Avoid `Array()` constructor; use index mapping or manual rendering:
```swift
// Option A: Index-based mapping (no Array constructor)
let top3: [Event] = {
    let n = min(3, events.count)
    return (0..<n).map { events[$0] }
}()
ForEach(top3, id: \.id) { event in ... }

// Option B: Manual renders (most reliable — no ForEach at all)
if !events.isEmpty { eventRow(for: 0) }
if events.count > 1 { eventRow(for: 1) }
if events.count > 2 { eventRow(for: 2) }
```

See `references/grdb-swiftui-foreach-collision.md` for the full error progression.

### 2. SwiftUI ForEach Resolves to `Binding<C>` Overload

When data comes from an `@StateObject`'s published property, Swift 6 type inference can resolve `ForEach` to the `init<C>(_ data: Binding<C>, ...)` overload instead of `init<Data: RandomAccessCollection>`. Symptoms: "cannot convert value of type '[X]' to expected argument type 'Binding<C>'".

**Fix**: Copy data into a plain `@State` array, sync via `.onAppear` + `.onChange(of:)`, and iterate the `@State` copy:
```swift
@StateObject private var manager = SomeManager()
@State private var items: [Item] = []

// .onAppear: copy from manager
// .onChange(of: manager.items): sync to @State
// ForEach iterates @State items (not @StateObject published property)
```

### 3. Swift 6 `@unchecked Sendable` for ObservableObject

Swift 6 requires all types used across concurrency boundaries to be `Sendable`. `ObservableObject` classes are NOT automatically Sendable. When used as `@StateObject`, the compiler will emit errors.

**Fix**: Add `@unchecked Sendable` conformance:
```swift
public final class AudioDeviceManager: ObservableObject, @unchecked Sendable { ... }
public final class CalendarManager: ObservableObject, @unchecked Sendable { ... }
```

Use `@unchecked` only when you control mutation (serial queues, `@MainActor`, etc.). Document why it's safe.

### 4. CoreAudio Listener: C Function Pointer Required

`AudioObjectAddPropertyListenerBlock` (the block-based API) does not exist on macOS. You must use `AudioObjectAddPropertyListener` with a C function pointer (`AudioObjectPropertyListenerProc`).

**Pattern**:
```swift
private var listenerProc: AudioObjectPropertyListenerProc?
private var listenerUserData: UnsafeMutableRawPointer?

private func startListener() {
    let pointer = Unmanaged.passUnretained(self).toOpaque()
    listenerUserData = pointer
    listenerProc = { (_, _) in
        let manager = Unmanaged<AudioDeviceManager>.fromOpaque(pointer).takeUnretainedValue()
        DispatchQueue.main.async { manager.refreshDevices() }
        return noErr
    }
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDevices,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    AudioObjectAddPropertyListener(AudioObjectID(kAudioObjectSystemObject), &address, listenerProc!, listenerUserData)
}

deinit {
    if let proc = listenerProc, let userData = listenerUserData {
        var address = AudioObjectPropertyAddress(...)
        AudioObjectRemovePropertyListener(AudioObjectID(kAudioObjectSystemObject), &address, proc, userData)
    }
}
```

### 5. CChar vs UInt8 String Conversion

`AudioDevice.name` returns `[CChar]` (signed). `String(decoding:as: UTF8.self)` requires `[UInt8]`. Direct use fails in Swift 6.

**Fix**:
```swift
let name: [CChar] = ...
let deviceName = String(decoding: name.prefix(while: { $0 != 0 }).map { UInt8($0) }, as: UTF8.self)
```

Or simpler:
```swift
let deviceName = String(cString: name) // works if name is null-terminated [CChar]
```

### 6. New Enum Cases Must Be Handled in All Switch Statements

Adding a new case to a Swift enum (e.g., `MeetingStatus.imported`) breaks **every** `switch` in the project. Find all switches before building:
```bash
grep -rn "switch .*status\|case \.recording\|case \.completed\|case \.imported" Sources/
```

### 6a. UI Patterns for New Status Cases

When adding a status case (e.g., `.imported` for drag-and-drop files), update all status consumers:

| Consumer | What to update |
|----------|----------------|
| `StatusBadge.swift` | Text label for the new status |
| `MeetingRow.swift` | Icon / color for the new status |
| `MeetingsListView.swift` | Sort/filter ordering if applicable |
| All `switch` blocks | `case` handling (Swift 6 exhaustive) |

## Token-Driven Design System

## Module Naming

When a source directory contains code that doesn't match the module name (e.g., `Sources/OllamaClient/LLMClient.swift`), the module import is determined by the **Package.swift target name**, not filenames. If you rename the purpose, rename both:
- The directory: `Sources/OllamaClient/` → `Sources/LLMClient/`
- The Package.swift target: `name: "OllamaClient"` → `name: "LLMClient"`
- All import statements: `import OllamaClient` → `import LLMClient`

## Architecture Patterns

### Menu Bar App (MenuBarExtra)
```swift
@main
struct ScribeApp: App {
    @StateObject var appState = AppState()
    var body: some Scene {
        MenuBarExtra { ScribeMenuView().environmentObject(appState) }
        label: { Label("Scribe", systemImage: "waveform") }
    }
}
```

### GRDB Migration Pattern
```swift
migrator.registerMigration("v3_add_segment_edited") { db in
    try db.alter(table: "transcriptSegment") { t in
        t.add(column: "isEdited", .boolean).defaults(to: false)
    }
}
```

### Incremental WAV Writing
Use a serial dispatch queue. Write WAV header on init (with placeholder sizes). Append PCM chunks. Update header sizes on close.

### Crash-Safe Segment Flush
Flush pending transcript segments to DB every 10 seconds during recording. On `stopRecording`, do a final flush. On app launch, recover any meetings with status `.recording` → mark `.interrupted`.

### UNUserNotificationCenter
Requires `import UserNotifications`. Always request authorization (`.alert`, `.sound`) before posting. In SwiftUI apps, request in `AppDelegate` or on first use via `UNUserNotificationCenter.current().requestAuthorization(options:)`.

### `.onChange(of:)` on Arrays Requires Equatable Elements
When syncing `@StateObject` published arrays to `@State` via `.onChange(of: manager.items)`, the element type must conform to `Equatable`. Add `Equatable` to the element struct if the compiler complains about conditional conformance.

### 7. Static Properties in Non-Sendable Types: Swift 6 `#MutableGlobalVariable`

`public static var` or `let` inside a non-Sendable `enum` or `struct` triggers Swift 6's `MutableGlobalVariable` error because the compiler treats non-Sendable static state as potentially shared mutable.

**Fix**: Add `Sendable` conformance:
```swift
public struct ShadowStyle: Sendable { ... }
// or add to enum:
public enum Token: Sendable { ... } // if enum defines static lets
```

**See**: `references/swift6-build-error-cookbook.md` for additional Swift 6 build errors.

### 8. `NSColor` Closure Picks the Wrong Initializer

`NSColor { appearance in ... }` does not exist as a dynamic provider. Swift selects `NSColor(patternImage:)` or `NSColor(controlTint:)` instead, producing `no exact matches in call`.

**Fix:** Use the explicit dynamic provider initializer:
```swift
Color(nsColor: NSColor(name: nil, dynamicProvider: { appearance in
    if appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua {
        return NSColor(red: 0.20, green: 0.20, blue: 0.21, alpha: 1.0)
    }
    return NSColor(red: 0.96, green: 0.96, blue: 0.97, alpha: 1.0)
}))
```

**See:** `references/swift6-macos-color-initializer.md`

### 9. `ShapeStyle` vs `Color` Type Mismatch

`.tertiary`, `.primary`, etc. on `Color` produce `some ShapeStyle`, not `Color`. If a property declares `var x: Color { ... }`, `.tertiary` won't type-check.

**Fix**: Use `Color(nsColor:)` for explicit Color construction:
```swift
public static var textTertiary: Color { Color(nsColor: .tertiaryLabelColor) } // ✅
public static var textTertiary: Color { .tertiary } // ❌ ShapeStyle, not Color
```

### 10. `@MainActor` + `Timer.scheduledTimer` Closure Isolation

Swift 6 treats `Timer.scheduledTimer` callbacks as Sendable closures. Inside a `@MainActor` class, capturing `@Published` properties or calling actor-isolated methods triggers warnings or errors.

**Fix:** Wrap the timer body in a `Task { @MainActor [self] in ... }` block:
```swift
private func startTimer() {
    timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { _ in
        Task { @MainActor [self] in
            guard let player = self.player else { return }
            self.currentTime = player.currentTime
            if !player.isPlaying {
                self.isPlaying = false
                self.stopTimer()
            }
        }
    }
}
```

**See:** `references/mainactor-timer.md` for the full error progression and approaches that don't work.

### 11. CoreAudio Device UID Routing to AVAudioEngine

To route the microphone to a specific CoreAudio device (e.g., user-selected USB mic), use `AudioUnitSetProperty(kAudioOutputUnitProperty_CurrentDevice)` on `audioEngine.inputNode.audioUnit`.

**Steps:**
1. Walk all devices via `AudioObjectGetPropertyData(kAudioHardwarePropertyDevices)`
2. Match target UID against `kAudioDevicePropertyDeviceUID`
3. Pass matched `AudioDeviceID` to `AudioUnitSetProperty()`
4. Must occur AFTER `installTap()` but BEFORE `audioEngine.start()`

**See:** `references/coreaudio-device-routing.md` for the full implementation pattern and hardware verification checklist.

## Linked References

- `references/grdb-swiftui-foreach-collision.md` — full error progression for ForEach overload
- `references/grdb-search-with-snippets.md` — multi-table search with matching snippets (title, summary, child table content)
- `references/swift6-build-error-cookbook.md` — NSColor dynamic provider patterns and gotchas
- `references/mainactor-timer.md` — `@MainActor` + `Timer.scheduledTimer` Swift 6 isolation fix
- `references/coreaudio-device-routing.md` — CoreAudio UID → AVAudioEngine input node routing
- `references/audio-import-wav-pipeline.md` — Drag-and-drop / share extension audio import pipeline with WAV conversion
- `references/structured-llm-output-swift.md` — Requesting JSON from Ollama/DeepSeek with Codable decoding
- `references/macos-share-extension.md` — macOS Share menu extension via app groups