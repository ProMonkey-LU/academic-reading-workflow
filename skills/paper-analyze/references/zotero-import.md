# Zotero Import Policy for Paper Analyze

## Purpose

When `paper-analyze` creates a detailed analytical note from a DOI, arXiv ID, publisher PDF, or local PDF, it should also try to place the paper and its PDF into Zotero so that the Obsidian note and reference manager stay aligned.

This policy applies only to selected detailed notes. It does not apply to `start-my-day` recommendation entries unless the user explicitly asks to import those papers.

## Required inputs

Import can be attempted only when these are available:

- stable identifier: DOI, arXiv ID, PMID, or a publisher landing page;
- metadata: title, authors, publication year, venue or source;
- a downloaded PDF or verified local PDF path.

If the PDF cannot be downloaded but metadata are reliable, ask before creating a metadata-only Zotero item.

## Preferred import routes

Use the first available route:

1. A callable Zotero connector, app tool, MCP tool, or plugin that can create/update Zotero items and attach PDFs.
2. Zotero Web API, only when credentials are already available from the environment or a configured secure store. Never read or write API keys into skill files or vault notes.
3. User-approved GUI automation of Zotero desktop or the browser connector.
4. A handoff package containing `.ris` or `.bib` plus the PDF, only when no direct import route is available.

## Deduplication

Before creating an item, search Zotero by:

1. DOI or arXiv ID;
2. normalized title;
3. first author plus publication year.

If a parent item exists:

- reuse the existing parent item key;
- attach the PDF only when no PDF attachment exists;
- do not create a duplicate item.

## Verification

Import is considered successful only after one of these is verified:

- a Zotero parent item key is returned by the import interface;
- `zotero.sqlite` copied to a temporary location contains a matching parent item after import;
- Zotero desktop/browser visibly exposes a stable parent item key or item link.

Do not infer success merely because a PDF was downloaded, a RIS file was created, or a command exited successfully.

## Obsidian note updates

When import succeeds, add these frontmatter fields:

```yaml
zotero_key: "ABCDEFGH"
zotero_link: "zotero://select/items/0_ABCDEFGH"
```

In the core information section, use:

```markdown
- **Zotero**：[在 Zotero 中打开](zotero://select/items/0_ABCDEFGH)
```

When import is not completed, keep:

```markdown
- **Zotero**：--
```

and report the reason in the final response.

## Safety rules

- Never write directly to the live `zotero.sqlite` database.
- Never assume an attachment item key is the parent item key.
- Never claim that a paper was imported unless the parent item key or Zotero link is verified.
- Do not expose local absolute PDF paths in public-facing notes unless the user asks.
