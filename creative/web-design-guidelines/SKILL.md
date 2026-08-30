---
name: web-design-guidelines
description: Audit UI code against Vercel Web Interface Guidelines.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags:
      - UI
      - Review
      - Guidelines
      - Vercel
---

# Web Design Guidelines

Audit UI code against the latest Vercel Web Interface Guidelines.

## When to use

Use when asked to:

- "review my UI"
- "check accessibility" (design/UX only, not full WCAG)
- "audit design"
- "review UX"
- "check my site against best practices"

## Workflow

1. Fetch the latest guidelines from `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md` using `web_extract` or `terminal` curl.
2. Read the files the user wants reviewed using `read_file`.
3. Check every guideline against the provided code.
4. Output findings in terse `file:line` format.
5. If no files are specified, ask the user which files to review.

## Output format

- One finding per line: `path/to/file.tsx:42: <rule violated> — brief suggestion`
- Group by severity only if the guidelines define severity.
- End with a short summary of total issues and next steps.

## Example

```
components/Button.tsx:12: Avoid ambiguous button labels — use a verb like "Save".
app/page.tsx:30: Maintain visual hierarchy — reduce competing headings.
```

## Notes

- Always fetch the latest guidelines first; do not rely on cached rules.
- Keep findings actionable and specific to the code shown.
- Do not paste the full guideline text into the output.