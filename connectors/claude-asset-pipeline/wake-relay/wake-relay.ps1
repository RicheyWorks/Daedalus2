# SPDX-License-Identifier: MIT
# wake-relay.ps1 - tails a team-link log.jsonl and POSTs a webhook whenever a bot that
# cannot read the broker (a "wake-needed" bot) gets a direct message from any other sender.
#
# Routing: relay-webhook.json holds a default webhook {url,key,header,prefix}, optional named
# "overrides" {"<target>": {url,key,header,prefix}}, and an optional "routes" map
# {"<recipient or glob>": "default" | "<override name>"}. When "routes" is present it is the only
# authority: a recipient with no route, or a route naming a missing override, stays PENDING in
# grok-relay.pending.jsonl and is never sent to the default. Without "routes" the old behaviour
# (override by exact name, else default) still works.
# Delivery: each route is POSTed separately. A failed POST keeps only that route's messages
# PENDING and retries them; delivered ids go to grok-relay.delivered.txt so nothing is sent twice.
# Pending is written before the read position advances, so a restart loses nothing and never
# replays the old log.
param(
  [Parameter(Mandatory=$true)][string]$LinkFolder,
  [string]$ConfigPath,
  [string]$BotsPath,
  [string]$StatePath,
  [string]$LogPath,
  [string]$PendingPath,
  [string]$DeliveredPath,
  [string]$Source='bot-team-link',
  [int]$PollSeconds=20,
  [switch]$DryRun
)
$ErrorActionPreference='Continue'
if(-not $ConfigPath){$ConfigPath=Join-Path $LinkFolder 'relay-webhook.json'}
if(-not $BotsPath){$BotsPath=Join-Path $PSScriptRoot 'wake-bots.json'}
if(-not $StatePath){$StatePath=Join-Path $LinkFolder 'grok-relay.state'}
if(-not $LogPath){$LogPath=Join-Path $LinkFolder 'grok-relay.log'}
if(-not $PendingPath){$PendingPath=Join-Path $LinkFolder 'grok-relay.pending.jsonl'}
if(-not $DeliveredPath){$DeliveredPath=Join-Path $LinkFolder 'grok-relay.delivered.txt'}
$log=Join-Path $LinkFolder 'log.jsonl'

function Get-WakeRegex([string]$path){
  $names=@((Get-Content $path -Raw | ConvertFrom-Json).wake)
  if($names.Count -eq 0){throw "no wake bots in $path"}
  $parts=$names | ForEach-Object { [regex]::Escape($_) -replace '\\\*','.*' }
  '^(' + ($parts -join '|') + ')$'
}
function Get-Text($o){ if($null -eq $o.body){return ''}; if($o.body -is [string]){return $o.body}; [string]$o.body.text }
function Get-RequestId($o){
  if($o.request_id){return [string]$o.request_id}
  if($o.body -and -not ($o.body -is [string]) -and $o.body.request_id){return [string]$o.body.request_id}
  ''
}
# Envelope keeps the broker's correlation fields, not just the body text.
function Select-WakeHits([string]$chunk,[string]$rx){
  $hits=@()
  foreach($l in ($chunk -split "`n")){
    if(-not $l.Trim()){continue}
    try{$o=$l|ConvertFrom-Json}catch{continue}
    if($o.to -match $rx -and $o.from -notmatch $rx){
      $hits+=[pscustomobject][ordered]@{id=$o.id;ts=$o.ts;from=$o.from;to=$o.to;type=$o.type;topic=[string]$o.topic;reply_to=$o.reply_to;request_id=(Get-RequestId $o);pointer=('log.jsonl#id='+$o.id);text=(Get-Text $o)}
    }
  }
  ,$hits
}
function Resolve-Route([string]$to,$cfg){
  if($cfg.routes){
    $r=$null
    $p=$cfg.routes.PSObject.Properties[$to]
    if($p){$r=[string]$p.Value}else{ foreach($q in $cfg.routes.PSObject.Properties){ if($q.Name.Contains('*') -and $to -like $q.Name){$r=[string]$q.Value;break} } }
    if(-not $r){return $null}
    if($r -eq 'default'){return @{Name='default';Target=$cfg}}
    if($cfg.overrides -and $cfg.overrides.PSObject.Properties[$r]){return @{Name=$r;Target=$cfg.overrides.$r}}
    return $null
  }
  if($cfg.overrides -and $cfg.overrides.PSObject.Properties[$to]){return @{Name=$to;Target=$cfg.overrides.$to}}
  @{Name='default';Target=$cfg}
}
function Group-WakeHits($hits,$cfg){
  $groups=[ordered]@{}; $unbound=New-Object System.Collections.ArrayList
  foreach($m in $hits){
    $rt=Resolve-Route ([string]$m.to) $cfg
    if(-not $rt){[void]$unbound.Add($m);continue}
    if(-not $groups.Contains($rt.Name)){$groups[$rt.Name]=@{Name=$rt.Name;Target=$rt.Target;Messages=New-Object System.Collections.ArrayList}}
    [void]$groups[$rt.Name].Messages.Add($m)
  }
  @{Groups=@($groups.Values);Unbound=@($unbound)}
}
function Read-Pending{ $a=@(); if(Test-Path $PendingPath){ foreach($l in Get-Content $PendingPath){ if($l.Trim()){ try{$a+=($l|ConvertFrom-Json)}catch{} } } }; ,$a }
function Write-Pending($items){ $tmp="$PendingPath.tmp"; $lines=[string[]]@($items|ForEach-Object{ $_|ConvertTo-Json -Depth 5 -Compress }); [IO.File]::WriteAllLines($tmp,$lines); Move-Item -Force $tmp $PendingPath }
function W($m){ $line=("{0} {1}" -f (Get-Date -f 'MM-dd HH:mm:ss'),$m); if($DryRun){Write-Output $line}else{Add-Content $LogPath $line} }

