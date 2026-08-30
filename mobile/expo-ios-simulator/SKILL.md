---
name: expo-ios-simulator
description: "Run Expo/React Native apps on iOS Simulator without Apple Developer account. Covers the code signing workaround for `expo run:ios` failures, direct xcodebuild builds, and Metro bundler setup."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mobile, react-native, expo, ios, simulator, xcode, testing]
    related: []
---

# Expo iOS Simulator Setup

Run Expo managed-workflow React Native apps on the iOS Simulator when `npx expo run:ios` fails with code signing errors. No Apple Developer account needed.

## When to Use

- `npx expo run:ios` fails with "No code signing certificates are available to use"
- User wants to test a React Native/Expo app on iOS Simulator
- No Apple Developer account configured
- First-time iOS build for an Expo project

## Prerequisites

1. **Xcode** — installed from Mac App Store
2. **CocoaPods** — `sudo gem install cocoapods` or `brew install cocoapods`
3. **Node.js** — 18+
4. **Simulator** — boot one via `xcrun simctl boot <device-id>` or open Simulator.app

Check: `xcodebuild -version` and `pod --version` must succeed.

## The Problem

`npx expo run:ios` checks for code signing certificates **before** building, even for simulator targets. On machines without an Apple Developer account, this fails immediately:

```
CommandError: No code signing certificates are available to use.
```

Workarounds that **don't work**:
- `EXPO_NO_CODESIGNING=1 npx expo run:ios` — ignored
- Adding `CODE_SIGNING_ALLOWED = "NO"` to the pbxproj — Expo checks before reaching Xcode
- Any env var or flag on `expo run:ios` — no simulator-only flag exists in current Expo SDK

## The Solution

Three-step process: prebuild → xcodebuild → install + launch.

### Step 1: Generate native project

```bash
cd apps/mobile  # or wherever app.json lives
npx expo prebuild --platform ios
```

This creates the `ios/` directory with a proper Xcode workspace, CocoaPods Podfile, and all Expo native modules configured. **Must run before the first build and after adding new Expo packages.**

### Step 2: Build with xcodebuild (skip code signing)

```bash
cd ios
xcodebuild \
  -workspace CruiserIntelligence.xcworkspace \
  -scheme CruiserIntelligence \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  2>&1 | tail -30
```

Key flags:
- `-destination 'platform=iOS Simulator,name=<device>'` — targets simulator only
- `CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO` — disables signing at build time
- `-derivedDataPath build` — keeps build artifacts local (not in ~/Library)
- First build: 5-10 minutes. Subsequent builds: 1-2 minutes (Xcode caches).

The workspace name and scheme come from `app.json` → `expo.slug`. Check with:
```bash
ls ios/*.xcworkspace
xcodebuild -workspace ios/*.xcworkspace -list 2>&1 | grep -A5 'Schemes'
```

### Step 3: Install and launch on simulator

```bash
# Find the built .app
APP_PATH=$(find ios/build -name "*.app" -not -path "*Watch*" | head -1)

# Install on booted simulator
xcrun simctl install booted "$APP_PATH"

# Start Metro bundler (serves JS to the app)
cd apps/mobile
npx expo start --dev-client &

# Wait for Metro to initialize, then launch the app
sleep 8
xcrun simctl launch booted com.anonymous.cruiser-intelligence
```

The bundle identifier comes from `app.json` → `expo.slug` (with `com.anonymous.` prefix if no explicit iOS bundle ID is set). Check with: `grep -r 'PRODUCT_BUNDLE_IDENTIFIER' ios/*.xcodeproj/project.pbxproj | head -1`.

### Step 4: Iterating on JS/TS-only changes (no rebuild needed)

**After the first build**, when you only change `.ts`/`.tsx`/`.js` files (no new Expo packages, no native module changes), you do **NOT** need to rebuild with xcodebuild. The existing `.app` on the simulator will pick up the updated JS bundle from Metro. This saves 5–10 minutes per iteration.

```bash
# The app is already installed from the first build. Just:

# 1. Kill any stale Metro process, then restart with cache clear
npx expo start --dev-client --clear &

# 2. Wait for Metro to be ready
sleep 10 && curl -s http://localhost:8081/status
# Should return: packager-status:running

# 3. Terminate and relaunch the app (forces JS bundle reload)
BUNDLE_ID=$(grep 'PRODUCT_BUNDLE_IDENTIFIER' ios/*.xcodeproj/project.pbxproj | head -1 | sed 's/.*= //;s/;//' | tr -d '"' | sed 's/$(PRODUCT_NAME)//')
xcrun simctl terminate booted "$BUNDLE_ID"
xcrun simctl launch booted "$BUNDLE_ID"

# 4. Verify visually (optional — for agent-driven QA)
xcrun simctl io booted screenshot /tmp/sim.png
```

