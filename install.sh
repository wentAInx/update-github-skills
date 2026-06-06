#!/usr/bin/env sh
set -eu

SKILL_NAME="update-github-skills"
REPO_SLUG="${REPO_SLUG:-wentAInx/update-github-skills}"
REF="${REF:-main}"
AGENT="codex"
SCOPE="global"
INSTALL_DIR=""
SOURCE_DIR=""
ARCHIVE_URL="${ARCHIVE_URL:-}"
TMP_DIR=""

usage() {
  cat <<'EOF'
Install update-github-skills.

Options:
  --agent codex|claude|agents   Target agent skill directory. Default: codex
  --scope global|local          Global user install or current-project install. Default: global
  --install-dir PATH            Override the parent skills directory
  --source-dir PATH             Install from an existing local repository or skill folder
  --repo OWNER/REPO             GitHub repository slug used by curl installs
  --ref REF                     GitHub branch/tag used by curl installs. Default: main
  --help                        Show this help
EOF
}

fail() {
  printf '%s\n' "Error: $*" >&2
  exit 1
}

cleanup() {
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT INT TERM

while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent)
      [ "$#" -ge 2 ] || fail "--agent requires a value"
      AGENT="$2"
      shift 2
      ;;
    --scope)
      [ "$#" -ge 2 ] || fail "--scope requires a value"
      SCOPE="$2"
      shift 2
      ;;
    --install-dir)
      [ "$#" -ge 2 ] || fail "--install-dir requires a value"
      INSTALL_DIR="$2"
      shift 2
      ;;
    --source-dir)
      [ "$#" -ge 2 ] || fail "--source-dir requires a value"
      SOURCE_DIR="$2"
      shift 2
      ;;
    --repo)
      [ "$#" -ge 2 ] || fail "--repo requires a value"
      REPO_SLUG="$2"
      shift 2
      ;;
    --ref)
      [ "$#" -ge 2 ] || fail "--ref requires a value"
      REF="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "unknown option: $1"
      ;;
  esac
done

case "$AGENT" in
  codex|claude|agents) ;;
  *) fail "--agent must be codex, claude, or agents" ;;
esac

case "$SCOPE" in
  global|local) ;;
  *) fail "--scope must be global or local" ;;
esac

default_install_dir() {
  if [ "$SCOPE" = "local" ]; then
    case "$AGENT" in
      codex) printf '%s\n' "$PWD/.codex/skills" ;;
      claude) printf '%s\n' "$PWD/.claude/skills" ;;
      agents) printf '%s\n' "$PWD/.agents/skills" ;;
    esac
    return
  fi

  case "$AGENT" in
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}/skills" ;;
    claude) printf '%s\n' "$HOME/.claude/skills" ;;
    agents) printf '%s\n' "$HOME/.agents/skills" ;;
  esac
}

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -z "$INSTALL_DIR" ]; then
  INSTALL_DIR=$(default_install_dir)
fi

download_source() {
  command -v curl >/dev/null 2>&1 || fail "curl is required for one-line installs"
  command -v tar >/dev/null 2>&1 || fail "tar is required for one-line installs"
  TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/update-github-skills.XXXXXX")
  archive="$TMP_DIR/source.tar.gz"
  if [ -z "$ARCHIVE_URL" ]; then
    ARCHIVE_URL="https://github.com/$REPO_SLUG/archive/refs/heads/$REF.tar.gz"
  fi
  printf '%s\n' "Downloading $ARCHIVE_URL"
  curl -fsSL "$ARCHIVE_URL" -o "$archive"
  tar -xzf "$archive" -C "$TMP_DIR"
  skill_md=$(find "$TMP_DIR" -name SKILL.md -print | head -n 1)
  [ -n "$skill_md" ] || fail "downloaded archive does not contain SKILL.md"
  dirname "$skill_md"
}

if [ -n "$SOURCE_DIR" ]; then
  SOURCE_DIR=$(cd "$SOURCE_DIR" && pwd)
elif [ -f "$SCRIPT_DIR/SKILL.md" ] || [ -f "$SCRIPT_DIR/skills/$SKILL_NAME/SKILL.md" ]; then
  SOURCE_DIR="$SCRIPT_DIR"
else
  SOURCE_DIR=$(download_source)
fi

PAYLOAD_DIR="$SOURCE_DIR"
if [ -f "$SOURCE_DIR/skills/$SKILL_NAME/SKILL.md" ]; then
  PAYLOAD_DIR="$SOURCE_DIR/skills/$SKILL_NAME"
fi
[ -f "$PAYLOAD_DIR/SKILL.md" ] || fail "source does not contain a skill payload: $PAYLOAD_DIR"

TARGET="$INSTALL_DIR/$SKILL_NAME"
mkdir -p "$INSTALL_DIR"

if [ -e "$TARGET" ]; then
  timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
  backup_dir="$INSTALL_DIR/.skill-backups"
  mkdir -p "$backup_dir"
  backup="$backup_dir/$SKILL_NAME.backup.$timestamp"
  mv "$TARGET" "$backup"
  printf '%s\n' "Existing installation moved to $backup"
fi

mkdir -p "$TARGET"
cp -R "$PAYLOAD_DIR"/. "$TARGET"/
rm -rf "$TARGET/.git" "$TARGET/__pycache__" "$TARGET/.pytest_cache"
chmod +x "$TARGET/scripts/github_skill_updater.py" 2>/dev/null || true

printf '%s\n' "Installed $SKILL_NAME for $AGENT at $TARGET"