$grok=Get-WakeRegex $BotsPath
$delivered=New-Object 'System.Collections.Generic.HashSet[string]'
if(-not $DryRun -and (Test-Path $DeliveredPath)){ foreach($l in Get-Content $DeliveredPath){ if($l.Trim()){[void]$delivered.Add($l.Trim())} } }
if($DryRun){ $pos=0; $queue=@() } else { $pos= if(Test-Path $StatePath){[int64](Get-Content $StatePath)} else {(Get-Item $log).Length}; $queue=Read-Pending }
if(-not $DryRun){ W "start pos=$pos pending=$(@($queue).Count)" }
$lastNote=''
while($true){
  try{
    $hits=@(); $newPos=$pos
    $len=(Get-Item $log).Length
    if($len -lt $pos){$pos=0;$newPos=0}
    if($len -gt $pos){
      $fs=[IO.File]::Open($log,'Open','Read','ReadWrite'); $fs.Seek($pos,'Begin')|Out-Null
      $sr=New-Object IO.StreamReader($fs); $txt=$sr.ReadToEnd(); $sr.Close()
      $last=$txt.LastIndexOf("`n")
      if($last -ge 0){ $chunk=$txt.Substring(0,$last+1); $newPos=$pos+[Text.Encoding]::UTF8.GetByteCount($chunk); $hits=Select-WakeHits $chunk $grok }
    }
    $seen=@{}; $work=New-Object System.Collections.ArrayList
    foreach($m in (@($queue)+@($hits))){ if($null -eq $m){continue}; $k=[string]$m.id; if($seen.ContainsKey($k) -or $delivered.Contains($k)){continue}; $seen[$k]=1; [void]$work.Add($m) }
    if($DryRun){
      $out=[ordered]@{source=$Source;messages=@($work);routes=[ordered]@{};pending=@()}
      if(Test-Path $ConfigPath){ $c=Get-Content $ConfigPath -Raw|ConvertFrom-Json; $g=Group-WakeHits $work $c; foreach($x in $g.Groups){$out.routes[$x.Name]=@($x.Messages|ForEach-Object{$_.id})}; $out.pending=@($g.Unbound|ForEach-Object{$_.id}) } else { $out.pending=@($work|ForEach-Object{$_.id}) }
      Write-Output ($out|ConvertTo-Json -Depth 6 -Compress); break
    }
    $still=New-Object System.Collections.ArrayList
    if($work.Count -gt 0){
      if(-not (Test-Path $ConfigPath)){ foreach($m in $work){[void]$still.Add($m)} }
      else{
        $c=Get-Content $ConfigPath -Raw|ConvertFrom-Json
        $g=Group-WakeHits $work $c
        foreach($m in $g.Unbound){[void]$still.Add($m)}
        foreach($x in $g.Groups){
          try{
            $h=@{}; $h[$x.Target.header]=("{0}{1}" -f $x.Target.prefix,$x.Target.key)
            $body=(@{source=$Source;route=$x.Name;messages=@($x.Messages)}|ConvertTo-Json -Depth 6 -Compress)
            Invoke-RestMethod -Uri $x.Target.url -Method Post -Headers $h -ContentType 'application/json' -Body $body -TimeoutSec 20 | Out-Null
            Add-Content $DeliveredPath (@($x.Messages|ForEach-Object{[string]$_.id}))
            foreach($m in $x.Messages){[void]$delivered.Add([string]$m.id)}
            W ("POSTED {0} via {1}: {2}" -f $x.Messages.Count, $x.Name, (($x.Messages|ForEach-Object{"$($_.id) $($_.from)->$($_.to)"}) -join '; '))
          }catch{ foreach($m in $x.Messages){[void]$still.Add($m)}; W ("ERR route {0}: {1}; {2} kept PENDING" -f $x.Name,$_.Exception.Message,$x.Messages.Count) }
        }
      }
      Write-Pending $still
    }
    $queue=@($still)
    $pos=$newPos; Set-Content $StatePath $pos
    $note= if($queue.Count -gt 0){ "PENDING {0}: {1}" -f $queue.Count, (($queue|ForEach-Object{"$($_.id)->$($_.to)"}) -join '; ') } else { '' }
    if($note -ne $lastNote){ if($note){W $note}else{W 'PENDING cleared'}; $lastNote=$note }
  }catch{ W "ERR $_"; if($DryRun){break}; Start-Sleep 30 }
  Start-Sleep $PollSeconds
}
