# Analytical Note Contract

## Contents

- File placement
- Frontmatter
- Required sections
- Obsidian conventions
- Update behavior

## File placement

Write notes under the configured `papers_dir`, grouped by a domain from the user's profile. Prefer the filename pattern `{first-author} {year} - {short-topic}.md` and store related images in a sibling directory.

## Frontmatter

Include stable identifiers and quote string values:

```yaml
---
date: "YYYY-MM-DD"
paper_id: "arXiv:XXXX.XXXXX"
doi: "10.xxxx/example"
title: "Paper title"
authors: "Author list"
domain: "Configured domain"
tags:
  - 论文笔记
quality_score: "8.0/10"
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
status: "analyzed"
---
```

Omit unavailable identifiers instead of inventing values.

## Required sections

Use the configured language consistently. Cover:

1. Core information and source links.
2. Research problem and motivation.
3. Method, data, and mathematical formulation.
4. Experimental or empirical evidence.
5. Main results with exact reported values where important.
6. Strengths, limitations, and applicability.
7. Relationship to inspected local or external papers.
8. Research implications when a local research profile is relevant.
9. A transparent multidimensional score.
10. A user-owned notes section.

## Obsidian conventions

- Use `[[path|display title]]` for note links.
- Use `![[filename.png|800]]` for embedded images.
- Use `$...$` for inline equations and `$$...$$` for display equations.
- Use `--` for missing display values, never `---`.
- Keep tags free of spaces.

## Update behavior

Before replacing a generated section, preserve manual text, custom frontmatter, annotations, and the user notes section. When safe merging is not possible, write a proposed companion note and report the conflict.
