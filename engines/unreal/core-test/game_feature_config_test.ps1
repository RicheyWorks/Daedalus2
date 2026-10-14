# Exercise only the existing generator's config helpers; never run its installer.
$ErrorActionPreference = "Stop"
$setupPath = Join-Path (Split-Path $PSScriptRoot -Parent) "setup-unreal.ps1"
$parseTokens = $null; $parseErrors = $null
$setupAst = [System.Management.Automation.Language.Parser]::ParseFile($setupPath, [ref]$parseTokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$helperNames = @("Set-IniValue", "Ensure-GameFeatureDataCookRule")
$helpers = @($setupAst.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $helperNames -contains $node.Name }, $true))
if ($helpers.Count -ne 2) { throw "Expected exactly two config helpers" }
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
Write-Host "PASS: creation, idempotence, scans, custom rules, comments, UTF8/UTF16 values and invalid UTF8 preservation"
