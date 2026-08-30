# GitHub Actions uv + TypeScript export-shape pitfall — 2026-06-15

## Workflow that failed

`.github/workflows/ci.yml` (initial version after UI refresh):

```yaml
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - uses: astral-sh/setup-uv@v5
        with:
          version: latest
      - name: Install Python dependencies
        run: uv pip install -e ".[dev]"
      - name: Run pytest
        run: uv run pytest -q

  mobile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 10
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'pnpm'
      - name: Install dependencies
        run: pnpm install --frozen-lockfile
      - name: Type check mobile app
        run: pnpm --filter expo-app run typecheck
      - name: Test mobile app
        run: pnpm --filter expo-app run test
```

## Errors in CI

### Python job
```
Process completed with exit code 2.
The process '/usr/bin/git' failed with exit code 128
```

Root cause: `uv pip install -e ".[dev]"` refused to install because no virtual environment existed.

### Mobile job
```
Property 'space' does not exist on type 'typeof import("/home/runner/work/elo-scenario-lab/elo-scenario-lab/mobile/apps/expo-app/src/design/tokens")'.
Property 'radius' does not exist on type 'typeof import(...)'.
Property 'colors' does not exist on type 'typeof import(...)'.
...
```

Root cause: `tokens.ts` exported a single nested `tokens` object:

```ts
export const tokens = { color: {...}, type: {...}, space: {...}, radius: {...} }
```

Screens imported `import * as Tokens` and referenced `Tokens.colors.*`, `Tokens.space.*`, `Tokens.radius.*`, etc. The names did not match.

## Fixes applied

### Python job

```yaml
      - name: Install Python dependencies
        run: |
          uv venv
          . .venv/bin/activate
          uv pip install -e ".[dev]"
      - name: Run pytest
        run: |
          . .venv/bin/activate
          pytest -q
```

### Mobile tokens.ts

Restructured to export top-level named exports matching the screen usage:

```ts
export const colors = {...};
export const type = {...};
export const space = {...};
export const radius = {...};

export const tokens = { color: {...}, type, space, radius } as const;
export default tokens;
```

This satisfies both the new `Tokens.colors.*` consumers and any legacy `tokens.color.*` consumers.

## Verification commands

```bash
# Local reproduction before fix
uv pip install -e ".[dev]"        # fails with no venv
pnpm --filter expo-app run typecheck  # fails with Token property errors

# Local reproduction after fix
uv venv && . .venv/bin/activate && uv pip install -e ".[dev]" && pytest -q
pnpm --filter expo-app run typecheck
```

## Commit

The combined fix was committed as:
```
fix(ci): export mobile token aliases and run uv in a venv
```

Both `main` and `develop` were updated to `bdf4eba`.
