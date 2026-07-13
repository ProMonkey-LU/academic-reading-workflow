# Configuration and Output Contract

## Contents

- Configuration location
- Required fields
- Optional search fields
- Daily note contract

## Configuration location

Read the local profile from:

```text
$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml
```

The public repository provides `config/research-interests.example.yaml`. Keep the real profile in the vault and keep credentials in environment variables.

## Required fields

```yaml
language: zh
daily_note_dir: Daily_paper
papers_dir: 论文笔记
runtime:
  conda_env: paper
research_domains:
  example-domain:
    keywords:
      - example keyword
    priority: 5
```

Each domain may also define `arxiv_categories`, `cnki_journals`, and source-specific query phrases.

## Optional search fields

Use `search_strategy` to configure source order, date windows, per-query limits, field-of-study filters, and domain queries. Use `excluded_keywords` to filter unwanted paper types. Use `cnki_settings` only when CNKI is part of the run.

Read the Semantic Scholar key only from:

```text
SEMANTIC_SCHOLAR_API_KEY
```

## Daily note contract

Write one note per requested date. Include:

1. Search coverage and any failed source.
2. A short overview grouped by research domain.
3. Ranked paper entries with stable external identifiers.
4. A concise relevance explanation grounded in configured keywords.
5. Existing Obsidian note links when matched.
6. `Zotero: --` until the item exists in Zotero.

Use `[[path|display title]]` for note links and `![[filename.png|600]]` for images.
