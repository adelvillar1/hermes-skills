---
name: react-native-patterns
description: "Reusable React Native UI patterns — SectionList refactors, selection mode, animated FABs, carousel components. Reference library for common mobile UX implementations."
version: 1.0.0
metadata:
  hermes:
    tags: [react-native, mobile, ui-patterns, expo]
    related: []
---

# React Native Patterns

Reference library for common React Native UI patterns. Each pattern includes the approach, key code snippets, and pitfalls.

## When to Use

Load this skill when:
- Refactoring ScrollView+FlatList anti-patterns to SectionList
- Building selection/comparison modes on list screens
- Creating swipeable carousels with dot indicators
- Adding animated floating action buttons
- Rendering inline SVG from API responses (route maps, deck plans)
- Setting up screen navigation across multiple navigator stacks
- Getting "screen doesn't exist in navigator" errors
- Filter pills overflowing screen (too many options for horizontal scroll)
- Needing cascading/drilldown filter UI (group → item)
- Adding hero image carousels to entity detail pages (ship, port, itinerary)
- Building multi-select toggle grids (month pickers, tag filters)
- App bypasses login screen and goes straight to main tabs
- Need auth gate before main navigator (conditional screen rendering)
- Duplicated filter pill bar across screens (extract shared component)
- FlatList header (pill bar, filter, summary) stretches vertically when list is empty

---

## Pattern 1: ScrollView+FlatList → SectionList Refactor

**Problem:** `ScrollView` wrapping `FlatList scrollEnabled={false}` disables virtualization and causes React Native warnings. Common anti-pattern in detail screens with a header + list.

**Solution:** Single `SectionList` with `ListHeaderComponent` for the header content.

### Before (anti-pattern)
```jsx
<ScrollView stickyHeaderIndices={[2]}>
  {/* Hero */}
  <View>...</View>
  {/* Filters */}
  <View>...</View>
  {/* Sticky heading */}
  <View>...</View>
  <FlatList
    data={items}
    scrollEnabled={false}    // ← disables windowing
    renderItem={...}
  />
</ScrollView>
```

### After (correct)
```jsx
<SectionList
  sections={[{ title: 'items', data: items }]}
  keyExtractor={(item) => item.id}
  ListHeaderComponent={
    <>
      {/* Hero */}
      <View>...</View>
      {/* Filters */}
      <View>...</View>
      {/* Heading */}
      <View>...</View>
    </>
  }
  stickyHeaderIndices={[3]}  // index within ListHeaderComponent
  renderItem={...}
/>
```

### Key decisions
- `stickyHeaderIndices` counts from the start of `ListHeaderComponent`, not the section headers
- For screens with tabs (e.g., itineraries vs cruise lines), build `sections` dynamically based on active tab
- Empty state goes in `ListEmptyComponent`, footer (load more) in `ListFooterComponent`
- `contentContainerStyle` replaces ScrollView's padding

### Pitfalls
- `stickyHeaderIndices` on SectionList applies to the ListHeaderComponent indices, NOT section headers. If you have 4 header elements and want the 4th to stick, use `stickyHeaderIndices={[3]}`
- SectionList's `renderSectionHeader` is separate from `ListHeaderComponent` — don't confuse the two
- When switching sections based on tab state, the list re-renders from scratch. If scroll position matters, save and restore it

---

## Pattern 2: Selection Mode with Long-Press

**Problem:** Users need to select multiple items from a list for batch action (compare, export, delete).

**Solution:** Long-press enters selection mode. Tap toggles. Animated FAB for action. Clear on blur.

### State
```jsx
const [selectionMode, setSelectionMode] = useState(false);
const [selectedIds, setSelectedIds] = useState(new Set());
const fabAnim = useRef(new Animated.Value(0)).current;
```

### Enter selection mode
```jsx
onLongPress={() => {
  if (!selectionMode) {
    setSelectionMode(true);
    setSelectedIds(new Set([item.id]));
  }
}}
```

### Toggle selection
```jsx
onPress={() => {
  if (selectionMode) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(item.id)) {
        next.delete(item.id);
        if (next.size === 0) setSelectionMode(false); // auto-exit
      } else if (next.size < MAX) {
        next.add(item.id);
      }
      return next;
    });
  } else {
    // normal navigation
  }
}}
```

### Animated FAB
```jsx
useEffect(() => {
  Animated.spring(fabAnim, {
    toValue: selectedIds.size >= 2 ? 1 : 0,
    useNativeDriver: true,
    tension: 60,
    friction: 8,
  }).start();
}, [selectedIds]);

// Wrap with pointerEvents to prevent ghost taps
<Animated.View
  style={{ transform: [{ translateY: fabAnim.interpolate({...}) }], opacity: fabAnim }}
  pointerEvents={selectedIds.size >= 2 ? 'auto' : 'none'}
>
```

### Clear on blur (navigation leave)
```jsx
useEffect(() => {
  const unsubscribe = navigation.addListener('blur', () => {
    setSelectionMode(false);
    setSelectedIds(new Set());
  });
  return unsubscribe;
}, [navigation]);
```

### Pitfalls
- Always auto-exit selection mode when last item is deselected
- Use `pointerEvents="none"` on hidden FAB to prevent ghost taps
- `new Set()` for O(1) lookup — don't use array for selectedIds
- Max selection count should be enforced in the toggle logic, not just the UI

---

## Pattern 3: Swipeable Carousel with Dot Indicators

**Problem:** Multiple content types (photo, map, chart) for a single entity need swipeable presentation.

**Solution:** FlatList with `pagingEnabled`, `horizontal`, snapToInterval, and dot indicators.

### Structure
```jsx
<FlatList
  data={slides}
  horizontal
  pagingEnabled
  showsHorizontalScrollIndicator={false}
  keyExtractor={(_, i) => String(i)}
  renderItem={({ item }) => <SlideComponent data={item} />}
  onViewableItemsChanged={onViewableItemsChanged}
  viewabilityConfig={{ viewAreaCoveragePercentThreshold: 50 }}
/>
<View style={styles.dots}>
  {slides.map((_, i) => (
    <View key={i} style={[styles.dot, currentIndex === i && styles.dotActive]} />
  ))}
</View>
```

