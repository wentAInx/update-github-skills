#!/usr/bin/env python3
"""Inventory, check, and update Codex skills sourced from Git repositories."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


IGNORED_DIRS = {".git", "__pycache__", ".mypy_cache", ".pytest_cache", "node_modules"}
IGNORED_FILES = {".DS_Store"}


def run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=check,
    )


def expand(path: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()


def default_roots() -> list[Path]:
    candidates = []
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home) / "skills")
    candidates.extend([Path.home() / ".codex" / "skills", Path.home() / ".agents" / "skills"])
    seen: set[Path] = set()
    roots: list[Path] = []
    for candidate in candidates:
        resolved = expand(candidate)
        if resolved.exists() and resolved not in seen:
            roots.append(resolved)
            seen.add(resolved)
    return roots


def parse_skill_name(skill_md: Path, fallback: str) -> str:
    try:
        lines = skill_md.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = skill_md.read_text(errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return fallback
    for line in lines[1:80]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return fallback


def discover_skills(roots: list[Path]) -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if child.name.startswith(".") or not child.is_dir():
                continue
            skill_md = child / "SKILL.md"
            if not skill_md.exists():
                continue
            path = child.resolve()
            if path in seen:
                continue
            seen.add(path)
            skills.append(
                {
                    "name": parse_skill_name(skill_md, child.name),
                    "path": str(path),
                    "root": str(root.resolve()),
                }
            )
    return skills


def load_manifest(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    skills = data.get("skills", {})
    normalized: list[dict[str, Any]] = []
    if isinstance(skills, dict):
        for name, spec in skills.items():
            if not isinstance(spec, dict):
                continue
            entry = dict(spec)
            entry.setdefault("name", name)
            normalized.append(entry)
    elif isinstance(skills, list):
        normalized = [dict(item) for item in skills if isinstance(item, dict)]
    data["skills"] = normalized
    return data


def manifest_match(skill: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any] | None:
    skill_name = skill["name"]
    skill_path = expand(skill["path"])
    for entry in manifest.get("skills", []):
        local_path = entry.get("local_path")
        if local_path and expand(local_path) == skill_path:
            return entry
        if entry.get("name") == skill_name:
            return entry
    return None


def direct_git_source(skill_path: Path) -> dict[str, Any] | None:
    git_marker = skill_path / ".git"
    if not git_marker.exists():
        return None
    origin = run_git(["config", "--get", "remote.origin.url"], cwd=skill_path, check=False)
    repo = origin.stdout.strip()
    if not repo:
        return None
    branch = run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=skill_path, check=False)
    ref = branch.stdout.strip() or "HEAD"
    local = run_git(["rev-parse", "HEAD"], cwd=skill_path, check=False)
    return {
        "source_type": "git",
        "repo": repo,
        "ref": ref,
        "subdir": ".",
        "local_commit": local.stdout.strip() if local.returncode == 0 else None,
    }


def attach_source(skill: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    item = dict(skill)
    entry = manifest_match(item, manifest)
    if entry:
        item.update(
            {
                "source_type": "manifest",
                "repo": entry.get("repo") or entry.get("url"),
                "ref": entry.get("ref") or entry.get("branch") or "HEAD",
                "subdir": entry.get("subdir") or entry.get("path") or ".",
            }
        )
    else:
        git_source = direct_git_source(expand(item["path"]))
        if git_source:
            item.update(git_source)
        else:
            item.update({"source_type": "unknown", "repo": None, "ref": None, "subdir": None})
    item.setdefault("status", "source_found" if item["source_type"] != "unknown" else "needs_source")
    return item


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(directory: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for root, dirnames, filenames in os.walk(directory):
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRS]
        root_path = Path(root)
        for filename in filenames:
            if filename in IGNORED_FILES or filename.endswith((".pyc", ".pyo")):
                continue
            file_path = root_path / filename
            rel = file_path.relative_to(directory).as_posix()
            files[rel] = hash_file(file_path)
    return files


def changed_files(local_dir: Path, remote_dir: Path) -> list[str]:
    local = snapshot(local_dir)
    remote = snapshot(remote_dir)
    changed = sorted(path for path in set(local) | set(remote) if local.get(path) != remote.get(path))
    return changed


def clone_repo(repo: str, ref: str | None, target: Path) -> tuple[Path, str | None]:
    clone_cmd = ["clone", "--quiet", "--depth", "1"]
    if ref and ref != "HEAD":
        clone_cmd.extend(["--branch", ref])
    clone_cmd.extend([repo, str(target)])
    first = run_git(clone_cmd, check=False)
    if first.returncode != 0:
        fallback = run_git(["clone", "--quiet", "--depth", "1", repo, str(target)], check=False)
        if fallback.returncode != 0:
            raise RuntimeError((first.stderr or fallback.stderr).strip())
        if ref and ref != "HEAD":
            checkout = run_git(["checkout", "--quiet", ref], cwd=target, check=False)
            if checkout.returncode != 0:
                fetch = run_git(["fetch", "--quiet", "--depth", "1", "origin", ref], cwd=target, check=False)
                if fetch.returncode != 0:
                    raise RuntimeError(fetch.stderr.strip() or checkout.stderr.strip())
                run_git(["checkout", "--quiet", "FETCH_HEAD"], cwd=target)
    commit = run_git(["rev-parse", "HEAD"], cwd=target, check=False)
    return target, commit.stdout.strip() if commit.returncode == 0 else None


def remote_subdir(item: dict[str, Any], tmpdir: Path) -> tuple[Path, str | None]:
    repo = item.get("repo")
    if not repo:
        raise RuntimeError("Missing repo in source metadata")
    target = tmpdir / item["name"]
    if target.exists():
        target = Path(tempfile.mkdtemp(prefix=f"{item['name']}-", dir=tmpdir))
    checkout, commit = clone_repo(repo, item.get("ref"), target)
    subdir = item.get("subdir") or "."
    source_dir = (checkout / subdir).resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise RuntimeError(f"Remote subdir not found: {subdir}")
    return source_dir, commit


def ensure_backup(skill_path: Path, backup_dir: Path, skill_name: str) -> Path:
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"{skill_name}-{timestamp}"
    counter = 1
    while target.exists():
        counter += 1
        target = backup_dir / f"{skill_name}-{timestamp}-{counter}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_path, target)
    return target


def check_manifest_item(item: dict[str, Any], tmpdir: Path) -> dict[str, Any]:
    result = dict(item)
    try:
        remote_dir, commit = remote_subdir(result, tmpdir)
        diff = changed_files(expand(result["path"]), remote_dir)
        result["remote_commit"] = commit
        result["changed_files"] = diff
        result["status"] = "update_available" if diff else "up_to_date"
    except Exception as exc:  # noqa: BLE001 - command-line report should not hide per-skill failures
        result["status"] = "error"
        result["error"] = str(exc)
        result["changed_files"] = []
    return result


def check_direct_git_item(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    try:
        repo = result.get("repo")
        ref = result.get("ref") or "HEAD"
        local = run_git(["rev-parse", "HEAD"], cwd=expand(result["path"]))
        remote = run_git(["ls-remote", repo, ref])
        remote_commit = remote.stdout.split()[0] if remote.stdout.strip() else None
        result["local_commit"] = local.stdout.strip()
        result["remote_commit"] = remote_commit
        result["changed_files"] = []
        result["status"] = "update_available" if remote_commit and remote_commit != result["local_commit"] else "up_to_date"
    except Exception as exc:  # noqa: BLE001
        result["status"] = "error"
        result["error"] = str(exc)
        result["changed_files"] = []
    return result


def check_item(item: dict[str, Any], tmpdir: Path) -> dict[str, Any]:
    if item["source_type"] == "unknown":
        result = dict(item)
        result["status"] = "needs_source"
        result["changed_files"] = []
        return result
    if item["source_type"] == "git":
        return check_direct_git_item(item)
    return check_manifest_item(item, tmpdir)


def update_manifest_item(item: dict[str, Any], tmpdir: Path, backup_dir: Path, yes: bool) -> dict[str, Any]:
    checked = check_manifest_item(item, tmpdir)
    if checked["status"] != "update_available":
        return checked
    if not yes:
        checked["status"] = "confirmation_required"
        return checked
    skill_path = expand(checked["path"])
    backup_path = ensure_backup(skill_path, backup_dir, checked["name"])
    remote_dir, _commit = remote_subdir(checked, tmpdir)
    shutil.rmtree(skill_path)
    shutil.copytree(remote_dir, skill_path)
    checked["backup_path"] = str(backup_path)
    checked["status"] = "updated"
    return checked


def update_direct_git_item(item: dict[str, Any], backup_dir: Path, yes: bool) -> dict[str, Any]:
    checked = check_direct_git_item(item)
    if checked["status"] != "update_available":
        return checked
    if not yes:
        checked["status"] = "confirmation_required"
        return checked
    skill_path = expand(checked["path"])
    status = run_git(["status", "--porcelain"], cwd=skill_path)
    if status.stdout.strip():
        checked["status"] = "blocked_dirty_worktree"
        checked["error"] = "Local Git skill has uncommitted changes"
        return checked
    backup_path = ensure_backup(skill_path, backup_dir, checked["name"])
    pull = run_git(["pull", "--ff-only"], cwd=skill_path, check=False)
    if pull.returncode != 0:
        checked["status"] = "error"
        checked["error"] = pull.stderr.strip() or pull.stdout.strip()
    else:
        checked["status"] = "updated"
        checked["backup_path"] = str(backup_path)
    return checked


def update_item(item: dict[str, Any], tmpdir: Path, backup_dir: Path, yes: bool) -> dict[str, Any]:
    if item["source_type"] == "unknown":
        result = dict(item)
        result["status"] = "needs_source"
        result["changed_files"] = []
        return result
    if item["source_type"] == "git":
        return update_direct_git_item(item, backup_dir, yes)
    return update_manifest_item(item, tmpdir, backup_dir, yes)


def summarize(skills: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {"total": len(skills)}
    for item in skills:
        status = item.get("status", "unknown")
        summary[status] = summary.get(status, 0) + 1
    return summary


def text_report(data: dict[str, Any]) -> str:
    lines = [f"Command: {data['command']}", f"Skills: {data['summary']['total']}"]
    for item in data["skills"]:
        line = f"- {item['name']}: {item.get('status')}"
        if item.get("source_type"):
            line += f" ({item['source_type']})"
        if item.get("repo"):
            line += f" {item['repo']}"
        if item.get("changed_files"):
            line += f" changed={len(item['changed_files'])}"
        if item.get("backup_path"):
            line += f" backup={item['backup_path']}"
        if item.get("error"):
            line += f" error={item['error']}"
        lines.append(line)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--root", action="append", default=[], help="Skill root to scan; repeatable")
        subparser.add_argument("--manifest", help="JSON manifest mapping copied skills to Git repositories")
        subparser.add_argument("--only", action="append", default=[], help="Limit to a skill name; repeatable")
        subparser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    add_common(subparsers.add_parser("inventory", help="List skills and detected sources"))
    add_common(subparsers.add_parser("check", help="Check source repositories for updates"))
    update = subparsers.add_parser("update", help="Update skills after confirmation")
    add_common(update)
    update.add_argument("--yes", action="store_true", help="Actually update; without this, update reports confirmation_required")
    update.add_argument("--backup-dir", help="Directory for pre-update backups")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    roots = [expand(path) for path in args.root] if args.root else default_roots()
    manifest_path = expand(args.manifest) if args.manifest else None
    manifest = load_manifest(manifest_path) if manifest_path else {}
    if not roots:
        roots = [Path.cwd()]
    skills = [attach_source(skill, manifest) for skill in discover_skills(roots)]
    if args.only:
        wanted = set(args.only)
        skills = [skill for skill in skills if skill["name"] in wanted]

    with tempfile.TemporaryDirectory(prefix="skill-updater-") as tmp:
        tmpdir = Path(tmp)
        if args.command == "check":
            skills = [check_item(skill, tmpdir) for skill in skills]
        elif args.command == "update":
            default_backup = roots[0] / ".skill-backups"
            backup_dir = expand(args.backup_dir) if args.backup_dir else default_backup
            skills = [update_item(skill, tmpdir, backup_dir, args.yes) for skill in skills]

    data = {
        "command": args.command,
        "roots": [str(root) for root in roots],
        "manifest": str(manifest_path) if manifest_path else None,
        "skills": skills,
        "summary": summarize(skills),
    }
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(text_report(data))
    return 1 if data["summary"].get("error", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
