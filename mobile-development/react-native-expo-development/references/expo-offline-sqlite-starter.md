# Expo Offline-First SQLite + TanStack Query Starter

A concise reference for the data-first mobile architecture used in ELO Scenario Lab: structured `expo-sqlite` as the offline source of truth, TanStack Query only for network fetches/mutations, and a Zod-validated sync endpoint.

## When to use this pattern

- The mobile app must work offline after first sync.
- Data is mostly read-only (or mutations are simple and idempotent).
- You already have a FastAPI/REST backend and want the simplest reliable offline layer.
- You do NOT want to fight Metro module resolution for raw `.sql` files or TanStack Query cache serialization.

## What NOT to do

1. **Do not persist TanStack Query cache to SQLite.** TanStack Query stores query results as a JSON blob. SQLite is relational. Mapping blobs to relational tables is an anti-pattern: you lose indexing, transactions, and type safety. Use TanStack Query for network only; store the parsed data in SQLite.
2. **Do not import `.sql` files directly in Metro.** Metro does not bundle raw SQL as strings. Embed migrations as TypeScript string exports.
3. **Do not use Expo SDK package versions from old blog posts.** Expo SDK 56 packages use SDK-aligned versions (`expo-sqlite ~56.0.x`), not legacy semver (`~16.2.0`).

## Workspace setup

Root `pnpm-workspace.yaml`:
```yaml
packages:
  - "mobile/**"
```

Mobile app `package.json` (Expo SDK 56):
```json
{
  "name": "expo-app",
  "main": "index.ts",
  "dependencies": {
    "expo": "~56.0.11",
    "expo-secure-store": "~56.0.1",
    "expo-sqlite": "~56.0.1",
    "react": "19.2.3",
    "react-native": "0.85.3",
    "@tanstack/react-query": "^5.74.4",
    "zod": "^3.25.42",
    "zustand": "^5.0.3"
  },
  "devDependencies": {
    "@types/jest": "^29.5.14",
    "@types/node": "^22.14.0",
    "babel-plugin-module-resolver": "^5.0.0",
    "jest": "^29.7.0",
    "jest-expo": "~56.0.0",
    "ts-jest": "^29.3.2",
    "typescript": "~6.0.3"
  }
}
```

Install with `pnpm install` from the repo root. If `pnpm install` silently does nothing, delete `pnpm-lock.yaml` and `node_modules` and regenerate — stale lockfiles often ignore newly added workspace packages. Also ensure every directory listed in `pnpm-workspace.yaml` actually contains a `package.json`; listing a directory without one (e.g., `ui/` that only has static HTML/JS) can confuse pnpm and cause it to skip installing other workspace packages.

## Expo SDK package-version map

Expo SDK packages are version-aligned with the SDK. As of SDK 56 (June 2026):

| Package | Correct version | Common stale version that 404s |
|---------|-----------------|------------------------------|
| `expo` | `~56.0.11` | — |
| `expo-secure-store` | `~56.0.1` | `~14.2.3` |
| `expo-sqlite` | `~56.0.1` | `~16.2.0` |
| `expo-status-bar` | `~56.0.4` | older `~x.y.z` |

Always verify with `pnpm view <pkg> versions` or use `npx expo install <pkg>` to resolve the SDK-compatible version.

## TypeScript path aliases

`tsconfig.json`:
```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "baseUrl": ".",
    "rootDir": ".",
    "paths": { "@/*": ["src/*"] },
    "ignoreDeprecations": "6.0"
  },
  "include": ["src/**/*", "App.tsx", "index.ts"]
}
```

`babel.config.js` (required for Metro at runtime):
```js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      ['babel-plugin-module-resolver', {
        root: ['./src'],
        alias: { '@': './src' },
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
      }],
    ],
  };
};
```

## Embedded migrations

`src/db/migrations.ts`:
```ts
export const MIGRATION_001_INITIAL = `
CREATE TABLE IF NOT EXISTS favorites (...);
CREATE TABLE IF NOT EXISTS schedule (...);
...
`;

export const MIGRATIONS: Record<number, string> = {
  1: MIGRATION_001_INITIAL,
};
```

`src/db/offline.ts` runs them with `PRAGMA user_version`.

## Sync architecture

1. App boots → run migrations.
2. Login → `POST /api/auth/login`, store JWT in `expo-secure-store`.
3. `SyncProvider` listens to `AppState`.
4. On foreground with ≥5 minutes since last sync → call `GET /api/mobile/sync`.
5. Validate response with Zod.
6. In a SQLite transaction: delete old rows, insert new ones, update `sync_meta`.
7. If a mutation fails, write to `mutation_outbox`; flush it before the next sync.

## Unit testing with ts-jest

Use `ts-jest` + `node` test environment for pure logic tests. Keep `jest-expo` for integration tests that need native modules.

`jest.config.js`:
```js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/src/$1' },
  transformIgnorePatterns: ['node_modules/(?!(zod|expo-constants)/)'],
};
```

Mock native modules like `expo-secure-store` and `expo-constants` in tests that import the API client.

## Verification checklist

- [ ] `pnpm install` from repo root succeeds and populates `node_modules/.pnpm`.
- [ ] `pnpm run typecheck` passes.
- [ ] `pnpm run test` passes with at least schema + API client tests.
- [ ] Migrations run on first app boot and `PRAGMA user_version` advances.
- [ ] Foreground sync with no network fails gracefully and uses existing SQLite data.
- [ ] A failed favorite mutation lands in `mutation_outbox` and is retried on next sync.
- [ ] JWT is cleared on 401.
