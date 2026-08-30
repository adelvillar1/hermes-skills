# Testing vanilla-JS helpers from pytest via a Node loader

When the dashboard uses a vanilla-JS helper (no build step, no JS test runner) and you want to test it from Python's pytest, the cleanest pattern is: pytest fixture writes a one-shot Node loader script, runs it via `subprocess.run(['node', loader])`, parses the JSON output, cleans up the loader file.

This works without adding `jsdom`, `pytest-js`, or any other JS-in-Python dependency — you only need `node` on PATH.

## The pattern

```python
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / "ui" / "js" / "components" / "team-display.js"

# Build the loader as a triple-quoted template. Use Python's repr() to
# inject the helper path so quoting is always correct.
LOADER_TEMPLATE = """\
const t = require({helper_path});
const out = {{
  redSox: t.getShortName({{id: 'BOS', name: 'Boston Red Sox', sport: 'mlb'}}),
  normRedSox: t.normalizeTeamName('BOSTON RED SOX'),
}};
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def helper():
    """Execute the JS helper under Node and return its exports as a dict."""
    if not HELPER.exists():
        pytest.skip(f"helper not found at {HELPER}")
    loader = REPO / "tests" / ".team-display-loader.cjs"
    loader.write_text(LOADER_TEMPLATE.format(helper_path=repr(str(HELPER))))
    try:
        r = subprocess.run(
            ["node", str(loader)],
            capture_output=True, text=True, timeout=10
        )
    finally:
        loader.unlink(missing_ok=True)
    if r.returncode != 0:
        pytest.fail(f"Node run failed: {r.stderr}")
    return json.loads(r.stdout)


def test_red_sox_uses_alias(helper):
    assert helper["redSox"] == "Red Sox"
```

## Two pitfalls that cost real time

### 1. Quote escaping inside Python f-strings

The first attempt will look like this and **break with a `SyntaxError: missing ) after argument list`** when Node parses it:

```python
# WRONG — backslash-escaped quotes inside an f-string + multi-line string
loader.write_text(
    f'const t = require({HELPER!r});\n'
    f'process.stdout.write(JSON.stringify({{\n'
    f"  redSox: t.getShortName({{id: 'BOS', name: 'Boston Red Sox'}}),\n"  # ← breaks
    f'}}));\n'
)
```

The `{{` and `}}` in an f-string mean "escaped brace" — but combined with shell-style escapes, the inner quotes get mangled when the loader is written to disk. Use the **triple-quoted `LOADER_TEMPLATE` + `.format(helper_path=repr(...))`** pattern above instead. The `.format()` step is a normal string substitution, not f-string evaluation, so the inner `{`/`}` and quotes pass through unchanged.

### 2. JS module vs CommonJS

If the helper uses `export { getShortName }` (ES module syntax), Node will treat it as a module and `require()` fails with `ERR_REQUIRE_ESM`. The helper must use either:
- CommonJS: `module.exports = { getShortName }` (works with plain `require()`)
- ES module: `export { getShortName }` (requires `"type": "module"` in package.json or `.mjs` extension, and `import` instead of `require`)

The `team-display.js` pattern uses BOTH:
```js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { getShortName, normalizeTeamName };
}
if (typeof window !== 'undefined') {
  window.TeamDisplay = { getShortName, normalizeTeamName };
}
```

This dual-export lets the same file be loaded as a `<script>` tag in the browser (sets `window.TeamDisplay`) AND `require()`'d from Node (sets `module.exports`). Recommended for any shared helper in a no-build-step JS codebase.

### 3. Pretest the loader directly before wrapping in pytest

Don't go straight from "wrote the loader" to "wrote the test". Run the loader script manually first:

```bash
node /tmp/test-loader.cjs
```

If it works, the test will work. If it fails, you'll see the actual Node error immediately instead of a cryptic "subprocess returned non-zero" from pytest. This is the same RED-step discipline as TDD — see the test-driven-development skill.

## Variation: testing many helpers in one run

If you have several helpers, build ONE loader that exercises all of them and returns one JSON blob. Faster, and ensures you only spawn one Node process:

```js
const t1 = require('./ui/js/components/team-display.js');
const t2 = require('./ui/js/components/date-format.js');
process.stdout.write(JSON.stringify({
  team: { short: t1.getShortName(...), norm: t1.normalizeTeamName(...) },
  date: { rel: t2.relativeTime(...) },
}));
```

## When NOT to use this

- You have a real JS test runner available (jest, vitest, mocha) — use that instead, this pattern is for the no-build-step case
- The helper is trivial enough to inline in the test (e.g., a 5-line regex) — just re-implement in Python
- You're testing browser-specific behavior (DOM, event handlers) — this pattern runs pure JS in Node, no DOM

## Environment check

Before relying on this pattern, confirm `node` is on PATH:

```bash
which node && node --version
```

If absent, the test should `pytest.skip(...)` rather than fail — a missing Node binary in a test environment is not a code bug.
