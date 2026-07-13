# Personal Academic Workflow

## Workflow map

```text
Discover -> Acquire -> Read -> Archive -> Retrieve -> Write / Review / Present
```

| Stage | Default skill | Artifact |
|---|---|---|
| Personalized daily discovery | `start-my-day` | Dated Obsidian recommendation note |
| Ad hoc external discovery | `nature-academic-search` | Verified literature set and citations |
| Full-text acquisition | `nature-downloader` or `cnki-*` | Legally obtained local paper |
| Full-paper reading or translation | `nature-reader` | Source-grounded Markdown reader |
| Analytical Obsidian archive | `paper-analyze` | Structured paper note and optional graph update |
| Zotero-based archive | `zotero-paper-note` | Zotero-linked analytical note |
| Local retrieval | `paper-search` | Ranked links to existing notes |
| Writing and publication | `nature-writing`, `nature-polishing`, and related Nature skills | Manuscript-ready artifacts |

Use `research-workflow` only when a request spans multiple stages or the user explicitly asks to start or continue the overall workflow.

## Trigger boundaries

| Request pattern | Use | Do not use |
|---|---|---|
| “开始科研工作流”“从检索到归档” | `research-workflow` | A single downstream skill acting as a router |
| “今日论文推荐”“开始今天的论文阅读” | `start-my-day` | `nature-literature-pipeline` |
| “读这篇 PDF”“全文翻译”“中英文对照” | `nature-reader` | `paper-analyze` |
| “分析并归档到 Obsidian” | `paper-analyze` | Generic paper reader |
| “从 Zotero 生成笔记” | `zotero-paper-note` | Standalone PDF route |
| “在我的论文笔记里找” | `paper-search` | External literature search |
| “联网查文献”“找最新论文” | `nature-academic-search` | Local note search |
| “从 arXiv 源码提取原图” | `extract-paper-images` | Automatic activation for every paper |
| Explicit CNKI request | Matching `cnki-*` skill | Generic multi-source search |
| “起草摘要/引言/讨论” | `nature-writing` | `nature-polishing` |
| “润色/翻译已有段落” | `nature-polishing` | `nature-writing` |

## Ownership and updates

- Edit personal skills under `skills/` and commit changes to this repository.
- Treat `vendor/nature-skills/` as read-only. Update it only with `scripts/skills.sh update-nature`.
- Keep `local-vendor/` untracked. It stores local snapshots whose upstream and redistribution terms are not managed by this repository.
- Use `config/active-skills.txt` as the single activation list. A skill may remain available in source without entering the Codex trigger catalog.

## Local data policy

Keep the real research profile in the Obsidian vault. Keep Zotero and Obsidian absolute paths in environment variables. Keep API keys in environment variables or an external secret manager. Do not place generated notes, search JSON, PDFs, or images inside a skill source directory.
