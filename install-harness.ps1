param(
    [string]$TargetPath = (Get-Location).Path,
    [string]$SourcePath = "",
    [string]$ReleaseTag = "harness-v1.0.0",
    [string]$Repository = "vibedong/jjamppong",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Convert-ToPosixPath([string]$PathValue) {
    return ($PathValue -replace "\\", "/")
}

function Write-Utf8NoBom([string]$PathValue, [string]$Content) {
    $parent = Split-Path -Parent $PathValue
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($PathValue, $Content, $encoding)
}

function Write-CanonicalJson([string]$PathValue, $Payload) {
    $json = $Payload | ConvertTo-Json -Depth 20 -Compress
    Write-Utf8NoBom -PathValue $PathValue -Content ($json + "`n")
}

function Get-FileSha256([string]$PathValue) {
    $stream = [System.IO.File]::OpenRead($PathValue)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $bytes = $sha.ComputeHash($stream)
        return (($bytes | ForEach-Object { $_.ToString("x2") }) -join "")
    } finally {
        $stream.Dispose()
    }
}

function Expand-HarnessArchive {
    param([string]$ArchivePath, [string]$DestinationPath)
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $destinationFullPath = [System.IO.Path]::GetFullPath($DestinationPath)
    $requiredPrefixes = @(
        "install-harness.ps1",
        "tools/harness-validator/",
        ".harness/definitions/",
        "AGENTS.md"
    )
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        foreach ($entry in $zip.Entries) {
            if ([string]::IsNullOrWhiteSpace($entry.FullName)) {
                continue
            }
            $normalizedName = $entry.FullName.Replace("\", "/").TrimStart("/")
            $candidateNames = @($normalizedName)
            $firstSlash = $normalizedName.IndexOf("/")
            if ($firstSlash -ge 0) {
                $candidateNames += $normalizedName.Substring($firstSlash + 1)
            }
            $relativeName = $null
            foreach ($candidateName in $candidateNames) {
                foreach ($prefix in $requiredPrefixes) {
                    if ($prefix.EndsWith("/")) {
                        if ($candidateName.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                            $relativeName = $candidateName
                            break
                        }
                    } elseif ($candidateName.Equals($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                        $relativeName = $candidateName
                        break
                    }
                }
                if ($relativeName) {
                    break
                }
            }
            if (-not $relativeName) {
                continue
            }
            $entryPath = $relativeName.Replace("/", [string][System.IO.Path]::DirectorySeparatorChar)
            $targetPath = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($destinationFullPath, $entryPath))
            if (-not $targetPath.StartsWith($destinationFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Unsafe archive entry path: $($entry.FullName)"
            }
            if ($entry.FullName.EndsWith("/") -or [string]::IsNullOrEmpty($entry.Name)) {
                New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
                continue
            }
            New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($targetPath)) | Out-Null
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $targetPath, $true)
        }
    } finally {
        $zip.Dispose()
    }
}

function Get-SourceRoot {
    param([string]$RequestedSourcePath, [string]$RequestedTag, [string]$Repo)
    if ($RequestedSourcePath -and (Test-Path -LiteralPath $RequestedSourcePath -PathType Container)) {
        return (Resolve-Path -LiteralPath $RequestedSourcePath).Path
    }

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("hi-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    $archivePath = Join-Path $tempRoot "harness-source.zip"
    $archiveUrl = "https://github.com/$Repo/archive/refs/tags/$RequestedTag.zip"
    try {
        Invoke-WebRequest -Uri $archiveUrl -OutFile $archivePath -UseBasicParsing
    } catch {
        $gh = Get-Command gh -ErrorAction SilentlyContinue
        if (-not $gh) {
            throw "Could not download Harness source from GitHub. For private repositories, install GitHub CLI and authenticate with 'gh auth login'. Original error: $($_.Exception.Message)"
        }
        $releasePattern = "harness-*-runtime.zip"
        & gh release download $RequestedTag --repo $Repo --pattern $releasePattern --dir $tempRoot --clobber | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $releasePattern = "harness-*-source.zip"
            & gh release download $RequestedTag --repo $Repo --pattern $releasePattern --dir $tempRoot --clobber | Out-Null
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Could not download Harness release asset with GitHub CLI."
        }
        $downloadedArchive = Get-ChildItem -LiteralPath $tempRoot -Filter $releasePattern -File | Select-Object -First 1
        if (-not $downloadedArchive) {
            throw "Harness release source asset was not found after GitHub CLI download."
        }
        $archivePath = $downloadedArchive.FullName
    }
    Expand-HarnessArchive -ArchivePath $archivePath -DestinationPath $tempRoot
    if (Test-Path -LiteralPath (Join-Path $tempRoot "install-harness.ps1") -PathType Leaf) {
        return $tempRoot
    }
    $sourceDir = Get-ChildItem -LiteralPath $tempRoot -Directory |
        Where-Object { $_.Name -ne "__MACOSX" -and (Test-Path -LiteralPath (Join-Path $_.FullName "install-harness.ps1") -PathType Leaf) } |
        Select-Object -First 1
    if ($sourceDir) {
        return $sourceDir.FullName
    }
    $sourceDir = Get-ChildItem -LiteralPath $tempRoot -Directory | Where-Object { $_.Name -ne "__MACOSX" } | Select-Object -First 1
    if (-not $sourceDir) {
        throw "Harness source archive did not contain a source directory."
    }
    return $sourceDir.FullName
}

