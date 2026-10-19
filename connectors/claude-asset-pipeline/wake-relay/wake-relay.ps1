# SPDX-License-Identifier: MIT
# wake-relay.ps1 - tails a team-link log.jsonl and POSTs a webhook whenever a bot that
# cannot read the broker (a "wake-needed" bot) gets a direct message from any other sender.
param(
  [Parameter(Mandatory=$true)][string]$LinkFolder,
  [string]$ConfigPath,
  [string]$BotsPath,
  [string]$StatePath,
  [string]$LogPath,
  [string]$Source='bot-team-link',
  [int]$PollSeconds=20,
  [switch]$DryRun
)
$ErrorActionPreference='Continue'
if(-not $ConfigPath){$ConfigPath=Join-Path $LinkFolder 'relay-webhook.json'}
if(-not $BotsPath){$BotsPath=Join-Path $PSScriptRoot 'wake-bots.json'}
if(-not $StatePath){$StatePath=Join-Path $LinkFolder 'grok-relay.state'}
if(-not $LogPath){$LogPath=Join-Path $LinkFolder 'grok-relay.log'}
$log=Join-Path $LinkFolder 'log.jsonl'

function Get-WakeRegex([string]$path){
  $names=@((Get-Content $path -Raw | ConvertFrom-Json).wake)
  if($names.Count -eq 0){throw "no wake bots in $path"}
  $parts=$names | ForEach-Object { [regex]::Escape($_) -replace '\\\*','.*' }
  '^(' + ($parts -join '|') + ')$'
}
function Select-WakeHits([string]$chunk,[string]$rx){
  $hits=@()
  foreach($l in ($chunk -split "`n")){
    if(-not $l.Trim()){continue}
    try{$o=$l|ConvertFrom-Json}catch{continue}
    if($o.to -match $rx -and $o.from -notmatch $rx){
      $hits+=@{id=$o.id;ts=$o.ts;from=$o.from;to=$o.to;type=$o.type;text=[string]$o.body.text}
    }
  }
  ,$hits
}
# Config is the default webhook {url,key,header,prefix}, plus optional "overrides": {"<bot>": {url,key,header,prefix}}.
# A message to a bot with an override goes to that bot's webhook; everything else goes to the default.
function Group-WakeHits($hits,$cfg){
  $groups=[ordered]@{}
  foreach($m in $hits){
    $name='default'; $target=$cfg
    if($cfg.overrides -and $cfg.overrides.PSObject.Properties[$m.to]){ $name=$m.to; $target=$cfg.overrides.($m.to) }
    if(-not $groups.Contains($name)){ $groups[$name]=@{Name=$name;Target=$target;Messages=New-Object System.Collections.ArrayList} }
    [void]$groups[$name].Messages.Add($m)
  }
  @($groups.Values)
}
function W($m){ $line=("{0} {1}" -f (Get-Date -f 'MM-dd HH:mm:ss'),$m); if($DryRun){Write-Output $line}else{Add-Content $LogPath $line} }

$grok=Get-WakeRegex $BotsPath
if($DryRun){ $pos=0 } else { $pos= if(Test-Path $StatePath){[int64](Get-Content $StatePath)} else {(Get-Item $log).Length} }
W "start pos=$pos"
while($true){
  try{
    $len=(Get-Item $log).Length
    if($len -lt $pos){$pos=0}
    if($len -gt $pos){
      $fs=[IO.File]::Open($log,'Open','Read','ReadWrite'); $fs.Seek($pos,'Begin')|Out-Null
      $sr=New-Object IO.StreamReader($fs); $txt=$sr.ReadToEnd(); $sr.Close()
      $last=$txt.LastIndexOf("`n"); if($last -lt 0){ if($DryRun){break}; Start-Sleep 5;continue}
      $chunk=$txt.Substring(0,$last+1); $newPos=$pos+[Text.Encoding]::UTF8.GetByteCount($chunk)
      $hits=Select-WakeHits $chunk $grok
      if($DryRun){ $routes=@{}; if(Test-Path $ConfigPath){ $c=Get-Content $ConfigPath -Raw|ConvertFrom-Json; foreach($g in (Group-WakeHits $hits $c)){ $routes[$g.Name]=@($g.Messages|ForEach-Object{$_.id}) } }; Write-Output (@{source=$Source;messages=$hits;routes=$routes}|ConvertTo-Json -Depth 5 -Compress); break }
      if($hits.Count -gt 0){
        if(-not (Test-Path $ConfigPath)){ W "PENDING $($hits.Count) msgs, no $(Split-Path -Leaf $ConfigPath) yet"; Start-Sleep 20; continue }
        $c=Get-Content $ConfigPath -Raw|ConvertFrom-Json
        foreach($g in (Group-WakeHits $hits $c)){
          $h=@{}; $h[$g.Target.header]=("{0}{1}" -f $g.Target.prefix,$g.Target.key)
          $body=(@{source=$Source;messages=@($g.Messages)}|ConvertTo-Json -Depth 5 -Compress)
          Invoke-RestMethod -Uri $g.Target.url -Method Post -Headers $h -ContentType 'application/json' -Body $body -TimeoutSec 20 | Out-Null
          W ("POSTED {0} via {1}: {2}" -f $g.Messages.Count, $g.Name, (($g.Messages|ForEach-Object{"$($_.id) $($_.from)->$($_.to)"}) -join '; '))
        }
      }
      $pos=$newPos; Set-Content $StatePath $pos
    } elseif($DryRun){ Write-Output '{"messages":[]}'; break }
  }catch{ W "ERR $_"; if($DryRun){break}; Start-Sleep 30 }
  Start-Sleep $PollSeconds
}