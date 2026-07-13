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
4. Search the paper directory by DOI, arXiv ID, and normalized title before creating a file.
5. If the source is an existing Zotero item, route to `zotero-paper-note` unless the user explicitly prefers a non-Zotero note.

## Acquire evidence

1. Resolve stable metadata: title, authors, affiliations, date, venue, DOI/arXiv ID, abstract, and source URLs.
2. Read the full paper whenever available. If only the abstract is available, label the note as abstract-only and do not fabricate methods or results.
3. Invoke `extract-paper-images` when figures are requested or materially help explain the method and results.
4. Search existing local notes for related work before adding wikilinks.
5. Read a local research-context file only if the user's vault configuration points to one and the paper matches that context.

## Analyze

Ground each section in the paper. Cover the research problem, motivation, method, evidence, principal results, limitations, relationship to prior work, and practical relevance. Preserve mathematical notation in Markdown LaTeX.

Use a consistent 0-10 rubric for novelty, technical quality, experimental adequacy, writing quality, and practical value. Explain scores with evidence instead of relying on the venue or author reputation.

## Write and update

1. Use `scripts/generate_note.py` to create a skeleton only when a note does not already exist.
2. Fill the skeleton with source-grounded content and insert figures near the paragraphs that discuss them.
3. Preserve the user's `## 我的笔记` or `## My Notes` section and any unrecognized frontmatter fields when updating an existing note.
4. Use `scripts/update_graph.py` only after the note is successfully written.
5. Return the note path, source identifier, analysis limitations, and whether the knowledge graph changed.

## Boundaries

- Do not convert a request to read or translate a paper into an Obsidian write operation.
- Do not claim a comparison with related work unless the compared sources were actually inspected.
- Do not use every extracted image indiscriminately; select figures that support the analytical narrative.
- Do not overwrite existing files silently.
