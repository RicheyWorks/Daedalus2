[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$BaselineReceipt,
    [Parameter(Mandatory)][string]$PluginRoot,
    [Parameter(Mandatory)][string]$ExpectedHead,
    [string]$OutputReceipt
)

# Read-only source admission check. Does not contact an editor, load a module,
# install a payload, or freeze content/map changes made by the asset owner.
$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath $BaselineReceipt -Raw | ConvertFrom-Json -AsHashtable
if ($manifest.schema -ne 'daedalus.combined184-accepted-production-baseline.v1' -or
    $ExpectedHead -cnotmatch '^[0-9a-f]{40}$' -or $manifest.head -cne $ExpectedHead -or
    $manifest.source_files -ne 184 -or $manifest.source.Count -ne 184) {
    throw 'Expected the explicitly selected accepted184 source receipt and exact head.'
}
$root = [IO.Path]::GetFullPath($PluginRoot).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
if (-not [IO.Directory]::Exists($root)) { throw 'Explicit plugin root is missing.' }
$prefix = $root + [IO.Path]::DirectorySeparatorChar
$receiptPath = $null
if ($OutputReceipt) {
    $receiptPath = [IO.Path]::GetFullPath($OutputReceipt)
    if ($receiptPath.Equals($root, [StringComparison]::OrdinalIgnoreCase) -or
        $receiptPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Evidence must be outside the read-only plugin tree.'
    }
    $parent = [IO.Path]::GetDirectoryName($receiptPath)
    if (-not [IO.Directory]::Exists($parent)) { throw 'Evidence parent must already exist.' }
    # An apparently external path must not alias the source via a junction.
    while ($parent) {
        if ((Get-Item -LiteralPath $parent -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'Evidence parent must not contain reparse points.'
        }
        $parent = [IO.Path]::GetDirectoryName($parent)
    }
}
$utf8 = [Text.UTF8Encoding]::new($false, $true)
$issues = [Collections.Generic.List[string]]::new()
$pending = [Collections.Generic.Queue[IO.DirectoryInfo]]::new()
$pending.Enqueue([IO.DirectoryInfo]::new((Join-Path $root 'Source')))
$directoryCount = 0
$observedFiles = 0
while ($pending.Count -gt 0) {
    $directory = $pending.Dequeue()
    if (++$directoryCount -gt 512 -or ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Source tree exceeds bounded traversal or contains a reparse point.'
    }
    foreach ($entry in $directory.EnumerateFileSystemInfos()) {
        if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Source admission refuses reparse points.' }
        if ($entry -is [IO.DirectoryInfo]) { $pending.Enqueue($entry); continue }
        if (++$observedFiles -gt 1024) { throw 'Source tree exceeds bounded file count.' }
        $name = $entry.FullName.Substring($prefix.Length).Replace([IO.Path]::DirectorySeparatorChar, '/')
        if (-not $manifest.source.Contains($name)) { $issues.Add("unexpected:$name") }
    }
}
$checked = 0
foreach ($relative in $manifest.source.Keys) {
    if ($relative -cnotmatch '^Source/[A-Za-z0-9_./-]+$' -or
        @($relative.Split('/') | Where-Object { $_ -in @('', '.', '..') }).Count -gt 0) {
        throw 'Receipt contains an invalid source-relative path.'
    }
    $path = [IO.Path]::GetFullPath((Join-Path $root $relative))
    if (-not $path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Source path escaped explicit plugin root.' }
    # Do not follow junctions/symlinks in an untrusted or stale source receipt.
    $cursor = $path
    while ($cursor.Length -ge $root.Length) {
        if (Test-Path -LiteralPath $cursor) {
            if ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Source admission refuses reparse points.'
            }
        }
        if ($cursor -eq $root) { break }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
    if (-not [IO.File]::Exists($path)) { $issues.Add("missing:$relative"); continue }
    $file = Get-Item -LiteralPath $path
    if ($file.Length -gt 2MB) { $issues.Add("oversize:$relative"); continue }
    $raw = [IO.File]::ReadAllBytes($path)
    $normalized = $utf8.GetBytes($utf8.GetString($raw).Replace("`r`n", "`n"))
    $actual = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($normalized)).ToLowerInvariant()
    $expected = $manifest.source[$relative]
    if ($expected.sha256 -cnotmatch '^[0-9a-f]{64}$' -or $actual -cne $expected.sha256 -or
        $normalized.Length -ne $expected.bytes) { $issues.Add("mismatch:$relative") }
    ++$checked
}
$result = [ordered]@{
    schema='daedalus.practical-app-source-admission.v1'
    utc=[DateTime]::UtcNow.ToString('o'); acceptedHead=$ExpectedHead; expectedFiles=184
    checkedFiles=$checked; observedFiles=$observedFiles
    sourceMatches=($issues.Count -eq 0 -and $checked -eq 184 -and $observedFiles -eq 184); issues=@($issues)
    scope='Explicit source tree and LF-normalized bytes only; no native/runtime/service acceptance'
    editorContacted=$false; installed=$false; contentOrSavedWorldChecked=$false
}
if ($receiptPath) {
    # Existing evidence is never replaced by a repeated admission check.
    $stream = [IO.File]::Open($receiptPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $bytes = $utf8.GetBytes(($result | ConvertTo-Json -Depth 5) + "`n")
        $stream.Write($bytes, 0, $bytes.Length)
    } finally { $stream.Dispose() }
}
$result | ConvertTo-Json -Depth 5
if (-not $result.sourceMatches) { throw 'Source admission failed; receipt identifies mismatched leaves. No mutation was performed.' }
