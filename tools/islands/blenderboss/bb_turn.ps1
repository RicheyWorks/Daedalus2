# Blender Boss Island editor turn. Run ONLY on a granted editor slot (CLAIM editor-slot ... on the link first; HANDOFF after).
# Sends bb_island_ue.py to the running editor through the 9877 bridge, then closes panels (Content Browser, Message Log) with tidy.ps1.
param([int]$Timeout = 900)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ue = Join-Path $here "bb_island_ue.py"
$send = "C:\Users\730ri\projects\pcg-ecology\ue_send.py"
python $send $ue $Timeout
$code = $LASTEXITCODE
$tidy = @("C:\Users\730ri\projects\bot-team\hooks\tidy.ps1", "C:\Users\730ri\projects\bot-team\hooks\post-job.ps1") | ? { Test-Path $_ } | select -First 1
if ($tidy) { powershell -NoProfile -ExecutionPolicy Bypass -File $tidy } else { Write-Warning "tidy.ps1 not found: close Content Browser and Message Log by hand" }
exit $code
