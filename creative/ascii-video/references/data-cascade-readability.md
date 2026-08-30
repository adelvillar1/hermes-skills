# Data Cascade Readability — Trail vs Brightness

When rendering a "matrix rain" or data-cascade effect where characters stream vertically, the readability of individual streams depends on three parameters that must be balanced.

## The Problem

A cascade with a long trail (8+ characters per column) and uniform brightness produces a solid wall of light. Individual "drops" blend together and the viewer cannot distinguish the direction or pace of the stream. The background becomes invisible.

## The Fix (tested in production)

Use a **short trail** with **sharp brightness falloff** and **distinct characters per position**:

| Position | Character | Brightness | Color |
|----------|-----------|------------|-------|
| Head (0) | Block `█` | 220 | Bright teal — clearly visible leading edge |
| Echo 1 | Terminal symbol from palette | 140 | Dimmer teal |
| Echo 2 | Dot `·` | 70 | Faint blue |
| Tail (3) | Dot `·` | 30 | Whisper |

**Key rules:**
- **4 characters max** per column trail. More than 4 blends into a solid smear.
- **Head must be a block character** (`█`) not a narrow symbol. The head is the visual anchor that defines the stream's position.
- **Brightness drops exponentially**: 220 → 140 → 70 → 30 (roughly halving each step).
- **Color shifts**: head is greenest/tealest, tail fades toward blue. This helps the eye distinguish depth.
- **Spacing**: place echoes every 3 rows (`head - i * 3`) not every row. Closer spacing creates density that defeats readability.
- **Sparse columns per frame**: not every column needs an active stream. 60-70% coverage leaves enough background visible for context.

## Implementation Pattern

```python
for c in range(cols):
    head = cascade_heads[c]
    for i in range(4):  # TRAIL LENGTH — never more than 4
        row = head - i * 3
        if 0 <= row < rows:
            if i == 0:
                ch[row, c] = "█"; co[row, c] = (50, 220, 110)     # head: bright block
            elif i == 1:
                ch[row, c] = PAL[i]; co[row, c] = (30, 140, 80)   # echo: dim terminal
            elif i == 2:
                ch[row, c] = "·"; co[row, c] = (20, 70, 50)       # fade: faint dot
            else:
                ch[row, c] = "·"; co[row, c] = (10, 30, 20)       # tail: whisper
```

## Scene Duration vs TTS Audio

When rendering narrated scenes, always measure the actual TTS audio duration and match the scene duration to it, not the reverse. Hardcoding scene durations (22s, 25s, etc.) will cut off the narration if the TTS is longer.

**Check and fix:**
```python
tts_dur = ffprobe_audio_duration("scene1.ogg")
clip_dur = ffprobe_video_duration("clip_00.mp4")
if tts_dur > clip_dur:
    pad_seconds = tts_dur - clip_dur
    # Use ffmpeg tpad filter to add frozen last frame:
    # tpad=stop_mode=clone:stop_duration={pad_seconds}
```
