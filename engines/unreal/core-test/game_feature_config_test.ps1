# Exercise only the existing generator's config helpers; never run its installer.
$ErrorActionPreference = "Stop"
$setupPath = Join-Path (Split-Path $PSScriptRoot -Parent) "setup-unreal.ps1"
$parseTokens = $null; $parseErrors = $null
$setupAst = [System.Management.Automation.Language.Parser]::ParseFile($setupPath, [ref]$parseTokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$helperNames = @("Read-IniDocument", "Set-IniValue", "Ensure-GameFeatureDataCookRule")
$helpers = @($setupAst.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $helperNames -contains $node.Name }, $true))
if ($helpers.Count -ne 3) { throw "Expected exactly three config helpers" }
foreach ($helper in $helpers) { Invoke-Expression $helper.Extent.Text }
$caseRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("daedalus-game-feature-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $caseRoot | Out-Null
$path = Join-Path $caseRoot "DefaultGame.ini"
if (-not (Ensure-GameFeatureDataCookRule $path)) { throw "Missing-file creation failed" }
$first = [System.IO.File]::ReadAllBytes($path)
if (Ensure-GameFeatureDataCookRule $path) { throw "Repeated addition was not idempotent" }
if ([Convert]::ToBase64String($first) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))) { throw "Idempotent call changed bytes" }
$other = '[+PrimaryAssetTypesToScan]' # Marker in an unrelated section must not count as a rule.
@('[Other]', 'Value=preserved', $other, '[/Script/Engine.AssetManagerSettings]', '+PrimaryAssetTypesToScan=(PrimaryAssetType="Map",CookRule=AlwaysCook)', '[Tail]', 'Keep=1') | Set-Content -LiteralPath $path -Encoding UTF8
if (-not (Ensure-GameFeatureDataCookRule $path)) { throw "Existing-section addition failed" }
$raw = Get-Content -LiteralPath $path -Raw
if ($raw -notmatch 'PrimaryAssetType="Map"' -or $raw -notmatch 'Keep=1' -or $raw -notmatch 'Value=preserved') { throw "Existing scans/settings were lost" }
if (@(Get-Content $path | Where-Object { $_ -match '^\+PrimaryAssetTypesToScan=.*GameFeatureData' }).Count -ne 1) { throw "Rule was not added once" }
@('[/Script/Engine.AssetManagerSettings]', '+PrimaryAssetTypesToScan=(PrimaryAssetType="GameFeatureData",CookRule=NeverCook)', 'Keep=custom') | Set-Content -LiteralPath $path -Encoding UTF8
$before = [IO.File]::ReadAllBytes($path)
if (Ensure-GameFeatureDataCookRule $path) { throw "Existing custom rule was overwritten" }
if ([Convert]::ToBase64String($before) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))) { throw "Custom rule bytes changed" }
@('[/Script/Engine.AssetManagerSettings]', '; +PrimaryAssetTypesToScan=(PrimaryAssetType="GameFeatureData")') | Set-Content -LiteralPath $path -Encoding UTF8
if (-not (Ensure-GameFeatureDataCookRule $path)) { throw "Commented entry blocked repair" }
$accent = "Caf" + [char]0x00e9 + " " + [char]0x96ea
$unicodeConfig = "[Other]`nDisplayName=$accent`n[/Script/Engine.AssetManagerSettings]`n+PrimaryAssetTypesToScan=(PrimaryAssetType=`"Map`",CookRule=AlwaysCook)`n"
foreach ($encoding in @((New-Object System.Text.UTF8Encoding($false)), [System.Text.Encoding]::Unicode)) {
    [IO.File]::WriteAllText($path, $unicodeConfig, $encoding)
    if (-not (Ensure-GameFeatureDataCookRule $path)) { throw "Unicode missing-rule repair failed" }
    $observed = [IO.File]::ReadAllText($path)
    if (-not $observed.Contains("DisplayName=$accent") -or -not $observed.Contains('PrimaryAssetType="Map"')) { throw "Unicode settings corrupted" }
    $before = [IO.File]::ReadAllBytes($path)
    if (Ensure-GameFeatureDataCookRule $path) { throw "Unicode repair was not idempotent" }
    if ([Convert]::ToBase64String($before) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))) { throw "Unicode second pass changed bytes" }
}
[byte[]]$invalidUtf8 = @(0x5b,0x4f,0x74,0x68,0x65,0x72,0x5d,0x0a,0x58,0x3d,0xe9,0x0a)
[IO.File]::WriteAllBytes($path, $invalidUtf8)
$rejected = $false
try { Ensure-GameFeatureDataCookRule $path | Out-Null } catch { $rejected = $true }
if (-not $rejected) { throw "Invalid UTF8 was silently rewritten" }
if ([Convert]::ToBase64String($invalidUtf8) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))) { throw "Rejected encoding changed input bytes" }

