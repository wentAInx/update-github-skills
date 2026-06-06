# update-github-skills

`update-github-skills` 是一个面向 Codex、Claude Code 等 Agent 的 Skill，用来盘点、检查并安全更新本地安装的 GitHub 来源 skills。它适合你同时使用插件市场、Git clone + cp、curl 一键脚本等多种安装方式后，需要统一管理第三方 skill 更新的场景。

English documentation: [README.en.md](README.en.md)

## 项目简介

### 它能做什么

- 扫描本地 skill 目录，生成 inventory 清单。
- 自动识别直接 Git clone 安装的 skill。
- 通过 `skill-sources.json` 管理手动复制、zip/curl 下载来源的 skill。
- dry-run 检查远端更新，不直接覆盖本地文件。
- 用户确认后更新，并在更新前自动备份。
- 同时支持 Codex、Claude Code、通用 `.agents` skill 目录。

### 适用场景

- 你安装了很多 GitHub 作者维护的 skills，希望定期检查更新。
- 有些 skills 是 `cp -R` 手动部署的，已经没有 `.git` 信息。
- 你希望在更新前看到哪些文件会变化。
- 你希望更新失败时能保留本地备份。

### Skill / MCP / Plugin 区别

本仓库核心是普通 Agent Skill，不是 MCP server。它不会出现在 MCP 面板，也不需要 `/mcp list` 验证。仓库同时提供 `.codex-plugin/plugin.json`，用于 Codex 插件市场识别和在线安装。

如果未来仓库新增 MCP server，再添加 `mcp-server` 标签；当前建议 GitHub Topics 使用：

- `codex-skill`
- `claude-code-skill`
- `agent-skill`
- `skills-updater`
- `github-skills`

## 环境依赖

### 全平台通用

- Python 3.9+：运行 updater 脚本。
- Git：检查或更新 GitHub/Git 来源 skill。
- 网络访问 GitHub：一键安装和远端更新检查需要。

### macOS / Linux

- `curl`
- `tar`
- `bash` 或兼容 POSIX shell

macOS 首次安装如果遇到权限问题，可先确认终端有访问用户目录的权限，并使用全局安装目录 `~/.codex/skills/` 或项目局部安装目录 `./.codex/skills/`。

### Windows

- Windows PowerShell 5+ 或 PowerShell 7+
- Git for Windows
- Python 3，并确保 `python` 或 `py` 可用

如果 PowerShell 阻止脚本运行，可使用临时执行权限：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 三种安装教程

### 方式一：一键 curl / PowerShell 安装

#### macOS / Linux：安装到 Codex 全局 skills

```bash
curl -fsSL https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.sh | bash
```

安装到 Claude Code：

```bash
curl -fsSL https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.sh | bash -s -- --agent claude
```

安装到当前项目局部目录：

```bash
curl -fsSL https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.sh | bash -s -- --scope local
```

自定义 GitHub 分支或 fork：

```bash
curl -fsSL https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.sh | bash -s -- --repo wentAInx/update-github-skills --ref main
```

#### Windows PowerShell：安装到 Codex 全局 skills

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -UseBasicParsing https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.ps1 | iex"
```

安装到 Claude Code：

```powershell
iwr -UseBasicParsing https://raw.githubusercontent.com/wentAInx/update-github-skills/main/install.ps1 -OutFile install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Agent claude
```

安装到当前项目局部目录：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Scope local
```

### 方式二：Git Clone + CP 手动部署

#### macOS / Linux

```bash
git clone https://github.com/wentAInx/update-github-skills.git
cd update-github-skills
bash install.sh --agent codex
```

也可以手动复制 skill 目录：

```bash
mkdir -p ~/.codex/skills
cp -R skills/update-github-skills ~/.codex/skills/update-github-skills
```

Claude Code：

```bash
mkdir -p ~/.claude/skills
cp -R skills/update-github-skills ~/.claude/skills/update-github-skills
```

项目局部安装：

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

