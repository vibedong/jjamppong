param(
    [string]$TargetPath = (Get-Location).Path,
    [string]$SourcePath = "",
    [ValidateSet("Install", "Update", "Repair")]
    [string]$Mode = "Install",
    [string]$ReleaseUrl = "https://github.com/vibedong/jjamppong/releases/latest",
    [string]$ReleaseTag = "harness-v1.0.1",
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
    $json = $Payload | ConvertTo-Json -Depth 30 -Compress
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

function Get-RuntimeTreeSha256([string]$SourceRoot) {
    $relativeFiles = @(
        "AGENTS.md",
        "install-harness.ps1",
        ".harness/definitions/schemas/handoff-contract.schema.json",
        ".harness/runtime/START_WORKFLOW_KO.md",
        ".harness/runtime/WORKFLOW_RULES_KO.md",
        ".harness/runtime/COMMANDS_KO.md",
        ".harness/runtime/READ_SET_POLICY_KO.md",
        "tools/harness-validator/run-doctor.py",
        "tools/harness-validator/harness_validator/__init__.py",
        "tools/harness-validator/harness_validator/doctor.py",
        "tools/harness-validator/harness_validator/runtime_contract.py"
    )
    $parts = @()
    foreach ($relativePath in $relativeFiles) {
        $path = Join-Path $SourceRoot $relativePath
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $parts += "$relativePath=$(Get-FileSha256 $path)"
        }
    }
    $content = ($parts | Sort-Object) -join "`n"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = $sha.ComputeHash($bytes)
    return (($hash | ForEach-Object { $_.ToString("x2") }) -join "")
}

function Get-SourceCommit([string]$SourceRoot, [string]$Repo, [string]$Tag) {
    try {
        $commit = (git -C $SourceRoot rev-parse HEAD 2>$null)
        if ($commit -match "^[0-9a-f]{40}$") {
            return @{ commit = $commit; status = "resolved_from_local_git" }
        }
    } catch {}
    try {
        $remote = "https://github.com/$Repo.git"
        $line = (git ls-remote --tags $remote "refs/tags/$Tag" 2>$null | Select-Object -First 1)
        if ($line -match "^([0-9a-f]{40})") {
            return @{ commit = $Matches[1]; status = "resolved_from_remote_tag" }
        }
    } catch {}
    return @{ commit = $null; status = "unresolved_with_recorded_asset_hash" }
}

function Expand-HarnessArchive {
    param([string]$ArchivePath, [string]$DestinationPath)
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $destinationFullPath = [System.IO.Path]::GetFullPath($DestinationPath)
    $allowedPrefixes = @(
        "AGENTS.md",
        "README.md",
        "install-harness.ps1",
        ".gitignore",
        ".harness/definitions/",
        ".harness/runtime/",
        "tools/harness-validator/run-doctor.py",
        "tools/harness-validator/harness_validator/"
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
                foreach ($prefix in $allowedPrefixes) {
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

function Get-NormalizedReleaseUrl([string]$UrlValue) {
    if ($UrlValue -match "^github\.com/") {
        return "https://$UrlValue"
    }
    return $UrlValue
}

function Get-SourceRoot {
    param(
        [string]$RequestedSourcePath,
        [string]$RequestedTag,
        [string]$Repo,
        [string]$UrlValue
    )
    if ($RequestedSourcePath -and (Test-Path -LiteralPath $RequestedSourcePath -PathType Container)) {
        return (Resolve-Path -LiteralPath $RequestedSourcePath).Path
    }

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("harness-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    $archivePath = Join-Path $tempRoot "harness-runtime.zip"
    $url = Get-NormalizedReleaseUrl $UrlValue
    if ($url -match "/download/.+\.zip$") {
        $assetUrl = $url
    } else {
        $assetUrl = "https://github.com/$Repo/releases/latest/download/harness-1.0.1-runtime.zip"
    }
    try {
        Invoke-WebRequest -Uri $assetUrl -OutFile $archivePath -UseBasicParsing
    } catch {
        $gh = Get-Command gh -ErrorAction SilentlyContinue
        if (-not $gh) {
            throw "비공개 저장소면 GitHub CLI 설치와 gh auth login이 필요합니다. Public release asset download failed: $($_.Exception.Message)"
        }
        & gh auth status 1>$null 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub 권한 확인이 필요합니다: gh auth login"
        }
        & gh release download $RequestedTag --repo $Repo --pattern "harness-*-runtime.zip" --dir $tempRoot --clobber | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not download Harness release asset with GitHub CLI."
        }
        $downloadedArchive = Get-ChildItem -LiteralPath $tempRoot -Filter "harness-*-runtime.zip" -File | Select-Object -First 1
        if (-not $downloadedArchive) {
            throw "Harness runtime asset was not found after GitHub CLI download."
        }
        $archivePath = $downloadedArchive.FullName
    }
    Expand-HarnessArchive -ArchivePath $archivePath -DestinationPath $tempRoot
    if (-not (Test-Path -LiteralPath (Join-Path $tempRoot "install-harness.ps1") -PathType Leaf)) {
        throw "Harness runtime archive did not contain install-harness.ps1."
    }
    return $tempRoot
}

function Copy-DirectoryContents {
    param([string]$Source, [string]$Target)
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        return
    }
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        $dest = Join-Path $Target $_.Name
        Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse -Force
    }
}