### Pitfalls
- `onViewableItemsChanged` must be wrapped in `useCallback` or stored in a ref — recreating it on every render causes FlatList to re-register the listener
- `viewAreaCoveragePercentThreshold: 50` means 50% of the item must be visible to count as "viewable"
- For mixed slide types (photo vs SVG map), conditionally render based on asset availability — don't show empty slides

---

## Pattern 4: Score Bars (Data Viz without Charts)

**Problem:** Need to visualize scores (0-100) without adding a charting library dependency.

**Solution:** Pure View-based horizontal bars. No `react-native-svg`, no third-party charts.

```jsx
function ScoreBar({ label, score, color = '#D9534F' }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
      <Text style={{ width: 70, fontSize: 11, color: '#78716C' }}>{label}</Text>
      <View style={{ flex: 1, height: 8, backgroundColor: '#F5F5F4', borderRadius: 4, marginHorizontal: 8 }}>
        <View style={{ width: `${score}%`, height: 8, borderRadius: 4, backgroundColor: color }} />
      </View>
      <Text style={{ width: 28, textAlign: 'right', fontSize: 11, color: '#A8A29E' }}>{score}</Text>
    </View>
  );
}
```

### Pitfalls
- Score must be 0-100 (percentage). Clamp before rendering
- Use different colors per category (family=blue, couples=red, luxury=purple) for quick scanning
- Background bar color should be very light (`inputBg` or similar) — not white (invisible on white canvas)

---

## Pattern 5: Dynamic Slide Carousel (Data-Driven)

**Problem:** Carousel slides depend on API data — some slides may not render if data is missing. Need to build slides dynamically and handle partial data gracefully.

**Solution:** Build slides array from available data, filter nulls, pass to FlatList.

```jsx
// Build slides — omit when data is null
const slides = [];
slides.push({ key: 'overview', component: <OverviewSlide data={data} /> });
if (data.venueProfile) slides.push({ key: 'venues', component: <VenueSlide data={data} /> });
if (data.cabinProfile) slides.push({ key: 'cabins', component: <CabinSlide data={data} /> });
if (data.narrative) slides.push({ key: 'narrative', component: <NarrativeSlide data={data} /> });

// Don't render carousel if only one slide
if (slides.length < 2) return null;

return (
  <FlatList
    data={slides}
    horizontal
    pagingEnabled
    keyExtractor={(item) => item.key}
    renderItem={({ item }) => (
      <View style={{ width: SLIDE_WIDTH, paddingRight: 16 }}>
        {item.component}
      </View>
    )}
    // ... dot indicators
  />
);
```

### Pitfalls
- Always check `slides.length < 2` — a single-slide carousel is confusing UX (no swipe affordance)
- Each slide component should handle its own null checks internally (defense in depth)
- `SLIDE_WIDTH` should be `SCREEN_WIDTH - padding` so slides fill the viewport
- The "overview" slide (stats summary) is always shown — conditional slides come after it

**Full example:** See `references/report-card-carousel-example.md` for the complete component with API shapes, score bar colors, and wiring pattern.

---

## Pattern 6: Dev Auth Bypass (OAuth-less Testing)

**Problem:** Need to test the app on iOS Simulator without Apple Developer account or Google OAuth credentials.

**Solution:** `__DEV__`-gated "Browse as Guest" button on LoginScreen that calls `login()` with a fake token. SecureStore calls wrapped in try/catch for unsigned builds.

**Full implementation:** See `references/dev-auth-bypass.md` for the complete LoginScreen button, AuthContext fix, and what works/doesn't with a dev token.

### Pitfalls
- `expo-secure-store` throws "A required entitlement isn't present" in unsigned simulator builds — always wrap `SecureStore.setItemAsync()` in try/catch
- The dev token (`dev-bypass-token`) is not a valid JWT — `/api/me/*` endpoints return 401. Browse features work; persistence features don't
- `__DEV__` is `false` in production builds — the bypass button is automatically hidden

---

## Pattern 7: Infinite Scroll Pagination

**Problem:** Browser/search screens fetch only page 1. Users can't see all items.

**Solution:** FlatList `onEndReached` with page tracking and loading footer.

### State
```jsx
const [items, setItems] = useState([]);
const [page, setPage] = useState(1);
const [hasMore, setHasMore] = useState(true);
const [loadingMore, setLoadingMore] = useState(false);
```

### Load more function
```jsx
function loadMore() {
  if (loadingMore || !hasMore) return;
  setLoadingMore(true);
  getItems({ page: page + 1, limit: 50 })
    .then((data) => {
      const newItems = data.items || [];
      setItems((prev) => [...prev, ...newItems]);
      setPage((p) => p + 1);
      setHasMore(newItems.length >= 50); // if fewer than limit, no more pages
    })
    .catch(console.error)
    .finally(() => setLoadingMore(false));
}
```

### FlatList wiring
```jsx
<FlatList
  data={items}
  onEndReached={loadMore}
  onEndReachedThreshold={0.5}
  ListFooterComponent={
    loadingMore ? <ActivityIndicator style={{ paddingVertical: 16 }} /> : null
  }
/>
```

### Pitfalls
- `onEndReachedThreshold={0.5}` triggers at 50% before the end — adjust based on item height
- Always guard `loadMore` with `loadingMore || !hasMore` to prevent double-fetches
- `setItems((prev) => [...prev, ...newItems])` uses the callback form to avoid stale closures
- The `hasMore` check should use `newItems.length >= limit` (not total pages from API) — more reliable
- For screens with search filters, reset `page=1`, `hasMore=true`, and `items=[]` when filters change

---

## Pattern 8: Shared Favorites Context (N+1 Fix)

