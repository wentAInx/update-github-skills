# update-github-skills

`update-github-skills` is an Agent Skill for Codex, Claude Code, and similar agent runtimes. It inventories, checks, and safely updates locally installed skills that came from GitHub repositories, copied repo subdirectories, zip downloads, or one-line installers.

中文文档: [README.md](README.md)

## Overview

### What it does

- Inventories local skill directories.
- Detects skills installed as direct Git repositories.
- Uses a `skill-sources.json` manifest for copied, zip, or curl-installed skills.
- Performs dry-run update checks before writing anything.
- Backs up local skill folders before confirmed updates.
- Supports Codex, Claude Code, and generic `.agents` skill directories.

### When to use it

- You have many third-party GitHub skills and want to check upstream updates.
- Some skills were installed with `cp -R` and no longer have `.git` metadata.
- You want to review changed files before updating local skills.
- You want a backup-first update path for beginner-friendly recovery.

### Skill, MCP, and plugin architecture

This repository is a regular Agent Skill, not an MCP server. It will not appear in MCP panels and should not be verified with `/mcp list`. The repository also includes `.codex-plugin/plugin.json` so Codex plugin marketplaces can recognize and install it as a skill package.

Recommended GitHub topics:

- `codex-skill`
- `claude-code-skill`
- `agent-skill`
- `skills-updater`
- `github-skills`

Only add `mcp-server` if a real MCP server is added later.

## Requirements

### All platforms

- Python 3.9+ for the updater script.
- Git for checking and updating Git/GitHub-backed skills.
- GitHub network access for one-line installation and upstream checks.

### macOS / Linux

- `curl`
- `tar`
- `bash` or a POSIX-compatible shell

If macOS reports a permissions issue on first install, grant your terminal access to your user directory or use local project installation.

### Windows

- Windows PowerShell 5+ or PowerShell 7+
- Git for Windows
- Python 3 available as `python` or `py`

If PowerShell blocks scripts, use a process-scoped bypass:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Three installation methods

### Method 1: One-line curl / PowerShell install

#### macOS / Linux: install globally for Codex

```bash
curl -fsSL https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.sh | bash
```

Install for Claude Code:

```bash
curl -fsSL https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.sh | bash -s -- --agent claude
```

Install only in the current project:

```bash
curl -fsSL https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.sh | bash -s -- --scope local
```

Use a fork or another branch:

```bash
curl -fsSL https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.sh | bash -s -- --repo wentAInx/update-github-skills --ref main
```

#### Windows PowerShell: install globally for Codex

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -UseBasicParsing https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.ps1 | iex"
```

Install for Claude Code:

```powershell
iwr -UseBasicParsing https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.ps1 -OutFile install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Agent claude
```

Install only in the current project:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Scope local
```

### Method 2: Git clone + manual copy

#### macOS / Linux

```bash
git clone https://github.com/wentAInx/update-github-skills.git
cd update-github-skills
bash install.sh --agent codex
```

Manual copy to Codex:

```bash
mkdir -p ~/.codex/skills
cp -R skills/update-github-skills ~/.codex/skills/update-github-skills
```

Manual copy to Claude Code:

```bash
mkdir -p ~/.claude/skills
cp -R skills/update-github-skills ~/.claude/skills/update-github-skills
```

Project-local install:

```bash
mkdir -p ./.codex/skills
cp -R skills/update-github-skills ./.codex/skills/update-github-skills
```

#### Windows PowerShell

```powershell
git clone https://github.com/wentAInx/update-github-skills.git
cd update-github-skills
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Agent codex
```

Manual copy to Codex:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\update-github-skills "$env:USERPROFILE\.codex\skills\update-github-skills"
```

Windows cmd:

```cmd
mkdir "%USERPROFILE%\.codex\skills"
xcopy /E /I /Y skills\update-github-skills "%USERPROFILE%\.codex\skills\update-github-skills"
```

### Method 3: Codex plugin marketplace install

Add the personal marketplace:

```text
/plugin marketplace add wentAInx/update-github-skills
```

Install the latest version:

```text
/plugin install update-github-skills@latest
```

Install a fixed version:

```text
/plugin install update-github-skills@0.1.0
```

This is a skill package, not an MCP plugin. Verify it in the skills/plugin list, not with `/mcp list`.

## Global vs local installation

| Mode | Directory | Best for |
| --- | --- | --- |
| Global | `~/.codex/skills/`, `~/.claude/skills/`, `%USERPROFILE%\.codex\skills\` | Use in every project |
| Local | `./.codex/skills/` or `./.claude/skills/` | Use only in the current repository |

## Quick start

After installation, try one of these prompts in Codex or Claude Code:

```text
$update-github-skills inventory my local skills and identify their sources
```

```text
$update-github-skills check ~/.codex/skills for GitHub skill updates, but do not update yet
```

```text
$update-github-skills dry-run copied skills using ~/.codex/skill-sources.json
```

You can also run the script directly:

```bash
python3 ~/.codex/skills/update-github-skills/scripts/github_skill_updater.py inventory --json
python3 ~/.codex/skills/update-github-skills/scripts/github_skill_updater.py check --manifest ~/.codex/skill-sources.json --json
```

## Source manifest example

Copied, zip-downloaded, or curl-installed skills usually do not contain `.git`. Create `~/.codex/skill-sources.json`:

```json
{
  "skills": {
    "some-skill": {
      "repo": "https://github.com/owner/repo.git",
      "ref": "main",
      "subdir": "skills/some-skill"
    }
  }
}
```

Then run:

```bash
python3 ~/.codex/skills/update-github-skills/scripts/github_skill_updater.py check --manifest ~/.codex/skill-sources.json --json
```

## FAQ

### 1. `Permission denied`

On macOS/Linux, ensure the script is executable:

```bash
chmod +x install.sh
```

Or install locally inside the current project:

```bash
bash install.sh --scope local
```

### 2. PowerShell blocks script execution

Use a temporary process-scoped bypass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

### 3. Python or Git cannot be found

Check the commands:

```bash
python3 --version
git --version
```

On Windows:

```powershell
py --version
git --version
```

### 4. Network download failed

Check GitHub access or install from a local clone:

```bash
git clone https://github.com/wentAInx/update-github-skills.git
cd update-github-skills
bash install.sh
```

### 5. A skill is reported as `needs_source`

The skill has no `.git` metadata and no manifest entry. Add `repo/ref/subdir` to `~/.codex/skill-sources.json`.

### 6. It does not appear in `/mcp list`

That is expected. This project is not an MCP server. Look for it in the agent's skills or plugin list.

### 7. Update is blocked by `blocked_dirty_worktree`

A directly cloned Git skill has local uncommitted changes. Back up or commit those changes before updating.

## Updating

### One-line installer users

Run the one-line command again. Existing installations are moved to a timestamped `.backup` path.

### Git clone users

```bash
cd update-github-skills
git pull --ff-only
bash install.sh --agent codex
```

Windows:

```powershell
git pull --ff-only
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Agent codex
```

### Marketplace users

```text
/plugin install update-github-skills@latest
```

## License and author

- License: MIT. See [LICENSE](LICENSE).
- Author: [wentAInx](https://github.com/wentAInx).
- Recommended repository settings: enable Issues for bug reports and Discussions for installation recipes, manifest examples, and new agent compatibility requests.

