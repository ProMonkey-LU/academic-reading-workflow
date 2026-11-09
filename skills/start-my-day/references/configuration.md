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
daily_note_dir: 00_收件箱/每日论文推荐
papers_dir: 30_文献
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

Use `search_strategy` to configure source order, date windows, per-query limits, field-of-study filters, and domain queries. OpenAlex reuses `s2_queries` by default; define `openalex_queries` only when it needs different terms. Set `openalex_enabled: false` or `semantic_scholar_enabled: false` to disable a provider. Use `excluded_keywords` to filter unwanted paper types. Use `cnki_settings` only when CNKI is part of the run.

The workflow supports keyless OpenAlex and Semantic Scholar requests. Optional credentials are read only from:

```text
OPENALEX_API_KEY
SEMANTIC_SCHOLAR_API_KEY
```

For a manually triggered daily recommendation, OpenAlex keyless basic search is normally sufficient. Semantic Scholar exposes public keyless endpoints, but its shared anonymous pool may return `429`; the workflow then continues with OpenAlex and arXiv. Configure free keys when running frequently, querying many domains, or needing Semantic Scholar reliably. Never put these values in the YAML profile.

## Daily note contract

Write one note per requested date. Include:

1. Search coverage and any failed source.
2. A short overview grouped by research domain.
3. Ranked paper entries with stable external identifiers.
4. A concise relevance explanation grounded in configured keywords.
5. Existing Obsidian note links when matched.
6. `Zotero: --` until the item exists in Zotero.

Use `[[path|display title]]` for note links and `![[filename.png|600]]` for images.
