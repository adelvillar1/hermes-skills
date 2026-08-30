# Hero Carousel Pattern — Entity Detail Pages

Three implementations sharing the same visual structure. Each has a full-width photo with dark overlay, entity name with text shadow, metadata badge, and favorite button.

## Ship Hero (single slide)

```jsx
// ShipHeroCarousel.js — simplest variant, no FlatList needed
export default function ShipHeroCarousel({ ship, shipId }) {
  const heroUri = getShipHeroUrl(shipId);
  return (
    <View style={styles.container}>
      <Image source={{ uri: heroUri }} style={styles.heroImage} resizeMode="cover" />
      <View style={styles.overlay} />
      <View style={styles.textWrap}>
        <View style={styles.textTop}>
          <View style={styles.nameWrap}>
            <Text style={styles.shipName}>{ship.name}</Text>
            {ship.cruiseLine && (
              <View style={styles.cruiseLinePill}>
                <Text style={styles.cruiseLineText}>{ship.cruiseLine.toUpperCase()}</Text>
              </View>
            )}
          </View>
          <FavoriteButton entityType="ship" entityId={shipId} />
        </View>
      </View>
    </View>
  );
}
```

## Port Hero (multi-slide: photo + SVG map + 2D projection)

⚠️ **Critical: SVG and 2D map use SEPARATE endpoints.** The `/map` endpoint returns JPEG when a rendered map image exists. SVG must be fetched from a dedicated `/map/svg` endpoint — otherwise the SVG fetch gets JPEG bytes and `SvgXml` receives garbage.

```jsx
// PortHeroCarousel.js — FlatList horizontal, builds slides dynamically
const CARD_WIDTH = SCREEN_WIDTH - spacing.xl * 2;
const DEFAULT_HEIGHT = 280;

function parseSvgViewBox(xml) {
  const m = xml && xml.match(/viewBox=\"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\"/);
  if (m) {
    const ratio = parseFloat(m[4]) / parseFloat(m[2]); // height / width
    if (ratio > 0 && ratio < 3) return Math.ceil(CARD_WIDTH * ratio);
  }
  return DEFAULT_HEIGHT;
}

// Fix SVG to fill like resizeMode="cover" — no letterboxing
function svgToCover(xml) {
  return xml.replace(
    /preserveAspectRatio="[^"]*"/,
    'preserveAspectRatio="xMidYMid slice"'
  );
}

// Build slides
const slides = [];
if (port.hasHeroImage) slides.push({ type: 'hero', uri: getPortHeroUrl(slug) });
if (port.hasMap) {
  slides.push({ type: 'svg' });
  fetch(getPortMapSvgUrl(slug))  // ← dedicated SVG endpoint
    .then((res) => (res.ok ? res.text() : null))
    .then((xml) => {
      if (xml) {
        setSvgXml(svgToCover(xml));            // patch preserveAspectRatio
        setCarouselHeight(parseSvgViewBox(xml));  // dynamic height from viewBox
      }
    })
    .catch(() => {});
}
if (port.hasMapImage) slides.push({ type: '2d', uri: getPortMapUrl(slug) });  // JPEG
if (slides.length === 0) slides.push({ type: 'text' });  // fallback

// Carousel container — ONE height for all slide types
<View style={[styles.container, { height: carouselHeight }]}>
  <FlatList ... getItemLayout uses CARD_WIDTH for proper paging />
</View>

// SVG slide — preserveAspectRatio="slice" fills edge-to-edge, no bg hack needed
if (item.type === 'svg') {
  return (
    <View style={[styles.slide, { height: carouselHeight }]}>
      <SvgXml xml={svgXml} width={CARD_WIDTH} height={carouselHeight} />
      <View style={styles.slideLabelWrap}>
        <Text style={styles.slideLabel}>Location Map</Text>
      </View>
    </View>
  );
}

// 2D projection slide — JPEG rendered map
if (item.type === '2d') {
  return (
    <View style={[styles.slide, { height: carouselHeight }]}>
      <Image source={{ uri: item.uri }} style={styles.slideImage} resizeMode="cover" />
      <View style={styles.slideLabelWrap}>
        <Text style={styles.slideLabel}>Port Map</Text>
      </View>
    </View>
  );
}

// Hero slide: photo with overlay (clips to carouselHeight)
if (item.type === 'hero') {
  return (
    <View style={[styles.slide, { height: carouselHeight }]}>
      <Image source={{ uri: item.uri }} style={styles.slideImage} resizeMode="cover" />
      <View style={styles.heroOverlay} />
      <View style={styles.heroTextWrap}>
        <Text style={styles.portNameLight}>{port.portName}</Text>
        <FavoriteButton entityType="port" entityId={slug} />
        {port.countryCode && <Text style={styles.portCountryLight}>{port.countryCode}</Text>}
      </View>
    </View>
  );
}
```

