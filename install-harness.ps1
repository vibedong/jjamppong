param(
    [string]$TargetPath = (Get-Location).Path,
    [string]$SourcePath = "",
    [string]$GitHubUrl = "",
    [string]$Repository = "https://github.com/vibedong/jjamppong",
    [string]$ReleaseTag = "harness-v1.0.5",
    [string]$ReleaseAssetPath = "",
    [string]$ReleaseManifestPath = "",
    [switch]$Force,
    [switch]$Update
)

$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $parent = Split-Path -Parent $Path
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

function Write-JsonNoBom {
    param([string]$Path, [object]$Payload)
    Write-Utf8NoBom -Path $Path -Text (($Payload | ConvertTo-Json -Depth 50 -Compress) + "`n")
}

function Get-FileSha256 {
    param([string]$Path)
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $hash = $sha.ComputeHash($stream)
        return ([System.BitConverter]::ToString($hash)).Replace("-", "").ToLowerInvariant()
    } finally {
        $stream.Dispose()
    }
}

function Get-StringSha256 {
    param([string]$Text)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ([System.BitConverter]::ToString($hash)).Replace("-", "").ToLowerInvariant()
}

function Normalize-RelPath {
    param([string]$Path)
    return $Path.Replace("\", "/")
}

function Normalize-Repository {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "https://github.com/vibedong/jjamppong" }
    $trimmed = $Value.Trim()
    if ($trimmed -match "^https://github\.com/") { return $trimmed.TrimEnd("/") }
    if ($trimmed -match "^github\.com/") { return "https://$($trimmed.TrimEnd('/'))" }
    if ($trimmed -match "^[^/]+/[^/]+$") { return "https://github.com/$trimmed" }
    return $trimmed.TrimEnd("/")
}

