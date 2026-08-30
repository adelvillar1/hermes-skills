---
name: react-native-expo-development
description: "React Native + Expo development patterns — iOS simulator builds, FlatList layouts, auth bypass for dev, image loading, dependency compatibility, hooks rules. Use when building, debugging, or testing React Native Expo apps."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [react-native, expo, ios, simulator, mobile, development]
---

# React Native + Expo Development

Patterns for building, testing, and debugging React Native Expo apps on macOS with iOS Simulator.

## iOS Simulator Build (Expo Managed, Unsigned)

Expo managed projects (`expo run:ios`) require code signing even for simulator builds. Bypass with direct `xcodebuild`:

```bash
# 1. Generate native project
cd apps/mobile && npx expo prebuild --platform ios

# 2. Build for simulator (no code signing)
cd ios && xcodebuild \
  -workspace CruiserIntelligence.xcworkspace \
  -scheme CruiserIntelligence \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO

# 3. Install on simulator
xcrun simctl install booted ios/build/Build/Products/Debug-iphonesimulator/AppName.app

# 4. Start Metro bundler
cd apps/mobile && npx expo start --dev-client

# 5. Launch app
xcrun simctl launch booted com.bundle.identifier
```

**After native dep changes:** re-run steps 1-3 (rebuild native).
**After JS-only changes:** Metro hot-reloads automatically. If stale, `npx expo start --dev-client --clear`.

### Pitfall: `localhost` in the simulator is the simulator, not the Mac

The iOS Simulator is a separate network host. `http://localhost:8000` inside the app resolves to the simulator itself, not the development machine. If the backend runs on the Mac, the app will get connection refused.

**Fix:** configure `app.config.ts` to resolve the Mac's LAN IP at build time, with an env override for production:

```ts
import os from 'os';

function getLocalIp(): string {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name] ?? []) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return 'localhost';
}

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  extra: {
    apiBaseUrl: process.env.API_BASE_URL ?? `http://${getLocalIp()}:8000`,
  },
});
```

Verify the resolved URL before building:

```bash
npx expo config --type public | grep apiBaseUrl
```

For production builds, always set `API_BASE_URL` to the real backend URL so the fallback IP is never used.

**Verify the runtime URL:** after launching the app, read the device log for actual fetch URLs:

```bash
xcrun simctl spawn <device-id> log show \
  --predicate 'process == "YourBundleName"' \
  --last 30s --style compact \
  | grep -E 'http://|https://'
```

A convenience script is in `references/verify-simulator-api-url.md`.

### Pitfall: expo run:ios --simulator flag

`npx expo run:ios --simulator` is NOT valid in Expo SDK 54+. The `--simulator` flag was removed. Use `npx expo run:ios` (auto-detects simulator) or build directly with `xcodebuild`.

### Pitfall: Xcode not installed (only CLT)

If `xcodebuild -version` says "requires Xcode, but active developer directory is CommandLineTools":
- Install Xcode from Mac App Store
- Run `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`

## Expo Dependency Version Compatibility

Expo SDK pins specific dependency versions. Installing a wrong-major-version package causes native module errors at runtime.

**Example:** `expo-font` v56 is for Expo SDK 56, but project uses SDK 54. Runtime error: `Cannot find native module 'ExpoFontLoader'`.

**Fix:** Always use `npx expo install <package>` instead of `npm install <package>`. Expo's install command picks the SDK-compatible version.

```bash
# WRONG — may install incompatible version
npm install expo-font

# RIGHT — installs SDK-compatible version
npx expo install expo-font
```

**After fixing:** regenerate native project (`rm -rf ios && npx expo prebuild --platform ios`) and rebuild.

### Pitfall: Stale baked API URL after network change

`expo prebuild` bakes the machine's LAN IP into the binary at `EXConstants.bundle/app.config`. If the machine changes networks (different DHCP IP), the app silently fails to connect — login returns "could not connect to the server" with no visible error about the URL.

**Symptoms:** `curl http://localhost:8000/api/health` works on the Mac, but the app shows "fetch failed: could not connect to the server." The server is running and reachable, but the app is trying to connect to a stale IP.

**Diagnosis:** Read the baked config from the built app:

```bash
APP_PATH="ios/build/Build/Products/Debug-iphonesimulator/AppName.app"
cat "$APP_PATH/EXConstants.bundle/app.config" | python3 -c "import sys,json; print(json.load(sys.stdin).get('extra',{}))"
# Output: {"apiBaseUrl": "http://192.168.68.65:8000"}  ← stale IP
```

