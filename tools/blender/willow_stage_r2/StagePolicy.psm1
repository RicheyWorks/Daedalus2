# Willow r2 policy helpers. No process, hub, lease or Blender operations.
function Write-WillowEvidence {
 param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)]$Value)
 $destination=[IO.Path]::GetFullPath($Path)
 $temporary=$destination+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
 $stream=$null
 try{
  $bytes=[Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 16))
  $stream=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true);$stream.Dispose();$stream=$null
  [IO.File]::Move($temporary,$destination) # No overwrite of an earlier attempt.
 }finally{
  if($stream){$stream.Dispose()}
  if([IO.File]::Exists($temporary)){[IO.File]::Delete($temporary)}
 }
}

function ConvertTo-WillowPath {
 param([Parameter(Mandatory=$true)][string]$Path)
 $normalized=$Path.Replace('\','/')
 if($normalized -match '(^/|:)' -or $normalized -match '[\x00-\x1f]'){throw 'Rooted/control/drive receipt path rejected'}
 foreach($part in $normalized.Split('/')){
  if($part -in @('','.', '..') -or $part -notmatch '^[A-Za-z0-9_.-]+$'){throw 'Unsafe receipt path segment'}
 }
 return $normalized
}

function Resolve-WillowPath {
 param([string]$Root,[string]$Relative)
 $normalized=ConvertTo-WillowPath $Relative
 $base=[IO.Path]::GetFullPath($Root)
 $full=[IO.Path]::GetFullPath((Join-Path $base $normalized))
 if(-not $full.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Receipt path escapes pilot root'}
 $current=Get-Item -LiteralPath $base -Force -ErrorAction Stop
 if($current.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse-point root rejected'}
 foreach($part in $normalized.Split('/')){
  $currentPath=Join-Path $current.FullName $part
  if(Test-Path -LiteralPath $currentPath){
   $current=Get-Item -LiteralPath $currentPath -Force -ErrorAction Stop
   if($current.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse-point receipt path rejected'}
  }else{return $full} # CheckFile still rejects a missing target.
 }
 return $full
}

function Invoke-WillowMemoryPreflight {
 param([string]$Path,[string]$Grant,[string]$Stage,$Memory,[string]$QueryError='',
       [DateTimeOffset]$ObservedUtc=[DateTimeOffset]::UtcNow)
 $physical=$null;$virtual=$null;$p=0L;$v=0L
 if($null -ne $Memory -and [long]::TryParse([string]$Memory.FreePhysicalMemory,[ref]$p) -and $p -ge 0){$physical=$p}
 if($null -ne $Memory -and [long]::TryParse([string]$Memory.FreeVirtualMemory,[ref]$v) -and $v -ge 0){$virtual=$v}
 $outcome='accepted';$reason='fresh_readings_meet_unchanged_floors'
 if($null -eq $physical -or $null -eq $virtual -or $QueryError){$outcome='blocked';$reason='memory_reading_unavailable_or_invalid'}
 elseif($physical -lt 1700000 -or $virtual -lt 2200000){$outcome='blocked';$reason='below_retained_memory_floor'}
 $evidence=[ordered]@{schema='daedalus.willow.prelaunch-memory/v2';grant=$Grant;stage=$Stage;
  observed_utc=$ObservedUtc.ToUniversalTime().ToString('o');units='KiB';
  physical_kib=$physical;virtual_kib=$virtual;physical_floor_kib=1700000;virtual_floor_kib=2200000;
  outcome=$outcome;reason=$reason;query_error=$QueryError;launched=$false;pid=$null}
 Write-WillowEvidence -Path $Path -Value $evidence
 # Evidence is durable BEFORE rejection; no launch is possible in this helper.
 if($outcome -ne 'accepted'){throw "Memory preflight blocked: $reason"}
 return $evidence
}

function Test-WillowMayRelease {
 param([bool]$Launched,[bool]$Terminal)
 return (-not $Launched -or $Terminal)
}

Export-ModuleMember -Function Write-WillowEvidence,ConvertTo-WillowPath,Resolve-WillowPath,Invoke-WillowMemoryPreflight,Test-WillowMayRelease