**Problem:** `FavoriteButton` component calls `getFavorites()` on every mount. Inside a FlatList with 20 items, this fires 20 identical API calls on page load.

**Solution:** React Context that fetches favorites once on auth, shares state across all components.

### Context provider
```jsx
const FavoritesContext = createContext();

export function FavoritesProvider({ children }) {
  const [favorites, setFavorites] = useState(new Set());
  const { user } = useContext(AuthContext);

  const refresh = useCallback(() => {
    if (!user) { setFavorites(new Set()); return; }
    getFavorites()
      .then((data) => {
        const set = new Set(
          (data.favorites || []).map((f) => `${f.entityType}:${f.entityId}`)
        );
        setFavorites(set);
      })
      .catch(() => {});
  }, [user]);

  useEffect(() => { refresh(); }, [refresh]);

  const addFavorite = useCallback(async (entityType, entityId) => {
    await addFavoriteAPI(entityType, entityId);
    setFavorites((prev) => new Set(prev).add(`${entityType}:${entityId}`));
  }, []);

  const removeFavorite = useCallback(async (entityType, entityId) => {
    await removeFavoriteAPI(entityType, entityId);
    setFavorites((prev) => {
      const next = new Set(prev);
      next.delete(`${entityType}:${entityId}`);
      return next;
    });
  }, []);

  return (
    <FavoritesContext.Provider value={{ favorites, refresh, addFavorite, removeFavorite }}>
      {children}
    </FavoritesContext.Provider>
  );
}

export function useFavorites() { return useContext(FavoritesContext); }
```

### FavoriteButton using context
```jsx
export default function FavoriteButton({ entityType, entityId }) {
  const { favorites, addFavorite, removeFavorite } = useFavorites();
  const isFav = favorites.has(`${entityType}:${entityId}`);

  const toggle = () => {
    if (isFav) removeFavorite(entityType, entityId);
    else addFavorite(entityType, entityId);
  };

  return (
    <TouchableOpacity onPress={toggle}>
      <Icon name={isFav ? 'heart' : 'heart-outline'} />
    </TouchableOpacity>
  );
}
```

### Pitfalls
- Composite key format (`entityType:entityId`) prevents collisions and enables O(1) Set lookups
- Use `new Set(prev).add()` (immutable update) — never mutate the Set in place
- Wrap the provider around the app AFTER AuthContext — favorites depend on auth state
- `refresh()` on logout clears favorites to empty Set
- The context handles the API call AND optimistic UI update — FavoriteButton becomes a pure presenter

---

## Pattern 9: Inline SVG Rendering from API Data

**Problem:** API returns SVG as inline XML strings (not URLs). Need to render them in React Native — e.g., route maps, deck plans, projection maps. The SVG must fill its container without cropping, letterboxing, or collapsing.

**Solution:** Use `SvgXml` from `react-native-svg` with dimensions computed from the SVG's viewBox aspect ratio.

### Basic rendering

```jsx
import { SvgXml } from 'react-native-svg';

function RouteMapSlide({ svgString }) {
  if (!svgString) return null;
  return (
    <SvgXml xml={svgString} width={CARD_WIDTH} height={CARD_WIDTH * 0.625} />
  );
}
```

### Carousel with SVG (correct sizing)

The SVG viewBox defines the intrinsic aspect ratio. Use it to compute the carousel height — never hardcode a pixel height or you get cropping or grey letterboxing.

```jsx
import { SvgXml } from 'react-native-svg';

const CARD_WIDTH = SCREEN_WIDTH - padding * 2;
const SVG_RATIO = 500 / 800;   // from viewBox="0 0 800 500"
const CAROUSEL_HEIGHT = Math.ceil(CARD_WIDTH * SVG_RATIO);

// SVG slide — exact fit, no bars
<SvgXml xml={svgString} width={CARD_WIDTH} height={CAROUSEL_HEIGHT} />

// Image slide — clips to same height
<Image source={{ uri }} style={{ width: CARD_WIDTH, height: CAROUSEL_HEIGHT }} resizeMode="cover" />
```

### ⚠️ Three Ways to Break SvgXml Sizing (all happened in production)

| Attempt | What happens | Why |
|---------|-------------|-----|
| `width={W} height={FIXED}` (e.g. 280px) | SVG crops/zooms — route edges clipped | Fixed height ≠ viewBox ratio → forced cover behavior |
| `width={W}` (no height) | SVG renders at **0 height** — invisible | `react-native-svg` can't infer height from viewBox alone |
| `width={W} height={W * ratio}` | ✅ Correct — fits perfectly | Computed height matches the viewBox aspect ratio |

**The rule:** Always compute height from `viewBox`. Parse it from the SVG string if it varies across assets:
```jsx
function getViewBoxRatio(xml) {
  const m = xml.match(/viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"/);
  return m ? parseFloat(m[2]) / parseFloat(m[1]) : 0.625; // fallback 5:8
}

// For carousels where viewBox varies per entity, use dynamic state:
const [carouselHeight, setCarouselHeight] = useState(DEFAULT_HEIGHT);
// Then in SVG fetch:
.then((xml) => {
  if (xml) {
    setSvgXml(xml);
    setCarouselHeight(Math.ceil(CARD_WIDTH * getViewBoxRatio(xml)));
  }
})
// Container: <View style={[styles.container, { height: carouselHeight }]}>
// SVG slide: <SvgXml xml={svgXml} width={CARD_WIDTH} height={carouselHeight} />
// Image slides: fill the same height, clip via overflow: 'hidden'
```

### Carousel wrapper — no grey letterboxing

When mixing SVG slides with image slides in a carousel, set the carousel height to `Math.ceil(CARD_WIDTH * SVG_RATIO)` — NOT a fixed pixel value like `280`. A fixed height taller than the SVG's natural height creates grey bars above/below; shorter crops the content.