Compare with the current IP:

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
# Output: inet 192.168.68.52  ← different IP
```

**Fix:** rebuild with an explicit `API_BASE_URL` so the baked config is correct regardless of network:

```bash
API_BASE_URL="http://localhost:8000" npx expo prebuild --platform ios --clean
# Then rebuild with xcodebuild and reinstall
```

Using `localhost` works because the iOS Simulator shares the Mac's network stack — `localhost` in the simulator resolves to the Mac itself. This avoids the stale-IP problem entirely for dev builds.

**For production builds:** always set `API_BASE_URL` to the real backend URL. Never rely on the `getLocalIp()` fallback for production.

## FlatList numColumns + Section Headers

**The problem:** `FlatList` with `numColumns={2}` groups items into rows. Section header items get treated as one column, pushing the first card to the right. Setting `width: '100%'` on the header doesn't help — the column wrapper constrains it.

**Solutions (in order of preference):**

1. **Separate FlatLists in ListHeaderComponent** — Put "popular" section as a horizontal FlatList inside the main FlatList's `ListHeaderComponent`. Remaining items use `numColumns={2}` on the main FlatList. No section header conflicts.

2. **SectionList** — Works for simple cases but `numColumns` on SectionList has quirks. Test thoroughly.

3. **Spacer items** — Insert invisible spacer items before section headers to force them into column 0. Fragile — breaks if data changes.

**Never:** Embed section markers in flat data with `numColumns` — the header will share a row with the first card.

## Auth / Login Screen Patterns

A minimal login screen should trim the email, show/hide the password, display the server's exact error detail, and dismiss a modal on success.

```tsx
export default function AuthLoginScreen({ navigation }) {
  const { login, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async () => {
    clearError();
    await login(email.trim(), password);
    if (useAuthStore.getState().isLoggedIn) {
      navigation.goBack(); // dismiss modal, don't navigate to root
    }
  };

  return (
    <View style={styles.container}>
      <TextInput
        autoCapitalize="none"
        keyboardType="email-address"
        autoCorrect={false}
        value={email}
        onChangeText={setEmail}
        editable={!isLoading}
      />
      <View>
        <TextInput
          secureTextEntry={!showPassword}
          value={password}
          onChangeText={setPassword}
          editable={!isLoading}
        />
        <Pressable onPress={() => setShowPassword(v => !v)}>
          <Text>{showPassword ? 'Hide' : 'Show'}</Text>
        </Pressable>
      </View>
      {error && <Text style={styles.error}>{error}</Text>}
      <Pressable onPress={handleLogin} disabled={isLoading}>
        <Text>Sign In</Text>
      </Pressable>
    </View>
  );
}
```

### Pitfall: navigating to the root screen from a modal

If the login screen is registered with `presentation: 'modal'` in a stack navigator whose initial route is the root tabs, calling `navigation.navigate('MainTabs')` does nothing because `MainTabs` is already the focused route underneath. Use `navigation.goBack()` to dismiss the modal.

### Pitfall: generic login error hides the real cause

Returning only `Login failed: 401` forces the user to guess whether the email, password, or network is wrong. Parse the response body and include the server's `detail` field in the error message:

```ts
if (!response.ok) {
  const body = await response.text();
  let detail = '';
  try {
    detail = JSON.parse(body).detail || body;
  } catch {
    detail = body || response.statusText;
  }
  throw new Error(`Login failed: ${response.status} ${detail}`);
}
```

### Pitfall: SecureStore fails in unsigned builds

`expo-secure-store` requires iOS entitlements that aren't present in unsigned builds. Both `getItemAsync` and `setItemAsync` throw `A required entitlement isn't present`.

**Fix:** Wrap all SecureStore calls in try/catch and continue gracefully:

```js
async function login(token, user) {
  try {
    await SecureStore.setItemAsync(AUTH_TOKEN_KEY, token);
    await SecureStore.setItemAsync(AUTH_USER_KEY, JSON.stringify(user));
  } catch (e) {
    console.warn('SecureStore write failed (dev build?)', e.message);
  }
  setAuthToken(token);
  setToken(token);
  setUser(user);
}
```

## Image Loading on iOS Simulator

### Pitfall: Static file URLs don't load via React Native Image component

The `Image` component's `source={{ uri: 'http://localhost:3000/images/foo.jpg' }}` may not load even when `curl` returns 200. This is often caused by:
- ATS (App Transport Security) blocking plain HTTP — `NSAllowsLocalNetworking: true` should be set
- Metro bundler caching stale 404 responses from before static serving was added
- The image URL construction using `API_BASE + imageUrl` where `imageUrl` is a relative path

**Reliable pattern:** Create a binary endpoint (like `/api/ships/:id/hero`) that reads the file and serves it with proper Content-Type headers. Use a URL constructor function in the API client:

```js
export function getDestinationHeroUrl(slug) { return `${API_URL}/destinations/${slug}/hero`; }
```

### Pitfall: Stale Metro cache after adding static file serving

If images were 404 before adding `express.static`, Metro caches the failure. Restart with `--clear`:
```bash
npx expo start --dev-client --clear
```

## React Hooks Order Rules

**Never put hooks after early returns.** React tracks hook call order between renders. If `useMemo` is after `if (loading) return`, the hook count changes when `loading` flips, causing `Rules of Hooks` violation.

```js
// BAD — useMemo after early return
const [loading, setLoading] = useState(true);
const data = useMemo(() => ...);
if (loading) return <Loading />;  // ← hooks after this point are skipped on first render
const derived = useMemo(() => ...); // ← only called when !loading, breaks hook order

// GOOD — all hooks before early returns
const [loading, setLoading] = useState(true);
const data = useMemo(() => ...);
const derived = useMemo(() => ...); // ← always called
if (loading) return <Loading />;
```

**Automated check:** scan for this pattern:
```bash
for f in src/screens/*.js; do
  hooks=$(grep -n 'useMemo\|useCallback\|useEffect\|useState' "$f" | tail -1 | cut -d: -f1)
  early=$(grep -n 'if (loading) return\|if (error)' "$f" | head -1 | cut -d: -f1)
  if [ -n "$hooks" ] && [ -n "$early" ] && [ "$hooks" -gt "$early" ]; then
    echo "ISSUE: $f — hooks at line $hooks after early return at line $early"
  fi
done
```

## FlatList ListHeaderComponent stretches vertically when list is empty

When a `FlatList` has no data items, its internal `contentContainerStyle` stretches with `flexGrow: 1` to fill the screen. Any component placed in `ListHeaderComponent` expands vertically — horizontal `ScrollView` pill bars stack their children vertically, buttons stretch to full height, and layouts break.

**Symptoms:** a horizontal pill bar (or any header) works fine when the list has data, but when the list is empty (e.g., no games scheduled for a sport), the pills stack vertically instead of horizontally.

**Fix:** render the header **outside** the FlatList, as a sibling in a `View` wrapper:

```tsx
// WRONG — header stretches when list is empty
<View style={styles.container}>
  <FlatList
    data={sortedGames}
    ListHeaderComponent={<SportPillBar ... />}
    ...
  />
</View>

// RIGHT — header is pinned, FlatList scrolls below it
<View style={styles.container}>
  <SportPillBar ... />
  <FlatList
    data={sortedGames}
    ...
  />
</View>
```

This keeps the header at its natural height regardless of list content. Pull-to-refresh still works on the FlatList below.

## Simulator Commands

```bash
# Boot a simulator
xcrun simctl boot <device-uuid>

# Open Simulator app
open -a Simulator

# List available simulators
xcrun simctl list devices available

# Take screenshot
xcrun simctl io booted screenshot /tmp/sim.png

# Terminate app
xcrun simctl terminate booted com.bundle.identifier

# Launch app
xcrun simctl launch booted com.bundle.identifier

# Install app
xcrun simctl install booted path/to/App.app
```

## Pitfalls Summary

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `expo run:ios --simulator` | `Unknown arguments: --simulator` | Use `xcodebuild` directly |
| Wrong Expo dep version | `Cannot find native module 'ExpoFontLoader'` | `npx expo install <pkg>` |
| SecureStore in unsigned build | `A required entitlement isn't present` | try/catch around all calls |
| FlatList numColumns + sections | Cards pushed to right, misaligned | Separate FlatLists in header |
| Hooks after early returns | `Rules of Hooks` violation | Move all hooks before returns |
| Stale Metro image cache | Images show as blank/gray | `npx expo start --dev-client --clear` |
| Image URLs from static files | Images don't load in RN Image | Use binary API endpoint instead |
| Slug mismatch (underscore vs hyphen) | Missing data in UI | Verify slugs against API response |
| Path alias works in TS but fails at runtime | `Unable to resolve module @/...` from Metro | Add `babel-plugin-module-resolver` config |
| Raw `.sql` import fails at runtime | Metro cannot resolve `.sql` assets | Embed migrations as TS string exports |
| pnpm install does nothing | Empty output, no node_modules change | Delete lockfile + node_modules, reinstall; also remove workspace dirs without `package.json` |
| Wrong Expo SDK package version | `No matching version found` for `expo-sqlite@~16.2.0` | Use SDK-aligned versions (`~56.0.x` for SDK 56) or `npx expo install` |
| Empty string team names | Schedule rows show only ` @ ` | Use `||` fallback to team ID: `away_team_name || away_team_id || 'Away'` |
| Backend schedule lacks team names | `home_team_name`/`away_team_name` are empty | Build a name lookup from ratings corpus by team ID and fill missing names |
| Backend duplicate IDs across sports | SQLite `UNIQUE constraint failed` during sync | Prefix `mobile_id` with sport, and use `INSERT OR REPLACE` on client |
| Navigator bypasses login | App opens to main tabs, pull-to-refresh does nothing | Gate navigator on `isLoggedIn` with conditional screen rendering — see `mobile-offline-first-expo` pitfall #25 |
| Stale baked API URL after network change | "could not connect to the server" despite server running | Rebuild with `API_BASE_URL="http://localhost:8000"` — check `EXConstants.bundle/app.config` for stale IP |
| FlatList ListHeaderComponent stretches when empty | Horizontal pills/buttons stack vertically when list has no data | Move header outside the FlatList as a sibling `View` |

## Screen Testing with Jest (without jest-expo)

When the Expo project already uses `ts-jest` with `testEnvironment: 'node'` for data-layer tests, switching the whole suite to `jest-expo` just to render a few screens can introduce ESM setup-file errors and transform conflicts. A lightweight alternative is to keep `ts-jest` and mock React Native + Expo modules so screen tests run in the same environment as data-layer tests.

**When to use this pattern:**
- Existing mobile tests use `ts-jest` + `node` and pass cleanly.
- You only need smoke tests for a handful of screens (render, text presence, press handlers, refresh control).
- You want to avoid the `jest-expo` / `@react-native/jest-preset` setup file wrestling match.

**When to switch to jest-expo:**
- You need deep native module behavior (reanimated, gesture handler, navigation state, SafeAreaContext).
- Tests need to render real `Animated`, `Image`, or platform-specific APIs.
- You need `@testing-library/react-native` matchers that depend on the RN renderer environment.

### Recipe

1. **Mock `react-native`** so screen imports don't load the real RN bundle in Node.
   Create `src/__mocks__/react-native.ts` that exports mock components for `View`, `Text`, `ScrollView`, `FlatList`, `Pressable`, `ActivityIndicator`, `RefreshControl`, `StatusBar`, and a `StyleSheet.create` passthrough.
2. **Mock `expo-constants`** because it imports ESM `expo-modules-core` which `ts-jest` won't transform if it's ignored.
   Create `src/__mocks__/expo-constants.ts` returning `{ expoConfig: { extra: { apiBaseUrl: 'http://localhost:8000' } } }`.
3. **Map the mocks in `jest.config.js`** using `moduleNameMapper`:
   ```js
   moduleNameMapper: {
     '^react-native$': '<rootDir>/src/__mocks__/react-native.ts',
     '^expo-constants$': '<rootDir>/src/__mocks__/expo-constants.ts',
   },
   ```
4. **Enable `act()`**. Add `jest.setup.ts` that sets `globalThis.IS_REACT_ACT_ENVIRONMENT = true` and switches to the React development build (`process.env.NODE_ENV = 'development'`). Wire it with `setupFilesAfterEnv`.
4. **Mock any other native deps** used by the screen under test (e.g., `expo-sqlite`, `expo-secure-store`).
5. **Wrap TanStack Query mutations** if the screen calls `useMutation`. Either mock the mutation hooks at the module level or render the screen inside a `QueryClientProvider` with a test `QueryClient`.
6. **Render with `act` and flush async effects**. If the screen fetches data in `useEffect`, wrap `TestRenderer.create` in `await act(async () => { ... })`. For press handlers, wrap the `onPress` call in `act` too.

Full starter config + mocks + example test are in `references/jest-screen-testing.md`.

### Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `act is not a function` | `react-test-renderer` exports `act` only in development builds; Jest sets `NODE_ENV=test` | Set `process.env.NODE_ENV = 'development'` in `jest.setup.ts` before requiring `react-test-renderer` |
| `The current testing environment is not configured to support act(...)` | `globalThis.IS_REACT_ACT_ENVIRONMENT` is false | Set it to `true` in `jest.setup.ts` |
| `No QueryClient set, use QueryClientProvider to set one` | Screen imports `useMutation` from `@tanstack/react-query` | Mock the mutation hook, or wrap screen in `QueryClientProvider` |
| `Cannot use import statement outside a module` from `expo-constants` | `expo-modules-core` is ignored by `transformIgnorePatterns` | Mock `expo-constants` via `moduleNameMapper` |
| Screen renders `null` or tree is unmounted | Effects/state updates aren't flushed | Wrap `TestRenderer.create` in `act(...)` and await it |
| Can't find `Pressable` by `node.type === 'Pressable'` | Mock components are anonymous functions, not string types | Use named mock functions so `node.type === 'Pressable'`, or match on the presence of `props.onPress` plus expected text in the subtree |
| FlatList shows no item text after rendering | The mock `FlatList` returned only the raw data prop; it did not evaluate `renderItem` | Make the `FlatList` mock map `data` through `renderItem` and return those elements as children |
| `JSON.stringify(tree.toJSON())` throws on circular props | `RefreshControl`, `QueryClientProvider`, and other wrappers embed element references | Use a recursive `extractText(node)` helper instead of stringifying the whole tree |

## Offline-First Data Layer with SQLite + TanStack Query

Reference docs:
- Starter recipe: `references/expo-offline-sqlite-starter.md`
- Jest screen testing: `references/jest-screen-testing.md`
- Multi-sport sync deduplication and missing-name handling: `references/mobile-sync-deduplication.md`
- Simulator API URL verification: `references/verify-simulator-api-url.md`
- **Simulator SQLite inspection**: `references/simulator-sqlite-inspection.md` — find and query the device DB directly from terminal to debug migration failures, verify row counts, and check column names.
- **Production-to-local data sync**: `references/production-to-local-data-sync.md` — pull production PostgreSQL data into local SQLite for mobile dev parity (schema drift handling, verification, league count expectations).

Summary of the pattern:

- Use `expo-sqlite` as the structured offline source of truth (relational tables, migrations via `PRAGMA user_version`).
- Use TanStack Query **only** for network fetches and mutations; do **not** persist its cache to SQLite.
- Validate the sync payload with Zod before writing to SQLite.
- Use a SQLite `mutation_outbox` to retry failed mutations on the next foreground sync.
- Always run migrations before rendering the root navigator.
- **Deduplicate cross-sport IDs in the backend:** team IDs like `HOU` exist in MLB, NBA, NFL, MLS. If `ratings.mobile_id` is set to the raw team ID, SQLite primary-key sync will abort. Prefix the ID with sport (`mlb:HOU`) and use `INSERT OR REPLACE` on the client for resilience.

### Pitfall: TanStack Query cache persistence to SQLite

**Why it's wrong:** TanStack Query stores each query result as a serialized JSON blob. SQLite is relational. You lose indexes, foreign-key constraints, and transactions by stuffing blobs into a single table. The UI then has to query the blob store, which reintroduces the serialization cost you were trying to avoid.

**Right shape:** TanStack Query fetches the API response; a sync layer parses it with Zod and writes rows into normalized SQLite tables. React hooks read from SQLite. TanStack Query handles retries, loading states, and mutations only.

### Pitfall: importing `.sql` migration files in Metro

Metro does not know how to bundle raw `.sql` files as strings. `import('./migrations/001_initial.sql')` will fail at runtime even if TypeScript is happy.

**Fix:** keep a `src/db/migrations.ts` file that exports each migration as a template-literal string, then import that module from `src/db/offline.ts`.

### Pitfall: path aliases work in TypeScript but fail at runtime

`tsconfig.json` path aliases only satisfy the type checker. Metro's bundler resolves modules at runtime and does not read `tsconfig.json`. If you see `Unable to resolve module @/store/auth` at app startup, your Babel config is missing or wrong.

**Fix:** add `babel-plugin-module-resolver` to `devDependencies` and configure it in `babel.config.js`.

### Pitfall: Expo SDK package versions are SDK-aligned

Starting with recent SDK releases, Expo packages like `expo-sqlite` and `expo-secure-store` use SDK-aligned versions (`~56.0.x` for SDK 56) rather than independent semver. Installing `expo-sqlite@~16.2.0` will fail with "No matching version found."

**Fix:** look up the correct SDK-aligned version in the Expo SDK docs or on npm, or use `npx expo install expo-sqlite` which resolves it automatically. For a concrete version map, see `references/expo-offline-sqlite-starter.md` under "Expo SDK package-version map".

### Pitfall: pnpm install silently does nothing in a workspace

If a workspace package was added but `pnpm-lock.yaml` predates it, `pnpm install` may complete with no output and no new packages installed.

**Fix:** delete `pnpm-lock.yaml` and `node_modules`, then run `pnpm install` from the workspace root.
