# Audio Import & WAV Conversion Pipeline

Importing MP3, M4A, AIFF, or other audio formats for local transcription requires converting to WAV (PCM 16-bit mono 16kHz) because speech-to-text engines expect standardized raw PCM.

## Scribe Session Pattern (2026-05-30)

1. **Validate** the dragged/shared file is audio/video via `UTType.audio` / `UTType.movie`
2. **Copy** to app support directory with UUID filename (avoids external renames breaking references)
3. **Convert** using `AVAudioEngine`:

```swift
import AVFoundation

func convertToWAV(source: URL, outputDir: URL) async throws -> URL {
    let engine = AVAudioEngine()
    let player = AVAudioPlayerNode()
    engine.attach(player)
    
    let file = try AVAudioFile(forReading: source)
    let format = file.processingFormat
    engine.connect(player, to: engine.mainMixerNode, format: format)
    try engine.start()
    player.scheduleFile(file, at: nil)
    player.play()
    
    // Render to PCM buffer and write WAV header + data
    let outputURL = outputDir.appendingPathComponent("\(UUID().uuidString).wav")
    // ... render + write implementation (see full AVAudioEngine docs)
    return outputURL
}
```

4. **Store** `originalURL`, `convertedURL`, and MIME type in the meeting record
5. **Transcribe** via the same pipeline as live recordings but with file input (`transcribeFile()`)
6. **Mark status** `.imported` so UI shows distinct import badge

## Storage Path

`~/Library/Application Support/<AppName>/audio/<uuid>.wav`

## Error Handling

- Unsupported format: show alert with allowed formats
- Conversion failure: mark meeting `.error` with description
- Interrupted import: recover on next launch via pending imports scan
