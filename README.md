# CC Paper Skills

Claude Code skills for academic paper reading workflow — daily paper recommendations, deep analysis, and image extraction.

## Skills

### start-my-day
Daily paper recommendation workflow. Searches Semantic Scholar + arXiv, filters by research interests, scores papers, and generates an Obsidian daily recommendation note with auto-linked keywords.

- Searches S2 (primary) + arXiv (supplementary) + CNKI (optional)
- Multi-dimensional scoring: relevance (40%) + recency (20%) + popularity (30%) + quality (10%)
- Top 3 papers get deep analysis + image extraction
- Generates Obsidian markdown notes with wikilinks and embedded images

### paper-analyze
Deep analysis skill for individual papers. Generates detailed Obsidian notes with full method descriptions, experimental results, and cross-paper comparisons.

- Downloads arXiv PDFs and extracts all figures
- Structured note template: background, methods, results, deep analysis, related papers
- Auto-generates knowledge graph connections

### extract-paper-images
Extracts figures from arXiv PDFs for embedding in Obsidian notes.

- Downloads arXiv source or PDF
- Extracts and renames figures (fig1.png, fig2.png, ...)
- Saves to Obsidian vault attachment folder

## Dependencies

- Python 3.x with PyYAML
- Conda environment (default: `paper`)
- Obsidian vault with configured `research_interests.yaml`
- Semantic Scholar API key (optional, for higher rate limits)

## Installation

Copy skill folders to your Claude Code skills directory:

```bash
cp -r start-my-day paper-analyze extract-paper-images ~/.cc-switch/skills/
```

Configure your research interests in your Obsidian vault:

```
$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml
```

## Usage

In Claude Code:

```
/start-my-day          # Today's paper recommendations
/start-my-day 2026-05-19  # Specific date
/paper-analyze 2605.00860  # Deep analyze a paper
```