```jsx
// ✅ Dynamic — SVG fills edge-to-edge after preserveAspectRatio fix
const CAROUSEL_HEIGHT = Math.ceil(CARD_WIDTH * SVG_RATIO);

// SVG slide — preserveAspectRatio="slice" fills like resizeMode="cover"
<View style={{ width: CARD_WIDTH, height: CAROUSEL_HEIGHT, overflow: 'hidden', borderRadius: 16 }}>
  <SvgXml xml={svgToCover(svgString)} width={CARD_WIDTH} height={CAROUSEL_HEIGHT} />
</View>

// Image slide — same container size, image uses resizeMode="cover"
<View style={{ width: CARD_WIDTH, height: CAROUSEL_HEIGHT, overflow: 'hidden', borderRadius: 16 }}>
  <Image source={{ uri }} style={{ width: CARD_WIDTH, height: CAROUSEL_HEIGHT }} resizeMode="cover" />
</View>
```

**SVG `preserveAspectRatio` must be changed to `slice` before rendering.** The SVGs produced by most generators (including CI route/location maps) use `preserveAspectRatio="xMidYMid meet"`, which letterboxes the content — creating grey bars when the container aspect ratio doesn't perfectly match. The correct fix is NOT dark backgrounds or extra padding. Patch the SVG XML to use `slice` (equivalent to `resizeMode="cover"`):

```jsx
// Fix the SVG to fill like cover — no bars, no gaps
function svgToCover(xml) {
  return xml.replace(
    /preserveAspectRatio="[^"]*"/,
    'preserveAspectRatio="xMidYMid slice"'
  );
}

// Apply before setting state
.then((xml) => {
  if (xml) {
    setSvgXml(svgToCover(xml));
    setCarouselHeight(parseSvgViewBox(xml));
  }
})
```

**Overlay labels must be at `top`, not `bottom`.** Placing labels at `bottom: spacing.md` puts them inside the container's `borderRadius` curve, where they get clipped by `overflow: 'hidden'`. Position all carousel labels consistently at the top-right:

```jsx
slideLabelWrap: {
  position: 'absolute',
  top: spacing.md,     // NOT bottom — avoids border-radius clipping
  right: spacing.md,
  backgroundColor: 'rgba(0,0,0,0.55)',
  ...
},
```

**Do NOT** use `justifyContent: 'flex-end'` on the slide style — it pushes SVG content down from the top, creating a gap. Label overlays use `position: 'absolute'` and don't need flex alignment.

**Do NOT** add dark background hacks, conditional +28px heights, or backgroundColor matching. These are band-aids that mask the real problem. The root cause is always `preserveAspectRatio="meet"` — fix it to `slice`.

### Pitfalls
- **Not a URL** — `SvgXml` takes the raw XML string, not a URI. Don't try to fetch it. The API response includes the SVG inline (e.g., `itinerary.detailDarkSvg`).
- **Missing `react-native-svg`** — This requires `react-native-svg` as a dependency. If not installed, `SvgXml` won't exist. Install with `npx expo install react-native-svg`.
- **Theme-specific SVGs** — Some API endpoints return multiple SVG variants (e.g., `detailDarkSvg` and `detailLightSvg`). Pick the one matching your theme or background color.
- **Large SVGs can be slow** — Complex route maps with hundreds of path elements may render slowly on older devices. Consider a fixed aspect ratio container to avoid layout shifts.
- **Don't render null SVGs** — Always guard with `if (!svgString) return null` or show a fallback. An empty string passed to `SvgXml` throws a parse error.
- **Never use `width="100%"` with a fixed-height parent** — Percentage-based sizing on `SvgXml` doesn't behave like CSS. Use computed pixel dimensions.
- **SVG endpoint must be separate from image endpoint** — If an API endpoint returns JPEG when a rendered image exists (e.g., `/map` prefers JPEG, falls back to SVG), a carousel trying to fetch SVG from that URL gets JPEG bytes → `SvgXml` renders nothing. Create a dedicated endpoint (e.g., `/map/svg`) that queries only the SVG table. This applies whenever a single URL can serve different content types based on data availability.
- **`preserveAspectRatio="meet"` causes grey bars** — Most SVG generators default to `xMidYMid meet` which letterboxes when the container ratio differs. Always patch to `xMidYMid slice` before rendering. Dark backgrounds and extra padding are band-aids, not fixes.
- **Don't position labels at `bottom` inside `overflow: 'hidden'` containers** — The border-radius curve clips them. Use `top: spacing.md` instead. All carousel labels should be consistent (top-right).
- **Don't add conditional heights per slide type** — The carousel container has ONE height. All slides (SVG, image, 2D map) render at that same height. No `+28` hacks for SVG slides.

---

## Pattern 10: Cross-Stack Screen Registration

**Problem:** A screen is registered in one navigator stack (e.g., `MoreStack`) but navigated to from another stack (e.g., `DestinationStack`). React Navigation throws `NAVIGATE` error — "The screen 'PortDetail' doesn't exist in the navigator."

**Solution:** Register the screen in EVERY navigator stack that navigates to it. Detail screens that are reached from multiple entry points (list views, itineraries, search results) must appear in all relevant stacks.

### The pattern

```jsx
// navigation.js — register in each stack that navigates to this screen

const DestinationStack = createStackNavigator();
function DestinationNavigator() {
  return (
    <DestinationStack.Navigator>
      <DestinationStack.Screen name="DestinationHome" component={DestinationHome} />
      <DestinationStack.Screen name="PortDetail" component={PortDetail} />
      <DestinationStack.Screen name="ItineraryDetail" component={ItineraryDetail} />
    </DestinationStack.Navigator>
  );
}

const CruiseLineStack = createStackNavigator();
function CruiseLineNavigator() {
  return (
    <CruiseLineStack.Navigator>
      <CruiseLineStack.Screen name="CruiseLineHome" component={CruiseLineHome} />
      <CruiseLineStack.Screen name="PortDetail" component={PortDetail} />
      <CruiseLineStack.Screen name="ShipDetail" component={ShipDetail} />
    </CruiseLineStack.Navigator>
  );
}
```

