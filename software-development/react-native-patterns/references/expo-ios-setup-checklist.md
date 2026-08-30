# Expo iOS Simulator Setup Checklist

## System Check

```bash
# Required
node --version          # 18+
xcodebuild -version     # Xcode installed
pod --version           # CocoaPods installed
npx expo --version      # Expo CLI available

# Available simulators
xcrun simctl list devices available | grep iPhone
```

## Full Build Sequence

```bash
# 1. Install dependencies
cd apps/mobile && npm install

# 2. Install SDK-compatible Expo packages
npx expo install expo-font   # CRITICAL: fixes version mismatch

# 3. Generate native project
npx expo prebuild --platform ios

# 4. Build (skip code signing)
cd ios
xcodebuild \
  -workspace *.xcworkspace \
  -scheme $(basename $(ls *.xcworkspace) .xcworkspace) \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  2>&1 | tail -10
cd ..

# 5. Boot simulator + install
xcrun simctl boot <device-udid>
open -a Simulator
xcrun simctl install booted $(find ios/build -name "*.app" -not -path "*Watch*" | head -1)

# 6. Start Metro + API + launch
cd ../api && npm run dev &    # API on port 3000
cd ../mobile
npx expo start --dev-client & # Metro on port 8081
sleep 8
xcrun simctl launch booted com.anonymous.cruiser-intelligence
```

## Quick Verification

```bash
# API running?
curl -s http://localhost:3000/api/destinations | head -100

# Metro running?
curl -s http://localhost:8081/status

# Simulator screenshot (for automated checks)
xcrun simctl io booted screenshot /tmp/sim.png
```

## Known Pitfalls

| Pitfall | Cause | Fix |
|---------|-------|-----|
| `expo run:ios --simulator` error | Flag doesn't exist in SDK 54+ | Use `xcodebuild` directly |
| `No code signing certificates` | `expo run:ios` checks signing before build | Use `xcodebuild` with `CODE_SIGNING_ALLOWED=NO` |
| `EXPO_NO_CODESIGNING=1` ignored | Expo CLI doesn't respect this env var | Use `xcodebuild` directly |
| `Cannot find native module 'ExpoFontLoader'` | expo-font v56 with Expo SDK 54 | `npx expo install expo-font` before prebuild |
| SecureStore entitlement error | Unsigned builds lack keychain entitlements | Wrap all SecureStore calls in try/catch |
| Hooks order crash | `useMemo` after `if (loading) return` | Move ALL hooks before ALL early returns |
| Blank screen on launch | Metro not running | Start Metro with `npx expo start --dev-client` |
| `browser_vision` shows blank | Browser tool captures browser, not simulator | Use `xcrun simctl io booted screenshot` |

## After Code Changes

- **JS-only changes**: Metro hot-reloads automatically. Just save the file.
- **New native dependency**: `rm -rf ios && npx expo prebuild --platform ios`, then rebuild.
- **New Expo package**: `npx expo install <package>`, then prebuild + rebuild.
