param(
    [Parameter(Position = 0)]
    [string]$Command = "doctor",
    [ValidateSet("installed", "release_candidate")]
    [string]$Mode = "installed"
)

$ErrorActionPreference = "Stop"

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

function Add-Violation {
    param([System.Collections.ArrayList]$List, [string]$Value)
    [void]$List.Add($Value)
}

function Get-RuntimeArtifactSha256 {
    param([string]$Root, [array]$RuntimePaths)
    $excluded = @(
        ".harness/current/source/SOURCE_IDENTITY.json",
        ".harness/current/status/STATUS_KO.md",
        ".harness/current/readsets/CURRENT_READ_SET.json",
        ".harness/improvement/BACKLOG.md",
        ".harness/improvement/BACKLOG.jsonl"
    )
    $paths = [string[]]$RuntimePaths
    [System.Array]::Sort($paths, [System.StringComparer]::Ordinal)
    $rows = @()
    foreach ($rel in $paths) {
        if ($excluded -contains $rel) { continue }
        $file = Join-Path $Root $rel
        if (Test-Path -LiteralPath $file -PathType Leaf) {
            $rows += "$rel=$(Get-FileSha256 -Path $file)"
        }
    }
    return Get-StringSha256 -Text (($rows -join "`n") + "`n")
}

