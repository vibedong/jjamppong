param(
    [string]$TargetPath = (Get-Location).Path,
    [string]$SourcePath = "",
    [ValidateSet("Preview", "Install", "Update", "Repair")]
    [string]$Mode = "Install",
    [string]$ReleaseUrl = "https://github.com/vibedong/jjamppong/releases/latest",
    [string]$ReleaseTag = "harness-v1.0.3",
    [string]$Repository = "vibedong/jjamppong",
    [string]$OutputPreviewPath = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Convert-ToPosixPath([string]$PathValue) {
    return ($PathValue -replace "\\", "/")
}

function Get-UtcIso() {
    return (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}

function Write-Utf8NoBom([string]$PathValue, [string]$Content) {
    $parent = Split-Path -Parent $PathValue
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($PathValue, $Content, $encoding)
}

function Write-CanonicalJson([string]$PathValue, [object]$Payload) {
    $json = $Payload | ConvertTo-Json -Depth 30 -Compress
    Write-Utf8NoBom -PathValue $PathValue -Content ($json + "`n")
}

function ConvertTo-CanonicalJsonString([object]$Payload) {
    return (($Payload | ConvertTo-Json -Depth 30 -Compress) + "`n")
}

function Get-FileSha256([string]$PathValue) {
    if (-not (Test-Path -LiteralPath $PathValue -PathType Leaf)) {
        return $null
    }
    $stream = [System.IO.File]::OpenRead($PathValue)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $bytes = $sha.ComputeHash($stream)
        return (($bytes | ForEach-Object { $_.ToString("x2") }) -join "")
    } finally {
        $stream.Dispose()
    }
}

function Get-StringSha256([string]$Value) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = $sha.ComputeHash($bytes)
    return (($hash | ForEach-Object { $_.ToString("x2") }) -join "")
}

