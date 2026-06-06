---
name: update-github-skills
description: Use when Codex needs to inventory, audit, check, dry-run, or update locally installed Codex skills that came from GitHub repositories, cloned folders, copied repo subdirectories, or curl/downloaded GitHub archives.
---

# Update GitHub Skills

## Overview

Use the bundled updater script to inspect local skill folders, identify Git-backed sources, check for upstream changes, and update only after a dry-run and explicit confirmation. Treat plugin-market, system, and unknown-source skills as read-only unless the user provides a source manifest.

## Workflow

1. Inventory the user's skill roots before changing anything.
2. Run `check` and report which skills are up to date, need a source, have updates, or produced errors.
3. For `needs_source` skills, ask the user for a GitHub repo/ref/subdir or help create a manifest entry.
4. Run `update --yes` only after the user confirms the specific skills to update.
5. After updating, validate updated skills with `quick_validate.py` when available and report backup paths.

## Updater Script

Run the script from this skill:

```bash
python3 /path/to/update-github-skills/scripts/github_skill_updater.py inventory --json
python3 /path/to/update-github-skills/scripts/github_skill_updater.py check --manifest ~/.codex/skill-sources.json --json
python3 /path/to/update-github-skills/scripts/github_skill_updater.py update --manifest ~/.codex/skill-sources.json --only skill-name --yes --json
```

Supported commands:

- `inventory`: list local skills and detected sources.
- `check`: clone/fetch upstream sources into a temporary directory and report changed files without modifying local skills.
- `update`: update eligible skills, creating a full backup first. Without `--yes`, it reports `confirmation_required` and writes nothing.

Important options:

- `--root PATH`: scan a skill root; repeat for multiple roots. Defaults to existing `${CODEX_HOME}/skills`, `~/.codex/skills`, and `~/.agents/skills`.
- `--manifest PATH`: use a JSON source map for copied/curl-installed skills.
- `--only NAME`: limit check/update to one skill; repeat for several skills.
- `--backup-dir PATH`: choose where update backups go. Default is `.skill-backups` inside the first scanned root.
- `--json`: prefer this for Codex-readable summaries.

## Source Detection

The script can safely handle:

- Direct Git skills: a skill folder whose `.git` marker is inside the folder. Updates use `git pull --ff-only` and stop if the worktree is dirty.
- Manifest skills: a local skill copied from a repo subdirectory, zip download, or curl command. Updates clone the configured repo/ref, compare the configured subdir, back up the local folder, then replace it.
- Unknown skills: any skill with no direct Git metadata and no manifest entry. Report these as `needs_source`; do not guess or update them.

Avoid scanning plugin cache roots such as `~/.codex/plugins/cache` unless the user explicitly asks. Marketplace/plugin skills are normally managed by their plugin installer, not by this skill.

## Manifest Format

Use a manifest for copied or curl-installed GitHub skills:

```json
{
  "skills": {
    "skill-name": {
      "repo": "https://github.com/owner/repo.git",
      "ref": "main",
      "subdir": "skills/skill-name"
    }
  }
}
```

Optional fields:

- `local_path`: match by exact local folder path instead of skill name.
- `branch`: alias for `ref`.
- `path`: alias for `subdir`.
- `url`: alias for `repo`.

If the user does not already have a manifest, create one outside the skill folder, usually `~/.codex/skill-sources.json`. If writing outside the workspace requires approval, ask for it or save a draft in the current workspace for the user to review.

## Safety Rules

- Always run `check` before `update`.
- Never update `needs_source`, plugin-market, system, or bundled skills without a user-provided source.
- Never pass `--yes` until the user confirms the exact skills to update.
- Preserve backup paths in the final answer.
- If a network command fails due to sandboxing, request escalation for the same command rather than working around approvals.
- If a direct Git skill has uncommitted changes, stop and report `blocked_dirty_worktree`.

## Validation

After updates, run the system skill validator on updated folders when available:

```bash
python3 /Users/wentainx/.codex/skills/.system/skill-creator/scripts/quick_validate.py /path/to/updated-skill
```

If the updated skill includes its own tests or validation script, run those too when practical.
