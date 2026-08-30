# Mobile App Visual Redesign Pattern

Pattern for a full visual overhaul of a React Native / Expo mobile app —
from "generic wireframes" to a cohesive design system.

## 1. Design Foundation (Task 1)

### theme.js structure

Central design token file. Every screen and component imports from here. Zero hardcoded colors elsewhere.

```js
// apps/mobile/src/theme.js

export const colors = {
  canvas:     '#FAFAF8',  // warm off-white background
  surface:    '#FFFFFF',  // cards, sheets
  text:       '#1A1A1A',  // warm near-black (never #000)
  textSecondary: '#6B6B6B',
  textTertiary:  '#999999',
  accent:     '#D4553A',  // warm terracotta (or project-specific)
  accentDark: '#B84430',
  accentLight:'#FDF0ED',
  success:    '#2D8A56',
  border:     '#EBEBEB',
  muted:      '#F2F2F0',  // input/pill backgrounds
};

export const typography = {
  headingLarge:  { fontSize: 28, fontWeight: '700', letterSpacing: -0.5 },
  headingMedium: { fontSize: 22, fontWeight: '600', letterSpacing: -0.3 },
  headingSmall:  { fontSize: 18, fontWeight: '600' },
  body:          { fontSize: 15, fontWeight: '400', lineHeight: 22 },
  bodyMedium:    { fontSize: 15, fontWeight: '500' },
  caption:       { fontSize: 13, fontWeight: '400', color: colors.textSecondary },
  label:         { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32, huge: 48 };

export const shadows = {
  card:     { shadowColor: '#000', shadowOpacity: 0.06, shadowOffset: { width: 0, height: 2 }, shadowRadius: 8, elevation: 2 },
  elevated: { shadowColor: '#000', shadowOpacity: 0.10, shadowOffset: { width: 0, height: 4 }, shadowRadius: 12, elevation: 4 },
};

export const radii = { sm: 8, md: 12, lg: 16, xl: 24, pill: 999 };
```

### Icon component

Wraps `@expo/vector-icons/Ionicons` (bundled with Expo — no install needed).
Provides themed defaults so screens don't pass raw color strings.

### Offline-first hook refresh pattern

When a screen reads from SQLite via a custom hook (e.g., `useSchedule`, `useFavorites`, `useSyncMeta`) and also offers a manual sync/refresh action, the hook must be able to re-read after sync completes. The cleanest pattern is an optional numeric `refresh` dependency:

```js
export function useSchedule(refresh = 0) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    getSchedule().then((rows) => {
      if (!cancelled) { setData(rows); setLoading(false); }
    });
    return () => { cancelled = true; };
  }, [refresh]);
  return { data, loading };
}
```

The screen increments a `refreshKey` after `await performSync()` and passes it to every hook it uses:

```js
const [refreshKey, setRefreshKey] = useState(0);
const { data: schedule } = useSchedule(refreshKey);
const { data: ratings } = useRatings(refreshKey);
// ...
await performSync();
setRefreshKey(k => k + 1);
```

This avoids introducing a global sync-completed event bus while still letting the UI reflect newly written offline data.

## 2. Shared Components (Task 2)

Must be built before any screen redesign. All screens import from these:

| Component | Purpose | Key props |
|-----------|---------|-----------|
| `Card` | White surface, warm shadow, 12px radius | children, onPress, style |
| `SectionHeader` | Title (18px semibold) + optional right action | title, action, subtitle |
| `PillFilter` | Horizontal scrollable category pills | items, activeIndex, onSelect |
| `LoadingState` | Centered spinner + text | message |
| `RefreshButton` | Calls sync + bumps refreshKey on all offline hooks | onSync |

## 3. Screen-by-Screen (Tasks 3+)

Each screen task:
1. Imports from `theme.js` and shared components
2. Replaces all hardcoded `#` colors with theme references
3. Replaces all emoji with Ionicons
4. Uses Card, SectionHeader, PillFilter where applicable
5. Adds entry/exit animations (future scope)
6. **If the screen reads offline SQLite data, passes `refreshKey` to the hooks and bumps it after sync**

## 4. Verification

```bash
# Zero hardcoded hex colors in screen files (all should be in theme.js)
grep -rn '#' apps/mobile/src/screens/ | grep -v 'node_modules'

# Zero emoji in screen files + navigation
grep -Pn '[\x{1F300}-\x{1F9FF}\x{2600}-\x{26FF}\x{2700}-\x{27BF}]' apps/mobile/src/screens/ apps/mobile/src/navigation.js

# All screens still render without errors
npx expo start
```

### Offline-first verification

- After adding a favorite or triggering sync, the screen re-reads and shows the new data without a full remount.
- Hooks accept an optional `refresh` argument; no hook is hard-coded to read only on mount.

## Design Direction Catalog

Common directions with their token signatures:

### Warm Editorial (Airbnb-style)
- Canvas: warm off-white `#FAFAF8`
- Accent: terracotta/rust `#D4553A`
- Font: DM Sans (warm, rounded, in Expo)
- Feel: travel magazine, dream planning

### Clean Premium (Apple-style)
- Canvas: pure white `#FFFFFF`
- Accent: deep navy `#1D3A5F` or muted blue
- Font: SF Pro / system
- Feel: expensive, calm, precise

### Fresh Nautical
- Canvas: soft sky `#F0F4F8`
- Accent: ocean blue `#1E88E5`
- Secondary: sandy gold `#D4A843`
- Feel: on vacation already

### Dark Immersive (Spotify-style)
- Canvas: near-black `#121212`
- Surface: dark grey `#1E1E1E`
- Accent: vibrant (green, coral, etc.)
- Feel: modern, content-first, evening mode
