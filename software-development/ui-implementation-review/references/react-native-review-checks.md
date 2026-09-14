# React Native Full-App Review Checks

Supplementary checklist for full-app reviews of React Native codebases. Use alongside the main `review-checklist.md` when auditing an entire app rather than a single feature.

## Navigation

- [ ] Grep every `navigation.navigate('X')` and `navigation.push('X')` — verify `'X'` is a registered screen name in the correct stack
- [ ] Check for screens navigated to from multiple stacks — must be registered in each stack or use a shared root stack
- [ ] Verify back-navigation: `navigation.goBack()` works correctly for all entry points (tab switch vs deep link vs push)

## FlatList / ScrollView

- [ ] `stickyHeaderIndices={[N]}` — N indexes into the data array, NOT visual position. Verify N matches the actual item that should be sticky
- [ ] Nested `ScrollView` + `FlatList` — flag as architecture debt (virtualization breaks, scroll conflicts)
- [ ] `keyExtractor` provided and unique — missing causes re-render bugs
- [ ] `getItemLayout` provided for fixed-height items — significant perf win

## Data Fetching Patterns

- [ ] **N+1 API calls**: Components rendered inside FlatList that each fire an API call on mount (e.g., FavoriteButton calling `getFavoriteStatus` per card). Flag for batch endpoint or parent-level prefetch
- [ ] **Session lifecycle**: Resources created on mount (chat sessions, event listeners, WebSocket connections) must have cleanup in `useEffect` return function. No cleanup = memory leak + phantom calls
- [ ] **Double-mount in StrictMode**: React 18 strict mode mounts → unmounts → remounts. API calls in useEffect without dedup/abort will fire twice
- [ ] **Race conditions**: Multiple rapid navigations or tab switches can cause stale responses to overwrite fresh data. Check for request cancellation or sequence guards

## State & Closures

- [ ] **Stale closures**: `useCallback`/`useEffect` that capture state values but don't include them in dependency arrays — the callback uses the value from when it was created, not current
- [ ] **`isMounted` ref pattern**: Checking `isMounted.current` after async work is often meaningless (component already remounted). Prefer AbortController or ignore-older-response patterns
- [ ] **Derived state**: Values computed from props/state that are also stored in local state (double source of truth). Derive in render or useMemo instead

## Styles & Design Tokens

- [ ] **Dead styles**: `StyleSheet.create` entries never referenced in JSX — noise that makes the file harder to maintain
- [ ] **Hardcoded values**: Colors, font sizes, spacing, or radii not from the theme. Grep for `#`, `rgb`, `fontSize:`, and `padding` outside of theme references
- [ ] **Inconsistent naming**: Same concept labeled differently across screens (e.g., "pax" vs "guests", "dest" vs "destination")

## Utility Function Duplication

- [ ] Identical helper functions appearing in 2+ screen files (e.g., `tierColor()`, `tierLabel()`, date formatters). Flag for extraction to `utils/` or a shared module
- [ ] In-line format strings repeated (currency, duration, dates). Extract to shared formatter

## Error & Loading States

- [ ] Every screen with async data has a loading state (spinner or skeleton)
- [ ] Every screen with async data has an error state (retry button, not just console.error)
- [ ] Empty lists show an empty state (icon + title + subtitle), not just a blank screen
- [ ] API errors in the client layer are surfaced to the UI, not silently swallowed
