# Academic Reading Workflow for Codex

Personal Codex skills for literature discovery, paper analysis, Zotero-to-Obsidian archiving, local note retrieval, and academic writing coordination.

## Architecture

- `skills/`: personal skills maintained in this repository.
- `vendor/nature-skills/`: upstream Nature Skills Git submodule; do not edit it locally.
- `local-vendor/`: untracked local snapshots of source-specific third-party skills such as CNKI.
- `catalog/skills.yaml`: inventory, ownership, trigger boundaries, and activation status.
- `config/active-skills.txt`: skills linked into Codex by default.
- `scripts/skills.sh`: installation, verification, update, and activation commands.

Read [docs/workflows.md](docs/workflows.md) for the workflow and trigger map.

## Initial setup

Clone with submodules:

```bash
git clone --recurse-submodules https://github.com/ProMonkey-LU/academic-reading-workflow.git
cd academic-reading-workflow
```

If local CNKI snapshots are available from an older CC Switch installation, place them under `local-vendor/` using their existing directory names. This directory is intentionally excluded from GitHub.

Install the active set into Codex:

```bash
./scripts/skills.sh install
./scripts/skills.sh check
```

Start a new Codex task after installation so the refreshed skill catalog is loaded.

## Management

```bash
./scripts/skills.sh list
./scripts/skills.sh install
./scripts/skills.sh check
./scripts/skills.sh update-nature
./scripts/skills.sh enable nature-paper-to-patent
./scripts/skills.sh disable nature-paper-to-patent
```

`update-nature` fast-forwards the Nature Skills submodule and leaves its new commit visible in the parent repository for review and commit.

## Local configuration

Copy `config/research-interests.example.yaml` into the Obsidian vault location expected by the personal workflow:

```text
$OBSIDIAN_VAULT_PATH/99_System/Config/research_interests.yaml
```

Keep real research preferences and credentials local. Set the optional Semantic Scholar credential through `SEMANTIC_SCHOLAR_API_KEY`; never write it into YAML or commit it.
