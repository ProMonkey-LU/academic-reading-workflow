[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("list", "install", "check", "update-nature", "update-obsidian", "enable", "disable")]
    [string]$Command,
    [Parameter(Position = 1)]
    [string]$SkillName,
    [string]$ActiveSkillsFile
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$NatureRoot = Join-Path $Root "vendor/nature-skills"
$ObsidianRoot = Join-Path $Root "vendor/obsidian-skills"
$DefaultActiveFile = Join-Path $Root "config/active-skills.windows.txt"
$ActiveFile = if ($ActiveSkillsFile) {
    $Candidate = $ActiveSkillsFile
    if (-not [IO.Path]::IsPathRooted($Candidate)) { $Candidate = Join-Path (Get-Location) $Candidate }
    [IO.Path]::GetFullPath($Candidate)
} elseif ($env:ACTIVE_SKILLS_FILE) {
    $Candidate = $env:ACTIVE_SKILLS_FILE
    if (-not [IO.Path]::IsPathRooted($Candidate)) { $Candidate = Join-Path (Get-Location) $Candidate }
    [IO.Path]::GetFullPath($Candidate)
} else {
    $DefaultActiveFile
}
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$Destination = if ($env:CODEX_SKILLS_DIR) { $env:CODEX_SKILLS_DIR } else { Join-Path $CodexHome "skills" }
$Manifest = Join-Path $Destination ".academic-reading-workflow-managed"

function Get-ActiveNames {
    if (-not (Test-Path -LiteralPath $ActiveFile -PathType Leaf)) {
        throw "active skill list not found: $ActiveFile"
    }
    @(Get-Content -LiteralPath $ActiveFile | ForEach-Object {
        ($_ -replace "\s*#.*$", "").Trim()
    } | Where-Object { $_ })
}

function Get-SkillSource([string]$Name) {
    $Candidates = @(
        (Join-Path $Root "skills/$Name"),
        (Join-Path $NatureRoot "skills/$Name"),
        (Join-Path $ObsidianRoot "skills/$Name"),
        (Join-Path $Root "local-vendor/$Name")
    )
    $Aliases = @{
        "aminer-data-search" = "aminer-open-academic-1.0.5"
        "memory" = "memory-1.0.2"
        "research-paper-writer" = "research-paper-writer-0.1.0"
        "obsidian-ontology-sync" = "obsidian-ontology-sync-1.0.1"
        "tmux" = "tmux-1.0.0"
    }
    if ($Aliases.ContainsKey($Name)) {
        $Candidates += Join-Path $Root "local-vendor/$($Aliases[$Name])"
    }
    foreach ($Candidate in $Candidates) {
        if (Test-Path -LiteralPath (Join-Path $Candidate "SKILL.md") -PathType Leaf) {
            return [IO.Path]::GetFullPath($Candidate)
        }
    }
    return $null
}

function Get-NatureSharedSource {
    foreach ($Name in @("nature-shared", "_shared")) {
        $Candidate = Join-Path $NatureRoot "skills/$Name"
        if (Test-Path -LiteralPath $Candidate -PathType Container) { return $Candidate }
    }
    return $null
}

function Get-LinkTarget([string]$Path) {
    $Item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if (-not $Item -or -not $Item.LinkType) { return $null }
    $Target = @($Item.Target)[0]
    if (-not [IO.Path]::IsPathRooted($Target)) {
        $Target = Join-Path (Split-Path -Parent $Path) $Target
    }
    [IO.Path]::GetFullPath($Target)
}

function Test-PreviouslyManaged([string]$Name) {
    (Test-Path -LiteralPath $Manifest -PathType Leaf) -and
        ((Get-Content -LiteralPath $Manifest) -contains $Name)
}

function Install-One([string]$Name) {
    $Source = Get-SkillSource $Name
    if (-not $Source) { throw "source not found for active skill: $Name" }
    $Target = Join-Path $Destination $Name
    $Existing = Get-Item -LiteralPath $Target -Force -ErrorAction SilentlyContinue
    if ($Existing) {
        $Current = Get-LinkTarget $Target
        if (-not $Current) { throw "refusing to replace unmanaged path: $Target" }
        if ($Current -eq $Source) { return }
        if (-not (Test-PreviouslyManaged $Name) -and -not $Current.StartsWith($Root)) {
            throw "refusing to replace unmanaged link: $Target -> $Current"
        }
        Remove-Item -LiteralPath $Target -Force
    }
    New-Item -ItemType Junction -Path $Target -Target $Source | Out-Null
    Write-Host "linked $Name"
}

function Install-All {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $Active = Get-ActiveNames
    foreach ($Name in $Active) { Install-One $Name }

    if (@($Active | Where-Object { $_ -like "nature-*" }).Count -gt 0) {
        $Shared = Get-NatureSharedSource
        if (-not $Shared) { throw "nature shared directory is missing" }
        $SharedName = Split-Path -Leaf $Shared
        $SharedTarget = Join-Path $Destination $SharedName
        $Existing = Get-Item -LiteralPath $SharedTarget -Force -ErrorAction SilentlyContinue
        if ($Existing) {
            if (-not (Get-LinkTarget $SharedTarget)) { throw "refusing to replace unmanaged path: $SharedTarget" }
            Remove-Item -LiteralPath $SharedTarget -Force
        }
        New-Item -ItemType Junction -Path $SharedTarget -Target $Shared | Out-Null
        foreach ($StaleName in @("_shared", "nature-shared")) {
            if ($StaleName -eq $SharedName) { continue }
            $StalePath = Join-Path $Destination $StaleName
            $StaleTarget = Get-LinkTarget $StalePath
            if ($StaleTarget -and $StaleTarget.StartsWith($Root)) { Remove-Item -LiteralPath $StalePath -Force }
        }
    }

    if (Test-Path -LiteralPath $Manifest -PathType Leaf) {
        foreach ($Old in Get-Content -LiteralPath $Manifest) {
            if ($Old -and $Active -notcontains $Old) {
                $OldPath = Join-Path $Destination $Old
                $OldTarget = Get-LinkTarget $OldPath
                if ($OldTarget -and $OldTarget.StartsWith($Root)) {
                    Remove-Item -LiteralPath $OldPath -Force
                    Write-Host "unlinked $Old"
                }
            }
        }
    }
    Set-Content -LiteralPath $Manifest -Value $Active -Encoding utf8
}

