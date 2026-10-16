param(
 [Parameter(Mandatory=$true)][ValidateSet('export','views','reopen')][string]$Stage,
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9-]{1,100}$')][string]$GrantId,
 [Parameter(Mandatory=$true)][DateTimeOffset]$StartByUtc,
 [Parameter(Mandatory=$true)][DateTimeOffset]$ExpiresUtc,
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ManifestSha256,
 [Parameter(Mandatory=$true)][string]$ManifestPath,
 [switch]$Execute
)
# Requires a FRESH human/coordinator grant matching this exact stage/thread count.
# Parameters are not permission. No allocation follows from file existence.
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'StagePolicy.psm1') -Force
$manifestPath=[IO.Path]::GetFullPath($ManifestPath)
if((Get-FileHash $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ManifestSha256){throw 'Manifest pin mismatch'}
$manifest=Get-Content $manifestPath -Raw|ConvertFrom-Json
$repo=$manifest.repository_root
$root=Join-Path $repo $manifest.output_root
$stagePlan=$manifest.stages.$Stage
foreach($pin in $manifest.pins){
 $file=Join-Path $repo $pin.path
 if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pin.sha256){throw "Changed pin $($pin.path)"}
}
foreach($relative in $stagePlan.must_be_absent){if(Test-Path (Join-Path $root $relative)){throw "Existing/partial stage ${relative}: reconcile, never replay"}}
$argv=@((Join-Path $root 'WillowPilot.blend'),'--background','--threads',[string]$stagePlan.cpu_threads,'--python-exit-code','1','--python',(Join-Path $repo 'tools/blender/shardstead_willow_wetland_pilot.py'),'--',$Stage)
if(-not $Execute){@{stage=$Stage;argv=$argv;allocation='NOT_GRANTED_BY_PREPARATION';cpu_threads=$stagePlan.cpu_threads};return}
if([DateTimeOffset]::UtcNow -ge $StartByUtc -or $ExpiresUtc -le $StartByUtc){throw 'Invalid/expired grant window'}
# Frozen views source sets two threads itself. Do not promise one-thread views.
if($Stage -eq 'views' -and $stagePlan.cpu_threads -ne 2){throw 'Frozen matched-view source requires a separate two-CPU allocation'}
$ttl=[math]::Ceiling(($ExpiresUtc-[DateTimeOffset]::UtcNow).TotalSeconds)+30
if($ttl -le $stagePlan.max_wall_seconds+30 -or $ttl -gt 1800){throw 'Grant/lease duration cannot cover bounded stage'}
$hub='http://127.0.0.1:9890'
$locks=Invoke-RestMethod "$hub/locks" -TimeoutSec 5
if($locks.compute){throw 'Compute held; do not race or steal'}
if($locks.unreal -and $locks.unreal.holder -ne 'codex-play-guard'){throw 'Native custody changed; reconcile'}
$lease=Invoke-RestMethod "$hub/lock" -Method Post -ContentType application/json -Body (@{me='team-codex';name='compute';ttl=$ttl;note=$GrantId}|ConvertTo-Json) -TimeoutSec 5
if(-not $lease.ok -or $lease.lock.holder -ne 'team-codex'){throw 'Exclusive compute not acquired'}
$job=$null;$terminal=$false;$attempt=$null
try{
 $locks=Invoke-RestMethod "$hub/locks" -TimeoutSec 5
 if($locks.compute.holder -ne 'team-codex' -or $locks.compute.note -ne $GrantId){throw 'Lease readback mismatch'}
 $busy=Get-CimInstance Win32_Process|Where-Object {($_.Name -eq 'blender.exe' -and $_.CommandLine -match '(--background| -b )') -or $_.Name -match '^(UnrealBuildTool|cl|link)\.exe$'}
 if($busy){throw 'Competing background producer/compiler'}
 $attempt=Join-Path $root "stage-plan-r2/attempts/$GrantId"
 if(Test-Path $attempt){throw 'Grant attempt already exists; reconcile it'}
 New-Item -ItemType Directory -Path $attempt|Out-Null
 $os=$null;$queryError=''
 try{$os=Get-CimInstance Win32_OperatingSystem}catch{$queryError=$_.Exception.Message}
 $memory=Invoke-WillowMemoryPreflight -Path (Join-Path $attempt 'prelaunch-memory.json') -Grant $GrantId -Stage $Stage -Memory $os -QueryError $queryError
 if([DateTimeOffset]::UtcNow -ge $StartByUtc){throw 'Start window expired UTC'}
 $start=[DateTimeOffset]::UtcNow;$clock=[Diagnostics.Stopwatch]::StartNew()
 $job=Start-Process -FilePath $manifest.blender -ArgumentList $argv -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $attempt 'stdout.log') -RedirectStandardError (Join-Path $attempt 'stderr.log')
 $started=@{grant=$GrantId;stage=$Stage;pid=$job.Id;start_utc=$start.ToString('o');argv=$argv;memory=$memory;manifest_sha256=$ManifestSha256;cpu_threads=$stagePlan.cpu_threads}
 Write-WillowEvidence -Path (Join-Path $attempt 'started.json') -Value $started
 $started|ConvertTo-Json -Depth 6
 while(-not $job.HasExited){
  if($clock.Elapsed.TotalSeconds -gt $stagePlan.max_wall_seconds -or [DateTimeOffset]::UtcNow -ge $ExpiresUtc){
   Write-WillowEvidence -Path (Join-Path $attempt 'uncertain.json') -Value @{state='UNCERTAIN_STILL_RUNNING';pid=$job.Id;grant=$GrantId;compute_retained=$true;retry=$false}
   throw 'Bounded deadline reached; do not kill/replay/release live process; operator reconciliation required'
  }
  Start-Sleep -Milliseconds 250;$job.Refresh()
 }
 $job.WaitForExit();$clock.Stop();$terminal=$true
 $result=@{grant=$GrantId;stage=$Stage;pid=$job.Id;exit_code=$job.ExitCode;end_utc=[DateTimeOffset]::UtcNow.ToString('o');wall_seconds=$clock.Elapsed.TotalSeconds;native=$null;quality_accepted=$null;validation=$null}
 # Always retain terminal status before trying content validation.
 Write-WillowEvidence -Path (Join-Path $attempt 'terminal.json') -Value $result
 if($job.ExitCode -eq 0){
  $result.validation=& (Join-Path $PSScriptRoot 'validate-stage.ps1') -Stage $Stage -Repo $repo -ManifestPath $manifestPath
  Write-WillowEvidence -Path (Join-Path $attempt 'verified.json') -Value $result
 }else{throw 'Stage failed: partial files remain; no automatic replay'}
}catch{
 if($attempt -and (Test-Path $attempt)){Write-WillowEvidence -Path (Join-Path $attempt 'failure.json') -Value @{utc=[DateTimeOffset]::UtcNow.ToString('o');error=$_.Exception.Message;launched=($null -ne $job);terminal=$terminal;retry=$false}}
 throw
}finally{
 if(Test-WillowMayRelease -Launched ($null -ne $job) -Terminal $terminal){
  $release=Invoke-RestMethod "$hub/unlock" -Method Post -ContentType application/json -Body (@{me='team-codex';name='compute';force=$false}|ConvertTo-Json) -TimeoutSec 5
  $locks=Invoke-RestMethod "$hub/locks" -TimeoutSec 5
  $proof=@{grant=$GrantId;utc=[DateTimeOffset]::UtcNow.ToString('o');unlock_ok=$release.ok;owned_compute_remaining=($locks.compute.holder -eq 'team-codex');terminal=$terminal;launched=($null -ne $job);locks=$locks}
  if($attempt){Write-WillowEvidence -Path (Join-Path $attempt 'release.json') -Value $proof}
  $proof|ConvertTo-Json -Depth 6
  if(-not $release.ok -or $proof.owned_compute_remaining){throw 'Release unverified: reconcile, no next job'}
 }
}