function Copy-DirectoryFromSource {
    param(
        [string]$SourceRoot,
        [string]$TargetRoot,
        [string]$RelativePath,
        [switch]$AllowExisting
    )
    $source = Join-Path $SourceRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        return
    }
    $target = Join-Path $TargetRoot $RelativePath
    if ((Test-Path -LiteralPath $target) -and (-not $AllowExisting) -and (-not $Force)) {
        throw "Target already has '$RelativePath'. Re-run with -Force after reviewing the existing files."
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
}

function Install-AgentsRouter {
    param([string]$TargetRoot)
    $agentsPath = Join-Path $TargetRoot "AGENTS.md"
    $backupDir = Join-Path $TargetRoot ".harness/evidence/install/backups"
    $block = @'
<!-- harness:start -->
# Harness Router

- Read `.harness/current/status/STATUS_KO.md` first.
- Read `.harness/manifests/CURRENT_READ_SET.json` for the current stage read set.
- Treat `.harness/current/source_identity/SOURCE_IDENTITY.json` as the local source identity pointer.
- Do not use `.harness/archive/` as a primary source.
- Keep work inside the active Harness stage and gate shown in the status file.
- Run `python -B -m unittest discover -s tools/harness-validator/tests` before claiming Harness implementation work is complete.
<!-- harness:end -->
'@
    if (Test-Path -LiteralPath $agentsPath -PathType Leaf) {
        New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
        $timestamp = Get-Date -Format "yyyyMMddHHmmss"
        Copy-Item -LiteralPath $agentsPath -Destination (Join-Path $backupDir "AGENTS.md.$timestamp.bak") -Force
        $existing = Get-Content -LiteralPath $agentsPath -Raw -Encoding UTF8
        if ($existing -match "(?s)<!-- harness:start -->.*?<!-- harness:end -->") {
            $updated = [regex]::Replace($existing, "(?s)<!-- harness:start -->.*?<!-- harness:end -->", $block)
        } else {
            $updated = $existing.TrimEnd() + "`n`n" + $block + "`n"
        }
        Write-Utf8NoBom -PathValue $agentsPath -Content $updated
    } else {
        Write-Utf8NoBom -PathValue $agentsPath -Content ("# Project Instructions`n`n" + $block + "`n")
    }
}

$targetRoot = (Resolve-Path -LiteralPath $TargetPath).Path
$sourceRoot = Get-SourceRoot -RequestedSourcePath $SourcePath -RequestedTag $ReleaseTag -Repo $Repository

Copy-DirectoryFromSource -SourceRoot $sourceRoot -TargetRoot $targetRoot -RelativePath "tools/harness-validator" -AllowExisting:$Force
Copy-DirectoryFromSource -SourceRoot $sourceRoot -TargetRoot $targetRoot -RelativePath ".harness/definitions" -AllowExisting:$true

New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/status") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/navigation") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/source_identity") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/manifests") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/evidence/install") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/artifacts") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/decisions") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/reviews") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/approvals") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/policies") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/archive") | Out-Null