### Pitfalls
- **No cross-stack navigation in React Navigation 6+** — `navigation.navigate('PortDetail')` only works if `PortDetail` exists in the CURRENT navigator. There is no global screen registry.
- **The error is silent in production** — In dev mode, React Navigation throws a visible error. In release builds, the tap just does nothing (or crashes on some versions). Always test navigation paths, not just the primary flow.
- **Shared screens import the same component** — Multiple stack registrations reference the same component file. This is fine — React Navigation creates separate route configs, not separate component instances.
- **Check ALL navigation callers** — When adding a new detail screen, grep for `navigation.navigate('ScreenName')` or `navigate('ScreenName')` across all screen files. Every stack whose screens call `navigate('ScreenName')` must register it.
- **Deep linking may still need root-level registration** — If the app supports deep links to detail screens, they may also need registration in the root stack or a linking configuration.

---

## Pattern 11: Multi-Select Date Filter Grid

**Problem:** A horizontal `ScrollView` of 13+ pill options (e.g., All + 12 months) overflows the screen on narrow devices. Users can't see all options and don't realize they need to scroll.

**Solution:** Year selector on top (single-select), then two rows of 6 month chips each (multi-select toggle). No months selected = show all.

### Layout

```
[2026]  [2027]  [2028]              ← year (single select, 3 pills)

[Jan] [Feb] [Mar] [Apr] [May] [Jun] ← row 1 (multi-select toggle)
[Jul] [Aug] [Sep] [Oct] [Nov] [Dec] ← row 2 (multi-select toggle)

        Clear month filter           ← link shown when any months selected
```

**User preference:** "Most people think in terms of year then months" — year filter goes on TOP, not bottom.

### Data

```jsx
const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const MONTH_ROW_1 = [1,2,3,4,5,6];
const MONTH_ROW_2 = [7,8,9,10,11,12];
const YEARS = [2026, 2027, 2028];  // or computed from current year
```

### State

```jsx
const [selectedMonths, setSelectedMonths] = useState(() => {
  return [new Date().getMonth() + 1];  // default to current month
});
const [yearIndex, setYearIndex] = useState(1);

function toggleMonth(m) {
  setSelectedMonths((prev) => {
    if (prev.includes(m)) return prev.filter((x) => x !== m);
    return [...prev, m].sort((a, b) => a - b);
  });
}
```

### Rendering

```jsx
{/* Year row — single select */}
<View style={styles.monthGrid}>
  {YEARS.map((y, i) => (
    <TouchableOpacity
      key={y}
      style={[styles.monthChip, yearIndex === i && styles.monthChipActive]}
      onPress={() => setYearIndex(i)}
    >
      <Text style={[styles.monthChipText, yearIndex === i && styles.monthChipTextActive]}>
        {y}
      </Text>
    </TouchableOpacity>
  ))}
</View>

{/* Month row 1 */}
<View style={styles.monthGrid}>
  {MONTH_ROW_1.map((m) => {
    const active = selectedMonths.includes(m);
    return (
      <TouchableOpacity
        key={m}
        style={[styles.monthChip, active && styles.monthChipActive]}
        onPress={() => toggleMonth(m)}
      >
        <Text style={[styles.monthChipText, active && styles.monthChipTextActive]}>
          {MONTH_NAMES[m - 1]}
        </Text>
      </TouchableOpacity>
    );
  })}
</View>

{/* Month row 2 */}
<View style={styles.monthGrid}>
  {MONTH_ROW_2.map((m) => {
    const active = selectedMonths.includes(m);
    return (
      <TouchableOpacity
        key={m}
        style={[styles.monthChip, active && styles.monthChipActive]}
        onPress={() => toggleMonth(m)}
      >
        <Text style={[styles.monthChipText, active && styles.monthChipTextActive]}>
          {MONTH_NAMES[m - 1]}
        </Text>
      </TouchableOpacity>
    );
  })}
</View>

{/* Clear link */}
{selectedMonths.length > 0 && (
  <TouchableOpacity onPress={() => setSelectedMonths([])}>
    <Text style={styles.clearMonths}>Clear month filter</Text>
  </TouchableOpacity>
)}
```

### Styles

```jsx
monthGrid: {
  flexDirection: 'row',
  justifyContent: 'space-between',
  paddingHorizontal: spacing.xl,
  marginBottom: spacing.xs,
},
monthChip: {
  flex: 1,
  alignItems: 'center',
  paddingVertical: spacing.sm,
  marginHorizontal: 2,
  borderRadius: radii.full,
  backgroundColor: colors.inputBg,
},
monthChipActive: {
  backgroundColor: colors.accent,
},
monthChipText: {
  ...typography.bodyMedium,
  fontSize: 13,
  color: colors.textSecondary,
},
monthChipTextActive: {
  color: colors.textInverse,
},
clearMonths: {
  fontSize: 12,
  color: colors.accent,
  textAlign: 'center',
  marginTop: spacing.xs,
},
```

### API: multi-value filter support

Selected months are sent as comma-separated `months` param. No months selected sends no filter.

```jsx
if (selectedMonths.length > 0 && selectedMonths.length < 12) {
  params.months = selectedMonths.join(',');
}
```

API side — accept both `month` (single) and `months` (comma-separated):

```js
if (month > 0 && month <= 12) {
  conditions.push(`EXTRACT(MONTH FROM departure_date) = $${idx++}`);
  params.push(month);
} else if (monthsParam) {
  const months = monthsParam.split(',').map(Number).filter(m => m >= 1 && m <= 12);
  if (months.length > 0) {
    conditions.push(`EXTRACT(MONTH FROM departure_date) IN (${months.map(() => `$${idx++}`).join(', ')})`);
    params.push(...months);
  }
}
```

