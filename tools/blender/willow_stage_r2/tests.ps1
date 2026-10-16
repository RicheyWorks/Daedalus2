# Tiny serial synthetic tests. All runner external boundaries are mocked below.
param([switch]$RealJunctionConformance,[switch]$JunctionClassificationOnly)
$ErrorActionPreference='Stop'
function Get-JunctionCreationDisposition([Management.Automation.ErrorRecord]$CreationError){
 # Called ONLY for the New-Item Junction catch, never unrelated fixture setup.
 # Category/message alone is insufficient; use explicit exception/native evidence.
 $decision='FAIL';$reason='unexpected_creation_error';$recognized=$null
 $node=$CreationError.Exception
 for($depth=0;$null -ne $node -and $depth -lt 16;$depth++){
  if($node -is [UnauthorizedAccessException]){$decision='SKIP';$reason='permission_denied';$recognized=$node.GetType().FullName;break}
  if($node -is [ComponentModel.Win32Exception]){
   if($node.NativeErrorCode -in @(5,1314)){$decision='SKIP';$reason='permission_denied';$recognized=$node.GetType().FullName;break}
   if($node.NativeErrorCode -in @(1,50,120)){$decision='SKIP';$reason='unsupported_capability';$recognized=$node.GetType().FullName;break}
  }
  if($node -is [PlatformNotSupportedException] -or ($node -is [NotSupportedException] -and $CreationError.CategoryInfo.Category -eq [Management.Automation.ErrorCategory]::NotImplemented)){
   $decision='SKIP';$reason='unsupported_capability';$recognized=$node.GetType().FullName;break
  }
  $node=$node.InnerException
 }
 return @{result=$decision;reason=$reason;recognized_exception=$recognized;
  exception_type=$CreationError.Exception.GetType().FullName;category=$CreationError.CategoryInfo.Category.ToString();
  fully_qualified_error_id=$CreationError.FullyQualifiedErrorId;message=$CreationError.Exception.Message;
  hresult=$CreationError.Exception.HResult;target=[string]$CreationError.TargetObject}
}
if($JunctionClassificationOnly){
 if($RealJunctionConformance){throw 'Select one mode; classification never creates a junction'}
 $cases=@(
  @{name='permission';exception=[UnauthorizedAccessException]::new('synthetic denied');category='PermissionDenied';expected='SKIP'},
  @{name='native-permission';exception=[ComponentModel.Win32Exception]::new(5,'synthetic denied');category='PermissionDenied';expected='SKIP'},
  @{name='platform-unsupported';exception=[PlatformNotSupportedException]::new('synthetic unsupported');category='NotImplemented';expected='SKIP'},
  @{name='native-unsupported';exception=[ComponentModel.Win32Exception]::new(50,'synthetic unsupported');category='NotImplemented';expected='SKIP'},
  @{name='explicit-unsupported';exception=[NotSupportedException]::new('synthetic unsupported');category='NotImplemented';expected='SKIP'},
  @{name='unexpected-io';exception=[IO.IOException]::new('synthetic disk fault');category='WriteError';expected='FAIL'},
  @{name='unexpected-setup';exception=[ArgumentException]::new('synthetic bad target');category='InvalidArgument';expected='FAIL'},
  @{name='message-category-alone';exception=[Exception]::new('Access is denied.');category='PermissionDenied';expected='FAIL'},
  @{name='wrapped-permission';exception=[Exception]::new('synthetic wrapper',[UnauthorizedAccessException]::new('synthetic denied'));category='PermissionDenied';expected='SKIP'}
 )
 $results=@()
 foreach($case in $cases){
  $record=[Management.Automation.ErrorRecord]::new($case.exception,'synthetic-classification',[Management.Automation.ErrorCategory]$case.category,'synthetic-target')
  $actual=Get-JunctionCreationDisposition $record
  if($actual.result -cne $case.expected){throw "Classifier mismatch: $($case.name)"}
  if($actual.message -cne $case.exception.Message -or $actual.target -cne 'synthetic-target'){throw 'Classifier lost original error context'}
  $results+=@{case=$case.name;expected=$case.expected;actual=$actual.result;reason=$actual.reason}
 }
 @{mode='pure-junction-error-classification';result='PASS';cases=$results;checks=$results.Count;
   junction_calls=0;filesystem_fixture_calls=0;production_calls=0;implementation_changed=$false}|ConvertTo-Json -Depth 6
 return
}
Import-Module (Join-Path $PSScriptRoot 'StagePolicy.psm1') -Force
$script:checks=0
function Check($condition,$label){if(-not $condition){throw "FAIL: $label"};$script:checks++}
function Throws($label,[scriptblock]$operation){try{& $operation|Out-Null}catch{$script:lastReject=$_.Exception.Message;$script:checks++;return};throw "Expected rejection: $label"}
if(-not $RealJunctionConformance){
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
 if($ClassName -eq 'Win32_OperatingSystem'){
  if($global:WillowR2Test.scenario -eq 'prelaunch-write-failure'){
   [IO.File]::WriteAllText("$($global:WillowR2Test.runRoot)/stage-plan-r2/attempts/$($global:WillowR2Test.grant)/prelaunch-memory.json",'retained prelaunch sentinel')
  }
  return $global:WillowR2Test.mockMemory
 }
 throw 'Unexpected CIM boundary'
}
function Start-Process {
 param($FilePath,$ArgumentList,$WorkingDirectory,$WindowStyle,[switch]$PassThru,$RedirectStandardOutput,$RedirectStandardError)
 $global:WillowR2Test.launches++
 if($global:WillowR2Test.scenario -in @('started-write-failure','started-and-failure-write')){
  $attempt="$($global:WillowR2Test.runRoot)/stage-plan-r2/attempts/$($global:WillowR2Test.grant)"
  [IO.File]::WriteAllText("$attempt/started.json",'retained started sentinel')
  if($global:WillowR2Test.scenario -eq 'started-and-failure-write'){[IO.File]::WriteAllText("$attempt/failure.json",'retained failure sentinel')}
 }
 if($global:WillowR2Test.scenario -eq 'complete'){
  SaveJson "$($global:WillowR2Test.runRoot)/reopened.json" @{stage='editable-reopened';inputs=@{'synthetic.py'='fake-source-pin'};filepath="$($global:WillowR2Test.runRoot)/WillowPilot.blend";objects=3;visual_review=$null;native=$null}
 }
 $fake=[pscustomobject]@{Id=12345;HasExited=($global:WillowR2Test.scenario -notin @('uncertain','started-write-failure','started-and-failure-write'));ExitCode=$(if($global:WillowR2Test.scenario -eq 'failed'){1}else{0})}
 $fake|Add-Member ScriptMethod WaitForExit {};$fake|Add-Member ScriptMethod Refresh {}
 return $fake
}
function Start-Sleep {throw 'Unexpected waiting; tests never start real processes'}
function Write-Warning {param($Message);$global:WillowR2Test.warnings+=([string]$Message)}
foreach($scenario in @('blocked','complete','failed','uncertain','consumed-r1','consumed-r2','prelaunch-write-failure','started-write-failure','started-and-failure-write')){
 $global:WillowR2Test.scenario=$scenario;$global:WillowR2Test.grant="synthetic-$scenario";$global:WillowR2Test.launches=0;$global:WillowR2Test.unlocks=0;$global:WillowR2Test.httpCalls=0;$global:WillowR2Test.leaseHeld=$false
 $global:WillowR2Test.mockMemory=@{FreePhysicalMemory=1700000;FreeVirtualMemory=$(if($scenario -eq 'blocked'){2199999}else{2200000})}
 $global:WillowR2Test.warnings=@()
 $global:WillowR2Test.runRoot=Join-Path $sandbox "run-$scenario";New-Item -ItemType Directory -Path $global:WillowR2Test.runRoot|Out-Null
 [IO.File]::WriteAllText("$($global:WillowR2Test.runRoot)/WillowPilot.blend",'synthetic bytes, not a Blender scene')
 SaveJson "$($global:WillowR2Test.runRoot)/authored.json" @{inputs=@{'synthetic.py'='fake-source-pin'}}
 $runManifest=Join-Path $sandbox "run-$scenario.json"
 SaveJson $runManifest @{repository_root=$sandbox;output_root="run-$scenario";blender='synthetic-no-process';pins=@(@{path="run-$scenario/WillowPilot.blend";sha256=(Get-FileHash "$($global:WillowR2Test.runRoot)/WillowPilot.blend" -Algorithm SHA256).Hash.ToLowerInvariant()});stages=@{reopen=@{cpu_threads=1;max_wall_seconds=$(if($scenario -eq 'uncertain'){0}else{60});must_be_absent=@('reopened.json')}}}
 $runnerParams=@{Stage='reopen';GrantId=$global:WillowR2Test.grant;StartByUtc=[DateTimeOffset]::UtcNow.AddMinutes(2);ExpiresUtc=[DateTimeOffset]::UtcNow.AddMinutes(5);ManifestPath=$runManifest;ManifestSha256=(Get-FileHash $runManifest -Algorithm SHA256).Hash.ToLowerInvariant();Execute=$true}
 $call={& (Join-Path $PSScriptRoot 'stage-runner.ps1') @runnerParams}
 if($scenario -in @('consumed-r1','consumed-r2')){
  $version=$(if($scenario -eq 'consumed-r1'){'stage-plan-r1'}else{'stage-plan-r2'})
  $oldAttempt="$($global:WillowR2Test.runRoot)/$version/attempts/$($global:WillowR2Test.grant)"
  New-Item -ItemType Directory -Path $oldAttempt -Force|Out-Null
  [IO.File]::WriteAllText("$oldAttempt/original.json",'retained original bytes')
  $originalHash=(Get-FileHash "$oldAttempt/original.json").Hash
 }
 if($scenario -eq 'complete'){& $call|Out-Null}else{Throws "runner $scenario outcome" $call}
 $attempt="$($global:WillowR2Test.runRoot)/stage-plan-r2/attempts/$($global:WillowR2Test.grant)"
 if($scenario -in @('consumed-r1','consumed-r2')){
  Check ($global:WillowR2Test.httpCalls -eq 0 -and $global:WillowR2Test.launches -eq 0 -and $global:WillowR2Test.unlocks -eq 0) 'consumed grant rejected before HTTP/lease/launch'
  Check ((Get-FileHash "$oldAttempt/original.json").Hash -eq $originalHash -and @(Get-ChildItem $oldAttempt).Count -eq 1) 'consumed attempt bytes and entries preserved'
  Check ($script:lastReject -like 'Consumed grant*') 'consumed rejection is the intended guard'
 }elseif($scenario -eq 'prelaunch-write-failure'){
  Check ($global:WillowR2Test.launches -eq 0 -and $global:WillowR2Test.unlocks -eq 1) 'prelaunch publication failure prevents launch and releases'
  Check ((Get-Content "$attempt/prelaunch-memory.json" -Raw) -eq 'retained prelaunch sentinel') 'failed prelaunch write preserves existing evidence'
  Check (-not(Test-Path "$attempt/started.json") -and -not(Test-Path "$attempt/terminal.json")) 'no started/terminal claim after rejected evidence publication'
 }elseif($scenario -in @('started-write-failure','started-and-failure-write')){
  Check ($global:WillowR2Test.launches -eq 1 -and $global:WillowR2Test.unlocks -eq 0 -and $global:WillowR2Test.leaseHeld) 'postlaunch publication failure retains lease'
  Check (-not(Test-Path "$attempt/terminal.json") -and -not(Test-Path "$attempt/verified.json")) 'postlaunch publication failure has no accepted terminal'
  Check ((Get-Content "$attempt/started.json" -Raw) -eq 'retained started sentinel') 'started evidence not overwritten'
  if($scenario -eq 'started-write-failure'){$failure=Get-Content "$attempt/failure.json" -Raw|ConvertFrom-Json}
  else{
   Check ((Get-Content "$attempt/failure.json" -Raw) -eq 'retained failure sentinel') 'failed failure-write preserves prior bytes'
   $prefix='WILLOW_FAILURE_FALLBACK '
   Check ($global:WillowR2Test.warnings.Count -eq 1 -and $global:WillowR2Test.warnings[0].StartsWith($prefix)) 'console fallback emitted if durable failure publication also fails'
   $failure=$global:WillowR2Test.warnings[0].Substring($prefix.Length)|ConvertFrom-Json
  }
  Check ($failure.pid -eq 12345 -and $failure.start_utc -and $failure.argv -contains '--background' -and $failure.grant -eq $global:WillowR2Test.grant) 'known PID/start/argv/grant retained after launch'
  Check ($failure.lifecycle_phase -eq 'launched-before-start-receipt' -and $failure.compute_retained -and -not $failure.terminal -and -not $failure.retry) 'lifecycle uncertainty explicit without kill/retry/release'
 }elseif($scenario -eq 'blocked'){
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

# Reparse metadata boundary mocks; never create symlinks or read production files.
$global:WillowR2Reparse=@{target='';reads=0;watched=@()}
function global:Get-Item {
 [CmdletBinding()]param([Parameter(Position=0)]$Path,$LiteralPath,[switch]$Force)
 $target=$(if($LiteralPath){$LiteralPath}else{$Path})
 $item=Microsoft.PowerShell.Management\Get-Item -LiteralPath $target -Force:$Force
 if([IO.Path]::GetFullPath($target) -eq $global:WillowR2Reparse.target){return [pscustomobject]@{FullName=$item.FullName;Attributes=[IO.FileAttributes]::ReparsePoint}}
 return $item
}
function global:Get-Content {
 [CmdletBinding()]param([Parameter(Position=0)]$Path,$LiteralPath,[switch]$Raw)
 $target=$(if($LiteralPath){$LiteralPath}else{$Path})
 if([IO.Path]::GetFullPath($target) -in $global:WillowR2Reparse.watched){$global:WillowR2Reparse.reads++}
 Microsoft.PowerShell.Management\Get-Content -LiteralPath $target -Raw:$Raw
}
try{
 $reopenRoot=Join-Path $sandbox 'reparse-pilot';New-Item -ItemType Directory -Path $reopenRoot|Out-Null
 [IO.File]::WriteAllText("$reopenRoot/WillowPilot.blend",'synthetic unopened scene')
 SaveJson "$reopenRoot/authored.json" @{inputs=@{'synthetic.py'='fake-source-pin'}}
 SaveJson "$reopenRoot/reopened.json" @{stage='editable-reopened';inputs=@{'synthetic.py'='fake-source-pin'};filepath="$reopenRoot/WillowPilot.blend";objects=3;visual_review=$null;native=$null}
 $reopenManifest=Join-Path $sandbox 'reparse-manifest.json';SaveJson $reopenManifest @{output_root='reparse-pilot';pins=@()}
 $global:WillowR2Reparse.watched=@([IO.Path]::GetFullPath("$reopenRoot/authored.json"),[IO.Path]::GetFullPath("$reopenRoot/reopened.json"))
 foreach($target in @($reopenRoot,"$reopenRoot/authored.json","$reopenRoot/reopened.json","$reopenRoot/WillowPilot.blend")){
  $global:WillowR2Reparse.target=[IO.Path]::GetFullPath($target);$global:WillowR2Reparse.reads=0
  Throws 'reparse rejected before content read' {& (Join-Path $PSScriptRoot 'validate-stage.ps1') -Stage reopen -Repo $sandbox -ManifestPath $reopenManifest}
  Check ($script:lastReject -like 'Reparse-point*' -and $global:WillowR2Reparse.reads -eq 0) 'root/authored/selected receipt/reopen target guarded before reads'
 }
 $global:WillowR2Reparse.target='';$global:WillowR2Reparse.reads=0
 $valid=& (Join-Path $PSScriptRoot 'validate-stage.ps1') -Stage reopen -Repo $sandbox -ManifestPath $reopenManifest
 Check ($valid.evidence -eq 'retained-files-verified' -and $global:WillowR2Reparse.reads -eq 2) 'normal reopen metadata remains valid'
}finally{
 Remove-Item Function:\global:Get-Item,Function:\global:Get-Content
}
@{checks=$script:checks;result='PASS';fixtures='synthetic only';sandbox=$sandbox;production_http=0;blender=0;native=0}|ConvertTo-Json
return
}

# Separate module-only mode, after the normal suite's mock-cleanup block.
# No runner, HTTP/CIM/process mock or production boundary is invoked in this mode.
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('willow-r2-junction-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture -ErrorAction Stop|Out-Null
$results=@()
$global:WillowConformanceReads=0
function Read-WillowConsumer([string]$Root,[string]$Relative){
 $resolved=Resolve-WillowPath -Root $Root -Relative $Relative
 $global:WillowConformanceReads++ # ONLY after successful resolution.
 return Get-Content -LiteralPath $resolved -Raw -ErrorAction Stop
}
function TargetSnapshot([string]$Target){
 $entries=@(Get-ChildItem -LiteralPath $Target -Force|Sort-Object Name|ForEach-Object {$_.Name})
 return @{entries=($entries|ConvertTo-Json -Compress);sha256=(Get-FileHash -LiteralPath (Join-Path $Target 'sentinel.txt') -Algorithm SHA256).Hash}
}
foreach($case in @('declared-root-junction','intermediate-junction')){
 $target=Join-Path $fixture ($case+'-target');New-Item -ItemType Directory -Path $target|Out-Null
 [IO.File]::WriteAllText((Join-Path $target 'sentinel.txt'),'owned conformance sentinel')
 $before=TargetSnapshot $target
 if($case -eq 'declared-root-junction'){
  $link=Join-Path $fixture 'declared-root-link';$declaredRoot=$link;$relative='sentinel.txt';$expected='Reparse-point root rejected'
 }else{
  $declaredRoot=Join-Path $fixture 'real-root';New-Item -ItemType Directory -Path $declaredRoot|Out-Null
  $link=Join-Path $declaredRoot 'intermediate-link';$relative='intermediate-link/sentinel.txt';$expected='Reparse-point receipt path rejected'
 }
 $row=[ordered]@{case=$case;result='PENDING';link=$link;target=$target;reads=0;guard=$null;creation_error=$null;creation_classification=$null;cleanup='not-created';target_before=$before;target_after=$null;target_preserved=$false}
 $created=$false
 try{
  try{New-Item -ItemType Junction -Path $link -Target $target -ErrorAction Stop|Out-Null;$created=$true}
  catch{$row.creation_classification=Get-JunctionCreationDisposition $_;$row.result=$row.creation_classification.result;$row.creation_error=$_.Exception.Message}
  if($created){
   $global:WillowConformanceReads=0;$guard=$null
   try{$null=Read-WillowConsumer $declaredRoot $relative}catch{$guard=$_.Exception.Message}
   $row.reads=$global:WillowConformanceReads;$row.guard=$guard
   if($guard -ceq $expected -and $row.reads -eq 0){$row.result='PASS'}
   else{$row.result='FAIL';$row.guard="Expected '$expected' and zero reads; observed '$guard' / $($row.reads)"}
  }
 }catch{$row.result='FAIL';$row.guard=$_.Exception.Message}
 finally{
  # Never delete a target or recursively traverse a link. Re-verify exact own
  # link identity, location, ReparsePoint, Junction kind and expected target.
  if($created -or (Test-Path -LiteralPath $link)){
   try{
    $item=Get-Item -LiteralPath $link -Force -ErrorAction Stop
    $fullLink=[IO.Path]::GetFullPath($link);$fullTarget=[IO.Path]::GetFullPath($target)
    $prefix=[IO.Path]::GetFullPath($fixture)+[IO.Path]::DirectorySeparatorChar
    $targets=@($item.Target)
    $known=$fullLink.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -and $fullTarget.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)
    $known=$known -and [IO.Path]::GetFullPath($item.FullName) -eq $fullLink
    $known=$known -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and $item.LinkType -eq 'Junction' -and $targets.Count -eq 1
    $known=$known -and [IO.Path]::GetFullPath([string]$targets[0]) -eq $fullTarget
    if(-not $known){throw 'Uncertain link identity/target; retain fixture without cleanup'}
    [IO.Directory]::Delete($fullLink,$false)
    if(Test-Path -LiteralPath $fullLink){throw 'Link remains after nonrecursive unlink'}
    $row.cleanup='verified-nonrecursive-unlink'
   }catch{$row.result='FAIL';$row.cleanup='UNCERTAIN: '+$_.Exception.Message}
  }
  try{$after=TargetSnapshot $target;$row.target_after=$after;$row.target_preserved=($after.entries -ceq $before.entries -and $after.sha256 -ceq $before.sha256);if(-not $row.target_preserved){$row.result='FAIL'}}
  catch{$row.result='FAIL';$row.target_preserved=$false}
 }
 $results+=$row
}
$ordinary=Join-Path $fixture 'ordinary';New-Item -ItemType Directory -Path $ordinary|Out-Null
[IO.File]::WriteAllText((Join-Path $ordinary 'sentinel.txt'),'ordinary conformance sentinel')
$before=TargetSnapshot $ordinary;$global:WillowConformanceReads=0
$control=[ordered]@{case='ordinary-directory';result='FAIL';reads=0;sentinel_match=$false;target_preserved=$false;error=$null}
try{
 $value=Read-WillowConsumer $ordinary 'sentinel.txt';$control.reads=$global:WillowConformanceReads
 $control.sentinel_match=($value -ceq 'ordinary conformance sentinel')
 $after=TargetSnapshot $ordinary;$control.target_preserved=($before.entries -ceq $after.entries -and $before.sha256 -ceq $after.sha256)
 if($control.reads -eq 1 -and $control.sentinel_match -and $control.target_preserved){$control.result='PASS'}
}catch{$control.error=$_.Exception.Message;$control.reads=$global:WillowConformanceReads}
$results+=$control
$failed=@($results|Where-Object {$_.result -eq 'FAIL'}).Count
$skipped=@($results|Where-Object {$_.result -eq 'SKIP'}).Count
$outcome=$(if($failed){'FAIL'}elseif($skipped){'PARTIAL_SKIPPED'}else{'PASS'})
@{mode='real-junction-module-conformance';result=$outcome;cases=$results;fixture=$fixture;
 powershell=$PSVersionTable.PSVersion.ToString();os=[Runtime.InteropServices.RuntimeInformation]::OSDescription;
 default_mocked_checks='NOT_RERUN_IN_THIS_MODE';production_http=0;production_cim=0;processes=0;blender=0;native=0}|ConvertTo-Json -Depth 8
if($failed){exit 1}
if($skipped){exit 2}
