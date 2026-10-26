# Blender Boss Island editor turn. Run ONLY on a granted editor slot (CLAIM editor-slot ... on the link first; HANDOFF after).
# Sends bb_island_ue.py to the running editor through the 9877 bridge (ue_send.py, async + job poll), then closes floating
# panels (Content Browser, Message Log) with studio-screen-connector tidy.ps1 -Once.
param([int]$Timeout = 540)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ue = Join-Path $here "bb_island_ue.py"
$send = @("C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py", "C:\Users\730ri\projects\Daedalus2-ark-dock\engines\unreal\ark-dock\ue_send.py") | ? { Test-Path $_ } | select -First 1
if (-not $send) { Write-Error "ue_send.py not found"; exit 2 }
python $send $ue $Timeout
$code = $LASTEXITCODE
$tidy = @("C:\Users\730ri\projects\studio-screen-connector\tidy.ps1", "C:\Users\730ri\projects\bot-team\hooks\tidy.ps1") | ? { Test-Path $_ } | select -First 1
if ($tidy) { powershell -NoProfile -ExecutionPolicy Bypass -File $tidy -Once } else { Write-Warning "tidy.ps1 not found: close Content Browser and Message Log by hand" }
exit $code