**When you DO need to rebuild** (re-run Step 2):
- Added or removed an Expo package (`npx expo install ...`)
- Changed native configuration in `app.json` or `app.config.*`
- Changed iOS-specific native code (Info.plist, entitlements, etc.)
- App crashes on launch with a native module error

## Troubleshooting

### "Cannot find native module 'ExpoFontLoader'" on launch

**Cause**: `expo-font` version is incompatible with the project's Expo SDK. This happens when `expo-font` was installed independently (e.g. `npm install expo-font@latest`) instead of through Expo's version resolver. The native module name changes across SDK versions (ExpoFontLoader in v56, ExpoFont in v54).

**Fix**: Install the SDK-compatible version BEFORE prebuild:
```bash
cd apps/mobile
npx expo install expo-font    # installs the version matching your Expo SDK
rm -rf ios
npx expo prebuild --platform ios
# Then repeat Step 2 (xcodebuild)
```

**How to detect**: Check `node_modules/expo-font/package.json` version vs `node_modules/expo/package.json` version. If expo-font is v55+ but expo is v54, that's the mismatch.

**General rule**: Always use `npx expo install <package>` instead of `npm install <package>` for Expo modules. The `expo install` command resolves the SDK-compatible version automatically.

### Metro bundler shows no output

Metro may take 10-15 seconds to initialize. Check with:
```bash
curl -s http://localhost:8081/status 2>&1
```

If it returns `packager-status:running`, Metro is ready. If not, restart:
```bash
npx expo start --dev-client --clear
```

### App shows blank white screen

The app is waiting for Metro to serve the JS bundle. Ensure:
1. Metro bundler is running (`npx expo start --dev-client`)
2. The API server is running (`cd apps/api && npm run dev`)
3. The app's API_BASE URL matches the local server (iOS simulator uses `localhost`, Android emulator uses `10.0.2.2`)

### Simulator not found

List available simulators:
```bash
xcrun simctl list devices available | grep iPhone
```

Boot one if none are running:
```bash
xcrun simctl boot <device-udid>
open -a Simulator
```

### Build fails with signing error inside xcodebuild

The `CODE_SIGNING_ALLOWED=NO` flag must be passed as a build setting (after the other flags), not as an env var. Verify:
```bash
xcodebuild ... CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO
```

Not: `CODE_SIGNING_ALLOWED=NO xcodebuild ...`

## Quick Reference

```bash
# Full sequence (copy-paste)
cd /path/to/project/apps/mobile

# 1. Prebuild (first time or after adding packages)
npx expo prebuild --platform ios

# 2. Build
cd ios && xcodebuild -workspace *.xcworkspace -scheme $(basename $(ls *.xcworkspace) .xcworkspace) -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath build CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO 2>&1 | tail -10 && cd ..

# 3. Install + launch
xcrun simctl install booted $(find ios/build -name "*.app" -not -path "*Watch*" | head -1)
npx expo start --dev-client &
sleep 8 && xcrun simctl launch booted $(grep -r 'PRODUCT_BUNDLE_IDENTIFIER' ios/*.xcodeproj/project.pbxproj | head -1 | sed 's/.*= //;s/;//' | tr -d '"')
```

## Pitfalls

1. **`expo run:ios` will never work without an Apple Developer account** on the current Expo SDK (54+). Don't keep retrying with different flags — go straight to the xcodebuild path.

2. **Prebuild must be re-run after adding new Expo packages** (expo-camera, expo-haptics, etc.). If the app crashes with "Cannot find native module", the native project is stale.

3. **The `--simulator` flag doesn't exist** on `npx expo run:ios` in Expo SDK 54+. Don't try it.

4. **`EXPO_NO_CODESIGNING=1` is ignored** by current Expo CLI. Don't rely on it.

5. **Direct xcodebuild builds are NOT identical to Expo's managed builds.** Some Expo tooling (expo-dev-client, expo-updates) may behave differently. For production builds, use EAS Build instead.

