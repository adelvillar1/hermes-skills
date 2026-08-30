# Verify the API URL an Expo app is using at runtime

When an Expo app running in the iOS Simulator can't reach a local backend, the first thing to confirm is the exact URL it is actually attempting to call. `app.config.ts` may resolve differently at build time than you expect, and `localhost` inside the simulator means the simulator itself, not the host Mac.

## Recipe

1. Find the simulator device ID:

   ```bash
   xcrun simctl list devices | grep Booted
   ```

2. Launch the app (or leave it running), then stream the device log filtered for the app and HTTP URLs:

   ```bash
   DEVICE_ID=E621FA7C-581F-4395-B81D-9ADC4E1AA70E
   BUNDLE_ID=com.eloscenariolab.app

   xcrun simctl spawn "$DEVICE_ID" log show \
     --predicate "process == \"$BUNDLE_ID\"" \
     --last 30s --style compact \
     | grep -E 'http://|https://'
   ```

   Example good output:
   ```
   url: http://192.168.68.65:8000/api/mobile/sync
   ```

   Example bad output (app points at itself):
   ```
   url: http://localhost:8000/api/mobile/sync
   ```

3. If the URL is `localhost`, reconfigure `app.config.ts` to resolve the host Mac's LAN IP. See the `localhost` pitfall in the main skill.

## Common related log errors

| Log line | Meaning |
|----------|---------|
| `Socket SO_ERROR [61: Connection refused]` | App reached a host but nothing listens on that port. |
| `nw_connection_report_state_with_handler ... failed error Connection refused` | Same as above; often means `localhost:8000` resolved to the simulator itself. |
| `response_status=401` on `/api/mobile/sync` | API URL is correct but request lacks auth token. For an unauthenticated user this is expected and the UI should offer login. |
| `response_status=200` on a Metro bundle URL | App is loading JS from Metro correctly. |

## One-liner

```bash
xcrun simctl spawn E621FA7C-581F-4395-B81D-9ADC4E1AA70E log show --predicate 'process == "ELOScenarioLab"' --last 30s --style compact | grep -E 'http://|https://|Connection refused'
```