function Check-All {
    $Failures = 0
    $Active = Get-ActiveNames
    if (@($Active | Group-Object | Where-Object Count -gt 1).Count -gt 0) {
        Write-Error "duplicate entries found in $ActiveFile" -ErrorAction Continue
        $Failures++
    }
    foreach ($Name in $Active) {
        $Source = Get-SkillSource $Name
        $Target = Join-Path $Destination $Name
        $Current = Get-LinkTarget $Target
        if (-not $Source) { Write-Host "MISSING SOURCE $Name"; $Failures++; continue }
        if (-not $Current) { Write-Host "MISSING LINK $Name"; $Failures++; continue }
        if ($Current -ne $Source) { Write-Host "WRONG LINK $Name -> $Current"; $Failures++; continue }
        Write-Host "OK $Name"
    }
    if (@($Active | Where-Object { $_ -like "nature-*" }).Count -gt 0) {
        $Shared = Get-NatureSharedSource
        if (-not $Shared) { Write-Host "MISSING SOURCE nature shared"; $Failures++ }
        else {
            $SharedTarget = Join-Path $Destination (Split-Path -Leaf $Shared)
            if ((Get-LinkTarget $SharedTarget) -ne [IO.Path]::GetFullPath($Shared)) {
                Write-Host "MISSING OR WRONG LINK $(Split-Path -Leaf $Shared)"
                $Failures++
            }
        }
    }
    if ($Failures -gt 0) { throw "$Failures skill checks failed" }
}

function List-All {
    $Active = Get-ActiveNames
    $Roots = @((Join-Path $Root "skills"), (Join-Path $NatureRoot "skills"), (Join-Path $ObsidianRoot "skills"), (Join-Path $Root "local-vendor"))
    $Rows = foreach ($SourceRoot in $Roots) {
        if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) { continue }
        Get-ChildItem -LiteralPath $SourceRoot -Directory | ForEach-Object {
            $SkillFile = Join-Path $_.FullName "SKILL.md"
            if (Test-Path -LiteralPath $SkillFile -PathType Leaf) {
                $NameLine = Get-Content -LiteralPath $SkillFile | Where-Object { $_ -match '^name:\s*' } | Select-Object -First 1
                $Name = if ($NameLine) { $NameLine -replace '^name:\s*', '' } else { $_.Name }
                [PSCustomObject]@{ Skill = $Name; Status = if ($Active -contains $Name -or $Active -contains $_.Name) { "active" } else { "optional" }; Source = $_.FullName }
            }
        }
    }
    $Rows | Sort-Object Skill | Format-Table -AutoSize
}

function Set-Enabled([bool]$Enabled, [string]$Name) {
    if (-not $Name) { throw "enable/disable requires one skill name" }
    if (-not (Get-SkillSource $Name)) { throw "unknown or unavailable skill: $Name" }
    $Lines = @(Get-Content -LiteralPath $ActiveFile)
    if ($Enabled -and (Get-ActiveNames) -notcontains $Name) { $Lines += $Name }
    if (-not $Enabled) { $Lines = @($Lines | Where-Object { $_.Trim() -ne $Name }) }
    Set-Content -LiteralPath $ActiveFile -Value $Lines -Encoding utf8
    Install-All
    Check-All
}

function Update-Nature {
    if (-not (Test-Path -LiteralPath (Join-Path $NatureRoot ".git"))) { throw "nature submodule is not initialized" }
    $Old = (& git -C $NatureRoot rev-parse HEAD).Trim()
    & git -C $NatureRoot fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
    & git -C $NatureRoot merge --ff-only origin/main
    if ($LASTEXITCODE -ne 0) { throw "nature update is not a fast-forward" }
    $New = (& git -C $NatureRoot rev-parse HEAD).Trim()
    Install-All
    Check-All
    Write-Host "nature-skills: $Old -> $New"
}

function Update-Obsidian {
    if (-not (Test-Path -LiteralPath (Join-Path $ObsidianRoot ".git"))) { throw "obsidian-skills submodule is not initialized" }
    $Old = (& git -C $ObsidianRoot rev-parse HEAD).Trim()
    $RemoteHead = (& git -C $ObsidianRoot symbolic-ref --short refs/remotes/origin/HEAD 2>$null).Trim()
    $Branch = if ($RemoteHead) { $RemoteHead -replace '^origin/', '' } else { "main" }
    & git -C $ObsidianRoot fetch origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
    & git -C $ObsidianRoot merge --ff-only "origin/$Branch"
    if ($LASTEXITCODE -ne 0) { throw "obsidian-skills update is not a fast-forward" }
    $New = (& git -C $ObsidianRoot rev-parse HEAD).Trim()
    Install-All
    Check-All
    Write-Host "obsidian-skills: $Old -> $New"
}

switch ($Command) {
    "list" { List-All }
    "install" { Install-All }
    "check" { Check-All }
    "update-nature" { Update-Nature }
    "update-obsidian" { Update-Obsidian }
    "enable" { Set-Enabled $true $SkillName }
    "disable" { Set-Enabled $false $SkillName }
}
