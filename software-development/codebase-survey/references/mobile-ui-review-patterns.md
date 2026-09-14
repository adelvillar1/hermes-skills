# Mobile / React Native UI Review Patterns

Audit checklist for deep-diving a React Native consumer app. Use after the targeted deep dive pattern in `codebase-survey` when the domain is mobile UI.

## 1. API Response Shape Verification

**The single most common silent bug:** API returns `{ recommendations: [...] }` but the frontend destructures `.itineraries`. All data flows into empty arrays with no error.

**Audit:**
```bash
# For every API function in client.js, grep the route handler's res.json() shape
grep -n "res.json" apps/api/src/routes/recommendations.js
# Then grep the consumer's destructuring
grep -n "\.itineraries\|\.recommendations\|\.ships\|\.cruiseLines" apps/mobile/src/screens/ItineraryDetail.js
```

**Checklist:**
- [ ] Every `res.json({ key: [...] })` in API routes — what key name?
- [ ] Every consumer `.then(data => data.X)` — does X match the API key?
- [ ] Every `.catch(() => ({ Y: [] }))` fallback — does Y match?
- [ ] Client functions that return raw `response.json()` — do callers destructure correctly?

**Common mismatch patterns:**
| API returns | Frontend expects | Result |
|-------------|-----------------|--------|
| `{ recommendations: [...] }` | `.itineraries` | Silent empty array |
| `{ cruiseLines: [...] }` | `.cruise_lines` | Silent empty array |
| `{ ships: [...] }` | `.fleet` | Silent empty array |

## 2. Nested ScrollView + FlatList Anti-Pattern

React Native explicitly warns against nesting `FlatList` inside `ScrollView`. When `scrollEnabled={false}` is used, FlatList's virtualization is disabled — all items render at once.

**Detection:**
```bash
grep -n "ScrollView" apps/mobile/src/screens/*.js | grep -v "StyleSheet\|style="
grep -n "FlatList\|SectionList" apps/mobile/src/screens/*.js
```

**Check if they're nested** by reading each screen that has both. The pattern is:
```jsx
<ScrollView>           {/* outer scroll */}
  <FlatList scrollEnabled={false} />  {/* disabled inner list — all items render */}
</ScrollView>
```

**Impact:**
- Pagination metadata from API is discarded (only first 20 items shown)
- Memory grows linearly with data size
- No "load more" / infinite scroll possible

**Fix options:**
- Short lists (<50 items): replace FlatList with `.map()` directly
- Long lists: refactor to single FlatList with `ListHeaderComponent` for the scrollable header content
- Detail pages: use `SectionList` instead of ScrollView+FlatList combo

## 3. Silent Error Swallowing

**Detection:**
```bash
grep -rn "\.catch(console\.error)" apps/mobile/src/screens/
grep -rn "\.catch(() =>" apps/mobile/src/screens/
```

Every `.catch(console.error)` or `.catch(() => {})` on sub-loads means failures are invisible to users. The initial data load shows a LoadingState, but supplementary data (recommendations, cruise lines, conditions) fail silently.

**Prioritize fixing catches on:**
- User-facing data (recommendations, related items)
- Data that determines UI visibility (conditional sections)
- Data the plan explicitly calls out as a feature

**Fix pattern:**
```javascript
.catch(err => {
  console.error('Failed to load recommendations', err);
  setRecError('Could not load recommendations');
})
```

## 4. Jargon Consistency Audit

After an "assumed-knowledge audit" that fixes jargon, residual instances often remain.

**Detection:**
```bash
grep -rn '"pax"\|"GT"\|"tonnage"\|passengerCapacity.*pax' apps/mobile/src/screens/
```

Check that fixes were applied consistently across ALL screens, not just the one being worked on. The audit fix on ShipDetail (`guests`) may have missed CruiseLineDetail (`pax`).

## 5. Component Prop Flow Audit

**Dead UI elements** — components that render but don't respond to taps.

**Detection:**
- Clan/route pills: styled as `View` but should be `TouchableOpacity`
- Stat cards: display-only, no tap target
- Badge chips: informational only, no navigation

```bash
# Find Views that look like they should be tappable but aren't
grep -n "clanPill\|clanWrap\|clanName" apps/mobile/src/screens/DestinationDetail.js
# If parent is <View> not <TouchableOpacity>, it's dead UI
```

## 6. Duplicate Content Rendering

Check for the same data rendered in multiple places on the same screen:
```bash
grep -n "region.description\|item.description" apps/mobile/src/screens/DestinationDetail.js
```

If both the hero overlay and a separate section show the same text, remove one.

## 7. Favorites/Wishlist State Sync

FavoriteButton defaults to `initialSaved={false}` with no pre-fetch. Users see empty hearts on items they've already saved.

**Check if any screen pre-fetches saved state:**
```bash
grep -rn "initialSaved\|getFavorites\|isSaved" apps/mobile/src/
```

If no pre-fetch exists, the button is optimistic-only. Fix: fetch favorites on mount, pass `initialSaved` prop.

## 8. Navigation Stack Duplicate Options

React Navigation silently takes the last `options` prop:
```jsx
<Stack.Screen options={{ title: 'Sailings' }} options={{ title: 'Itineraries' }} />
```
Only "Itineraries" wins. Check for duplicate `options` props on any `Stack.Screen`.

## 9. Pull-to-Refresh Coverage

Browse/listing screens should have pull-to-refresh. Check:
```bash
grep -rn "RefreshControl\|refreshing\|onRefresh" apps/mobile/src/screens/
```

Favorites has it; DestinationGrid and CruiseLineList likely don't.

## 10. Tab Icon Quality

Check if icons are Unicode/emoji placeholders vs proper icon set:
```bash
grep -n "TAB_ICONS\|tabBarIcon" apps/mobile/src/navigation.js
```

Ionicons names like `compass`, `boat`, `sparkles` are functional but not custom-branded. Flag if the design direction calls for editorial/custom iconography.
