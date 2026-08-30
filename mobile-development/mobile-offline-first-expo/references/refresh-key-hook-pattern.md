# Refresh-Key Pattern for Offline-First SQLite Hooks

When a mobile screen reads from `expo-sqlite` via `useEffect(..., [])`, the hook only loads data on mount. After a manual or foreground sync writes new rows, the screen will still display stale data until it remounts.

Add an optional `refresh` dependency to every offline hook and pass a counter from the screen that increments after `performSync()`.

## `src/hooks/useOfflineData.ts`

```ts
import { useState, useEffect } from 'react';
import { getSchedule } from '@/db/offline';
import type { MobileScheduleGame } from '@/types/api';

export function useSchedule(refresh = 0) {
  const [data, setData] = useState<MobileScheduleGame[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getSchedule().then((rows) => {
      if (!cancelled) {
        setData(rows);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  return { data, loading };
}
```

Repeat the same signature for `useRatings`, `useFavorites`, `useSyncMeta`, etc.

## `src/screens/TodayFeed.tsx`

```tsx
import { useState, useCallback } from 'react';
import { useSchedule, useRatings, useFavorites, useSyncMeta } from '@/hooks/useOfflineData';
import { performSync } from '@/store/sync';

export default function TodayFeedScreen() {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data: schedule, loading: scheduleLoading } = useSchedule(refreshKey);
  const { data: ratings } = useRatings(refreshKey);
  const { data: favorites } = useFavorites(refreshKey);
  const { meta: syncMeta } = useSyncMeta(refreshKey);

  const handleRefresh = useCallback(async () => {
    try {
      await performSync();
      setRefreshKey(k => k + 1);
    } catch (err) {
      console.error('Refresh failed', err);
    }
  }, []);

  // render schedule, ratings, favorites, syncMeta …
}
```

## Why not a global sync event?

A global event bus works too, but a counter keeps hook dependencies simple and testable. Choose one convention per project and apply it to every offline hook.
