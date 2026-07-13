---
name: paper-search
description: Search only the user's existing Obsidian paper notes by title, author, DOI/arXiv ID, domain, tag, method, or content. Use for "在我的论文笔记中查找", "搜索本地 Obsidian 文献", "我的笔记里有没有", or requests to retrieve and compare already archived papers. Do not use for internet literature search, discovering new papers, or citation lookup.
---

# Paper Search

Search the local paper-note directory efficiently and return links into the user's knowledge base.

## Workflow

1. Resolve `$OBSIDIAN_VAULT_PATH`; ask for it when unset.
2. Read `papers_dir` from `99_System/Config/research_interests.yaml`, defaulting to `论文笔记` only when the vault configuration exists but omits the field.
3. Parse required terms, optional terms, exclusions, author names, identifiers, domains, and tags from the request.
4. Use `rg` across Markdown files. Search frontmatter separately for identifiers, authors, domains, and tags; search headings and body text for concepts and methods.
5. Rank exact identifier and title matches first, then author, heading, tag, and body matches.
6. Read only the highest-ranked notes needed to summarize the result.

## Output

Group results by domain when useful. For each result include the display title, Obsidian wikilink, authors, date, domain, why it matched, and a short relevant excerpt or paraphrase. State the searched directory and query terms when no result is found.

## Rules

- Never search the web as a fallback. Suggest `nature-academic-search` if the user wants new literature.
- Preserve relative note paths in `[[path|display title]]` links.
- Do not calculate a precise relevance score unless the ranking inputs support it.
- Avoid reading every note when `rg` can narrow the candidate set.
