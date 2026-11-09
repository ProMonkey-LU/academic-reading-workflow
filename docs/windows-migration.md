# Windows Migration

## Recommended layout

Keep one Git checkout as the source of truth and let Codex load directory junctions from `%USERPROFILE%\.codex\skills`. Do not copy skill folders independently after installation.

```text
C:\Users\<you>\Documents\academic-reading-workflow
C:\Users\<you>\.codex\skills
<Obsidian vault>\99_System\Config\research_interests.yaml
<Zotero data>\zotero.sqlite
```

The full Windows profile enables the personal Zotero/Obsidian workflow, maintained Obsidian Markdown support, and the Nature core. CNKI snapshots and Mac-only local tools are not enabled. If Nature Skills and `grill-me` already exist on the target machine, use the personal-only profile below so this repository does not replace or manage them.

## 1. Prepare software

Install Git for Windows, Python 3.9 or newer, Codex, Zotero, Obsidian, and ripgrep. If the personal scripts use the `paper` conda environment, install Miniconda or Anaconda as well.

In Codex, install or enable the official OpenAI Zotero plugin. It is the preferred route for Zotero discovery, metadata, indexed full text, and citation operations. The personal `zotero-paper-note` skill keeps a read-only SQLite fallback for local attachment paths.

## 2. Clone with upstream skills

```powershell
cd "$HOME\Documents"
git clone --recurse-submodules https://github.com/ProMonkey-LU/academic-reading-workflow.git
cd academic-reading-workflow
```

If the repository was cloned without submodules:

```powershell
git submodule update --init --recursive
```

## 3. Configure local paths and credentials

Set user-level environment variables in PowerShell. Replace the example paths first.

```powershell
[Environment]::SetEnvironmentVariable("OBSIDIAN_VAULT_PATH", "D:\Obsidian\Research", "User")
[Environment]::SetEnvironmentVariable("ZOTERO_DATA_DIR", "$HOME\Zotero", "User")
[Environment]::SetEnvironmentVariable("SEMANTIC_SCHOLAR_API_KEY", "replace-with-new-key", "User")
```

Restart Codex after changing user-level variables. Do not commit the real key or research profile.

Copy the local, private `research_interests.yaml` through your trusted file-sync method to:

```text
%OBSIDIAN_VAULT_PATH%\99_System\Config\research_interests.yaml
```

Review absolute paths inside that YAML. Prefer vault-relative paths; keep machine-specific paths in environment variables.

## 4. Create the Python environment

When using Conda:

```powershell
conda create -n paper python=3.11 pyyaml requests pymupdf
conda run -n paper python scripts\skill_doctor.py
```

Without Conda:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install pyyaml requests pymupdf
.\.venv\Scripts\python scripts\skill_doctor.py
```

The doctor is read-only. Resolve every `ERROR`; `WARN` entries describe optional fallbacks or reduced functionality.

## 5. Install the Windows profile

When Nature Skills and `grill-me` are already installed, use:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\skills.ps1 install -ActiveSkillsFile .\config\active-skills.windows-personal.txt
.\scripts\skills.ps1 check -ActiveSkillsFile .\config\active-skills.windows-personal.txt
```

For a new machine that also needs this repository to manage Nature Skills, use the full profile:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\skills.ps1 install
.\scripts\skills.ps1 check
```

The script creates directory junctions and refuses to replace unmanaged paths. The personal-only profile installs `research-workflow`, `start-my-day`, `paper-analyze`, `paper-search`, `extract-paper-images`, `zotero-paper-note`, and `obsidian-markdown`. Start a new Codex task after installation.

Keep the existing `grilling` installation from `mattpocock/skills`; it remains an independent third-party skill rather than a file copied into this repository.

## 6. Validate without touching the real vault

1. Copy the vault configuration and a few disposable notes into a temporary test vault.
2. Set `OBSIDIAN_VAULT_PATH` for the current PowerShell session to the test path.
3. Run `paper-search`, then generate one test note with `zotero-paper-note`.
4. Confirm the parent Zotero key, attachment path, wikilinks, Unicode filenames, and preservation of `## 我的笔记`.
5. Restore the real vault path only after the test passes.

## Updates

```powershell
git pull --ff-only
git submodule update --init --recursive
.\scripts\skills.ps1 update-nature
.\scripts\skills.ps1 update-obsidian
.\scripts\skills.ps1 check -ActiveSkillsFile .\config\active-skills.windows-personal.txt
```

Skip `update-nature` when Nature Skills are managed by their existing Windows installation. Run `update-obsidian` for this repository's Obsidian dependency. Commit updated submodule pointers in the personal repository only after review. Never edit files inside either vendor submodule.
