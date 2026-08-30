---
name: mobile-design-system
description: "Implement a design system in a React Native / Expo mobile app: theme creation, shared components, screen-by-screen migration, and visual quality audit."
version: 1.0.0
metadata:
  hermes:
    tags: [mobile, react-native, expo, design-system, ui, theme]
    related_skills: [anti-ai-slop, design-review, claude-design]
---

# Mobile Design System Implementation

Build a cohesive design system for a React Native (Expo) mobile app and migrate all screens to use it.

## When to Use

- App has hardcoded colors, inconsistent spacing, emoji-as-icons, or no shared theme
- Visual overhaul or redesign of an existing mobile app
- Greenfield app that needs a design foundation before building screens

## Process

### 1. Create `theme.js`

Export a single source of truth. All visual constants live here — nothing hardcoded in screens.

```js
export const colors = {
  canvas: '#FAFAF8',        // background — warm off-white, not cold grey
  surface: '#FFFFFF',        // cards, modals
  textPrimary: '#1A1A1A',   // near-black, warm tone
  textSecondary: '#6B6B6B',
  textTertiary: '#999999',
  accent: '#D4553A',        // primary action — pick something with character
  accentLight: '#FEF0ED',   // tinted background for accent
  accentDark: '#B84430',
  border: '#E8E8E6',
  inputBg: '#F0EFED',
  white: '#FFFFFF',
};

export const typography = {
  headingLarge:  { fontSize: 28, fontWeight: '700', letterSpacing: -0.5 },
  headingMedium: { fontSize: 22, fontWeight: '600', letterSpacing: -0.3 },
  headingSmall:  { fontSize: 17, fontWeight: '600' },
  body:          { fontSize: 15, fontWeight: '400', lineHeight: 22 },
  bodyMedium:    { fontSize: 15, fontWeight: '500', lineHeight: 22 },
  caption:       { fontSize: 13, fontWeight: '400', color: '#6B6B6B' },
  label:         { fontSize: 11, fontWeight: '600', letterSpacing: 0.5, textTransform: 'uppercase' },
};

export const spacing = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32, huge: 48,
};

export const radii = {
  sm: 6, md: 12, lg: 16, xl: 24, full: 9999,
};

export const shadows = {
  card:     { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 3, elevation: 1 },
  elevated: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.12, shadowRadius: 8, elevation: 4 },
};
```