function Get-RequestedTagFromUrl {
    param([string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) { return $null }
    if ($Url -match "/releases/tag/([^/?#]+)") { return $Matches[1] }
    return $null
}

function Test-HarnessInstalled {
    param([string]$Root)
    return (Test-Path -LiteralPath (Join-Path $Root ".harness/current/status/STATUS_KO.md") -PathType Leaf)
}

function Write-UpdatePreflightAndExit {
    param([string]$Root)
    $proposal = [ordered]@{
        artifact_id = "harness.update_preflight"
        artifact_version = "1.0.5"
        intent = "update_required"
        write_free = $true
        target_path = $Root
        suggested_command = ".\install-harness.ps1 -TargetPath `"$Root`" -Update"
        preserved_by_default = @(
            ".harness/current/status/STATUS_KO.md",
            ".harness/current/readsets/CURRENT_READ_SET.json",
            ".harness/improvement/BACKLOG.md",
            ".harness/improvement/BACKLOG.jsonl",
            ".harness/current/planning",
            ".harness/current/conversation",
            "user product files"
        )
    }
    Write-Output ($proposal | ConvertTo-Json -Depth 20 -Compress)
    exit 2
}

function Get-RuntimeCoverage {
    param([string]$Root)
    $path = Join-Path $Root ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json"
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Release coverage universe is missing: $path"
    }
    return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-RuntimeCoveragePaths {
    param([string]$Root)
    $coverage = Get-RuntimeCoverage -Root $Root
    return [string[]]$coverage.runtime_paths
}

$canonicalStarterFiles = @(
    "AGENTS.md",
    "README.md",
    "install-harness.ps1",
    "harness.ps1",
    ".harness\current\status\STATUS_KO.md",
    ".harness\current\readsets\CURRENT_READ_SET.json",
    ".harness\current\source\SOURCE_IDENTITY.json",
    ".harness\current\START_HERE.md",
    ".harness\runtime\contracts\PLANNING_STAGE_CONTRACT.md"
)

function Get-RuntimeArtifactSha256 {
    param([string]$Root)
    $runtimeFiles = Get-RuntimeCoveragePaths -Root $Root
    [System.Array]::Sort($runtimeFiles, [System.StringComparer]::Ordinal)
    $excluded = @(
        ".harness/current/source/SOURCE_IDENTITY.json",
        ".harness/current/status/STATUS_KO.md",
        ".harness/current/readsets/CURRENT_READ_SET.json",
        ".harness/improvement/BACKLOG.md",
        ".harness/improvement/BACKLOG.jsonl"
    )
    $rows = @()
    foreach ($rel in $runtimeFiles) {
        if ($excluded -contains $rel) { continue }
        $file = Join-Path $Root $rel
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Missing runtime file for artifact hash: $rel"
        }
        $rows += "$rel=$(Get-FileSha256 -Path $file)"
    }
    return Get-StringSha256 -Text (($rows -join "`n") + "`n")
}

function Resolve-SourcePath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "SourcePath does not exist: $Path"
    }
    $root = (Resolve-Path -LiteralPath $Path).Path
    $commit = (git -C $root rev-parse HEAD 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or $commit -notmatch "^[0-9a-f]{40}$") {
        throw "SourcePath must be a Git checkout so immutable_commit can be resolved."
    }
    return [ordered]@{
        source_root = $root
        source_repository = Normalize-Repository -Value $Repository
        release_tag = $ReleaseTag
        immutable_commit = $commit
        artifact_sha256 = Get-RuntimeArtifactSha256 -Root $root
        source_identity_status = "resolved"
        from_release_manifest = $false
    }
}

function Resolve-GitHubReleaseSource {
    param(
        [string]$Url,
        [string]$AssetPath,
        [string]$ManifestPath
    )
    if ([string]::IsNullOrWhiteSpace($Url)) { return $null }
    if ([string]::IsNullOrWhiteSpace($AssetPath) -or [string]::IsNullOrWhiteSpace($ManifestPath)) {
        throw "GitHubUrl install requires ReleaseAssetPath and ReleaseManifestPath in this runtime candidate."
    }
    if (-not (Test-Path -LiteralPath $AssetPath -PathType Leaf)) { throw "Release asset is missing: $AssetPath" }
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) { throw "Release manifest is missing: $ManifestPath" }

    $manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $requestedTag = Get-RequestedTagFromUrl -Url $Url
    if ($requestedTag -and $requestedTag -ne $manifest.release_tag) {
        throw "GitHub release tag mismatch: requested tag '$requestedTag' but manifest tag '$($manifest.release_tag)'"
    }
    $assetHash = Get-FileSha256 -Path $AssetPath
    if ($assetHash -ne ([string]$manifest.release_asset_sha256).ToLowerInvariant()) {
        throw "Release asset SHA-256 does not match manifest."
    }

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("harness-release-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    Expand-Archive -LiteralPath $AssetPath -DestinationPath $tempRoot -Force
    $artifactHash = Get-RuntimeArtifactSha256 -Root $tempRoot
    if ($artifactHash -ne ([string]$manifest.runtime_artifact_sha256).ToLowerInvariant()) {
        throw "Runtime artifact SHA-256 does not match release manifest."
    }
    $repo = Normalize-Repository -Value ([string]$manifest.source_repository)
    return [ordered]@{
        source_root = $tempRoot
        source_repository = $repo
        release_tag = [string]$manifest.release_tag
        immutable_commit = [string]$manifest.immutable_commit
        artifact_sha256 = $artifactHash
        source_identity_status = "resolved"
        from_release_manifest = $true
    }
}

function Copy-RuntimeFile {
    param(
        [string]$SourceRoot,
        [string]$TargetRoot,
        [string]$RelativePath,
        [bool]$PreserveExisting
    )
    $src = Join-Path $SourceRoot $RelativePath
    $dst = Join-Path $TargetRoot $RelativePath
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
        throw "Runtime source file missing: $RelativePath"
    }
    if ($PreserveExisting -and (Test-Path -LiteralPath $dst -PathType Leaf)) {
        return
    }
    $parent = Split-Path -Parent $dst
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Copy-Item -LiteralPath $src -Destination $dst -Force
}

function Write-InstalledSourceIdentity {
    param([string]$TargetRoot, [object]$Source)
    $identity = [ordered]@{
        artifact_id = "harness.installed_source_identity"
        artifact_version = "1.0.5"
        source_repository = [string]$Source.source_repository
        release_tag = [string]$Source.release_tag
        immutable_commit = [string]$Source.immutable_commit
        artifact_sha256 = [string]$Source.artifact_sha256
        artifact_hash_rule = "runtime_paths_file_hash_rows_excluding_mutable_local_state"
        local_cache_path_is_identity = $false
        source_identity_status = [string]$Source.source_identity_status
    }
    Write-JsonNoBom -Path (Join-Path $TargetRoot ".harness/current/source/SOURCE_IDENTITY.json") -Payload $identity
}

function Write-InstallRecord {
    param([string]$TargetRoot, [string]$Kind, [object]$Source)
    $dir = Join-Path $TargetRoot ".harness/evidence/install"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    if ($Kind -eq "update") {
        $record = [ordered]@{
            artifact_id = "harness.update_record"
            artifact_version = "1.0"
            update_result = "pass"
            release_tag = [string]$Source.release_tag
            preserved_paths = @(
                ".harness/current/status/STATUS_KO.md",
                ".harness/current/readsets/CURRENT_READ_SET.json",
                ".harness/current/planning",
                ".harness/current/conversation",
                ".harness/improvement/BACKLOG.md",
                ".harness/improvement/BACKLOG.jsonl"
            )
        }
        Write-JsonNoBom -Path (Join-Path $dir "UPDATE_RECORD_V1_0.json") -Payload $record
    } else {
        $record = [ordered]@{
            artifact_id = "harness.install_record"
            artifact_version = "1.0"
            install_result = "pass"
            release_tag = [string]$Source.release_tag
            runtime_only = $true
        }
        Write-JsonNoBom -Path (Join-Path $dir "INSTALL_RECORD_V1_0.json") -Payload $record
    }
}

$targetRoot = [System.IO.Path]::GetFullPath($TargetPath)
if (-not (Test-Path -LiteralPath $targetRoot -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
}

if ((Test-HarnessInstalled -Root $targetRoot) -and -not $Update) {
    Write-UpdatePreflightAndExit -Root $targetRoot
}

$releaseSource = Resolve-GitHubReleaseSource -Url $GitHubUrl -AssetPath $ReleaseAssetPath -ManifestPath $ReleaseManifestPath
if ($null -ne $releaseSource) {
    $source = $releaseSource
} else {
    if ([string]::IsNullOrWhiteSpace($SourcePath)) {
        $SourcePath = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    $source = Resolve-SourcePath -Path $SourcePath
}

$runtimePaths = Get-RuntimeCoveragePaths -Root ([string]$source.source_root)
[System.Array]::Sort($runtimePaths, [System.StringComparer]::Ordinal)
$preserveOnUpdate = @(
    ".harness/current/status/STATUS_KO.md",
    ".harness/current/readsets/CURRENT_READ_SET.json",
    ".harness/improvement/BACKLOG.md",
    ".harness/improvement/BACKLOG.jsonl"
)

foreach ($rel in $runtimePaths) {
    $preserve = ($Update -and ($preserveOnUpdate -contains $rel))
    Copy-RuntimeFile -SourceRoot ([string]$source.source_root) -TargetRoot $targetRoot -RelativePath $rel -PreserveExisting:$preserve
}

Write-InstalledSourceIdentity -TargetRoot $targetRoot -Source $source
if ($Update) {
    Write-InstallRecord -TargetRoot $targetRoot -Kind "update" -Source $source
    Write-Output "updated"
} else {
    Write-InstallRecord -TargetRoot $targetRoot -Kind "install" -Source $source
    Write-Output "installed"
}
Write-Output "Run .\harness.ps1 doctor"
