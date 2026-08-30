# Patch Tool TypeScript Template Literal Corruption

## Symptom

When using the `patch` tool to replace code containing TypeScript template literals (backtick strings with `${}` interpolation or `\n` sequences), the replacement text gets literal `\n` characters inserted instead of actual newlines. The file becomes corrupted with lines like:

```typescript
const row = await ctx.prisma.$queryRaw<[\\n      {\\n        active_lines: bigint;\\n...
```

This produces TypeScript errors: `Invalid character`, `',' expected`, etc.

## Root Cause

The `patch` tool's string matching treats `\n` in the `old_string` and `new_string` parameters as literal two-character sequences rather than newline escape sequences. When writing the replacement, it inserts literal `\n` characters into the file.

## Workaround

Use `terminal` with a Python script for replacements involving:
- TypeScript template literals (backtick strings)
- Multi-line SQL queries in Prisma `$queryRaw` calls
- Any code containing `\n` escape sequences

Pattern:

```python
python3 << 'PYEOF'
with open('path/to/file.ts', 'r') as f:
    content = f.read()

old = """    const row = await ctx.prisma.$queryRaw<[
      {
        active_lines: bigint;
      }
    ]>`SELECT * FROM dashboard_stats`;"""

new = """    const row = await ctx.prisma.$queryRaw<[
      {
        active_lines: bigint;
      }
    ]>`
      SELECT
        (SELECT COUNT(*) FROM table WHERE condition) AS active_lines
    `;"""

if old in content:
    content = content.replace(old, new)
    with open('path/to/file.ts', 'w') as f:
        f.write(content)
    print("OK: replaced")
else:
    print("ERROR: old string not found")
PYEOF
```

## When to Use Python Instead of Patch

| Scenario | Tool |
|----------|------|
| Simple string replacement, no template literals | `patch` tool |
| Code with backtick template literals | `terminal` + Python |
| Multi-line SQL in `$queryRaw` | `terminal` + Python |
| YAML, JSON, Markdown (no `\n` in content) | `patch` tool |
| Adding new sections to Markdown files | `patch` tool (safe) |

## Recovery

If the file was corrupted:
```bash
git checkout -- path/to/file.ts
```

Then redo with the Python approach.
