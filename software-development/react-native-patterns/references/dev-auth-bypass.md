# Dev Auth Bypass for OAuth-less Testing

## AuthContext.js — wrap SecureStore in try/catch

```js
async function login(token, user) {
  try {
    await SecureStore.setItemAsync(AUTH_TOKEN_KEY, token);
    await SecureStore.setItemAsync(AUTH_USER_KEY, JSON.stringify(user));
  } catch (e) {
    // SecureStore may fail in unsigned dev builds — continue anyway
    console.warn('SecureStore write failed (dev build?)', e.message);
  }
  setAuthToken(token);
  setToken(token);
  setUser(user);
}

async function loadAuthState() {
  try {
    const storedToken = await SecureStore.getItemAsync(AUTH_TOKEN_KEY);
    const storedUser = await SecureStore.getItemAsync(AUTH_USER_KEY);
    if (storedToken && storedUser) {
      setToken(storedToken);
      setAuthToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
  } catch (e) {
    // SecureStore may fail in unsigned dev builds — that's OK
    console.warn('SecureStore read failed (dev build?)', e.message);
  } finally {
    setLoading(false);
  }
}
```

## LoginScreen.js — dev bypass button

```jsx
import { setAuthToken } from '../api/client';

// After the "terms" text, inside the content View:
{__DEV__ && (
  <TouchableOpacity
    style={styles.devBypass}
    onPress={() => login('dev-bypass-token', {
      id: 'dev-user',
      name: 'Dev User',
      email: 'dev@test.com'
    })}
    activeOpacity={0.7}
  >
    <Text style={styles.devBypassText}>Browse as Guest (dev only)</Text>
  </TouchableOpacity>
)}

// Styles:
devBypass: {
  marginTop: spacing.xl,
  paddingVertical: spacing.sm,
},
devBypassText: {
  ...typography.caption,
  color: colors.accent,
  textAlign: 'center',
  textDecorationLine: 'underline',
},
```

## What works / doesn't with dev token

| Feature | Works? | Why |
|---------|--------|-----|
| Browse destinations, cruise lines, ships | ✅ | Public API endpoints (no auth required) |
| Itinerary detail, port detail | ✅ | Public endpoints |
| Comparison screen | ✅ | No API calls |
| Report card carousels | ✅ | Public endpoints |
| Quiz | ✅ | Questions are public |
| Favorites / bookmarks | ❌ | `/api/me/favorites` returns 401 |
| Chat history | ❌ | `/api/me/chat` returns 401 |
| Quiz result persistence | ❌ | `/api/me/quiz` returns 401 |