### Pitfalls
- **Default to current month** — On load, pre-select the current month so users see relevant sailings immediately
- **Year goes on TOP** — Users think "year first, then months". Don't put years at the bottom
- **No months selected = show all** — Empty `selectedMonths` array means no month filter applied
- **`flex: 1` on each chip** — Distributes evenly across the row. With `marginHorizontal: 2` for gaps. No ScrollView needed
- **Don't use PillFilter for multi-select** — PillFilter assumes single-select (one `activeIndex`). For multi-select, build inline chips directly
- **Sort on add** — `toggleMonth` sorts the array so API params are always in order
- **Clear link is important** — Users need an obvious way to deselect all months without tapping each one
- **Place filters below overview/hero content, not above** — Users see entity info first, then narrow down sailings. Putting filters above the carousel breaks the visual flow

---

## Pattern 12: Entity Hero Image Carousel

**Problem:** Entity detail pages (Ship, Port, Itinerary) need a large hero image at the top with overlaid entity name, metadata badges, and a favorite button — matching a consistent visual pattern across the app.

**Solution:** Single-purpose hero component per entity type, all sharing the same structure: full-width photo → dark gradient overlay → bottom-anchored text + favorite button.

### Shared structure (all 3 hero types)

```
┌─────────────────────────────┐
│                             │
│    [hero photo/image]       │
│                             │
│  ┌───────────────────────── │  ← dark overlay (rgba 0.35–0.45)
│  │ Entity Name        [♡]  │  ← large white text + favorite button
│  │ METADATA PILL           │  ← entity-specific badge
│  └──────────────────────────│
└─────────────────────────────┘
```

### Component skeleton

```jsx
export default function EntityHeroCarousel({ entity, entityId }) {
  const heroUri = getEntityHeroUrl(entityId);  // API binary endpoint

  return (
    <View style={styles.container}>
      <Image source={{ uri: heroUri }} style={styles.heroImage} resizeMode="cover" />
      <View style={styles.overlay} />
      <View style={styles.textWrap}>
        <View style={styles.textTop}>
          <View style={styles.nameWrap}>
            <Text style={styles.entityName}>{entity.name}</Text>
            {/* Entity-specific pill badge */}
            {entity.cruiseLine && (
              <View style={styles.pill}>
                <Text style={styles.pillText}>{entity.cruiseLine.toUpperCase()}</Text>
              </View>
            )}
          </View>
          <FavoriteButton entityType="entityType" entityId={entityId} />
        </View>
      </View>
    </View>
  );
}
```

### Styles (consistent across all hero types)

```jsx
container: {
  marginHorizontal: spacing.xl,
  marginTop: spacing.lg,
  borderRadius: radii.lg,
  overflow: 'hidden',
  height: 280,
},
heroImage: {
  width: SCREEN_WIDTH - spacing.xl * 2,
  height: 280,
},
overlay: {
  ...StyleSheet.absoluteFillObject,
  backgroundColor: 'rgba(28,25,23,0.4)',
},
textWrap: {
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  padding: spacing.lg,
},
entityName: {
  ...typography.displaySmall,
  color: colors.textInverse,
  fontSize: 28,
  lineHeight: 34,
  textShadowColor: 'rgba(0,0,0,0.5)',
  textShadowOffset: { width: 0, height: 1 },
  textShadowRadius: 4,
},
```

### Entity-specific variations

| Entity | Hero source | Badge | Extra slides |
|--------|------------|-------|-------------|
| **Ship** | `GET /ships/:id/hero` (PG binary) | Cruise line name + tier badge | None (single slide) |
| **Port** | `GET /ports/:slug/hero` (PG binary) | Country code | SVG location map, 2D projection |
| **Itinerary** | Ship image + route map SVG | Cruise line pill, ship name, duration | Route map SVG as slide 0 |

### API hero endpoint pattern

All hero endpoints follow the same pattern: binary PG `bytea` column served via `Content-Type: image/jpeg` with `Cache-Control: public, max-age=604800`. If no image exists, return 404 — the mobile app should handle the missing case with a text-only fallback.

### Pitfalls
- **Text shadow is required** — White text on a photo is unreadable without `textShadowColor/Offset/Radius`. Use dark shadow, not the overlay, for text legibility
- **`overflow: 'hidden'` on container** — Without this, the image bleeds past the `borderRadius`
- **Hero replaces the header card** — When adding a hero carousel to an existing detail page, remove the duplicate entity name/favorite button from the header card below. Don't show the same info twice
- **`resizeMode="cover"` on image** — Crops to fill. Use "contain" only for logos/icons
- **Multi-slide heroes (Port, Itinerary)** use FlatList horizontal with paging. Single-slide heroes (Ship) skip the FlatList entirely — just render the Image directly

---

## Pattern 13: Named-Export-Only Module Imports

**Problem:** Importing a default export from a module that only has named exports returns `undefined`. Then destructuring from it crashes: `Cannot read property 'X' of undefined`.

**Solution:** Always check whether a module uses `export default` or only named exports. When it only has named exports, import them directly — never via default + destructuring.

### The bug pattern
```jsx
// Module only has named exports (no `export default`)
export function SkeletonA() { ... }
export function SkeletonB() { ... }

// ❌ BROKEN — no default export, so SkeletonBlocks is undefined
import SkeletonBlocks, { SkeletonBlock } from './SkeletonBlocks';
const { SkeletonA, SkeletonB } = SkeletonBlocks;  // TypeError!

// ✅ CORRECT — import each named export directly
import { SkeletonBlock, SkeletonA, SkeletonB } from './SkeletonBlocks';
```

### How it happens
1. A module starts with `export default X` and some named exports
2. A refactor removes the default export
3. Files that imported `import X, { Y } from` still reference the (now absent) default
4. `X` becomes `undefined` at runtime → `X.Y` throws TypeError
5. **RedBox crash in dev, silent blank in release**

### Detection
- After any module refactor that removes `export default`, grep for `import ModuleName` (without braces) across all consumers
- ESLint `import/no-default-export` rule can prevent this, but most React Native projects don't enable it
- The error message `Cannot read property 'Something' of undefined` at an import line is a telltale sign