Install-AgentsRouter -TargetRoot $targetRoot

$statusText = @(
    '# Harness 상태',
    '',
    'Harness 1.0 설치 완료.',
    '',
    '- 현재 단계: 프로젝트 시작 준비',
    '- 다음 행동: Codex에게 만들 제품의 목표를 설명하고 Harness 단계 진행을 요청한다.',
    '- Implementation Entry Gate: closed',
    '- 제품 코드 구현: 아직 시작하지 않음',
    '- 공식 읽기 시작점: `.harness/manifests/CURRENT_READ_SET.json`'
) -join [Environment]::NewLine
$statusPath = [System.IO.Path]::Combine($targetRoot, ".harness", "current", "status", "STATUS_KO.md")
Write-Utf8NoBom -PathValue $statusPath -Content $statusText

$startHere = @(
    '# Harness 시작',
    '',
    '1. `.harness/current/status/STATUS_KO.md`를 먼저 읽는다.',
    '2. `.harness/manifests/CURRENT_READ_SET.json`의 read set만 우선 읽는다.',
    '3. 승인된 단계 밖 구현이나 secret 저장은 하지 않는다.'
) -join [Environment]::NewLine
Write-Utf8NoBom -PathValue (Join-Path $targetRoot ".harness/current/navigation/START_HERE.md") -Content $startHere

$readSet = [ordered]@{
    artifact_id = "harness.current_read_set"
    artifact_version = "1.0"
    stage = "installed_project_start"
    language = "ko"
    paths = @(
        [ordered]@{ path = ".harness/current/status/STATUS_KO.md"; purpose_ko = "현재 상태" },
        [ordered]@{ path = ".harness/current/navigation/START_HERE.md"; purpose_ko = "시작 안내" },
        [ordered]@{ path = ".harness/current/source_identity/SOURCE_IDENTITY.json"; purpose_ko = "설치 출처" },
        [ordered]@{ path = ".harness/definitions/schemas/handoff-contract.schema.json"; purpose_ko = "handoff contract schema" },
        [ordered]@{ path = "tools/harness-validator/harness_validator"; purpose_ko = "Harness validator runtime" }
    )
}
Write-CanonicalJson -PathValue (Join-Path $targetRoot ".harness/manifests/CURRENT_READ_SET.json") -Payload $readSet

$sourceCommit = $null
try {
    $sourceCommit = (git -C $sourceRoot rev-parse HEAD 2>$null)
} catch {
    $sourceCommit = $null
}

$sourceIdentity = [ordered]@{
    artifact_id = "harness.installed_source_identity"
    artifact_version = "1.0"
    source_repository = "https://github.com/$Repository"
    release_tag = $ReleaseTag
    source_commit = $sourceCommit
    installed_at_local = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    installer = "install-harness.ps1"
    install_root = Convert-ToPosixPath $targetRoot
}
Write-CanonicalJson -PathValue (Join-Path $targetRoot ".harness/current/source_identity/SOURCE_IDENTITY.json") -Payload $sourceIdentity

$installedFiles = @(
    "AGENTS.md",
    ".harness/current/status/STATUS_KO.md",
    ".harness/current/navigation/START_HERE.md",
    ".harness/current/source_identity/SOURCE_IDENTITY.json",
    ".harness/manifests/CURRENT_READ_SET.json",
    "tools/harness-validator/harness_validator/final_release.py"
)
$fileRecords = @()
foreach ($relativePath in $installedFiles) {
    $path = Join-Path $targetRoot $relativePath
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $fileRecords += [ordered]@{
            path = $relativePath
            sha256 = Get-FileSha256 $path
        }
    }
}

$installRecord = [ordered]@{
    artifact_id = "harness.install_record"
    artifact_version = "1.0"
    install_result = "pass"
    release_tag = $ReleaseTag
    source_repository = "https://github.com/$Repository"
    target_path = Convert-ToPosixPath $targetRoot
    installed_files = $fileRecords
}
Write-CanonicalJson -PathValue (Join-Path $targetRoot ".harness/evidence/install/INSTALL_RECORD_V1_0.json") -Payload $installRecord

Write-Output "Harness 1.0 installed into $targetRoot"
Write-Output "Next: open this folder in Codex and read .harness/current/status/STATUS_KO.md"
