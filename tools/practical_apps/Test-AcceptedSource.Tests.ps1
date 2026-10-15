[CmdletBinding()]
param([Parameter(Mandatory)][string]$TestRoot)
$ErrorActionPreference = 'Stop'
$check = Join-Path $PSScriptRoot 'Test-AcceptedSource.ps1'
$root = [IO.Path]::GetFullPath($TestRoot)
if (Test-Path -LiteralPath $root) { throw 'Use a new test-owned directory; existing files are not replaced.' }
[IO.Directory]::CreateDirectory((Join-Path $root 'plugin/Source/Fixture')) | Out-Null
$head = '074c519b70225b36e890531843bc55eb0fd3a363'
$utf8 = [Text.UTF8Encoding]::new($false)
$source = [ordered]@{}
1..184 | ForEach-Object {
    $relative = 'Source/Fixture/Leaf' + $_ + '.cpp'
    $text = "// synthetic fixture $_`n"
    [IO.File]::WriteAllText((Join-Path $root ('plugin/' + $relative)), $text.Replace("`n", "`r`n"), $utf8)
    $bytes = $utf8.GetBytes($text)
    $source[$relative] = @{bytes=$bytes.Length;sha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()}
}
$manifest = @{schema='daedalus.combined184-accepted-production-baseline.v1';head=$head;source_files=184;source=$source}
$receipt = Join-Path $root 'baseline.json'
function Save-Manifest { $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receipt -Encoding utf8 }
function Expect-Rejected([scriptblock]$Action, [string]$Label) {
    $rejected=$false
    try { & $Action | Out-Null } catch { $rejected=$true }
    if (-not $rejected) { throw ('Expected rejection: ' + $Label) }
    $script:passed.Add($Label)
}
$passed = [Collections.Generic.List[string]]::new()
Save-Manifest
$output = Join-Path $root 'first-result.json'
$result = & $check -BaselineReceipt $receipt -PluginRoot (Join-Path $root 'plugin') -ExpectedHead $head -OutputReceipt $output | ConvertFrom-Json
if (-not $result.sourceMatches -or $result.checkedFiles -ne 184) { throw 'Matching CRLF source did not pass.' }
$passed.Add('184 matching LF-normalized leaves pass')
Expect-Rejected { & $check -BaselineReceipt $receipt -PluginRoot (Join-Path $root 'plugin') -ExpectedHead $head -OutputReceipt $output } 'Existing receipt is not overwritten'
$inside = Join-Path $root 'plugin/Source/Fixture/evidence.json'
Expect-Rejected { & $check -BaselineReceipt $receipt -PluginRoot (Join-Path $root 'plugin') -ExpectedHead $head -OutputReceipt $inside } 'Evidence output inside plugin rejected'
if (Test-Path -LiteralPath $inside) { throw 'Admission wrote into the source tree.' }
$alias = Join-Path $root 'evidence-alias'
New-Item -ItemType Junction -Path $alias -Target (Join-Path $root 'plugin/Source') | Out-Null
$aliasedOutput = Join-Path $alias 'aliased-evidence.json'
Expect-Rejected { & $check -BaselineReceipt $receipt -PluginRoot (Join-Path $root 'plugin') -ExpectedHead $head -OutputReceipt $aliasedOutput } 'Evidence parent reparse alias rejected'
if (Test-Path -LiteralPath $aliasedOutput) { throw 'Admission wrote through a source alias.' }
$extra = Join-Path $root 'plugin/Source/Fixture/Unexpected.cpp'
[IO.File]::WriteAllText($extra, '// extra', $utf8)
Expect-Rejected { & $check -BaselineReceipt $receipt -PluginRoot (Join-Path $root 'plugin') -ExpectedHead $head } 'Unexpected source leaf rejected'
[IO.File]::Delete($extra)
[IO.File]::AppendAllText((Join-Path $root 'plugin/Source/Fixture/Leaf1.cpp'), '// changed', $utf8)
Expect-Rejected { & $check -BaselineReceipt $receipt -PluginRoot (Join-Path $root 'plugin') -ExpectedHead $head } 'Changed source fails admission'
$manifest.source_files=140; Save-Manifest
Expect-Rejected { & $check -BaselineReceipt $receipt -PluginRoot (Join-Path $root 'plugin') -ExpectedHead $head } 'Historical140 receipt rejected'
$manifest.source_files=184
$source.Remove('Source/Fixture/Leaf184.cpp')
$source['Source/../outside.cpp']=@{bytes=0;sha256=('0' * 64)}
Save-Manifest
Expect-Rejected { & $check -BaselineReceipt $receipt -PluginRoot (Join-Path $root 'plugin') -ExpectedHead $head } 'Traversal receipt rejected'
[ordered]@{synthetic=$true;passed=$passed.Count;cases=@($passed);nativeRuntimeClaim=$false} | ConvertTo-Json -Depth 4