手动复制到 Codex：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\update-github-skills "$env:USERPROFILE\.codex\skills\update-github-skills"
```

Windows cmd：

```cmd
mkdir "%USERPROFILE%\.codex\skills"
xcopy /E /I /Y skills\update-github-skills "%USERPROFILE%\.codex\skills\update-github-skills"
```

### 方式三：Codex 插件市场安装

在 Codex 中添加个人 marketplace：

```text
/plugin marketplace add wentAInx/update-github-skills
```

安装最新版本：

```text
/plugin install update-github-skills@latest
```

安装固定版本：

```text
/plugin install update-github-skills@0.1.0
```

说明：本项目是 Skill 型插件，不是 MCP 插件。安装后请在 skills/插件列表中查看，不要用 `/mcp list` 验证。

## 全局安装 vs 项目局部安装

| 模式 | 目录 | 适合谁 |
| --- | --- | --- |
| 全局安装 | `~/.codex/skills/`、`~/.claude/skills/`、`%USERPROFILE%\.codex\skills\` | 希望所有项目都能使用 |
| 项目局部安装 | 当前项目的 `./.codex/skills/` 或 `./.claude/skills/` | 希望只在当前仓库启用 |

## 快速上手示例

安装后，在 Codex 或 Claude Code 中尝试：

```text
$update-github-skills 帮我盘点当前本地 skills 的来源
```

```text
$update-github-skills 检查 ~/.codex/skills 里哪些 GitHub skill 有更新，先不要更新
```

```text
$update-github-skills 根据 ~/.codex/skill-sources.json dry-run 检查手动复制安装的 skills
```

也可以直接运行脚本：

```bash
python3 ~/.codex/skills/update-github-skills/scripts/github_skill_updater.py inventory --json
python3 ~/.codex/skills/update-github-skills/scripts/github_skill_updater.py check --manifest ~/.codex/skill-sources.json --json
```

## source manifest 示例

对于 `curl`、zip 下载、手动 `cp` 安装的 skill，本地目录里通常没有 `.git`。这时创建 `~/.codex/skill-sources.json`：

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

然后运行：

```bash
python3 ~/.codex/skills/update-github-skills/scripts/github_skill_updater.py check --manifest ~/.codex/skill-sources.json --json
```

## 常见问题 FAQ

### 1. `Permission denied`

macOS/Linux 先确认安装脚本可执行：

```bash
chmod +x install.sh
```

如果用户目录受限，改用项目局部安装：

```bash
bash install.sh --scope local
```

### 2. Windows 提示脚本被策略阻止

使用临时执行权限，不改变系统长期策略：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

### 3. 找不到 Python 或 Git

确认命令可用：

```bash
python3 --version
git --version
```

Windows 可尝试：

```powershell
py --version
git --version
```

### 4. 网络下载失败

检查 GitHub 网络连接，或改用 `git clone` 后本地安装：

```bash
git clone https://github.com/wentAInx/update-github-skills.git
cd update-github-skills
bash install.sh
```

### 5. 显示 `needs_source`

这表示该 skill 没有 `.git`，也没有 manifest 记录。请在 `~/.codex/skill-sources.json` 中补充 `repo/ref/subdir`。

### 6. `/mcp list` 看不到它

这是正常的。本项目不是 MCP server，不会出现在 MCP 面板。请在 Agent 的 skills 或插件列表中查看。

### 7. 更新时提示 `blocked_dirty_worktree`

直接 Git 安装的 skill 有本地未提交修改。先备份或提交你的改动，再重新检查更新。

## 版本更新

### curl / PowerShell 一键安装用户

重新运行安装命令即可。安装脚本会把旧版本移动到带时间戳的 `.backup` 目录。

### Git clone 用户

```bash
cd update-github-skills
git pull --ff-only
bash install.sh --agent codex
```

Windows：

```powershell
git pull --ff-only
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Agent codex
```

### 插件市场用户

```text
/plugin install update-github-skills@latest
```

## 开源协议 & 作者信息

- License: MIT，见 [LICENSE](LICENSE)。
- Author: [wentAInx](https://github.com/wentAInx)。
- 建议开启 GitHub Issues 反馈 bug，开启 Discussions 收集安装经验、manifest 示例和新 Agent 兼容需求。

