---
name: extract-paper-images
description: Extract original publication figures from an arXiv source package or a local paper PDF and create an indexed image directory for Obsidian or downstream analysis. Use only when the user explicitly asks to "从 arXiv 源码提图", "提取论文原图", "导出论文图片", or needs the paper's figures as files. Do not trigger merely because a paper is being read or summarized.
---

# Extract Paper Images

Use `scripts/extract_images.py` to extract useful scientific figures while filtering logos, icons, and small fragments.

Read `references/legacy-workflow-notes.md` when the task needs the older extraction priority rationale, TikZ/PDF fallback handling, output index examples, or troubleshooting notes.

## Inputs

Accept an arXiv ID, an `arXiv:` identifier, or a local PDF path. Require an explicit output directory. When the images belong to an Obsidian note, resolve the vault from `$OBSIDIAN_VAULT_PATH` and place them beside that note.

## Extraction order

1. For an arXiv ID, download the source package and inspect common figure directories such as `figures/`, `fig/`, `images/`, `img/`, and `pics/`.
2. Convert standalone figure PDFs from the source package to PNG previews while retaining the source file when useful.
3. Fall back to extracting sufficiently large embedded PDF images.
4. For inline TikZ or vector figures that are not embedded objects, crop the relevant figure region from the rendered paper page only when it can be located reliably.
5. Record the provenance of every output as `arxiv-source`, `pdf-figure`, or `pdf-extraction`.

## Run the script

```bash
python3 scripts/extract_images.py \
  "<arxiv-id-or-pdf>" \
  "<output-directory>" \
  "<output-directory>/index.md"
```

Use the configured conda environment when `python3` lacks PyMuPDF or requests.

## Output contract

Return the output directory, index path, total figure count, provenance counts, and the most relevant figure filenames. For Obsidian, provide embeds as `![[filename.png|800]]`.

## Safety and quality

- Reject unsafe paths and links inside downloaded archives.
- Never overwrite unrelated files in a nonempty output directory.
- Preserve original filenames when possible and resolve collisions deterministically.
- Filter small decorative objects and disclose when only page-rendered fallbacks were available.
- If the arXiv source download fails, continue with the PDF when available.
