# macOS Share Extension Setup

Receiving files via the macOS Share menu into a Swift/SwiftUI app.

## Architecture

macOS share extensions are separate processes. They can't directly interact with the main app. File-based IPC via app groups is the simplest approach.

## Setup Steps

### 1. Entitlements

Add to your main app and extension targets:
```xml
<key>com.apple.security.application-groups</key>
<array>
    <string>group.com.yourapp.shared</string>
</array>
```

### 2. Package.swift Target

```swift
.target(
    name: "ShareExtension",
    dependencies: ["ScribeApp"],
    exclude: ["Info.plist"]  // Prevents SPM warning about unhandled resource
),
```

### 3. Info.plist

Standard `NSExtension` setup for share services with `com.apple.share-services` point identifier.

### 4. Handler Implementation

- Validate incoming items are audio/video via `UTType`
- Copy validated files to the shared app group container with UUID filenames
- Write a pending-import manifest (`pending_imports.json`) listing copied files

### 5. Main App Polling

```swift
class SharedContainerMonitor: ObservableObject {
    private var timer: Timer?
    func start() {
        timer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { _ in
            Task { @MainActor [self] in self.poll() }
        }
    }
    private func poll() {
        guard let container = FileManager.default
            .containerURL(forSecurityApplicationGroupIdentifier: "group.com.yourapp.shared"),
              let data = try? Data(contentsOf: container.appendingPathComponent("pending_imports.json"))
        else { return }
        let imports = try? JSONDecoder().decode([PendingImport].self, from: data)
        // Process imports, then delete the manifest
    }
}
```

## SPM Quirk

If you include an `Info.plist` in a Swift Package Manager target but don't declare `exclude: ["Info.plist"]`, SPM emits a warning about unhandled resource files. Always exclude plists in extension targets.