function Copy-HarnessRuntimeFiles {
    param([string]$SourceRoot, [string]$TargetRoot)
    Copy-Item -LiteralPath (Join-Path $SourceRoot "install-harness.ps1") -Destination (Join-Path $TargetRoot "install-harness.ps1") -Force
    Copy-DirectoryContents -Source (Join-Path $SourceRoot ".harness/definitions") -Target (Join-Path $TargetRoot ".harness/definitions")
    Copy-DirectoryContents -Source (Join-Path $SourceRoot ".harness/runtime") -Target (Join-Path $TargetRoot ".harness/runtime")
    Copy-DirectoryContents -Source (Join-Path $SourceRoot "tools/harness-validator") -Target (Join-Path $TargetRoot "tools/harness-validator")
    $testsPath = Join-Path (Join-Path $TargetRoot "tools/harness-validator") "tests"
    if (Test-Path -LiteralPath $testsPath) {
        Remove-Item -LiteralPath $testsPath -Recurse -Force
    }
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
- Use `.harness/runtime/START_WORKFLOW_KO.md` and `.harness/runtime/WORKFLOW_RULES_KO.md` for the project workflow.
- Do not use archive, design history, or validator source as default context.
- Run `python tools/harness-validator/run-doctor.py` before claiming Harness installation or update is complete.
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

function Write-InstalledState {
    param(
        [string]$TargetRoot,
        [string]$SourceRoot,
        [string]$InstallResult,
        [string]$ModeValue,
        [string]$UrlValue,
        [string]$Repo,
        [string]$Tag,
        $PreviousIdentity
    )
    $statusText = @(
        '# Harness 상태',
        '',
        'Harness 1.0 runtime 설치 완료.',
        '',
        '- 현재 단계: R00 Install Check 완료',
        '- 다음 단계: R01 Product Goal Intake',
        '- 다음 행동: 사용자가 만들 제품의 목표를 말하면 먼저 목표와 제약을 정리하고 확인 질문을 만든다.',
        '- 제품 코드 구현: R08 Implementation Start Approval 전까지 금지',
        '- 공식 읽기 시작점: `.harness/manifests/CURRENT_READ_SET.json`'
    ) -join [Environment]::NewLine
    Write-Utf8NoBom -PathValue (Join-Path $TargetRoot ".harness/current/status/STATUS_KO.md") -Content $statusText

    $startHere = @(
        '# Harness 시작',
        '',
        '1. `.harness/current/status/STATUS_KO.md`를 먼저 읽는다.',
        '2. `.harness/manifests/CURRENT_READ_SET.json`의 파일만 우선 읽는다.',
        '3. `.harness/runtime/START_WORKFLOW_KO.md`에 따라 제품 목표를 정리한다.',
        '4. 구현 시작 승인 전에는 제품 코드를 만들지 않는다.'
    ) -join [Environment]::NewLine
    Write-Utf8NoBom -PathValue (Join-Path $TargetRoot ".harness/current/navigation/START_HERE.md") -Content $startHere

    $readSet = [ordered]@{
        artifact_id = "harness.current_read_set"
        artifact_version = "1.0.1"
        stage = "installed_project_start"
        language = "ko"
        paths = @(
            [ordered]@{ path = ".harness/current/status/STATUS_KO.md"; purpose_ko = "현재 상태" },
            [ordered]@{ path = ".harness/current/navigation/START_HERE.md"; purpose_ko = "시작 안내" },
            [ordered]@{ path = ".harness/runtime/START_WORKFLOW_KO.md"; purpose_ko = "workflow 시작 규칙" },
            [ordered]@{ path = ".harness/runtime/WORKFLOW_RULES_KO.md"; purpose_ko = "stage 순서와 금지선" },
            [ordered]@{ path = ".harness/runtime/READ_SET_POLICY_KO.md"; purpose_ko = "xhigh read set 정책" },
            [ordered]@{ path = ".harness/current/source_identity/SOURCE_IDENTITY.json"; purpose_ko = "설치 출처" }
        )
    }
    Write-CanonicalJson -PathValue (Join-Path $TargetRoot ".harness/manifests/CURRENT_READ_SET.json") -Payload $readSet

    $commitInfo = Get-SourceCommit -SourceRoot $SourceRoot -Repo $Repo -Tag $Tag
    $identity = [ordered]@{
        artifact_id = "harness.installed_source_identity"
        artifact_version = "1.0.1"
        source_repository = "https://github.com/$Repo"
        release_url = (Get-NormalizedReleaseUrl $UrlValue)
        release_tag = $Tag
        source_commit = $commitInfo.commit
        source_commit_status = $commitInfo.status
        installer_sha256 = Get-FileSha256 (Join-Path $TargetRoot "install-harness.ps1")
        runtime_asset_sha256 = Get-RuntimeTreeSha256 $SourceRoot
        install_mode = $ModeValue
        install_result = $InstallResult
        installed_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        install_root = Convert-ToPosixPath $TargetRoot
        previous_identity = $PreviousIdentity
    }
    Write-CanonicalJson -PathValue (Join-Path $TargetRoot ".harness/current/source_identity/SOURCE_IDENTITY.json") -Payload $identity

    $installRecord = [ordered]@{
        artifact_id = "harness.install_record"
        artifact_version = "1.0.1"
        install_result = $InstallResult
        install_mode = $ModeValue
        release_tag = $Tag
        source_repository = "https://github.com/$Repo"
        target_path = Convert-ToPosixPath $TargetRoot
        recorded_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    Write-CanonicalJson -PathValue (Join-Path $TargetRoot ".harness/evidence/install/INSTALL_RECORD_V1_0.json") -Payload $installRecord
}

if (-not (Test-Path -LiteralPath $TargetPath -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $TargetPath | Out-Null
}
$targetRoot = (Resolve-Path -LiteralPath $TargetPath).Path
$sourceRoot = Get-SourceRoot -RequestedSourcePath $SourcePath -RequestedTag $ReleaseTag -Repo $Repository -UrlValue $ReleaseUrl

New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/status") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/navigation") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/source_identity") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/manifests") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/evidence/install") | Out-Null

$identityPath = Join-Path $targetRoot ".harness/current/source_identity/SOURCE_IDENTITY.json"
$previousIdentity = $null
if (Test-Path -LiteralPath $identityPath -PathType Leaf) {
    try {
        $previousIdentity = Get-Content -Raw -LiteralPath $identityPath | ConvertFrom-Json
    } catch {
        $previousIdentity = $null
    }
}

$sameVersion = $false
if ($previousIdentity -and $previousIdentity.release_tag -eq $ReleaseTag) {
    $sameVersion = $true
}

if (($Mode -eq "Install" -or $Mode -eq "Update") -and $sameVersion) {
    Install-AgentsRouter -TargetRoot $targetRoot
    Write-InstalledState -TargetRoot $targetRoot -SourceRoot $sourceRoot -InstallResult "already_up_to_date" -ModeValue $Mode -UrlValue $ReleaseUrl -Repo $Repository -Tag $ReleaseTag -PreviousIdentity $previousIdentity
    Write-Output "already_up_to_date"
    exit 0
}

Copy-HarnessRuntimeFiles -SourceRoot $sourceRoot -TargetRoot $targetRoot
Install-AgentsRouter -TargetRoot $targetRoot

$result = "installed"
if ($Mode -eq "Update") {
    $result = "updated"
} elseif ($Mode -eq "Repair") {
    $result = "repaired"
}

Write-InstalledState -TargetRoot $targetRoot -SourceRoot $sourceRoot -InstallResult $result -ModeValue $Mode -UrlValue $ReleaseUrl -Repo $Repository -Tag $ReleaseTag -PreviousIdentity $previousIdentity

Write-Output $result
Write-Output "Harness 1.0 runtime is ready in $targetRoot"
Write-Output "Next: run python tools/harness-validator/run-doctor.py"
