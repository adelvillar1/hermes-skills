# React Native / Expo Screen Testing with Jest (no jest-expo)

Lightweight recipe for writing React Native screen tests in a project that already uses `ts-jest` + `testEnvironment: 'node'` for data-layer tests. Keeps one Jest config instead of fighting `jest-expo` setup files.

## Why mock components?

The real `react-native` package ships native/ESM code that `ts-jest` in a Node environment cannot load cleanly. Rather than switching the whole suite to `jest-expo` (which can conflict with `ts-jest` setup files and ESM transforms), we replace RN primitives with simple mock components. This is only appropriate for **smoke tests**: verify a screen renders the right text, that lists map data correctly, that press handlers fire, and that pull-to-refresh controls exist. It is not appropriate for testing animation, gestures, native module behavior, or pixel-perfect layout.

## Files to add

### 1. `src/__mocks__/react-native.ts`

Use named functions so the rendered JSON tree retains string element types (`'View'`, `'Pressable'`, etc.), which makes test assertions far easier than anonymous mock functions.

```ts
import * as React from 'react';

export function View(props: any) { return React.createElement('View', props, props.children); }
export function Text(props: any) { return React.createElement('Text', props, props.children); }
export function ScrollView(props: any) { return React.createElement('ScrollView', props, props.children); }
export function Pressable(props: any) { return React.createElement('Pressable', props, props.children); }
export function ActivityIndicator(props: any) { return React.createElement('ActivityIndicator', props, props.children); }
export function RefreshControl(props: any) { return React.createElement('RefreshControl', props, null); }
export function StatusBar(props: any) { return React.createElement('StatusBar', props, null); }
export const StyleSheet = {
  create: (styles: any) => styles,
  flatten: (styles: any) => (Array.isArray(styles) ? Object.assign({}, ...styles) : styles || {}),
};

// FlatList needs to actually render its items, otherwise the JSON tree will
// contain the raw data prop but no child elements from renderItem.
export function FlatList(props: any) {
  const { data, renderItem, keyExtractor, ListEmptyComponent, refreshControl, ...rest } = props;
  const children = data && data.length
    ? data.map((item: any, index: number) =>
        React.createElement(
          React.Fragment,
          { key: keyExtractor ? keyExtractor(item, index) : index },
          renderItem({ item, index, separators: {} })
        )
      )
    : ListEmptyComponent || null;
  return React.createElement('FlatList', rest, children, refreshControl);
}

export default {
  View, Text, ScrollView, FlatList, Pressable,
  ActivityIndicator, RefreshControl, StatusBar, StyleSheet,
};
```

### 2. `src/__mocks__/expo-constants.ts`

```ts
export default {
  expoConfig: {
    extra: {
      apiBaseUrl: 'http://localhost:8000',
    },
  },
};
```

### 3. `jest.setup.ts`

`react-test-renderer` only exports `act` in development builds, and React 18+ needs `IS_REACT_ACT_ENVIRONMENT` set before `act` works.

```ts
declare global {
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}
process.env.NODE_ENV = 'development';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
export {};
```

### 4. `jest.config.js`

```js
/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^react-native$': '<rootDir>/src/__mocks__/react-native.ts',
    '^expo-constants$': '<rootDir>/src/__mocks__/expo-constants.ts',
  },
  transform: {
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        tsconfig: '<rootDir>/tsconfig.json',
        isolatedModules: true,
      },
    ],
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  transformIgnorePatterns: [
    'node_modules/(?!(zod|expo-constants)/)',
  ],
};
```

## Example screen test

```ts
process.env.NODE_ENV = 'development';

const TestRenderer = require('react-test-renderer');
const act = TestRenderer.act;

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MyScreen from '@/screens/MyScreen';
import * as offline from '@/db/offline';

jest.mock('expo-sqlite', () => ({
  openDatabaseSync: jest.fn(() => ({
    getFirstAsync: jest.fn(),
    getAllAsync: jest.fn(),
    runAsync: jest.fn(),
    execAsync: jest.fn(),
    withTransactionAsync: jest.fn((fn: () => Promise<unknown>) => fn()),
  })),
}));

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
const mockNavigation = { navigate: jest.fn() } as any;

function renderWithClient(element: React.ReactElement) {
  return TestRenderer.create(
    React.createElement(QueryClientProvider, { client: queryClient }, element)
  );
}

// Safe text extraction that doesn't stringify circular props.
function extractText(node: any): string {
  if (node == null) return '';
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (node.children) return extractText(node.children);
  return '';
}

function findPressableByChar(node: any, char: string): any {
  let match: any = null;
  function walk(n: any): void {
    if (!n) return;
    if (n.type === 'Pressable') {
      const text = extractText(n);
      if (text.includes(char)) match = n;
    }
    if (Array.isArray(n.children)) {
      for (const child of n.children) walk(child);
    }
  }
  walk(node);
  return match;
}

it('renders data and toggles favorite', async () => {
  jest.spyOn(offline, 'getItems').mockResolvedValue([{ id: '1', name: 'A' }]);

  let tree: any;
  await act(async () => {
    tree = renderWithClient(<MyScreen navigation={mockNavigation} route={{} as any} />);
  });

  expect(extractText(tree.toJSON())).toContain('A');
});
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `act is not a function` | `react-test-renderer` exports `act` only in development builds | `process.env.NODE_ENV = 'development'` in `jest.setup.ts` |
| `The current testing environment is not configured to support act(...)` | `IS_REACT_ACT_ENVIRONMENT` is false | Set `globalThis.IS_REACT_ACT_ENVIRONMENT = true` |
| `No QueryClient set` | Screen calls `useMutation` from TanStack Query | Wrap screen in `QueryClientProvider`, or mock the mutation hook at the module level |
| `Cannot use import statement outside a module` from `expo-constants` | `expo-modules-core` is ignored | Add `^expo-constants$` mock via `moduleNameMapper` |
| Tree `.toJSON()` is `null` or root is unmounted | Render happened outside `act`, or async state didn't flush | Wrap `TestRenderer.create` in `await act(async () => { ... })` |
| FlatList renders no item text | Mock `FlatList` didn't evaluate `renderItem` | Implement the mock so it maps `data` through `renderItem` and returns the resulting elements as children |
| Can't find a `Pressable` by type | Mock components are anonymous functions | Use named mock functions so `node.type === 'Pressable'`, or match on `props.onPress` plus expected text |
| `JSON.stringify(tree.toJSON())` throws on circular props | `RefreshControl`, `QueryClientProvider`, etc. embed element references | Use a recursive text-extraction helper instead of stringifying the whole tree |

## When to switch to jest-expo

Use this lightweight approach for smoke tests only. Switch to `jest-expo` when you need:
- Real native module behavior (Animated, Gesture Handler, Reanimated, SafeAreaContext)
- `@testing-library/react-native` matchers
- Navigation state testing
- Platform-specific rendering logic
