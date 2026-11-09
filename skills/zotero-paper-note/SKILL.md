---
name: zotero-paper-note
description: Create or update a structured Obsidian analytical note from an existing Zotero item and its locally stored PDF, preserving Zotero metadata, item links, and selected figures. Use for "Zotero 笔记", "从 Zotero 生成 Obsidian 笔记", "导入 Zotero 论文笔记", or requests that identify Zotero as the source. Do not use for standalone PDFs, generic paper reading, or importing a citation into Zotero.
---

# Zotero Paper Note

Use Zotero as the metadata and attachment source, then create a structured analytical note in the user's Obsidian vault.

## Preflight

1. Resolve `$OBSIDIAN_VAULT_PATH`. Prefer the installed OpenAI Zotero capability or Zotero's local API for item discovery, metadata, collections, tags, and indexed full text.
2. Resolve `$ZOTERO_DATA_DIR` only when a local PDF path or a field unavailable through the API is needed. Default it to `$HOME/Zotero` only when that directory exists.
3. If database fallback is necessary, locate `$ZOTERO_DATA_DIR/zotero.sqlite` and `storage/`, then read `references/zotero-sql.md` before querying.
4. Read `references/legacy-workflow-notes.md` when the task needs the older Zotero query flow, PDF extraction fallbacks, note template, or recommendation-note link update convention.
5. Read the user's local research configuration when the note should include project-specific implications.

## Workflow

1. Identify the Zotero item by title, DOI, citation key, or explicit item key.
2. Resolve the parent item metadata, creators, and eight-character Zotero item key through the Zotero capability or local API when available.
3. If the local attachment path cannot be resolved through that route, run `scripts/zotero_snapshot.py` and query only its temporary snapshot. Resolve the attachment key and PDF path from the snapshot.
4. Verify that the attachment is a real PDF.
5. Extract full text and selected figures from the local PDF. Prefer embedded figures; render pages only when necessary and disclose the fallback.
6. Follow `paper-analyze`'s analytical note contract, adding Zotero-specific metadata and the item link.
7. Preserve existing manual note content and update a matching note instead of creating a duplicate.
8. Optionally replace a `Zotero: --` placeholder in a daily recommendation note after the item link is known.

## Zotero-specific requirements

Add the item key to frontmatter and place this link near the title:

```markdown
[在 Zotero 中打开](zotero://select/items/0_<item-key>)
```

Use the parent item key for the link, not the Better BibTeX citation key or attachment key.

## Boundaries

- Do not modify the live Zotero database.
- Do not use SQLite when the Zotero capability or local API already supplies the required data.
- Do not assume the attachment key equals the parent item key.
- Do not expose local absolute paths in the public note unless the user asks.
- If the item has no local PDF, create a metadata-only note only with explicit user approval.
