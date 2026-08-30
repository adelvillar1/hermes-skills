---
name: macos-shortcuts
title: macOS Shortcuts (Global + Local) in SwiftUI
description: Add global and local keyboard shortcuts to a macOS SwiftUI app using NSEvent.globalMonitor and CommandGroup.
---

# macOS Keyboard Shortcuts in SwiftUI

A two-tier system: **global shortcuts** work from any app (require Accessibility permission) and **local shortcuts** work only when your app is focused.

## 1. Global Shortcuts — Enum-Based GlobalHotkeyManager

### Why enum-based?
- One handler closure (`onShortcut`) dispatches all shortcuts
- Extensible: add a case + keyCode/modifier tuple without rewriting event handling
- Each shortcut has a human-readable `label()` and `displayString()` for Settings UI

### Implementation

```swift
import Cocoa

public final class GlobalHotkeyManager: @unchecked Sendable {
    public enum Shortcut: String, CaseIterable, Sendable {
        case toggleRecording // ⌘⇧R
        case startRecording  // ⌘⇧N
        case toggleMenuBar   // ⌘⇧T
    }

    public var onShortcut: ((Shortcut) -> Void)?
    private var monitor: Any?
    private let queue = DispatchQueue(label: "com.app.hotkey", qos: .userInitiated)

    // (shortcut, keyCode, modifiers)
    private let config: [(Shortcut, UInt16, NSEvent.ModifierFlags)] = [
        (.toggleRecording, 15, [.command, .shift]), // R
        (.startRecording,  45, [.command, .shift]), // N
        (.toggleMenuBar,   17, [.command, .shift]), // T
    ]

    public func start() {
        queue.sync {
            guard monitor == nil else { return }
            monitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
                self?.handleEvent(event)
            }
        }
    }

    public func stop() {
        queue.sync {
            if let monitor { NSEvent.removeMonitor(monitor); self.monitor = nil }
        }
    }

    private func handleEvent(_ event: NSEvent) {
        let modifiers = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
        for (shortcut, keyCode, targetModifiers) in config {
            guard modifiers == targetModifiers, event.keyCode == keyCode else { continue }
            DispatchQueue.main.async { [weak self] in self?.onShortcut?(shortcut) }
            break
        }
    }
}
```

### Key Code Reference (ANSI US Layout)
| Key | Code |
|-----|------|
| R   | 15   |
| T   | 17   |
| N   | 45   |
| S   | 1    |
| E   | 14   |
| D   | 2    |
| P   | 35   |

## 2. Wiring in AppState

```swift
private var hotkeyManager = GlobalHotkeyManager()

init() {
    hotkeyManager.onShortcut = { [weak self] shortcut in
        switch shortcut {
        case .toggleRecording:
            self?.toggleRecording()
        case .startRecording:
            if !(self?.isRecording ?? true) { self?.startRecording() }
        case .toggleMenuBar:
            break // MenuBarExtra has no programmatic toggle in SwiftUI
        }
    }
    hotkeyManager.start()
}
```

## 3. Local Shortcuts — CommandGroup

For shortcuts that only work when the app is focused:

```swift
WindowGroup { ... }
    .commands {
        CommandGroup(replacing: .appSettings) {
            Button("Settings…") {
                NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
            }
            .keyboardShortcut(",", modifiers: .command)
        }
    }
```

## 4. Settings Help Tab

Display shortcuts in a Settings/Preferences window:

```swift
private var shortcutsTab: some View {
    VStack(alignment: .leading, spacing: 12) {
        Text("Global Shortcuts")
            .font(.caption)
            .foregroundStyle(.secondary)
            .textCase(.uppercase)
        ForEach(GlobalHotkeyManager.Shortcut.allCases, id: \.rawValue) { s in
            HStack {
                Text(label(for: s))
                Spacer()
                Text(displayString(for: s))
                    .foregroundStyle(.secondary)
            }
        }
    }
}
```

## 5. Adding a New Shortcut

1. Add a case to `GlobalHotkeyManager.Shortcut`
2. Add tuple to `config` array with keyCode and modifiers
3. Add `label()` and `displayString()` entries
4. Handle the case in `AppState.onShortcut`
5. Add to Settings `shortcutsTab` if desired

## Pitfalls

- **MenuBarExtra** (`@main struct App: App` with `MenuBarExtra` scene) **cannot be toggled programmatically** from a global shortcut. This is a SwiftUI limitation — `NSStatusBar` would be needed for that.
- **Accessibility permission** is required for `addGlobalMonitorForEvents`. On first use, silently fails. Document this in UI.
- **Key layout** — keyCode 15 is "R" on ANSI US layout, but may differ on other keyboard layouts. For production multi-language support, consider mapping by `event.characters` instead of keyCode (but this requires a local event tap, not `addGlobalMonitorForEvents`).
- **Multiple modifiers** — `.command` and `.shift` are standard. Avoid `.control` on Mac (conflicts with Emacs-style shortcuts in many apps).
- **Deinit cleanup** — `stop()` must be called or `removeMonitor` will leak. Use `deinit` in the manager.

## Verification

Build and run, then:
1. Focus another app (e.g., Safari)
2. Press ⌘⇧R — recording should toggle
3. Open Settings → Shortcuts tab — verify all three shortcuts display correctly
4. Check Console.app for "Accessibility" permission prompts