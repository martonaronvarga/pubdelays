---
title: Documentation
description: Zensical authoring conventions and source-grounding rules for this repository.
icon: octicons/pencil-16
---

# Documentation

This site uses Zensical with Python Markdown compatibility. Author pages under `docs/` and avoid keeping both `README.md` and `index.md` in the same directory.

## Source-grounding checklist

Before adding or rewriting a page, identify:

1. The reader question the page answers.
2. The code, config, test, script, CLI output, or existing docs that prove the content.
3. Claims that should be marked unknown instead of invented.
4. Links to adjacent reference or internals pages.

## Markdown conventions

- Use one `#` heading per page.
- Use relative links to Markdown files, such as `[Schemas](../reference/schemas.md)`.
- Use front matter with `title` and `description`; add `icon` on section pages.
- Indent admonition content by four spaces.
- Use tables only for structured reference data.
- Use Mermaid for diagrams; store reusable sources under `docs/assets/diagrams/`.

!!! note "Zensical Markdown"
    Python Markdown requires four-space indentation for nested block content, including admonitions inside lists or examples.

## Build docs

```bash
uv run zensical build
uv run zensical serve
```

Run `git diff --check` after documentation edits to catch trailing whitespace and broken patch hygiene.