6. **Metro bundler must be running** when the app launches. Without it, the app shows a blank screen or a connection error. Always start Metro before launching the app.

7. **API server must be running** on the correct port. iOS simulator accesses `localhost` directly (unlike Android emulator which needs `10.0.2.2`).

8. **SecureStore requires entitlements** that aren't present in unsigned builds. Calls to `SecureStore.getItemAsync()` and `SecureStore.setItemAsync()` will throw `"A required entitlement isn't present"`. The best fix is a **wrapper module** with in-memory fallback — don't scatter try/catch at every callsite:
   ```typescript
   // api/client.ts — wrap ALL SecureStore calls through this
   const memoryStore = new Map<string, string>();

   async function secureGet(key: string): Promise<string | null> {
     try { return await SecureStore.getItemAsync(key); }
     catch { return memoryStore.get(key) ?? null; }
   }

   async function secureSet(key: string, value: string): Promise<void> {
     try { await SecureStore.setItemAsync(key, value); }
     catch { memoryStore.set(key, value); }
   }

   async function secureDelete(key: string): Promise<void> {
     try { await SecureStore.deleteItemAsync(key); }
     catch { memoryStore.delete(key); }
   }
   ```
   This ensures `setToken()` (called after login) doesn't crash the app. In-memory storage loses the token on app restart, so the user re-logs-in — acceptable for dev testing. For production builds with proper entitlements, SecureStore works normally and the memory fallback is never hit.

9. **React hooks must be called before any early returns.** A common crash pattern in React Native screens: `useMemo` or `useCallback` placed after `if (loading) return <LoadingState />`. When `loading` changes, React sees hooks called in a different order and crashes with "React has detected a change in the order of Hooks". Fix: move ALL hooks before ALL early returns:
   ```js
   // ✅ Correct
   const data = useMemo(() => { ... }, [deps]);
   if (loading) return <LoadingState />;

   // ❌ Wrong — useMemo skipped on first render
   if (loading) return <LoadingState />;
   const data = useMemo(() => { ... }, [deps]);
   ```

10. **Taking simulator screenshots programmatically**: `xcrun simctl io booted screenshot /tmp/sim.png`. Useful for verifying app state after builds without manual inspection. Note: this captures the simulator screen, not the macOS desktop — `browser_vision` won't see the simulator.

11. **JS-only changes don't need a native rebuild.** After the first build, iterating on `.ts`/`.tsx`/`.js` files only requires restarting Metro (`npx expo start --dev-client --clear`) and relaunching the app (`xcrun simctl terminate booted <bundle-id> && xcrun simctl launch booted <bundle-id>`). The existing `.app` loads the fresh JS bundle from Metro. This saves 5–10 minutes per iteration. Only rebuild with xcodebuild when you add/remove Expo packages or change native code. See Step 4 above.

12. **Stale baked LAN IP — "fetch failed: could not connect to the server".** If `app.config.ts` uses `os.networkInterfaces()` to auto-resolve the host Mac's LAN IP at prebuild time (common pattern for connecting simulator apps to a local dev server), the IP is **baked into the `.app` binary**. When the machine changes networks (different WiFi, hotspot, office vs home), the baked IP is stale. Every API call from the app returns connection refused. The symptom looks like the server is down, but `curl localhost:8000` works fine from the Mac.

    **Verify the baked IP:**
    ```bash
    cat <app>.app/EXConstants.bundle/app.config | python3 -c "import sys,json; print(json.load(sys.stdin).get('extra',{}))"
    # Compare to current: ifconfig | grep "inet " | grep -v 127.0.0.1
    ```

    **Fix:** Re-run prebuild (picks up current IP) + xcodebuild + reinstall:
    ```bash
    npx expo prebuild --platform ios --clean
    cd ios && xcodebuild -workspace *.xcworkspace -scheme <Name> -configuration Debug \
      -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
      -derivedDataPath build CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO
    xcrun simctl terminate booted <bundle-id> 2>/dev/null
    xcrun simctl install booted ios/build/Build/Products/Debug-iphonesimulator/<Name>.app
    xcrun simctl launch booted <bundle-id>
    ```

    **Prevention:** `localhost` works correctly in the iOS Simulator — it shares the host Mac's network namespace. Use `http://localhost:8000` as the API base URL instead of `getLocalIp()` to avoid this entirely. The `getLocalIp()` pattern is only needed for Android Emulator (which uses `10.0.2.2` to reach the host).
