---
name: start-my-day
description: Generate a manually triggered daily paper recommendation note tailored to the user's research interests and save it in Obsidian. Use for "今日论文推荐", "开始今天的论文阅读", "start my day", "每日文献", or requests for a dated personalized reading list. Do not use for one-off literature searches, generic paper reading, or unattended scheduled literature delivery.
---

# Start My Day

Generate one dated Obsidian recommendation note from the user's configured research profile. Use Semantic Scholar as the primary source and arXiv as a supplement. Use CNKI only when its browser integration is available and Chinese literature is requested by the profile.

## Preflight

1. Resolve the vault from `$OBSIDIAN_VAULT_PATH`. If unset, ask for the vault path instead of guessing.
2. Read `$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml`.
3. Read `references/configuration.md` for the supported fields and output contract.
4. Read `references/legacy-workflow-notes.md` when generating the full daily note, debugging ranking/linking, or matching the older note layout and scoring style.
5. Resolve Python from the configured conda environment, falling back to `python3` only when its dependencies are available.
6. Read `SEMANTIC_SCHOLAR_API_KEY` from the environment when present. Never read or write API keys in YAML.

## Workflow

1. Run `scripts/scan_existing_notes.py` against the configured paper-notes directory to build a local deduplication and wikilink index.
2. Run `scripts/search_arxiv.py --config <config> --output <temporary-json>` for the requested date. Keep generated JSON in a temporary directory, not inside this skill.
3. Merge and rank results using the script's configured relevance, recency, popularity, and quality scores.
4. Remove papers already represented in the local vault unless the user explicitly wants updates on known work.
5. Create one dated Markdown note in the configured daily-note directory.
6. Use Obsidian wikilinks for existing notes and `![[filename|width]]` for local images. Use `--` for missing values; never use `---` as a placeholder.
7. Run `scripts/link_keywords.py` only when the local index is available and the user wants automatic concept links.

## Output requirements

Include the search date, profile domains, source coverage, ranked papers, title, authors, affiliation when supported, publication date, DOI/arXiv link, concise relevance rationale, score components, and existing-note link when found. Leave the Zotero field as `--` until an item is actually imported.

Do not automatically create full analytical notes for every recommendation. Route a selected paper to `paper-analyze` or `zotero-paper-note` only when the user requests the next stage.

## Failure handling

- Continue with the remaining source when one provider fails, and disclose the missing source.
- On rate limits, use the script's retry behavior and return partial results instead of inventing papers.
- If the research configuration is missing or invalid, stop before searching and identify the exact field that needs correction.
- Never overwrite an existing daily note without preserving user-authored content.
