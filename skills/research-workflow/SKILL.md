---
name: research-workflow
description: Route multi-stage personal academic workflows across literature discovery, paper acquisition, reading, Obsidian archiving, local note retrieval, writing, figures, and submission. Use when the user asks to "开始科研工作流", "继续论文工作流", "从检索到归档", or describes a research task spanning two or more stages and needs help choosing the right skills. Do not trigger for a single clearly scoped action such as merely reading one PDF, polishing one paragraph, or searching local notes.
---

# Research Workflow

Act as a router and coordinator. Select the smallest set of downstream skills that completes the request; do not duplicate their detailed procedures.

## Route the request

| User intent | Route |
|---|---|
| Daily personalized recommendations saved to Obsidian | `start-my-day` |
| Ad hoc external literature search or citation verification | `nature-academic-search` |
| Legal full-text acquisition | `nature-downloader` or an explicit `cnki-*` skill |
| Full-paper reading, translation, or bilingual Markdown | `nature-reader` |
| Detailed analytical note saved to the user's Obsidian vault | `paper-analyze` |
| Create a note from an existing Zotero item and local PDF | `zotero-paper-note` |
| Search only the user's existing paper notes | `paper-search` |
| Extract original figures from arXiv source or a PDF | `extract-paper-images` |
| Draft manuscript sections | `nature-writing` |
| Polish or translate existing academic prose | `nature-polishing` |
| Add or verify citations | `nature-citation` or `nature-ref-verifier` |
| Create manuscript figures or review statistics | `nature-figure` or `nature-statistics` |
| Pre-submission review or reviewer response | `nature-reviewer` or `nature-response` |
| Build a paper presentation | `nature-paper2ppt` |

## Coordinate multi-stage work

1. Confirm the desired final artifact and destination only when the request leaves them ambiguous.
2. Inspect existing Zotero items and Obsidian notes before downloading or creating duplicates.
3. Use external discovery before reading, and reading before analytical archiving.
4. Preserve source anchors, DOI/arXiv identifiers, and Zotero item keys between stages.
5. Keep generated artifacts out of skill source directories.
6. Report which stages completed, which artifacts were created, and any stage that needs user credentials or login.

## Resolve overlaps

- Use `nature-reader` for understanding or translating a paper; use `paper-analyze` only when the requested result is a structured Obsidian analysis note.
- Use `nature-academic-search` for external sources; use `paper-search` only for the local vault.
- Use `start-my-day` for the user's manually triggered, research-profile-aware daily recommendation flow. Do not substitute `nature-literature-pipeline` unless the user explicitly asks for unattended scheduled delivery.
- Use `zotero-paper-note` when Zotero is the source of truth. Use `paper-analyze` for an arXiv ID, standalone PDF, or non-Zotero source.
- Invoke source-specific skills such as CNKI only when the user names the source or the workflow explicitly requires Chinese literature.

## Preserve the personal research profile

Read research preferences from `$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml` when a personalized stage needs them. Never copy secrets or private profile data into the public skill repository.