### Pitfalls
- **Affects all consumers** — When the module is shared (like a skeleton components file), every screen that imports it breaks simultaneously
- **Easy to miss in refactors** — The module itself is valid JS; only the consumers break
- **Named destructuring looks fine syntactically** — `const { A, B } = X` is valid JS when `X` is undefined, it just throws at runtime
- **Not caught by linters without explicit rules** — Standard ESLint won't flag this

---

## Pattern 14: Conditional Sections — Hide When Data Is Thin

**Problem:** A data-driven section renders but shows generic placeholder labels (e.g., "Package 1", "Package 2" with no description, or rows of "N/A"). This looks broken and erodes trust — users assume the app is incomplete rather than the data being sparse.

**Solution:** If a section doesn't have consistent, meaningful content, don't render it at all. An empty screen with fewer high-quality sections is better than one padded with noise.

### Decision criteria

Show a section when **all** of these hold:
1. Data exists (non-empty array/object)
2. Data has **meaningful** values (not just generic labels like "Item 1", "Item 2")
3. At least 2–3 rows have real content (not just 1 out of 10)

Hide when **any** of these is true:
- Labels are synthetic (auto-numbered: "Package 1", "Option A")
- Core fields (description, price, details) are missing for most items
- The section adds no information beyond what the header already says

### Implementation

```jsx
// BEFORE — shows empty/noise sections
const packages = cl.packages || [];
{packages.length > 0 && (
  <View>
    {packages.map((pkg, i) => (
      <Text>{pkg.name || `Package ${i + 1}`}</Text>  // ← generic fallback = noise
    ))}
  </View>
)}

// AFTER — remove the section entirely
// Delete the rendering block AND the unused variable
```

### Clean removal checklist
1. Remove the rendering block (JSX)
2. Remove the variable extraction (`const packages = ...`)
3. Remove unused styles (pkgCard, pkgName, etc.)
4. API query can stay — removing from the source is sufficient
5. Verify with grep that no references remain

### Pitfalls
- **Don't hide behind a feature flag** — thin data is a content problem, not a rollout problem
- **Don't add "Coming soon" placeholders** — that's worse than the empty space
- **Re-evaluate when data improves** — if the data source gets enriched later, the section can return
- **The API query is harmless** — leaving it in the backend avoids a deploy; just hide the UI

---

## Pattern 15: Auth Gate Navigator

**Problem:** The app always opens to the main tabs regardless of login state. Auth screens exist in the navigator but are never shown first — the app "bypasses" login entirely.

**Root cause:** `RootNavigator` has `initialRouteName="MainTabs"` unconditionally. React Navigation renders the initial route on mount without checking auth state. Even if `AuthLogin` is registered as a screen, it's only reachable via manual `navigation.navigate('AuthLogin')`.

**Solution:** Conditionally render navigator screens based on `isLoggedIn` from the auth store. When logged out, render ONLY `AuthLogin` as the initial route. When logged in, render the main app screens.

```jsx
import { useAuthStore } from '@/store/auth';

export default function RootNavigator() {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn);

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={isLoggedIn ? 'MainTabs' : 'AuthLogin'}
        screenOptions={{...}}
      >
        {!isLoggedIn && (
          <Stack.Screen
            name="AuthLogin"
            component={AuthLoginScreen}
            options={{ headerShown: false }}
          />
        )}
        {isLoggedIn && (
          <>
            <Stack.Screen name="MainTabs" component={MainTabs} options={{ headerShown: false }} />
            <Stack.Screen name="AuthLogin" component={AuthLoginScreen} options={{ title: 'Log In', presentation: 'modal' }} />
            <Stack.Screen name="TeamDetail" component={TeamDetailScreen} />
            <Stack.Screen name="GameDetail" component={GameDetailScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

### How it works

1. App launches → `isLoggedIn` is `false` → only `AuthLogin` screen is registered → user sees login form
2. User enters credentials → `useAuthStore.login()` sets `isLoggedIn: true`
3. Store change triggers re-render → navigator now registers `MainTabs` + detail screens → `initialRouteName` flips to `MainTabs`
4. User sees the main app. If they navigate to `AuthLogin` later (e.g., from settings), it opens as a modal.

### AuthLogin screen: navigation after login

```jsx
async function handleSubmit() {
  await login(email, password);
  const { isLoggedIn: success } = useAuthStore.getState();
  if (success) {
    await performSync();  // initial data sync
    navigation.replace('MainTabs' as any);  // replace, don't push
  }
}
```

Use `navigation.replace` (not `navigate`) so the login screen is removed from the back stack — pressing back from the main app should NOT return to login.

### Pitfalls

- **Don't use `initialRouteName` alone without conditional rendering.** React Navigation's `initialRouteName` only sets the FIRST screen on mount — it doesn't gate navigation. If all screens are always registered, the user can navigate around the auth screen.
- **The auth store must persist across re-renders.** If using Zustand, the store survives re-renders by default. If the token is stored in SecureStore/AsyncStorage, hydrate it into the store on app launch (`isLoggedIn` should start as `false` and flip to `true` after token validation).
- **SecureStore throws in unsigned dev builds** — wrap token persistence in try/catch (see Pattern 6: Dev Auth Bypass).
- **Sync after login** — call `performSync()` immediately after successful login so the offline store is populated before the main screens render.
- **Back button on Android** — after login, use `navigation.replace` so the login screen isn't in the back stack. Otherwise hardware back button returns to login.

---

## Pattern 16: Shared Filter Component (Sport Pill Bar)

**Problem:** A horizontal scrollable filter bar (pills) is duplicated across multiple screens (Today, Schedule, Ratings). Each screen reimplements the same pill rendering, active state, and sport-ordering logic.

**Solution:** Extract a shared component with the filter logic, sport ordering, and styling. Each screen passes its data source and receives the selected value.
import { ScrollView, Pressable, Text } from 'react-native';
import { sportTint, leagueLabel } from '@/design/tokens';

// Canonical ordering — American sports first, then European football
export const LEAGUE_ORDER = [
  'MLB', 'NFL', 'NBA', 'NHL', 'MLS',
  'FOOTBALL_EPL', 'FOOTBALL_LALIGA', 'FOOTBALL_SERIEA',
  'FOOTBALL_BUNDESLIGA', 'FOOTBALL_LIGUE1',
];

export function deriveAvailableSports(...sources: (string | null | undefined)[][]): string[] {
  const sports = new Set<string>();
  sources.forEach(src => src.forEach(s => { if (s) sports.add(s); }));
  const ordered = LEAGUE_ORDER.filter(s => sports.has(s));
  sports.forEach(s => { if (!LEAGUE_ORDER.includes(s)) ordered.push(s); });
  return ordered;
}

interface Props {
  sports: string[];
  selected: string;
  onSelect: (sport: string) => void;
}

export default function SportPillBar({ sports, selected, onSelect }: Props) {
  if (sports.length <= 1) return null;  // hide when only one sport
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <Pressable onPress={() => onSelect('all')}>
        <Text style={selected === 'all' ? styles.active : styles.inactive}>All</Text>
      </Pressable>
      {sports.map(sport => (
        <Pressable key={sport} onPress={() => onSelect(sport)}>
          <Text style={[selected === sport ? styles.active : styles.inactive,
                       selected === sport && { color: sportTint(sport).text }]}>
            {leagueLabel(sport)}
          </Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}
```