# Verify the bytes independently of the production reader and PowerShell's
# ambient encoding. Mixed line endings and the missing final newline survive.
$beforeRule = "[Other]`r`nDisplayName=$accent`n[/Script/Engine.AssetManagerSettings]`r+PrimaryAssetTypesToScan=(PrimaryAssetType=`"Map`",CookRule=AlwaysCook)`n"
$afterRule = "[Tail]`rKeep=$accent"
$formats = @(
    @{ Name="UTF8-noBOM"; Encoding=(New-Object System.Text.UTF8Encoding($false, $true)) },
    @{ Name="UTF8-BOM"; Encoding=(New-Object System.Text.UTF8Encoding($true, $true)) },
    @{ Name="UTF16-LE"; Encoding=(New-Object System.Text.UnicodeEncoding($false, $true, $true)) },
    @{ Name="UTF16-BE"; Encoding=(New-Object System.Text.UnicodeEncoding($true, $true, $true)) },
    @{ Name="UTF32-LE"; Encoding=(New-Object System.Text.UTF32Encoding($false, $true, $true)) },
    @{ Name="UTF32-BE"; Encoding=(New-Object System.Text.UTF32Encoding($true, $true, $true)) }
)
foreach ($format in $formats) {
    $codec = $format.Encoding
    [IO.File]::WriteAllText($path, $beforeRule + $afterRule, $codec)
    if (-not (Ensure-GameFeatureDataCookRule $path)) { throw ($format.Name + " repair failed") }
    [byte[]]$actual = [IO.File]::ReadAllBytes($path)
    [byte[]]$preamble = $codec.GetPreamble()
    for ($i=0; $i -lt $preamble.Length; $i++) {
        if ($actual[$i] -ne $preamble[$i]) { throw ($format.Name + " BOM changed") }
    }
    $decoded = $codec.GetString($actual, $preamble.Length, $actual.Length - $preamble.Length)
    if (-not $decoded.StartsWith($beforeRule) -or -not $decoded.EndsWith($afterRule)) {
        throw ($format.Name + " custom text or line endings changed")
    }
    if ([regex]::Matches($decoded, '^\+PrimaryAssetTypesToScan=.*GameFeatureData', 'Multiline').Count -ne 1) {
        throw ($format.Name + " rule not added exactly once")
    }
    if (Ensure-GameFeatureDataCookRule $path) { throw ($format.Name + " repeated repair changed state") }
    if ([Convert]::ToBase64String($actual) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))) {
        throw ($format.Name + " repeated repair changed bytes")
    }
    Set-IniValue $path "Other" "DisplayName" ($accent + " updated")
    [byte[]]$updated = [IO.File]::ReadAllBytes($path)
    $updatedText = $codec.GetString($updated, $preamble.Length, $updated.Length - $preamble.Length)
    if (-not $updatedText.Contains("DisplayName=$accent updated`n") -or -not $updatedText.EndsWith($afterRule)) {
        throw ($format.Name + " direct value update lost encoding/text")
    }
    for ($i=0; $i -lt $preamble.Length; $i++) {
        if ($updated[$i] -ne $preamble[$i]) { throw ($format.Name + " direct update changed BOM") }
    }

    # Appending after an unterminated section or adding an absent section must
    # separate the new rule from custom text and retain the absent final newline.
    foreach ($original in @("[Other]`nDisplayName=$accent`n[/Script/Engine.AssetManagerSettings]", "[Other]`nDisplayName=$accent")) {
        [IO.File]::WriteAllText($path, $original, $codec)
        if (-not (Ensure-GameFeatureDataCookRule $path)) { throw ($format.Name + " EOF repair failed") }
        [byte[]]$repaired = [IO.File]::ReadAllBytes($path)
        $repairedText = $codec.GetString($repaired, $preamble.Length, $repaired.Length - $preamble.Length)
        if (-not $repairedText.StartsWith($original + "`n") -or
            -not $repairedText.Contains("[/Script/Engine.AssetManagerSettings]`n+PrimaryAssetTypesToScan=") -or
            -not $repairedText.EndsWith('CookRule=AlwaysCook))')) {
            throw ($format.Name + " EOF text, separation or final newline changed")
        }
    }
    $custom = "[/Script/Engine.AssetManagerSettings]`r`n+PrimaryAssetTypesToScan=(PrimaryAssetType=`"GameFeatureData`",CookRule=NeverCook)`nKeep=$accent"
    [IO.File]::WriteAllText($path, $custom, $codec)
    $customBytes = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))
    if (Ensure-GameFeatureDataCookRule $path) { throw ($format.Name + " custom rule replaced") }
    if ($customBytes -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))) { throw ($format.Name + " custom bytes changed") }
}

