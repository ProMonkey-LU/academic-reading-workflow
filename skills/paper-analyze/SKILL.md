---
name: paper-analyze
description: Create or update a structured, figure-aware analytical paper note inside the user's Obsidian vault from an arXiv ID, local PDF, DOI, or supplied paper text. Use when the user explicitly asks to "生成 Obsidian 论文笔记", "深度分析并归档", "分析这篇论文并存入论文笔记", or requests a scored local knowledge-base note. Do not use for generic paper reading, translation, or bilingual full-text output; route those to nature-reader.
---

# Paper Analyze

Create an evidence-grounded analytical note in the user's configured Obsidian paper directory. Preserve any existing manual notes.

## Preflight

1. Resolve `$OBSIDIAN_VAULT_PATH`; ask for it when unset.
2. Read `$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml` when present to determine language, paper directory, domains, and conda environment.
3. Read `references/note-contract.md` before writing the final note.
4. Read `references/legacy-workflow-notes.md` when the task needs the detailed historical analysis template, scoring rubric, Obsidian formatting rules, graph relationship types, or troubleshooting workflow.
5. Search the paper directory by DOI, arXiv ID, and normalized title before creating a file.
6. If the source is an existing Zotero item, route to `zotero-paper-note` unless the user explicitly prefers a non-Zotero note.
7. For every newly analyzed paper with a resolved PDF, attempt Zotero import by following `references/zotero-import.md` before finalizing the note. Do not mark Zotero as imported unless a real Zotero parent item key or item link is verified.
8. Use `conda run -n <env> python` or an available `python`/`python3`; do not assume a Unix interpreter path. Use the platform temporary-directory API instead of `/tmp`.

## Acquire evidence

1. Resolve stable metadata: title, authors, affiliations, date, venue, DOI/arXiv ID, abstract, and source URLs.
2. Read the full paper whenever available. If only the abstract is available, label the note as abstract-only and do not fabricate methods or results.
3. Invoke `extract-paper-images` when figures are requested or materially help explain the method and results.
4. Search existing local notes for related work before adding wikilinks.
5. Read a local research-context file only if the user's vault configuration points to one and the paper matches that context.

## Zotero import

Use Zotero as the reference-manager destination for detailed analytical notes, not for daily recommendation cards.

1. Before importing, search Zotero by DOI, arXiv ID, normalized title, and first author/year. Prefer the installed OpenAI Zotero capability or Zotero's local API; use a read-only SQLite snapshot only for fields or local attachment paths unavailable through that route.
2. If a matching Zotero parent item already exists, reuse it and attach the downloaded PDF only when the item has no local PDF attachment.
3. If no matching item exists and an import-capable Zotero interface is available, create a parent item from DOI/arXiv/CrossRef metadata and attach the downloaded PDF.
4. After import, verify the parent item key and add `zotero_key` and `zotero_link` to the note frontmatter. Near the core information section, replace `Zotero: --` with `[在 Zotero 中打开](zotero://select/items/0_<item-key>)`.
5. If Zotero import cannot be completed because no connector, CLI, API credential, or GUI automation route is available, keep the PDF and citation metadata in the temporary working directory only when the user asked for a handoff package; otherwise clean temporary files. In the final response, explicitly say "Zotero 导入未完成" and why.
6. Never edit the live `zotero.sqlite` database directly. Query copies only, as described by `zotero-paper-note`, and use official connectors, APIs, or user-approved GUI automation for writes.

## Analyze

Ground each section in the paper. Cover the research problem, motivation, method, evidence, principal results, limitations, relationship to prior work, and practical relevance. Preserve mathematical notation in Markdown LaTeX.

Use a consistent 0-10 rubric for novelty, technical quality, experimental adequacy, writing quality, and practical value. Explain scores with evidence instead of relying on the venue or author reputation.

## Write and update

1. Use `scripts/generate_note.py` to create a skeleton only when a note does not already exist.
2. Fill the skeleton with source-grounded content and insert figures near the paragraphs that discuss them.
3. Include Zotero status in frontmatter and the core information section: use a verified Zotero link when import succeeded, otherwise `--`.
4. Preserve the user's `## 我的笔记` or `## My Notes` section and any unrecognized frontmatter fields when updating an existing note.
5. Use `scripts/update_graph.py` only after the note is successfully written.
6. Return the note path, source identifier, Zotero import status, analysis limitations, and whether the knowledge graph changed.

## Boundaries

- Do not convert a request to read or translate a paper into an Obsidian write operation.
- Do not claim a comparison with related work unless the compared sources were actually inspected.
- Do not use every extracted image indiscriminately; select figures that support the analytical narrative.
- Do not overwrite existing files silently.