### SVG sizing — the right way (no hacks)

The root cause of grey bars/letterboxing is always `preserveAspectRatio="xMidYMid meet"`. Fix it to `slice` before rendering. Do NOT use dark backgrounds, extra heights, or conditional sizing.

| Symptom | Wrong fix | Right fix |
|---------|-----------|-----------|
| Grey bars above/below SVG | Dark `backgroundColor` to hide them | Patch SVG: `preserveAspectRatio="xMidYMid slice"` |
| Label clipped at bottom | Add +28px to slide height | Move label to `top: spacing.md` (avoids border-radius curve) |
| Inconsistent slide heights | Conditional height per slide type | One `carouselHeight` for all slides |

### API: dual map endpoints for ports

```
GET /api/ports/:slug/map      → JPEG rendered map (port_map_images table, preferred)
GET /api/ports/:slug/map/svg  → SVG location map ONLY (port_location_map_svgs table)
```

Both endpoints must exist separately because the `/map` endpoint prefers JPEG and falls back to SVG. A carousel trying to fetch SVG from `/map` gets JPEG bytes instead → `SvgXml` fails silently.

### Dynamic viewBox height — no grey bands

Port SVGs may have different viewBoxes (e.g., `0 0 600 400`). The carousel height is computed from the SVG's viewBox ratio, not a fixed pixel value. Image slides (hero, 2D) fill the same height and clip via `overflow: 'hidden'` on the container.

## Itinerary Hero (multi-slide: route map SVG + ship photo)

```jsx
// ItineraryHeroCarousel.js — SVG first, ship image second
const slides = [];
if (itinerary.detailDarkSvg) slides.push({ type: 'svg', xml: itinerary.detailDarkSvg });
if (itinerary.shipImageUrl) slides.push({ type: 'image', uri: itinerary.shipImageUrl });

// SVG slide height computed from viewBox ratio (800×500 → 0.625)
const CARD_WIDTH = SCREEN_WIDTH - spacing.xl * 2;
const SVG_HEIGHT = Math.ceil(CARD_WIDTH * 0.625);
```

## Key differences between implementations

| Aspect | Ship | Port | Itinerary |
|--------|------|------|-----------|
| Slides | 1 (photo) | 0–3 (photo, SVG, 2D) | 2 (SVG, photo) |
| Carousel | Direct Image | FlatList | FlatList |
| Dot indicators | No | Yes (if multi) | Yes |
| Overlay opacity | 0.4 | 0.35 | 0.45 |
| Badge | Cruise line + tier | Country code | Cruise line + ship name + duration |
| SVG source | N/A | Fetch from dedicated `/map/svg` endpoint | Inline in API response |
| Height | Fixed (280px) | Dynamic (from SVG viewBox) | Dynamic (fixed ratio 0.625) |
| SVG letterbox fix | N/A | Patch `preserveAspectRatio` to `slice` | N/A |

## Page integration pattern

When adding a hero carousel to a detail screen:
1. Place it as the FIRST element in `ListHeaderComponent`
2. Remove the entity name + favorite button from the card below (they're now in the hero)
3. Keep description and detail sections in the card below
4. Example page order: Hero → Description → At a Glance → Onboard → Overview Carousel → Date Filters → Results
