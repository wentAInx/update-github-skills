[CmdletBinding()]
Param(
    [ValidateSet("codex", "claude", "agents")]
    [string]$Agent = "codex",

    [ValidateSet("global", "local")]
    [string]$Scope = "global",

    [string]$InstallDir = "",
    [string]$SourceDir = "",
    [string]$RepoSlug = "",
    [string]$Ref = "",
    [string]$ArchiveUrl = ""
)

$ErrorActionPreference = "Stop"
$SkillName = "update-github-skills"

if ([string]::IsNullOrWhiteSpace($RepoSlug)) {
    if ([string]::IsNullOrWhiteSpace($env:REPO_SLUG)) {
        $RepoSlug = "wentAInx/update-github-skills"
    } else {
        $RepoSlug = $env:REPO_SLUG
    }
}

if ([string]::IsNullOrWhiteSpace($Ref)) {
    if ([string]::IsNullOrWhiteSpace($env:REF)) {
        $Ref = "main"
    } else {
        $Ref = $env:REF
    }
}

if ([string]::IsNullOrWhiteSpace($ArchiveUrl) -and -not [string]::IsNullOrWhiteSpace($env:ARCHIVE_URL)) {
    $ArchiveUrl = $env:ARCHIVE_URL
}

function Get-DefaultInstallDir {
    param([string]$AgentName, [string]$InstallScope)

    if ($InstallScope -eq "local") {
        switch ($AgentName) {
            "codex" { return (Join-Path (Get-Location) ".codex\skills") }
            "claude" { return (Join-Path (Get-Location) ".claude\skills") }
            "agents" { return (Join-Path (Get-Location) ".agents\skills") }
        }
    }

    switch ($AgentName) {
        "codex" { return (Join-Path $env:USERPROFILE ".codex\skills") }
        "claude" { return (Join-Path $env:USERPROFILE ".claude\skills") }
        "agents" { return (Join-Path $env:USERPROFILE ".agents\skills") }
    }
}

function Get-SourceDirFromArchive {
    param([string]$Repo, [string]$BranchOrTag, [string]$Url)

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("update-github-skills-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    $zipPath = Join-Path $tempRoot "source.zip"
    if ([string]::IsNullOrWhiteSpace($Url)) {
        $Url = "https://github.com/$Repo/archive/refs/heads/$BranchOrTag.zip"
    }
    Write-Host "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $tempRoot -Force
    $skillMd = Get-ChildItem -Path $tempRoot -Filter "SKILL.md" -Recurse -File | Select-Object -First 1
    if ($null -eq $skillMd) {
        throw "Downloaded archive does not contain SKILL.md"
    }
    return $skillMd.Directory.FullName
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Get-DefaultInstallDir -AgentName $Agent -InstallScope $Scope
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($SourceDir)) {
    if ((Test-Path (Join-Path $scriptRoot "SKILL.md")) -or (Test-Path (Join-Path $scriptRoot "skills\$SkillName\SKILL.md"))) {
        $SourceDir = $scriptRoot
    } else {
        $SourceDir = Get-SourceDirFromArchive -Repo $RepoSlug -BranchOrTag $Ref -Url $ArchiveUrl
    }
}

$payloadDir = $SourceDir
$nestedSkill = Join-Path $SourceDir "skills\$SkillName"
if (Test-Path (Join-Path $nestedSkill "SKILL.md")) {
    $payloadDir = $nestedSkill
}
if (-not (Test-Path (Join-Path $payloadDir "SKILL.md"))) {
    throw "Source does not contain a skill payload: $payloadDir"
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
$target = Join-Path $InstallDir $SkillName
if (Test-Path $target) {
    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $backupRoot = Join-Path $InstallDir ".skill-backups"
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    $backup = Join-Path $backupRoot "$SkillName.backup.$timestamp"
    Move-Item -Path $target -Destination $backup
    Write-Host "Existing installation moved to $backup"
}

New-Item -ItemType Directory -Path $target -Force | Out-Null
Get-ChildItem -Path $payloadDir -Force | Where-Object { $_.Name -ne ".git" } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $target -Recurse -Force
}

$gitDir = Join-Path $target ".git"
if (Test-Path $gitDir) {
    Remove-Item -Path $gitDir -Recurse -Force
}

Write-Host "Installed $SkillName for $Agent at $target"
