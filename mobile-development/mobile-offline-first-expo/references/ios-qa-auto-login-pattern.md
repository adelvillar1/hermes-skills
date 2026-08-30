# iOS simulator QA auto-login pattern

When iterating on a React Native / Expo app that requires authentication before showing synced data, manually logging in on every reinstall is slow. This pattern temporarily makes the login screen auto-submit a test account, then restores normal navigation before committing.

## When to use

- You need to verify post-login screens (Today, Schedule, Ratings) repeatedly.
- The app stores the JWT in `expo-secure-store`, so uninstalling wipes the token.
- You are testing against a local backend on the Mac's LAN IP.

## Temporary QA code

In `src/screens/AuthLogin.tsx`:

```tsx
import { useEffect } from 'react';
import { useAuthStore } from '@/store/auth';
import { performSync } from '@/store/sync';

const AUTO_LOGIN_TEST_USER = true;  // flip to false before committing
const TEST_EMAIL = 'test@example.com';
const TEST_PASSWORD = '<test-password>';

export default function AuthLoginScreen({ navigation }: Props) {
  const { login } = useAuthStore();

  useEffect(() => {
    if (!AUTO_LOGIN_TEST_USER) return;
    async function run() {
      await login(TEST_EMAIL, TEST_PASSWORD);
      if (useAuthStore.getState().isLoggedIn) {
        try { await performSync(); } catch { /* logged internally */ }
        (navigation as any).replace('MainTabs');
      }
    }
    run();
  }, []);

  // ... normal login form
}
```

Key points:
- Declare the login function **inside** the effect as a hoisted `async function`, or use a function declaration elsewhere. Do **not** reference a `const handleLogin = async () => ...` defined later in the component — const arrow functions are not hoisted.
- Use `navigation.replace('MainTabs')` instead of `navigation.goBack()` when the login screen is the stack's initial route.
- Set `initialRouteName="AuthLogin"` in the stack navigator temporarily so the app launches straight into login.

## Cleanup before commit

1. Set `AUTO_LOGIN_TEST_USER = false`.
2. Restore `initialRouteName="MainTabs"` in the navigator.
3. Remove any hardcoded credentials from the file.
4. Run tests and typecheck.

## Alternative: environment-driven toggle

For a less risky setup, gate the QA login on an Expo extra field:

```ts
// app.config.ts
extra: { autoLoginTestUser: process.env.AUTO_LOGIN_TEST_USER === 'true' }
```

```tsx
import Constants from 'expo-constants';
const AUTO_LOGIN_TEST_USER = Constants.expoConfig?.extra?.autoLoginTestUser ?? false;
```

Build the QA version with `AUTO_LOGIN_TEST_USER=true pnpm run ios` and the production-like version without the variable.
