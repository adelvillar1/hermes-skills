# CSS Sprite Resizing & overflow:hidden Clipping Pitfalls

Two related failure modes from a mobile card-viewer iteration (2026-08-23, the mahjong VTT) where tiles rendered as "blank green backs" and hand cards rendered empty. Both are class-level: any CSS-sprite icon/tile system and any auto-height list item with taller inner content.

## Pitfall 1 — Never resize CSS-sprite elements via CSS width/height

When an element's background is a sprite whose `background-size` / `background-position` are computed **inline from the element's own width** (atlas tiles, sprite icons):

```
displayW = 26
displayH = round(ATLAS_CELL_H / ATLAS_CELL_W * displayW)   // 26 → 33
style = { width: displayW, height: displayH,
          backgroundSize: `${colsX * w}px ${rowsY * h}px`,
          backgroundPosition: `${-u0 * colsX * w}px ${-topFrac * rowsY * h}px` }
```

A CSS rule forcing different dimensions (especially `!important`) desyncs the sprite:

- The inline `background-size` stays sized for the ORIGINAL dimensions.
- Forcing `height: 34px` on a bgSize computed for 33px squashes vertically AND drifts every row boundary ~1px per row.
- By atlas rows 3–6 the element's window straddles two cells → faces render as smeared/blank backs.

**Fix:** change the source value (`displayW`) so bgSize recomputes. Never override sprite dimensions in CSS.

### Diagnosing

Compare computed vs expected background-size:

```
computed.backgroundSize === "227.5px 231px"   // sized for h=33
CSS-implied would be 7 * 34 = 238             // mismatch = desync
```

### Rounding gotcha when reproducing the math in analysis scripts

JS `Math.round(32.5)` = 33 (half rounds up). Python `round(32.5)` = 32 (banker's rounding). Emulate JS with `math.floor(x + 0.5)` or your verification numbers will disagree with the browser by a pixel and send you chasing ghosts.

## Pitfall 2 — overflow:hidden on auto-height list items silently empties them

Adding `overflow: hidden` to a card/row whose **inner content is taller than its collapsed header** (sample strip, image, expanded groups) clips that content to a sliver. Cards render "empty," showing only header/badges.

Live case: hand cards showed only score badges; tile strips were 53px tall inside 44px boxes → 6px visible sliver. Two separate rules carried the same `overflow: hidden` (one from an earlier overlap-containment fix); both had to go.

**Fix:** let content size the container. A flex column layout prevents sibling overlap on its own — clipping is not needed for containment, and it destroys content.

## Verifying "empty element" bugs without vision

When screenshots are ambiguous (vision service at capacity / timing out), measure child geometry vs parent geometry directly via `page.evaluate`:

```js
() => {
  const strip = card.querySelector('.hand-sample');
  const sr = strip.getBoundingClientRect();
  const cr = card.getBoundingClientRect();
  return {
    stripH: Math.round(sr.height),
    visibleH: Math.max(0, Math.min(sr.bottom, cr.bottom) - sr.y),
    tileCount: strip.querySelectorAll('.hand-sample-tile').length,
    bgSize: getComputedStyle(strip.querySelector('.hand-sample-tile')).backgroundSize,
  };
}
```

Interpretation:
- Strip present, N tiles, but `visibleH` ≈ 6px → **clipping bug**, not rendering.
- `background-size` ≠ inline-derived expectation → **sprite sizing desync**.
- Also check `scrollHeight > clientHeight` on scroll containers, and remember flex children need `min-height: 0` or they grow to fit content and never scroll.

Companion to `css-grid-layout-assertions.md`: assertions prove structure; these probes prove *why* something renders wrong.

## Vision service degradation pattern

When `your vision tool` returns repeated timeouts / 429 "capacity upstream" errors, don't loop retries — fall back to DOM geometry measurement above, then retry vision between other steps (capacity often recovers in minutes).

macOS screenshot filename gotcha: names contain U+202F (narrow no-break space) before AM/PM (`Screenshot 2026-08-23 at 3.16.45\u202fPM.png`). Literal-string paths fail with "media file not found." Copy via `os.listdir` + match + `shutil.copy2`, or glob by date fragment.
