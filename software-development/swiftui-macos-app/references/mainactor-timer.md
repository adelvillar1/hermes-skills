# @MainActor + Timer Pattern in Swift 6

## Problem

Inside a `@MainActor` view or class, `Timer.scheduledTimer` callbacks cause Swift 6 concurrency warnings/errors because the closure is treated as Sendable but captures `@MainActor`-isolated properties.

## Errors

```
warning: main actor-isolated property 'player' can not be referenced from a Sendable closure
warning: main actor-isolated property 'currentTime' can not be mutated from a Sendable closure
error: call to main actor-isolated instance method 'stopTimer()' in a synchronous nonisolated context
```

## Solution

Wrap timer body in `Task { @MainActor [self] in ... }`:

```swift
@MainActor
final class AudioPlayerState: ObservableObject {
    private var timer: Timer?

    private func startTimer() {
        stopTimer()
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

    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }
}
```

## What NOT to do

- `@MainActor` on the Timer callback closure itself — doesn't help
- `MainActor.assumeIsolated { ... }` — assumes isolation but not always safe
- `[weak self]` inside a `@MainActor` type — unnecessary; `self` is already bound to main actor
- Using `@preconcurrency import` on the framework — suppresses, doesn't fix

## Verification

Build with `-strict-concurrency=complete` or Swift 6 language mode. Should be 0 warnings.
