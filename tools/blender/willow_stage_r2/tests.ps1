# Tiny serial synthetic tests. All runner external boundaries are mocked below.
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'StagePolicy.psm1') -Force
$script:checks=0
function Check($condition,$label){if(-not $condition){throw "FAIL: $label"};$script:checks++}
function Throws($label,[scriptblock]$operation){try{& $operation|Out-Null}catch{$script:lastReject=$_.Exception.Message;$script:checks++;return};throw "Expected rejection: $label"}
$sandbox=Join-Path ([IO.Path]::GetTempPath()) ('willow-r2-tests-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $sandbox|Out-Null
# Synthetic files are retained in this unique temp directory for inspection.
$viewRoot=Join-Path $sandbox 'pilot';New-Item -ItemType Directory -Path "$viewRoot/views"|Out-Null
$settings=@{engine='CYCLES';device='CPU';threads=2;samples=24;resolution=@(1000,1000);sun_energy=2;world_strength=.4}
function SaveJson($path,$value){$value|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $path -Encoding utf8}
$images=@()
foreach($name in @('overview','player_contact','refuge_detail')){
 # Intentionally header-only synthetic PNG fixture, not rendered pixels.
 $bytes=[byte[]]::new(25);$signature=@(137,80,78,71,13,10,26,10)
 for($i=0;$i -lt 8;$i++){$bytes[$i]=$signature[$i]}
 $bytes[18]=3;$bytes[19]=232;$bytes[22]=3;$bytes[23]=232
 $path="$viewRoot/views/$name.png";[IO.File]::WriteAllBytes($path,$bytes)
 $images+=@{path="views/$name.png";sha256=(Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant();reviewed=$false}
}
SaveJson "$viewRoot/authored.json" @{inputs=@{'synthetic.py'='fake-source-pin'}}
$viewManifest=Join-Path $sandbox 'view-manifest.json'
SaveJson $viewManifest @{output_root='pilot';pins=@();view_settings=$settings}
function Receipt($entries=$images,$config=$settings){SaveJson "$viewRoot/views.json" @{stage='rendered-unreviewed';inputs=@{'synthetic.py'='fake-source-pin'};views=$entries;settings=$config;native=$null}}
function ValidateViews {& (Join-Path $PSScriptRoot 'validate-stage.ps1') -Stage views -Repo $sandbox -ManifestPath $viewManifest}
Receipt
$result=ValidateViews
Check ($result.verified.Count -eq 3 -and $null -eq $result.quality_accepted) 'forward slashes accepted, quality unknown'
$backslash=@($images|ForEach-Object {@{path=$_.path.Replace('/','\');sha256=$_.sha256;reviewed=$false}})
Receipt $backslash
Check ((ValidateViews).verified.Count -eq 3) 'backslashes identify same three allowed files'
foreach($bad in @('../views/overview.png','views/../views/overview.png','/views/overview.png','C:\views\overview.png','views//overview.png','views/./overview.png','views/overview.png:stream')){
 Throws "reject unsafe $bad" {ConvertTo-WillowPath $bad}
}
$changed=@($images|ForEach-Object {@{path=$_.path;sha256=$_.sha256;reviewed=$false}})
$changed[0].path='../views/overview.png';Receipt $changed;Throws 'traversal receipt' {ValidateViews}
Receipt @($images[0],$images[0],$images[2]);Throws 'duplicate receipt' {ValidateViews}
Receipt @($images[0],$images[1]);Throws 'missing receipt entry' {ValidateViews}
$changed=@($images|ForEach-Object {@{path=$_.path;sha256=$_.sha256;reviewed=$false}})
$changed[0].sha256='0'*64;Receipt $changed;Throws 'hash mismatch' {ValidateViews}
$changed[0].sha256=$images[0].sha256;$changed[0].path='views/Overview.png';Receipt $changed;Throws 'case not exact allowlist' {ValidateViews}
$badSettings=$settings.Clone();$badSettings.samples=25;Receipt $images $badSettings;Throws 'settings mismatch' {ValidateViews}
Receipt
$missingRoot=Join-Path $sandbox 'missing-pilot';New-Item -ItemType Directory -Path "$missingRoot/views"|Out-Null
Copy-Item -LiteralPath "$viewRoot/authored.json","$viewRoot/views.json" -Destination $missingRoot
foreach($name in @('overview','player_contact')){Copy-Item -LiteralPath "$viewRoot/views/$name.png" -Destination "$missingRoot/views/$name.png"}
SaveJson $viewManifest @{output_root='missing-pilot';pins=@();view_settings=$settings}
Throws 'missing used file' {ValidateViews}
SaveJson $viewManifest @{output_root='pilot';pins=@();view_settings=$settings}
$memoryDir=Join-Path $sandbox 'memory';New-Item -ItemType Directory -Path $memoryDir|Out-Null
$low=@{FreePhysicalMemory=1699999;FreeVirtualMemory=2200000}
Throws 'low physical blocks after evidence' {Invoke-WillowMemoryPreflight -Path "$memoryDir/physical.json" -Grant 'synthetic' -Stage 'reopen' -Memory $low}
$proof=Get-Content "$memoryDir/physical.json" -Raw|ConvertFrom-Json
Check ($proof.physical_kib -eq 1699999 -and $proof.virtual_kib -eq 2200000) 'actual numeric readings retained'
Check ($proof.units -eq 'KiB' -and $proof.physical_floor_kib -eq 1700000 -and $proof.virtual_floor_kib -eq 2200000) 'units/floors unchanged'
Check ($proof.outcome -eq 'blocked' -and -not $proof.launched -and $null -eq $proof.pid -and $proof.observed_utc) 'prelaunch outcome UTC/no PID'
Throws 'low virtual' {Invoke-WillowMemoryPreflight -Path "$memoryDir/virtual.json" -Grant 'synthetic' -Stage 'reopen' -Memory @{FreePhysicalMemory=1700000;FreeVirtualMemory=2199999}}
$accepted=Invoke-WillowMemoryPreflight -Path "$memoryDir/accepted.json" -Grant 'synthetic' -Stage 'reopen' -Memory @{FreePhysicalMemory=1700000;FreeVirtualMemory=2200000}
Check ($accepted.outcome -eq 'accepted') 'exact floors accepted'
Throws 'unknown memory fails closed' {Invoke-WillowMemoryPreflight -Path "$memoryDir/unknown.json" -Grant 'synthetic' -Stage 'reopen' -Memory $null -QueryError 'synthetic query error'}
Check ((Get-Content "$memoryDir/unknown.json" -Raw|ConvertFrom-Json).reason -eq 'memory_reading_unavailable_or_invalid') 'query error retained'
Throws 'evidence immutable' {Invoke-WillowMemoryPreflight -Path "$memoryDir/physical.json" -Grant 'duplicate' -Stage 'reopen' -Memory $low}
Check ((Get-Content "$memoryDir/physical.json" -Raw|ConvertFrom-Json).grant -eq 'synthetic') 'prior evidence preserved'

# Full runner synthetic boundary mocks: no actual HTTP/CIM/process/sleep is used.
$global:WillowR2Test=@{}
function Invoke-RestMethod {
 param($Uri,$Method,$ContentType,$Body,$TimeoutSec)
 $global:WillowR2Test.httpCalls++
 if($Uri -notlike 'http://127.0.0.1:9890/*'){throw 'Unexpected URI: no network allowed'}
 if($Uri.EndsWith('/lock')){$global:WillowR2Test.leaseHeld=$true;return @{ok=$true;lock=@{holder='team-codex'}}}
 if($Uri.EndsWith('/unlock')){$global:WillowR2Test.unlocks++;$global:WillowR2Test.leaseHeld=$false;return @{ok=$true}}
 if($Uri.EndsWith('/locks')){if($global:WillowR2Test.leaseHeld){return @{compute=@{holder='team-codex';note=$global:WillowR2Test.grant};unreal=@{holder='codex-play-guard'}}};return @{unreal=@{holder='codex-play-guard'}}}
 throw 'Unexpected hub boundary; no network allowed'
}
function Get-CimInstance {
 param($ClassName)
 if($ClassName -eq 'Win32_Process'){return @()}
 if($ClassName -eq 'Win32_OperatingSystem'){return $global:WillowR2Test.mockMemory}
 throw 'Unexpected CIM boundary'
}
function Start-Process {
 param($FilePath,$ArgumentList,$WorkingDirectory,$WindowStyle,[switch]$PassThru,$RedirectStandardOutput,$RedirectStandardError)
 $global:WillowR2Test.launches++
 if($global:WillowR2Test.scenario -eq 'complete'){
  SaveJson "$($global:WillowR2Test.runRoot)/reopened.json" @{stage='editable-reopened';inputs=@{'synthetic.py'='fake-source-pin'};filepath="$($global:WillowR2Test.runRoot)/WillowPilot.blend";objects=3;visual_review=$null;native=$null}
 }
 $fake=[pscustomobject]@{Id=12345;HasExited=($global:WillowR2Test.scenario -ne 'uncertain');ExitCode=$(if($global:WillowR2Test.scenario -eq 'failed'){1}else{0})}
 $fake|Add-Member ScriptMethod WaitForExit {};$fake|Add-Member ScriptMethod Refresh {}
 return $fake
}
function Start-Sleep {throw 'Unexpected waiting; tests never start real processes'}
foreach($scenario in @('blocked','complete','failed','uncertain')){
 $global:WillowR2Test.scenario=$scenario;$global:WillowR2Test.grant="synthetic-$scenario";$global:WillowR2Test.launches=0;$global:WillowR2Test.unlocks=0;$global:WillowR2Test.httpCalls=0;$global:WillowR2Test.leaseHeld=$false
 $global:WillowR2Test.mockMemory=@{FreePhysicalMemory=1700000;FreeVirtualMemory=$(if($scenario -eq 'blocked'){2199999}else{2200000})}
 $global:WillowR2Test.runRoot=Join-Path $sandbox "run-$scenario";New-Item -ItemType Directory -Path $global:WillowR2Test.runRoot|Out-Null
 [IO.File]::WriteAllText("$($global:WillowR2Test.runRoot)/WillowPilot.blend",'synthetic bytes, not a Blender scene')
 SaveJson "$($global:WillowR2Test.runRoot)/authored.json" @{inputs=@{'synthetic.py'='fake-source-pin'}}
 $runManifest=Join-Path $sandbox "run-$scenario.json"
 SaveJson $runManifest @{repository_root=$sandbox;output_root="run-$scenario";blender='synthetic-no-process';pins=@(@{path="run-$scenario/WillowPilot.blend";sha256=(Get-FileHash "$($global:WillowR2Test.runRoot)/WillowPilot.blend" -Algorithm SHA256).Hash.ToLowerInvariant()});stages=@{reopen=@{cpu_threads=1;max_wall_seconds=$(if($scenario -eq 'uncertain'){0}else{60});must_be_absent=@('reopened.json')}}}
 $runnerParams=@{Stage='reopen';GrantId=$global:WillowR2Test.grant;StartByUtc=[DateTimeOffset]::UtcNow.AddMinutes(2);ExpiresUtc=[DateTimeOffset]::UtcNow.AddMinutes(5);ManifestPath=$runManifest;ManifestSha256=(Get-FileHash $runManifest -Algorithm SHA256).Hash.ToLowerInvariant();Execute=$true}
 $call={& (Join-Path $PSScriptRoot 'stage-runner.ps1') @runnerParams}
 if($scenario -eq 'complete'){& $call|Out-Null}else{Throws "runner $scenario outcome" $call}
 $attempt="$($global:WillowR2Test.runRoot)/stage-plan-r2/attempts/$($global:WillowR2Test.grant)"
 if($scenario -eq 'blocked'){
  Check ($global:WillowR2Test.launches -eq 0 -and $global:WillowR2Test.unlocks -eq 1) "memory rejection no launch/release; observed $script:lastReject"
  Check ((Get-Content "$attempt/prelaunch-memory.json" -Raw|ConvertFrom-Json).virtual_kib -eq 2199999) 'runner blocked readings persisted'
  Check (-not(Test-Path "$attempt/terminal.json")) 'no false terminal receipt for no-launch'
 }elseif($scenario -eq 'uncertain'){
  Check ($global:WillowR2Test.launches -eq 1 -and $global:WillowR2Test.unlocks -eq 0 -and $global:WillowR2Test.leaseHeld) 'uncertain live process retains lease'
  Check (Test-Path "$attempt/uncertain.json") 'uncertainty retained'
 }else{
  Check ($global:WillowR2Test.launches -eq 1 -and $global:WillowR2Test.unlocks -eq 1) 'terminal process releases exactly once'
  Check (Test-Path "$attempt/terminal.json") 'terminal status retained before validation'
  Check ((Test-Path "$attempt/verified.json") -eq ($scenario -eq 'complete')) 'success validation distinct from failed exit'
 }
}
@{checks=$script:checks;result='PASS';fixtures='synthetic only';sandbox=$sandbox;production_http=0;blender=0;native=0}|ConvertTo-Json