# Simulate PS5.1's non-UTF8 ANSI reader without changing machine code pages or
# session encoding defaults. The helpers must never consult this legacy path.
[IO.File]::WriteAllText($path, $beforeRule + $afterRule, (New-Object System.Text.UTF8Encoding($false)))
$legacyText = [Text.Encoding]::GetEncoding(1252).GetString([IO.File]::ReadAllBytes($path))
if ($legacyText.Contains("DisplayName=$accent")) { throw "ANSI witness did not demonstrate the original defect" }
$script:legacyReads = 0
function Get-Content {
    param([Parameter(Position=0)][string]$Path, [string]$LiteralPath)
    $script:legacyReads++
    $selected = if ($LiteralPath) { $LiteralPath } else { $Path }
    [Text.Encoding]::GetEncoding(1252).GetString([IO.File]::ReadAllBytes($selected)) -split '\r\n|\n|\r'
}
try {
    if (-not (Ensure-GameFeatureDataCookRule $path)) { throw "Simulated ANSI repair failed" }
    if ($script:legacyReads -ne 0 -or -not [IO.File]::ReadAllText($path).Contains("DisplayName=$accent")) {
        throw "Ambient ANSI reader corrupted the repair"
    }
} finally { Remove-Item -LiteralPath Function:Get-Content }

# BOM selection must retain strict fallbacks. Both entry points refuse damaged
# Unicode before writing, including when StreamReader would replace bad input.
$damaged = @(
    [byte[]]@(0xef,0xbb,0xbf,0xe9),
    [byte[]]@(0xff,0xfe,0x00,0xd8),
    [byte[]]@(0xfe,0xff,0xd8,0x00),
    [byte[]]@(0xff,0xfe,0x41),
    [byte[]]@(0xff,0xfe,0x00,0x00,0x00,0xd8,0x00,0x00),
    [byte[]]@(0x00,0x00,0xfe,0xff,0x00,0x00,0xd8,0x00)
)
foreach ($data in $damaged) {
    [IO.File]::WriteAllBytes($path, $data)
    foreach ($operation in @({ Ensure-GameFeatureDataCookRule $path }, { Set-IniValue $path "Other" "Value" "updated" })) {
        $rejected = $false
        try { & $operation | Out-Null } catch { $rejected = $true }
        if (-not $rejected) { throw "Damaged BOM input was silently rewritten" }
        if ([Convert]::ToBase64String($data) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))) {
            throw "Rejected BOM input changed bytes"
        }
    }
}
Write-Host "PASS: config rules, Unicode encodings/BOMs, mixed endings, simulated ANSI, malformed-byte refusal and idempotence"
