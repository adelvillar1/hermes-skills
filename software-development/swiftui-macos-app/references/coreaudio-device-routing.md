# CoreAudio Device Routing via AudioUnitSetProperty

## Problem

In a SwiftUI macOS app, the user selects an audio input device (e.g., USB microphone) via a `Picker` in Settings. The `AVAudioEngine.inputNode` must be routed to that device UID before `audioEngine.start()` is called.

## Solution

### Step 1: Walk devices and find UID → AudioDeviceID

```swift
private static func deviceID(from uid: String) -> AudioDeviceID? {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDevices,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )

    var size: UInt32 = 0
    guard AudioObjectGetPropertyDataSize(
        AudioObjectID(kAudioObjectSystemObject),
        &address, 0, nil, &size
    ) == noErr else { return nil }

    let deviceCount = Int(size) / MemoryLayout<AudioDeviceID>.size
    var deviceIDs = [AudioDeviceID](repeating: 0, count: deviceCount)
    guard AudioObjectGetPropertyData(
        AudioObjectID(kAudioObjectSystemObject),
        &address, 0, nil, &size, &deviceIDs
    ) == noErr else { return nil }

    for deviceID in deviceIDs {
        var uidSize: UInt32 = 0
        var uidAddress = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyDeviceUID,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        guard AudioObjectGetPropertyDataSize(deviceID, &uidAddress, 0, nil, &uidSize) == noErr else { continue }

        var uidRef: CFString?
        var mutableSize = uidSize
        guard AudioObjectGetPropertyData(deviceID, &uidAddress, 0, nil, &mutableSize, &uidRef) == noErr,
              let deviceUID = uidRef as? String,
              deviceUID == uid else { continue }
        return deviceID
    }
    return nil
}
```

### Step 2: Route the AVAudioEngine inputNode to that device

```swift
@discardableResult
public func setMicrophoneDeviceUID(_ uid: String?) -> Bool {
    guard let audioUnit = audioEngine.inputNode.audioUnit else {
        return false
    }
    guard let uid = uid else { return false }
    guard var deviceID = Self.deviceID(from: uid) else { return false }

    let status = AudioUnitSetProperty(
        audioUnit,
        kAudioOutputUnitProperty_CurrentDevice,
        kAudioUnitScope_Global,
        0,
        &deviceID,
        UInt32(MemoryLayout<AudioDeviceID>.size)
    )
    return status == noErr
}
```

### Step 3: Read persisted UID and apply before starting engine

```swift
public func start(config: AudioStreamConfig) async throws {
    // ... permission checks, install tap ...
    
    if let selectedUID = UserDefaults.standard.string(forKey: "selectedInputDeviceUID") {
        if !self.setMicrophoneDeviceUID(selectedUID) {
            print("⚠️ Failed to set selected microphone device, falling back to default")
        }
    }
    
    try startAudioEngine()
    isCapturing = true
}
```

## Why `UserDefaults` instead of `AudioDeviceManager().selectedDevice?.uid`

Creating a fresh `AudioDeviceManager()` instance doesn't share the `inputDevices` array with the UI's `@StateObject` manager. The manager's `selectedDevice` depends on device enumeration, which takes time. `UserDefaults` is the common ground that both the UI picker and the capture engine read from.

## Imports Required

```swift
import CoreAudio
import CoreAudioTypes
// AVFoundation is already implied by AVAudioEngine
```

## Pitfalls

- `audioEngine.inputNode.audioUnit` is `Optional<AudioUnit>` — unwrap with `guard let`
- `AudioUnitSetProperty` with `&deviceID` requires `var deviceID`, not `let`
- CFString pointer: use `&uidRef` with `AudioObjectGetPropertyData` but cast as `String?` after
- This routing must happen AFTER `installTap()` but BEFORE `audioEngine.start()`
- On device disconnection mid-recording, engine may crash — not handled here; wrap in recovery in production

## Hardware Verification Checklist

- [ ] Multi-device Mac (built-in mic + USB audio interface or Bluetooth headset)
- [ ] Select non-default device in Settings → verify RecordingView shows correct device name
- [ ] Start recording → verify waveform / levels appear
- [ ] Unplug selected device during recording → verify fallback to default without crash
- [ ] Stop → restart → verify selection persists across launches