function Invoke-Doctor {
    param([string]$Root, [string]$DoctorMode)

    $missing = New-Object System.Collections.ArrayList
    $coverageViolations = New-Object System.Collections.ArrayList
    $releaseSurfaceViolations = New-Object System.Collections.ArrayList
    $readSetViolations = New-Object System.Collections.ArrayList
    $sourceIdentityViolations = New-Object System.Collections.ArrayList
    $forbiddenFirstTurnTargets = New-Object System.Collections.ArrayList
    $readSetTotalBytes = 0

    $coveragePath = Join-Path $Root ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json"
    $runtimePaths = @()
    if (-not (Test-Path -LiteralPath $coveragePath -PathType Leaf)) {
        Add-Violation $missing ".harness/runtime/coverage/RELEASE_COVERAGE_UNIVERSE.json"
    } else {
        try {
            $coverage = Get-Content -LiteralPath $coveragePath -Raw -Encoding UTF8 | ConvertFrom-Json
            $runtimePaths = [string[]]$coverage.runtime_paths
            $sorted = [string[]]$runtimePaths
            [System.Array]::Sort($sorted, [System.StringComparer]::Ordinal)
            $actualHash = Get-StringSha256 -Text (($sorted -join "`n") + "`n")
            if ($actualHash -ne ([string]$coverage.runtime_paths_sha256).ToLowerInvariant()) {
                Add-Violation $coverageViolations "runtime_paths_sha256_mismatch"
            }
            foreach ($rel in $runtimePaths) {
                if ($rel.EndsWith("/") -or $rel.StartsWith("tests/") -or $rel.StartsWith("tools/") -or $rel.StartsWith("docs/") -or $rel.StartsWith("_organized_harness_design/") -or $rel.StartsWith("PRIVATE_HARNESS_CONTEXT/")) {
                    Add-Violation $coverageViolations $rel
                }
                if (-not (Test-Path -LiteralPath (Join-Path $Root $rel) -PathType Leaf)) {
                    Add-Violation $missing $rel
                }
            }
        } catch {
            Add-Violation $coverageViolations "coverage_parse_error: $($_.Exception.Message)"
        }
    }

    $readSetPath = Join-Path $Root ".harness/current/readsets/CURRENT_READ_SET.json"
    if (-not (Test-Path -LiteralPath $readSetPath -PathType Leaf)) {
        Add-Violation $missing ".harness/current/readsets/CURRENT_READ_SET.json"
    } else {
        try {
            $readSet = Get-Content -LiteralPath $readSetPath -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($item in @($readSet.paths)) {
                $rel = [string]$item.path
                if ($rel.EndsWith("/") -or $rel.StartsWith("tests/") -or $rel.StartsWith("tools/") -or $rel.StartsWith("_organized_harness_design/")) {
                    Add-Violation $readSetViolations $rel
                    Add-Violation $forbiddenFirstTurnTargets $rel
                }
                $file = Join-Path $Root $rel
                if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
                    Add-Violation $readSetViolations "missing:$rel"
                } else {
                    $readSetTotalBytes += (Get-Item -LiteralPath $file).Length
                }
            }
            if ($readSetTotalBytes -gt 20480) {
                Add-Violation $readSetViolations "read_set_over_20k"
            }
        } catch {
            Add-Violation $readSetViolations "read_set_parse_error: $($_.Exception.Message)"
        }
    }

    $identityPath = Join-Path $Root ".harness/current/source/SOURCE_IDENTITY.json"
    $sourceIdentityStatus = "missing"
    if (-not (Test-Path -LiteralPath $identityPath -PathType Leaf)) {
        Add-Violation $missing ".harness/current/source/SOURCE_IDENTITY.json"
    } else {
        try {
            $identity = Get-Content -LiteralPath $identityPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $sourceIdentityStatus = [string]$identity.source_identity_status
            if ($identity.source_identity_status -ne "resolved") { Add-Violation $sourceIdentityViolations "source_identity_status_not_resolved" }
            if ($identity.local_cache_path_is_identity -ne $false) { Add-Violation $sourceIdentityViolations "local_cache_path_used_as_identity" }
            if ([string]$identity.immutable_commit -notmatch "^[0-9a-f]{40}$") { Add-Violation $sourceIdentityViolations "immutable_commit_invalid" }
            if ([string]$identity.artifact_sha256 -notmatch "^[0-9a-f]{64}$") { Add-Violation $sourceIdentityViolations "artifact_sha256_invalid" }
            if ($runtimePaths.Count -gt 0) {
                $actualArtifact = Get-RuntimeArtifactSha256 -Root $Root -RuntimePaths $runtimePaths
                if ($actualArtifact -ne ([string]$identity.artifact_sha256).ToLowerInvariant()) {
                    Add-Violation $sourceIdentityViolations "artifact_sha256_mismatch"
                }
            }
        } catch {
            Add-Violation $sourceIdentityViolations "source_identity_parse_error: $($_.Exception.Message)"
        }
    }

    if ($DoctorMode -eq "release_candidate" -and $runtimePaths.Count -gt 0) {
        $expected = @{}
        foreach ($rel in $runtimePaths) { $expected[$rel] = $true }
        Get-ChildItem -LiteralPath $Root -Recurse -File -Force | ForEach-Object {
            $rel = $_.FullName.Substring($Root.Length + 1).Replace("\", "/")
            if ($rel -eq ".git" -or $rel.StartsWith(".git/")) { return }
            if (-not $expected.ContainsKey($rel)) {
                Add-Violation $releaseSurfaceViolations $rel
            }
        }
    }

    $overall = "pass"
    if ($missing.Count -gt 0 -or $coverageViolations.Count -gt 0 -or $releaseSurfaceViolations.Count -gt 0 -or $readSetViolations.Count -gt 0 -or $sourceIdentityViolations.Count -gt 0) {
        $overall = "fail"
    }

    $payload = [ordered]@{
        overall_status = $overall
        public_command = ".\harness.ps1 doctor"
        read_only = $true
        mode = $DoctorMode
        missing_required_files = @($missing)
        coverage_violations = @($coverageViolations)
        release_surface_violations = @($releaseSurfaceViolations)
        read_set_violations = @($readSetViolations)
        read_set_total_bytes = $readSetTotalBytes
        forbidden_first_turn_targets = @($forbiddenFirstTurnTargets)
        source_identity_status = $sourceIdentityStatus
        source_identity_violations = @($sourceIdentityViolations)
    }
    Write-Output ($payload | ConvertTo-Json -Depth 50 -Compress)
    if ($overall -eq "pass") { exit 0 }
    exit 1
}

if ($Command -ne "doctor") {
    Write-Error "Unsupported Harness command: $Command"
    exit 64
}

Invoke-Doctor -Root (Get-Location).Path -DoctorMode $Mode