### Usage in screens

```jsx
// In a FlatList screen — use ListHeaderComponent
const [selectedSport, setSelectedSport] = useState('all');
const availableSports = useMemo(
  () => deriveAvailableSports(games.map(g => g.sport)), [games]
);
const filtered = useMemo(() =>
  selectedSport === 'all' ? games : games.filter(g => g.sport === selectedSport),
  [games, selectedSport]
);

<FlatList
  data={filtered}
  ListHeaderComponent={
    <SportPillBar sports={availableSports} selected={selectedSport} onSelect={setSelectedSport} />
  }
  ...
/>
```

### Pitfalls

- **Hide when ≤1 sport** — Don't show a single pill; it adds visual noise without function.
- **Derive from actual data, not hardcoded** — Use `deriveAvailableSports` so only sports with data show up as pills. Some leagues may have zero entries (off-season, between matchdays).
- **Different screens derive from different sources** — Today screen may derive from schedule + ratings; Schedule screen derives from schedule only; Ratings screen derives from ratings only. Use `deriveAvailableSports(source1, source2)` to accept multiple sources.
- **Do NOT put pill bar in `ListHeaderComponent`** — FlatList applies `flexGrow: 1` to its `contentContainerStyle` when the list is empty, which stretches the header vertically and makes pills stack instead of scroll horizontally. Instead, place the pill bar as a **sibling `<View>` above the FlatList**. This keeps it pinned at the top and immune to the empty-list stretching behavior. For ScrollView screens, place it inline above the content sections.

## Pattern 17: FlatList Empty-State Header Stretching

**Problem:** A `FlatList` with a `ListHeaderComponent` renders the header correctly when the list has data, but when the list is **empty**, the header stretches vertically — filling the entire screen height. Horizontal `ScrollView` pills inside the header stack vertically instead of scrolling sideways.

**Root cause:** FlatList applies `flexGrow: 1` to its `contentContainerStyle` internally when the list is empty. This causes the content container (including the header) to fill the parent's height, stretching any flex children. The header's horizontal `ScrollView` then gets a tall flex parent and its children wrap vertically.

**Solution:** Move the header **outside** the FlatList as a sibling `<View>`. The FlatList only contains the scrollable data items.

```jsx
// ❌ WRONG — header stretches when list is empty
<View style={styles.container}>
  <FlatList
    data={filteredItems}
    ListHeaderComponent={<SportPillBar ... />}
    ListEmptyComponent={<Text>No data</Text>}
    ...
  />
</View>

// ✅ CORRECT — header is a fixed sibling, FlatList only has data
<View style={styles.container}>
  <SportPillBar
    sports={availableSports}
    selected={selectedSport}
    onSelect={setSelectedSport}
  />
  <FlatList
    data={filteredItems}
    ListEmptyComponent={<Text>No data</Text>}
    style={{ flex: 1 }}
    ...
  />
</View>
```

### When this matters
- **Any screen where the list can be empty** — filtered views, off-season sports, search results with no matches
- **Pill bar / filter bar as a FlatList header** — the most common trigger, because horizontal ScrollViews are very sensitive to parent height
- **Stat cards or summary headers** — less visually obvious but still stretch

### Pitfalls
- **This only manifests when the list is empty** — with ≥1 item, `flexGrow: 1` is not applied and the header renders normally. Test with empty data.
- **`contentContainerStyle={{ flexGrow: 0 }}` does NOT fix it** — FlatList overrides this internally when empty
- **`ListEmptyComponent` renders inside the same stretched container** — so the empty state also looks wrong (stretched vertically)
- **Workaround for keeping it in ListHeaderComponent** — you could add `contentContainerStyle={{ minHeight: 0 }}` but the sibling approach is cleaner and more predictable

---

## Reference Files

- `references/expo-ios-setup-checklist.md` — Full macOS setup checklist for iOS Simulator testing without Apple Developer account. Covers xcodebuild with CODE_SIGNING_ALLOWED=NO, expo-font version mismatch fix, SecureStore entitlement workaround.
- `references/report-card-carousel-example.md` — Complete ReportCardCarousel component with API shapes, score bar colors, and wiring pattern.
- `references/dev-auth-bypass.md` — Dev auth bypass implementation for OAuth-less testing.
- `references/hero-carousel-pattern.md` — Hero image carousel pattern for entity detail pages (Port, Ship, Itinerary).