**Key decisions:**
- Pick one accent color with personality. Avoid corporate blue (#1a73e8), generic purple, or Tailwind blue (#3b82f6)
- Warm backgrounds (`#FAFAF8`) feel more premium than cold grey (`#F5F5F5`)
- Negative letter-spacing on headings tightens large text

### 2. Replace Emoji with Icon Library

Install `@expo/vector-icons` (ships with Expo, no install needed). Create a wrapper:

```js
// components/Icon.js
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme';

export default function Icon({ name, size = 24, color = colors.textSecondary, style }) {
  return <Ionicons name={name} size={size} color={color} style={style} />;
}
```

**Why Ionicons:** Ships with Expo, 1,300+ icons, covers navigation (chevrons, back), content (map, compass, boat), and actions (search, filter). No native dependency chain.

**Audit for emoji:** `perl -CSD -ne 'print "$ARGV:$. $_" if /[\x{1F300}-\x{1F9FF}]/' screens/*.js` — zero tolerance for emoji in UI.

### 3. Build Shared Components

Minimum viable set for most apps:

| Component | Purpose | Key props |
|-----------|---------|-----------|
| `Card` | White surface container | `onPress`, `style`, `padding` |
| `SectionHeader` | Consistent section titles | `title`, `subtitle`, `right` |
| `PillFilter` | Horizontal scrollable filter with optional secondary row | `items`, `activeIndex`, `onSelect`, `secondaryItems`, `secondaryActiveIndex`, `onSecondarySelect` |
| `LoadingState` | Centered spinner | `message` |
| `Icon` | Ionicons wrapper | `name`, `size`, `color` |

**PillFilter secondary row:** For date pickers that need both month and year selection, pass `secondaryItems` (array of `{key, label}`), `secondaryActiveIndex`, and `onSecondarySelect`. The component renders two horizontal scroll rows — primary on top, secondary below. Use for any two-axis filter where the secondary axis has fewer options (e.g., 3 years vs 12 months).

```jsx
<PillFilter
  items={MONTHS}             // [{key: '1', label: 'Jan'}, ...]
  activeIndex={monthIndex}
  onSelect={setMonthIndex}
  secondaryItems={YEARS}     // [{key: '2026', label: '2026'}, ...]
  secondaryActiveIndex={yearIndex}
  onSecondarySelect={setYearIndex}
/>
```

**When to use PillFilter vs inline chips:** PillFilter assumes single-select (one `activeIndex`). For multi-select filters (e.g., choose multiple months), build inline chips directly — use `flex: 1` on each chip for even distribution across the row. See `react-native-patterns` Pattern 11 for the multi-select date grid pattern.

**ListHeaderComponent technique for FlatList screens:** On screens that use `FlatList` (not `ScrollView`), render the filter bar as `ListHeaderComponent` rather than placing it above the FlatList in a parent View. This makes the filter bar scroll naturally with the content and avoids nested-scroll issues:

```jsx
<FlatList
  data={filteredGames}
  ListHeaderComponent={<SportPillBar sports={availableSports} selected={selectedSport} onSelect={setSelectedSport} />}
  renderItem={...}
/>
```

**Extract shared helpers alongside shared components:** When extracting a filter component, also extract any ordering/derivation helpers it depends on (e.g., `LEAGUE_ORDER`, `deriveAvailableSports`). Export them from the same file so each screen can derive its available options from its own data source:

```jsx
// components/SportPillBar.tsx
export const LEAGUE_ORDER = ['MLB', 'NFL', ...];
export function deriveAvailableSports(...sources: string[][]) { ... }
export default function SportPillBar({ sports, selected, onSelect }) { ... }
```

Each component imports from `theme.js` — never hardcodes colors or spacing.

### 4. Migrate Screens

Rewrite each screen to use theme + shared components. Order:

1. Navigation (tab icons, header styles)
2. List/browse screens (highest traffic, patterns repeat)
3. Detail screens (most complex layout)
4. Form/quiz screens
5. Utility screens (settings, about)

**Per-screen checklist:**
- [ ] All colors from `theme.js` — zero hardcoded hex
- [ ] All spacing from `theme.spacing`
- [ ] Typography from `theme.typography` — no inline fontSize/fontWeight
- [ ] Shared components used where applicable
- [ ] No emoji anywhere
- [ ] Icons are functional/semantic, not decorative
- [ ] Consistent section structure (SectionHeader → content)

### 5. Post-Migration Audit

```bash
# Hardcoded colors (outside theme.js)
grep -rn '#[0-9a-fA-F]\{3,8\}' screens/ components/ navigation.js | grep -v shadowColor

# Emoji
perl -CSD -ne 'print "$ARGV:$. $_" if /[\x{1F300}-\x{1F9FF}\x{2600}-\x{26FF}]/' screens/*.js

# Filler copy
grep -rni 'revolutionizing\|unlock your\|next-generation\|seamlessly\|thousands of' screens/

# Icon count per screen (flag if >10 — likely excessive)
for f in screens/*.js; do echo "$(basename $f): $(grep -c '<Icon ' $f)"; done
```

## Local Dev & Expo Web Testing

Testing React Native apps without a physical device or simulator — use Expo's web mode:

```bash
# Terminal 1: Start the API server (Docker may occupy 3000, use 3001)
PORT=3001 node apps/api/src/server.js

# Terminal 2: Start Expo web
npx expo start --web
# If port 8081 conflicts, it auto-increments to 8082
```

### API client configuration for web

React Native's `Platform.select` lets you route web requests to `localhost` while iOS/Android use the device's host:

```js
// api/client.js
const API_BASE = Platform.select({
  web: 'http://localhost:3001',
  default: 'http://10.0.2.2:3000',  // Android emulator default
});
```

### Dependencies for web support

Expo web requires `react-dom` and `react-native-web`:

```bash
npx expo install react-dom react-native-web
```

### What works in web mode

- Tab navigation (bottom tabs render as a tab bar)
- FlatList scrolling and card layouts
- Text input and form submission
- API calls with proper Platform routing
- Image loading from remote URLs

### What may differ from native

- Shadows and elevation render differently (CSS vs native shadow)
- Touch feedback (no `Pressable` ripple effect)
- Platform-specific native modules will fail
- Some `@expo/vector-icons` may not render identically
- KeyboardAvoidingView behavior differs

### Debugging web issues

- Use browser DevTools console for network errors
- Check `X-Cache` response headers for cache HIT/MISS debugging
- React Native web console warnings are verbose but not fatal — focus on actual errors

## Navigation Architecture

When the app has more than one drill-down path per tab, use a **stack navigator per tab**:

```js
const Tab = createBottomTabNavigator();
const DestStack = createNativeStackNavigator();
const LinesStack = createNativeStackNavigator();

function DestinationsStackNav() {
  return (
    <DestStack.Navigator screenOptions={{ headerShown: false }}>
      <DestStack.Screen name="DestinationGrid" component={DestinationGrid} />
      <DestStack.Screen name="DestinationDetail" component={DestinationDetail} />
      <DestStack.Screen name="CruiseLineDetail" component={CruiseLineDetail} />
      <DestStack.Screen name="ShipDetail" component={ShipDetail} />
    </DestStack.Navigator>
  );
}

// Each tab gets its own stack
<Tab.Screen name="Destinations" component={DestinationsStackNav} />
```

**Key points:**
- Each tab's stack is independent — pressing a tab returns to its root screen
- Shared screens (like `ShipDetail`, `ItineraryDetail`) appear in MULTIPLE stacks since they're reachable from different tabs
- `headerShown: false` on stack screens → custom headers in-screen or none at all
- Tab icons use `@expo/vector-icons/Ionicons`: `compass` (Destinations), `boat` (Cruise Lines), `sparkles` (Quiz), `chatbubble` (Chat), `ellipsis-horizontal` (More)

**Pitfall:** Don't put shared detail screens at the tab level — they belong in each tab's stack separately. A `ShipDetail` reached from "Destinations > Caribbean > Royal Caribbean > ship" and one reached from "Cruise Lines > Royal Caribbean > ship" are different navigation contexts that should each have their own back stack.

### Demoting Screens to "More" Tab

When a screen doesn't justify a top-level tab (e.g., Ports with 1,688 items but low direct-browse intent), demote it to a row inside the More tab. Pattern:

1. Remove the tab from `Tab.Navigator`
2. Add a section in `MoreScreen.js` with icon, title, subtitle, and chevron
3. Add a stack screen in More's stack navigator
4. Navigation: `navigation.navigate('PortBrowser')` from the More row's `onPress`

This keeps the tab bar clean (5 items max) while preserving access to lower-priority screens.

### Active-Records-Only Data Fetching

For consumer-facing apps that read from a shared data engine, every API call must filter to active records. Enforce in both the API route and the mobile screen:

- **API routes**: Always add `WHERE status = 'active'` for itineraries and cruise lines; join through active records for ships (must have ≥1 active itinerary)
- **Mobile screens**: Trust the API filter — don't re-filter client-side. But DO verify the API returns expected counts (e.g., 49 active cruise lines, not 83 total)
- **Pagination**: Always use server-side pagination with `limit`/`offset` — never fetch all records client-side for lists that could exceed 100 items

## Consumer-First Language (User-Verified Principle)

All user-facing copy in the mobile app must be written for **cruise passengers**, not travel advisors or industry insiders. This was an explicit design correction: *"make sure that the UI surfaces don't overwhelm consumers with data that is not meaningful to them, avoid technical terms and things that would only be meaningful to travel advisors."*

**Rules:**

1. **Speak English, not schema.** Section headers should be "At a Glance" (not "Vessel Specifications"), "Rooms" (not "Cabin Profile"), "Onboard" (not "Venue Profile"). Labels like "What experts say", "What's included", "Is it expensive?", "Good to know" are consumer-friendly.

2. **Show only helpful info.** If a field is null or empty, hide the entire section — never show "N/A" or placeholder text. Use conditional rendering: `{description ? <Text>{description}</Text> : null}`.
3. **Hide sections with thin or inconsistent data.** Even when data IS present, if the content is generic ("Package 1", "Package 2") or doesn't add real value, remove the entire section rather than showing filler. Empty/generic sections look worse than no section at all. When in doubt, ask: "does this help the user make a decision?" If not, cut it.

4. **Translate raw data to meaning.** Don't show raw scores without context. A cabin mix percentage is meaningful as a bar chart; a `cabinProfile` JSONB object is not. Port verdicts should show tier badges ("Excellent", "Good") not numeric scores alone.

5. **No travel-advisor jargon.** Terms like "fare code", "cabin category", "embarkation port", "tender port", "repositioning cruise" should be translated or simplified. "Fare options" is better than "Fare packages". "Ports of call" → just "Ports".

6. **Check/cross for boolean inclusions.** For features like "What's included", use ✓/✗ icons with plain labels ("Meals", "Drinks", "Wi-Fi") — never show the raw column names from the database.

7. **Risk flags as tips, not warnings.** Port risk flags should use 💡 "Good to know" framing, not alarming ⚠️ "Risk" framing. The user is planning a vacation, not assessing danger.

## Pitfalls

- **Docker may occupy port 3000 on macOS.** If `node server.js` fails with EADDRINUSE, check `lsof -i :3000` — Docker Desktop's proxy often binds it. Use `PORT=3001` instead and update the mobile API client's web config accordingly.
- **Do not use Inter/Roboto/system font as a branding choice.** These are fine for body text but scream "demo" for headings. If you can't load a custom font, at minimum use negative letter-spacing and heavier weights to differentiate headings from body.
- **Shadow values need `shadowColor: '#000'` on iOS.** Without it, React Native shadows don't render. Always include it in shadow objects.
- **`gap` property in flexbox works on RN 0.71+ / Expo SDK 48+.** If targeting older versions, use `marginRight`/`marginBottom` instead.
- **PillFilter needs `showsHorizontalScrollIndicator={false}`** on the ScrollView or users see an ugly scrollbar.
- **`shadowColor` will show up in the hex color audit.** Exclude it — it's not a design color, it's a shadow definition.
- **Data slop is sneaky.** "Browse thousands of ports" when you know the real count is 2,377. Use real numbers or cut the claim entirely. Honest copy beats inflated copy.
- **Avoid the "border-left accent card" pattern.** This is the #1 AI-generated design smell per the anti-slop checklist. Use background color contrast or font weight contrast instead.
- **Don't over-polish after shipping.** Once the screens are migrated and the anti-slop audit passes clean, stop. Spending 10+ minutes chasing edge cases in filler copy or borderline icon counts is the #1 cause of "you've been stuck for 10 minutes" frustration. Ship the commit, deploy, verify the API works — done. Further polish happens in a dedicated follow-up session, not as scope creep at the end.
- **Binary images from API endpoints.** For hero images and map images stored as bytea in PG, the API serves them with proper Content-Type headers (`image/jpeg`, `image/svg+xml`). On mobile, use `<Image source={{ uri: getPortHeroUrl(slug) }} />` for JPEGs, and `<SvgXml xml={svgString} />` for SVGs. The component should check `hasHeroImage` / `hasMapImage` flags from the port detail response to skip fetches for ports without assets, avoiding 404 waterfalls.
- **Hero image text overlay.** For port detail screens, use `position: 'absolute'` text over the hero image with a dark gradient overlay (`rgba(0,0,0,0.35)`) for readability. `textShadowColor`/`textShadowRadius` on heading text prevents illegibility on light images.
- **Cross-platform label consistency — mirror the web app's label mappings.** When a web app has a human-readable label mapping (e.g., `LEAGUE_LABELS` mapping `FOOTBALL_EPL` → `Premier League`), the mobile app MUST mirror it. Showing raw database keys (`FOOTBALL_EPL`, `FOOTBALL_BUNDESLIGA`) instead of friendly names (`Premier League`, `Bundesliga`) is immediately noticed by the user: *"the names are not the friendly names we show on the web app."* Put the mapping in `design/tokens.ts` alongside other shared constants, export a `label()` helper, and apply it consistently across ALL screens that render the label — not just one. Grep every screen for raw `{item.sport}` or `{game.league}` text render and replace with the helper call. The web app's mapping file is the source of truth for the label set; copy it wholesale.
- **Sport/league filter pill ordering — use the web app's fixed priority, not alphabetical.** When rendering sport filter pills, alphabetical sort puts football leagues first (Bundesliga, La Liga, Ligue 1…) and pushes primary American sports (MLB, NBA, NHL) off-screen on mobile. Mirror the web app's fixed priority order — typically American sports first (MLB, NFL, NBA, NHL, MLS), then European football leagues. Derive available sports from data, filter through the fixed priority list, and append any unknown sports at the end. This ensures the most-used filters are always visible without horizontal scrolling.
- **Propagate filters across ALL sibling screens — consistency is not optional.** When a filter (sport, date, category) exists on one screen (e.g., Today feed), every sibling screen showing the same data type must have the same filter. Users perceive the absence of a filter they've used elsewhere as a bug: *"the schedule and ratings pages are showing information for all leagues."* Audit all tab screens whenever a new filter is added to one. Extract the filter into a shared component (see `SportPillBar` pattern above) so the visual language, ordering, and behavior are identical everywhere. Check `Schedule`, `Ratings`, `Today`, and any browse screens — if they show entities that have a `sport`/`league`/`category` field, they need the pill bar.

### Hero Carousel (Multi-Asset Hero Areas)

When a detail screen has multiple visual assets for the same entity (photo, map, projection, chart), replace the separate hero + map sections with a single swipeable carousel. Consistent pattern across PortDetail (photo/SVG map/2D projection) and ItineraryDetail (ship image/route map).

**Implementation:**
```jsx
// components/PortHeroCarousel.js (or any entity)
import { FlatList, Dimensions } from 'react-native';
const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Build slides from available assets — only include what exists
const slides = [];
if (entity.hasHeroImage) slides.push({ type: 'photo', uri: getHeroUrl(id) });
if (entity.hasMapImage || entity.hasMap) slides.push({ type: 'map', uri: getMapUrl(id) });
if (slides.length === 0) slides.push({ type: 'text' }); // fallback

<FlatList
  data={slides}
  horizontal
  pagingEnabled
  showsHorizontalScrollIndicator={false}
  getItemLayout={(_, i) => ({
    length: containerWidth, offset: containerWidth * i, index: i,
  })}
  onMomentumScrollEnd={(e) => {
    setActiveIndex(Math.round(e.nativeEvent.contentOffset.x / containerWidth));
  }}
/>

// Dot indicators below — only show when >1 slide
{slides.length > 1 && (
  <View style={styles.dots}>
    {slides.map((_, i) => (
      <View style={[styles.dot, i === activeIndex && styles.dotActive]} />
    ))}
  </View>
)}
```

**Key decisions:**
- Hero photo slide: keep text overlay (name, badge, favorite button) — same as standalone hero
- Map/chart slides: render as `<Image>` — the endpoint handles JPEG/SVG negotiation server-side. No text overlay — let the visual speak. Add small label chip in corner ("Route Map", "Location Map", "Ship") with semi-transparent background.
- Pre-fetch is NOT needed for map slides — they render as standard images from a URI endpoint
- Text fallback (no assets): render the same text hero as before, no dots
- Container width: `SCREEN_WIDTH - spacing.xl * 2` (accounts for parent margin)
- SVG rendering: use `SvgXml` from `react-native-svg` with explicit width/height matching the slide dimensions
- Image rendering: use `<Image source={{ uri }} resizeMode="cover" />` filling the slide
- Dots: 6px circles, accent color for active (wider: 18px), border color for inactive
- No horizontal scroll conflict inside vertical ScrollView — FlatList with fixed height + pagingEnabled handles this natively

**When to use:**
- Detail screen has 2+ visual assets (photo, map, chart, projection)
- Assets are from different sources (hero table, map table, SVG field)
- User benefits from seeing all views without scrolling past them

**When NOT to use:**
- Single asset (just a hero photo) — use a simple Image
- Assets are content (not visual) — use separate sections
- More than 4 slides — carousel becomes hard to discover; use tabs instead

**API contract:** The detail endpoint must return flags indicating which assets exist (`hasHeroImage`, `hasMapImage`, `hasMap`). The carousel reads these to decide which slides to show. Binary image endpoints serve with proper Content-Type and Cache-Control headers.

**Map slides — always render as Image, not SVG fetch.** The `/map` endpoint may return either JPEG (rendered map image) or SVG (location map) depending on which data exists. Do NOT try to fetch-as-text and check content-type for SVG — this silently fails when the endpoint returns JPEG, leaving a permanent "loading" or blank slide. Instead, always render the map slide as `<Image source={{ uri: getMapUrl(slug) }} />`. The endpoint handles format negotiation server-side; the client just displays whatever comes back. Consolidate `hasMapImage` and `hasMap` into a single slide:

```jsx
if (port.hasMapImage || port.hasMap) {
  slides.push({ type: 'map', uri: getPortMapUrl(slug) });
}
// Render:
if (item.type === 'map') {
  return (
    <View style={styles.slide}>
      <Image source={{ uri: item.uri }} style={styles.slideImage} resizeMode="cover" />
      <View style={styles.slideLabelWrap}>
        <Text style={styles.slideLabel}>Location Map</Text>
      </View>
    </View>
  );
}
```

### Multi-Select Date Grid (ShipDetail pattern)

For date filtering where users think "year first, then months", use a multi-select grid instead of quarter-based pills. Users expect: year selection → month toggles → results.

**Layout:**
```
FIND SAILINGS BY DATE

[2026]  [2027]  [2028]              ← year pills (single-select)

[Jan] [Feb] [Mar] [Apr] [May] [Jun]     ← row 1 (multi-select toggle)
[Jul] [Aug] [Sep] [Oct] [Nov] [Dec]     ← row 2 (multi-select toggle)

         Clear month filter               ← only when months selected
```

**Implementation:**
```jsx
const MONTH_ROW_1 = [1,2,3,4,5,6];   // Jan–Jun
const MONTH_ROW_2 = [7,8,9,10,11,12]; // Jul–Dec

// State
const [selectedMonths, setSelectedMonths] = useState(() => {
  return [new Date().getMonth() + 1]; // default: current month
});
const [yearIndex, setYearIndex] = useState(0);

function toggleMonth(m) {
  setSelectedMonths((prev) => {
    if (prev.includes(m)) return prev.filter((x) => x !== m);
    return [...prev, m].sort((a, b) => a - b);
  });
}

// API call sends comma-separated months param
// GET /api/ships/:id/itineraries?year=2027&months=4,5,6
```

**Key decisions:**
- Years on top (users think year-first), months below in two rows of 6
- Each month chip uses `flex: 1` for even distribution — always fits screen width
- Multi-select: tap to toggle on/off, sorted array of month numbers
- No months selected = show all sailings for that year (the API interprets empty months param as "all")
- Haptic feedback on every toggle
- "Clear month filter" link only appears when ≥1 month is selected

## References

- `references/anti-slop-audit-checklist.md` — grep commands and pass/fail criteria for the post-migration audit
- `references/tokenizing-existing-react-native-app.md` — retrofitting an existing RN/Expo app with a centralized `tokens.ts` file, migration order, and verification commands (use when the app already has hardcoded inline colors)
- `references/web-css-token-migration.md` — cross-platform token migration when the project also has a vanilla-JS web dashboard (CSS custom properties); includes density rules, drift checks, and the `patch` tool path-dropping workaround