function Get-RuntimeFileList([string]$SourceRoot) {
    $sourceFullPath = [System.IO.Path]::GetFullPath($SourceRoot)
    $files = Get-ChildItem -LiteralPath $sourceFullPath -Recurse -File -Force |
        Where-Object {
            $rel = $_.FullName.Substring($sourceFullPath.Length + 1).Replace("\", "/")
            -not (
                $rel.StartsWith(".git/") -or
                $rel.StartsWith("tests/") -or
                $rel.StartsWith("docs/") -or
                $rel.StartsWith("_organized_harness_design/") -or
                $rel.StartsWith(".release-worktrees/") -or
                $rel.StartsWith(".worktrees/") -or
                $rel -eq ".gitignore"
            )
        }
    return @($files | ForEach-Object { $_.FullName.Substring($sourceFullPath.Length + 1).Replace("\", "/") } | Sort-Object)
}

function Get-RuntimeTreeSha256([string]$SourceRoot) {
    $parts = @()
    foreach ($relativePath in Get-RuntimeFileList $SourceRoot) {
        $path = Join-Path $SourceRoot $relativePath
        $parts += "$relativePath=$(Get-FileSha256 $path)"
    }
    return Get-StringSha256 (($parts | Sort-Object) -join "`n")
}

function Get-NormalizedReleaseUrl([string]$ReleaseUrl) {
    if ([string]::IsNullOrWhiteSpace($ReleaseUrl)) { return $null }
    $trimmed = $ReleaseUrl.Trim()
    if ($trimmed -match '^github\.com/') { return "https://$trimmed" }
    if ($trimmed -match '^https://github\.com/') { return $trimmed }
    throw "Unsupported release URL: $ReleaseUrl"
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
        ".agents/skills/",
        ".harness/definitions/",
        ".harness/runtime/",
        "tools/harness-validator/run-doctor.py",
        "tools/harness-validator/run-bootstrap-entry-audit.py",
        "tools/harness-validator/run-gate-close-verification.py",
        "tools/harness-validator/run-e2e-scenario.py",
        "tools/harness-validator/harness_validator/"
    )
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        foreach ($entry in $zip.Entries) {
            if ([string]::IsNullOrWhiteSpace($entry.FullName)) { continue }
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
                if ($relativeName) { break }
            }
            if (-not $relativeName) { continue }
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
        $assetVersion = $RequestedTag -replace "^harness-v", ""
        $assetUrl = "https://github.com/$Repo/releases/latest/download/harness-$assetVersion-runtime.zip"
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
    Copy-DirectoryContents -Source (Join-Path $SourceRoot ".agents/skills") -Target (Join-Path $TargetRoot ".agents/skills")
    Copy-DirectoryContents -Source (Join-Path $SourceRoot ".harness/definitions") -Target (Join-Path $TargetRoot ".harness/definitions")
    Copy-DirectoryContents -Source (Join-Path $SourceRoot ".harness/runtime") -Target (Join-Path $TargetRoot ".harness/runtime")
    $validatorTarget = Join-Path $TargetRoot "tools/harness-validator"
    if (Test-Path -LiteralPath $validatorTarget) {
        Remove-Item -LiteralPath $validatorTarget -Recurse -Force
    }
    Copy-DirectoryContents -Source (Join-Path $SourceRoot "tools/harness-validator") -Target (Join-Path $TargetRoot "tools/harness-validator")
    foreach ($remove in @("tests", "__pycache__")) {
        $removePath = Join-Path $validatorTarget $remove
        if (Test-Path -LiteralPath $removePath) {
            Remove-Item -LiteralPath $removePath -Recurse -Force
        }
    }
    Get-ChildItem -LiteralPath $validatorTarget -Directory -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
    Get-ChildItem -LiteralPath $validatorTarget -File -Recurse -Force -Include "*.pyc","*.pyo" -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
}

function Test-RuntimeComplete {
    param([string]$TargetRoot)
    $required = @(
        "AGENTS.md",
        "install-harness.ps1",
        ".agents/skills/harness-workflow-router/SKILL.md",
        ".harness/current/status/STATUS_KO.md",
        ".harness/current/navigation/START_HERE.md",
        ".harness/current/source_identity/SOURCE_IDENTITY.json",
        ".harness/manifests/CURRENT_READ_SET.json",
        ".harness/runtime/START_WORKFLOW_KO.md",
        ".harness/runtime/WORKFLOW_RULES_KO.md",
        ".harness/runtime/COMMANDS_KO.md",
        ".harness/runtime/READ_SET_POLICY_KO.md",
        "tools/harness-validator/run-doctor.py",
        "tools/harness-validator/harness_validator/doctor.py",
        "tools/harness-validator/harness_validator/runtime_contract.py"
    )
    foreach ($relativePath in $required) {
        if (-not (Test-Path -LiteralPath (Join-Path $TargetRoot $relativePath) -PathType Leaf)) {
            return $false
        }
    }
    return $true
}

function Get-AgentsHarnessBlock() {
    return @'
<!-- harness:start -->
# Harness Router

- Read `.harness/current/status/STATUS_KO.md` first.
- Read `.harness/manifests/CURRENT_READ_SET.json` for the current stage read set.
- Treat `.harness/current/source_identity/SOURCE_IDENTITY.json` as the local source identity pointer.
- Use `.agents/skills/harness-workflow-router/SKILL.md` to route the current stage.
- Use `.harness/runtime/START_WORKFLOW_KO.md` and `.harness/runtime/WORKFLOW_RULES_KO.md` for the project workflow.
- Do not use archive, design history, or validator source as default context.
- Run `python tools/harness-validator/run-doctor.py --mode installed-project .` before claiming Harness installation or update is complete.
<!-- harness:end -->
'@
}

function Install-AgentsRouter {
    param([string]$TargetRoot)
    $agentsPath = Join-Path $TargetRoot "AGENTS.md"
    $backupDir = Join-Path $TargetRoot ".harness/evidence/install/backups"
    $block = Get-AgentsHarnessBlock
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

function Get-GitState([string]$TargetRoot) {
    if (-not (Test-Path -LiteralPath (Join-Path $TargetRoot ".git"))) { return "not_git" }
    $status = git -C $TargetRoot status --porcelain 2>$null
    if ($LASTEXITCODE -ne 0) { return "git_unreadable" }
    if ($status) { return "dirty" }
    return "clean"
}

function Invoke-GitCapture([string]$TargetRoot, [string[]]$GitArgs) {
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git -C $TargetRoot @GitArgs 2>$null
        return @{ output = @($output); code = $LASTEXITCODE }
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

function Convert-GitPorcelainPaths($Lines) {
    $paths = @()
    foreach ($line in @($Lines)) {
        if (-not $line) { continue }
        if ($line.Length -ge 4) {
            $paths += $line.Substring(3).Replace("\", "/")
        } else {
            $paths += $line.Replace("\", "/")
        }
    }
    return $paths
}

function Test-SecretCandidate([string]$RelativePath) {
    $lower = $RelativePath.ToLowerInvariant()
    foreach ($marker in @(".env", "secret", "token", "password", "credential", "recovery")) {
        if ($lower.Contains($marker)) { return $true }
    }
    return $false
}

function Get-PreviewFileAction([string]$TargetRoot, [string]$SourceRoot, [string]$RelativePath) {
    $target = Join-Path $TargetRoot $RelativePath
    $source = Join-Path $SourceRoot $RelativePath
    $exists = Test-Path -LiteralPath $target -PathType Leaf
    $action = "create"
    $merge = "none"
    $reason = "target_missing"
    if ($exists) {
        if ($RelativePath -eq "AGENTS.md") {
            $action = "merge_harness_block"
            $merge = "harness_block_replace"
            $reason = "preserve_user_instructions_and_replace_harness_block"
        } else {
            $action = "replace_harness_block"
            $merge = "backup_then_replace"
            $reason = "runtime_owned_file_exists"
        }
    }
    return [ordered]@{
        relative_path = $RelativePath
        action = $action
        reason = $reason
        existing_sha256 = if ($exists) { Get-FileSha256 $target } else { $null }
        new_sha256 = if (Test-Path -LiteralPath $source -PathType Leaf) { Get-FileSha256 $source } elseif ($RelativePath -eq "AGENTS.md") { Get-StringSha256 (Get-AgentsHarnessBlock) } else { $null }
        backup_path = if ($exists) { ".harness/evidence/install/backups/$RelativePath.bak" } else { $null }
        merge_strategy = $merge
        requires_user_choice = $false
    }
}

function Invoke-Preview([string]$TargetRoot, [string]$SourceRoot) {
    $hardBlockers = @()
    if (Test-Path -LiteralPath $TargetRoot -PathType Container) {
        Get-ChildItem -LiteralPath $TargetRoot -Force -Recurse -File |
            Where-Object {
                $rel = $_.FullName.Substring([System.IO.Path]::GetFullPath($TargetRoot).Length + 1).Replace("\", "/")
                ($rel -notmatch "^\.git/") -and (Test-SecretCandidate $rel)
            } |
            ForEach-Object {
                $rel = $_.FullName.Substring([System.IO.Path]::GetFullPath($TargetRoot).Length + 1).Replace("\", "/")
                $hardBlockers += [ordered]@{ code = "installer.secret_candidate_present"; path = $rel; severity = "hard_blocker" }
            }
    }
    $actions = @()
    foreach ($relativePath in @("AGENTS.md", "install-harness.ps1", ".harness/runtime/START_WORKFLOW_KO.md", ".harness/runtime/WORKFLOW_RULES_KO.md", ".harness/runtime/COMMANDS_KO.md", ".harness/runtime/READ_SET_POLICY_KO.md", "tools/harness-validator/run-doctor.py")) {
        $actions += Get-PreviewFileAction -TargetRoot $TargetRoot -SourceRoot $SourceRoot -RelativePath $relativePath
    }
    $preview = [ordered]@{
        schema_version = "1.0"
        harness_release = "harness-v1.0.3"
        mode = "Preview"
        target_path = Convert-ToPosixPath ([System.IO.Path]::GetFullPath($TargetRoot))
        target_git_state = Get-GitState $TargetRoot
        detected_existing_harness_version = $null
        file_actions = $actions
        hard_blockers = $hardBlockers
        warnings = @()
        requires_user_choice = $false
        korean_summary = if ($hardBlockers.Count -gt 0) { "secret 후보 파일이 있어 설치 전 확인이 필요합니다." } else { "설치 가능 상태입니다." }
        created_at_utc = Get-UtcIso
    }
    $json = ConvertTo-CanonicalJsonString $preview
    if ($OutputPreviewPath) {
        Write-Utf8NoBom -PathValue $OutputPreviewPath -Content $json
    }
    Write-Output $json
}

function Write-SourceIdentityEvidence([string]$TargetRoot, [string]$ReleaseUrl, [string]$ModeValue) {
    $normalized = Get-NormalizedReleaseUrl $ReleaseUrl
    $path = Join-Path $TargetRoot ".harness/evidence/source-identity/HARNESS_SOURCE_IDENTITY.json"
    Write-CanonicalJson -PathValue $path -Payload ([ordered]@{
        schema_version = "1.0"
        requested_release_url = $ReleaseUrl
        normalized_release_url = $normalized
        resolution_mode = if ($normalized) { "github_release_url" } else { "local_source_path" }
        install_mode = $ModeValue
        release_tag = "harness-v1.0.3"
        source_archive_sha256 = $null
        resolved_at_utc = Get-UtcIso
    })
}

function Write-GitBaselineEvidence([string]$TargetRoot, [bool]$CreateBaselineCommit = $false, [bool]$CreateBaselineTag = $false) {
    $dir = Join-Path $TargetRoot ".harness/evidence/git"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $path = Join-Path $dir "GIT_BASELINE_RECORD_$timestamp.json"
    $status = "not_required"
    $commit = $null
    $preApplyHead = $null
    $postApplyHead = $null
    $remoteVerified = $false
    $dirtyBefore = @()
    $dirtyAfter = @()
    $remoteUrlPresent = $false
    $baselineTag = $null
    $nextAction = "run_git_init_or_confirm_non_git"
    if (Test-Path -LiteralPath (Join-Path $TargetRoot ".git")) {
        $headResult = Invoke-GitCapture -TargetRoot $TargetRoot -GitArgs @("rev-parse", "HEAD")
        if ($headResult.code -eq 0 -and $headResult.output.Count -gt 0 -and $headResult.output[0] -match "^[0-9a-f]{40}$") {
            $preApplyHead = $headResult.output[0]
            $commit = $preApplyHead
        }
        $dirtyBefore = Convert-GitPorcelainPaths @(git -C $TargetRoot status --porcelain 2>$null)
        $nameResult = Invoke-GitCapture -TargetRoot $TargetRoot -GitArgs @("config", "user.name")
        $emailResult = Invoke-GitCapture -TargetRoot $TargetRoot -GitArgs @("config", "user.email")
        $name = if ($nameResult.code -eq 0 -and $nameResult.output.Count -gt 0) { $nameResult.output[0] } else { $null }
        $email = if ($emailResult.code -eq 0 -and $emailResult.output.Count -gt 0) { $emailResult.output[0] } else { $null }
        if (-not $name -or -not $email) {
            $status = "skipped_no_git_identity"
            $nextAction = "verify_remote_before_implementation_entry"
        } elseif ($dirtyBefore -and -not $CreateBaselineCommit) {
            $status = "skipped_user_declined"
            $nextAction = "verify_remote_before_implementation_entry"
        } elseif ($dirtyBefore -and $CreateBaselineCommit) {
            git -C $TargetRoot add -A | Out-Null
            git -C $TargetRoot commit -m "chore: establish Harness install baseline" | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $newHeadResult = Invoke-GitCapture -TargetRoot $TargetRoot -GitArgs @("rev-parse", "HEAD")
                $commit = if ($newHeadResult.code -eq 0 -and $newHeadResult.output.Count -gt 0) { $newHeadResult.output[0] } else { $null }
                $status = "created"
                if ($CreateBaselineTag) {
                    $baselineTag = "harness-install-baseline-v1-0-3"
                    git -C $TargetRoot tag $baselineTag $commit 2>$null | Out-Null
                }
                $nextAction = "verify_remote_before_implementation_entry"
            } else {
                $status = "failed"
                $nextAction = "fix_git_baseline_commit_failure"
            }
        } elseif ($commit -match "^[0-9a-f]{40}$") {
            $status = "remote_unverified"
            $nextAction = "verify_remote_before_implementation_entry"
            $remoteResult = Invoke-GitCapture -TargetRoot $TargetRoot -GitArgs @("remote")
            $remoteUrlPresent = ($remoteResult.code -eq 0 -and $remoteResult.output.Count -gt 0)
            if ($remoteUrlPresent) {
                git -C $TargetRoot ls-remote --exit-code origin $commit 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    $remoteVerified = $true
                    $status = "verified"
                    $nextAction = "none"
                }
            }
        } else {
            $status = "failed"
            $nextAction = "fix_git_baseline_commit_failure"
        }
        $postHeadResult = Invoke-GitCapture -TargetRoot $TargetRoot -GitArgs @("rev-parse", "HEAD")
        if ($postHeadResult.code -eq 0 -and $postHeadResult.output.Count -gt 0 -and $postHeadResult.output[0] -match "^[0-9a-f]{40}$") {
            $postApplyHead = $postHeadResult.output[0]
        }
        $dirtyAfter = Convert-GitPorcelainPaths @(git -C $TargetRoot status --porcelain 2>$null)
    }
    Write-CanonicalJson -PathValue $path -Payload ([ordered]@{
        repository_state = (Get-GitState $TargetRoot)
        pre_apply_head = $preApplyHead
        post_apply_head = $postApplyHead
        baseline_commit = $commit
        baseline_tag = $baselineTag
        remote_url_present = $remoteUrlPresent
        remote_push_verified = $remoteVerified
        dirty_files_before_apply = $dirtyBefore
        dirty_files_after_apply = $dirtyAfter
        baseline_commit_status = $status
        user_refusal_reason = $null
        next_required_action = $nextAction
    })
}

function Get-LegacyStage([string]$TargetRoot) {
    $statusPath = Join-Path $TargetRoot ".harness/current/status/STATUS_KO.md"
    if (-not (Test-Path -LiteralPath $statusPath)) { return $null }
    $text = Get-Content -LiteralPath $statusPath -Raw -Encoding UTF8
    if ($text.Contains("Stage set version: harness-stage-set-v1.0.3")) { return $null }
    if ($text -match "R06") { return "R06" }
    if ($text -match "R07") { return "R07" }
    if ($text -match "R08") { return "R08" }
    return $null
}

function Get-MigrationBlockedTransition([string]$LegacyStage) {
    switch ($LegacyStage) {
        "R06" { return "R06 Development Plan cannot become R07 automatically because R06 Technical Architecture is missing" }
        "R07" { return "R07 Work Units cannot become R08 automatically because Technical Architecture insertion requires Development Plan and Work Units revalidation" }
        "R08" { return "R08 Implementation Start Approval is stale until Technical Architecture, Development Plan, and Work Units are revalidated" }
        default { return $null }
    }
}

function Apply-StageSetMigrationIfNeeded([string]$TargetRoot) {
    $legacyStage = Get-LegacyStage $TargetRoot
    if (-not $legacyStage) { return $false }
    $evidencePath = Join-Path $TargetRoot ".harness/evidence/migration/WORKFLOW_STAGE_SET_MIGRATION_NEEDED_V1_0_3.json"
    $statusPath = Join-Path $TargetRoot ".harness/current/status/STATUS_KO.md"
    $legacyArtifacts = @()
    foreach ($candidate in @(".harness/current/planning/DEVELOPMENT_PLAN.md", ".harness/current/planning/WORK_UNITS.md", ".harness/current/planning/IMPLEMENTATION_START_APPROVAL_REQUEST.md")) {
        if (Test-Path -LiteralPath (Join-Path $TargetRoot $candidate)) { $legacyArtifacts += $candidate }
    }
    $blockedTransition = Get-MigrationBlockedTransition $legacyStage
    Write-CanonicalJson -PathValue $evidencePath -Payload ([ordered]@{
        artifact_id = "workflow_stage_set_migration_needed.v1.0.3"
        from_stage_set_version = "harness-stage-set-v1.0.2"
        to_stage_set_version = "harness-stage-set-v1.0.3"
        detected_stage = $legacyStage
        legacy_artifacts = $legacyArtifacts
        blocked_transitions = @($blockedTransition)
        required_user_action = "review_migration"
        status = "user_review_required"
        created_at_utc = Get-UtcIso
    })
    $statusText = Get-Content -LiteralPath $statusPath -Raw -Encoding UTF8
    if (-not $statusText.Contains("Implementation Entry Gate: closed")) {
        $statusText = $statusText.TrimEnd() + "`nImplementation Entry Gate: closed`n"
    }
    if (-not $statusText.Contains("harness-stage-set-v1.0.3 migration review required")) {
        $statusText = $statusText.TrimEnd() + "`n`n- harness-stage-set-v1.0.3 migration review required: $legacyStage state is preserved and cannot auto-advance. $blockedTransition`n"
    }
    Write-Utf8NoBom -PathValue $statusPath -Content $statusText
    return $true
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
        $PreviousIdentity,
        [switch]$PreserveCurrentState
    )
    $startHere = @(
        '# Harness 시작',
        '',
        '1. `.harness/current/status/STATUS_KO.md`를 먼저 읽는다.',
        '2. `.harness/manifests/CURRENT_READ_SET.json`의 파일만 우선 읽는다.',
        '3. `.agents/skills/harness-workflow-router/SKILL.md`로 현재 단계 skill을 고른다.',
        '4. `.harness/runtime/START_WORKFLOW_KO.md`에 따라 제품 목표를 정리한다.',
        '5. 구현 시작 승인 전에는 제품 코드를 만들지 않는다.'
    ) -join [Environment]::NewLine
    $startHerePath = Join-Path $TargetRoot ".harness/current/navigation/START_HERE.md"
    if ((-not $PreserveCurrentState) -or (-not (Test-Path -LiteralPath $startHerePath -PathType Leaf))) {
        Write-Utf8NoBom -PathValue $startHerePath -Content $startHere
    }

    if (-not $PreserveCurrentState) {
        $statusText = @(
            '# Harness 상태',
            '',
            'Harness version: harness-v1.0.3',
            'Stage set version: harness-stage-set-v1.0.3',
            'Current stage: R01 Product Goal',
            'Implementation Entry Gate: closed',
            'Migration status: not_needed',
            '',
            '다음 행동: 사용자가 만들 제품의 목표를 말하면 먼저 제품 목표, 성공 기준, 제약, 확인 질문을 정리한다.',
            '제품 코드 구현: R09 Implementation Entry 승인 전까지 금지',
            '공식 읽기 시작점: `.harness/manifests/CURRENT_READ_SET.json`'
        ) -join [Environment]::NewLine
        Write-Utf8NoBom -PathValue (Join-Path $TargetRoot ".harness/current/status/STATUS_KO.md") -Content $statusText

        $readSet = [ordered]@{
            artifact_id = "harness.current_read_set"
            artifact_version = "1.0.3"
            schema_version = "1.0"
            stage = "R01"
            stage_set_version = "harness-stage-set-v1.0.3"
            language = "ko"
            paths = @(
                [ordered]@{ path = ".harness/current/status/STATUS_KO.md"; purpose_ko = "현재 상태" },
                [ordered]@{ path = ".harness/current/navigation/START_HERE.md"; purpose_ko = "시작 안내" },
                [ordered]@{ path = ".agents/skills/harness-workflow-router/SKILL.md"; purpose_ko = "현재 단계 skill 선택" },
                [ordered]@{ path = ".agents/skills/harness-r01-product-goal/SKILL.md"; purpose_ko = "R01 제품 목표 정리 skill" },
                [ordered]@{ path = ".harness/definitions/stage-contracts/R01_PRODUCT_GOAL_CONTRACT.md"; purpose_ko = "R01 단계 계약" },
                [ordered]@{ path = ".harness/runtime/START_WORKFLOW_KO.md"; purpose_ko = "workflow 시작 규칙" },
                [ordered]@{ path = ".harness/runtime/READ_SET_POLICY_KO.md"; purpose_ko = "xhigh read set 정책" },
                [ordered]@{ path = ".harness/current/source_identity/SOURCE_IDENTITY.json"; purpose_ko = "설치 출처" }
            )
        }
        Write-CanonicalJson -PathValue (Join-Path $TargetRoot ".harness/manifests/CURRENT_READ_SET.json") -Payload $readSet
    }

    $commitInfo = Get-SourceCommit -SourceRoot $SourceRoot -Repo $Repo -Tag $Tag
    $previousIdentitySummary = $null
    if ($PreviousIdentity) {
        $previousIdentitySummary = [ordered]@{
            release_tag = $PreviousIdentity.release_tag
            source_commit = $PreviousIdentity.source_commit
            source_commit_status = $PreviousIdentity.source_commit_status
            installer_sha256 = $PreviousIdentity.installer_sha256
            runtime_asset_sha256 = $PreviousIdentity.runtime_asset_sha256
            install_result = $PreviousIdentity.install_result
            installed_at_utc = $PreviousIdentity.installed_at_utc
        }
    }

    $identity = [ordered]@{
        artifact_id = "harness.installed_source_identity"
        artifact_version = "1.0.3"
        source_repository = "https://github.com/$Repo"
        release_url = (Get-NormalizedReleaseUrl $UrlValue)
        release_tag = $Tag
        source_commit = $commitInfo.commit
        source_commit_status = $commitInfo.status
        installer_sha256 = Get-FileSha256 (Join-Path $TargetRoot "install-harness.ps1")
        runtime_asset_sha256 = Get-RuntimeTreeSha256 $SourceRoot
        install_mode = $ModeValue
        install_result = $InstallResult
        installed_at_utc = Get-UtcIso
        install_root = Convert-ToPosixPath $TargetRoot
        previous_identity = $previousIdentitySummary
    }
    Write-CanonicalJson -PathValue (Join-Path $TargetRoot ".harness/current/source_identity/SOURCE_IDENTITY.json") -Payload $identity

    $installRecord = [ordered]@{
        artifact_id = "harness.install_record"
        artifact_version = "1.0.3"
        install_result = $InstallResult
        install_mode = $ModeValue
        release_tag = $Tag
        source_repository = "https://github.com/$Repo"
        target_path = Convert-ToPosixPath $TargetRoot
        recorded_at_utc = Get-UtcIso
    }
    Write-CanonicalJson -PathValue (Join-Path $TargetRoot ".harness/evidence/install/INSTALL_RECORD_V1_0.json") -Payload $installRecord
}

if (-not (Test-Path -LiteralPath $TargetPath -PathType Container)) {
    if ($Mode -eq "Preview") {
        $targetRoot = [System.IO.Path]::GetFullPath($TargetPath)
    } else {
        New-Item -ItemType Directory -Force -Path $TargetPath | Out-Null
        $targetRoot = (Resolve-Path -LiteralPath $TargetPath).Path
    }
} else {
    $targetRoot = (Resolve-Path -LiteralPath $TargetPath).Path
}

$sourceRoot = Get-SourceRoot -RequestedSourcePath $SourcePath -RequestedTag $ReleaseTag -Repo $Repository -UrlValue $ReleaseUrl

if ($Mode -eq "Preview") {
    Invoke-Preview -TargetRoot $targetRoot -SourceRoot $sourceRoot
    exit 0
}

New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/status") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/navigation") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/current/source_identity") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/manifests") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $targetRoot ".harness/evidence/install") | Out-Null

$identityPath = Join-Path $targetRoot ".harness/current/source_identity/SOURCE_IDENTITY.json"
$statusPath = Join-Path $targetRoot ".harness/current/status/STATUS_KO.md"
$readSetPath = Join-Path $targetRoot ".harness/manifests/CURRENT_READ_SET.json"
$preserveCurrentState = (
    (Test-Path -LiteralPath $statusPath -PathType Leaf) -and
    (Test-Path -LiteralPath $readSetPath -PathType Leaf)
)
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

Write-SourceIdentityEvidence -TargetRoot $targetRoot -ReleaseUrl $ReleaseUrl -ModeValue $Mode

if (($Mode -eq "Install" -or $Mode -eq "Update") -and $sameVersion -and (Test-RuntimeComplete $targetRoot)) {
    Install-AgentsRouter -TargetRoot $targetRoot
    Write-InstalledState -TargetRoot $targetRoot -SourceRoot $sourceRoot -InstallResult "already_up_to_date" -ModeValue $Mode -UrlValue $ReleaseUrl -Repo $Repository -Tag $ReleaseTag -PreviousIdentity $previousIdentity -PreserveCurrentState:$preserveCurrentState
    if ($Mode -eq "Update") {
        Apply-StageSetMigrationIfNeeded -TargetRoot $targetRoot | Out-Null
    }
    Write-GitBaselineEvidence -TargetRoot $targetRoot
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

Write-InstalledState -TargetRoot $targetRoot -SourceRoot $sourceRoot -InstallResult $result -ModeValue $Mode -UrlValue $ReleaseUrl -Repo $Repository -Tag $ReleaseTag -PreviousIdentity $previousIdentity -PreserveCurrentState:$preserveCurrentState

if ($Mode -eq "Update" -or $Mode -eq "Repair") {
    Apply-StageSetMigrationIfNeeded -TargetRoot $targetRoot | Out-Null
}

Write-GitBaselineEvidence -TargetRoot $targetRoot

Write-Output $result
Write-Output "Harness 1.0.3 runtime is ready in $targetRoot"
Write-Output "Next: run python tools/harness-validator/run-doctor.py --mode installed-project ."
