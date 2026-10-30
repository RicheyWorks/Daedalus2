# SPDX-License-Identifier: MIT
# Hidden PCG ecology job: one UnrealEditor-Cmd run, no window, no .uproject edit (PCG enabled per run).
# Refuses to start if any UnrealEditor is running (one editor at a time on BLACKBEARD) and announces on the team link.
param([string]$Project = "C:\Unreal\DaedalusRealm\DaedalusRealm.uproject",
      [string]$Engine = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe",
      [switch]$NullRhi)
$here = $PSScriptRoot
function Link($text) { try { $b = @{from='pythagoras';to='*';type='note';body=@{text=$text}} | ConvertTo-Json -Depth 4
  Invoke-WebRequest -UseBasicParsing -Method Post -Uri http://127.0.0.1:9890/send -Body $b -ContentType 'application/json' | Out-Null } catch {} }
if (Get-Process UnrealEditor* -ErrorAction SilentlyContinue) { "BUSY: another Unreal editor is running; not starting"; exit 2 }
Link "Pythagoras: taking the Unreal editor slot now (hidden UnrealEditor-Cmd, PCG ecology job)."
$rhi = if ($NullRhi) { "-nullrhi" } else { "-RenderOffscreen" }
$log = Join-Path $here "out\job.log"; New-Item -ItemType Directory -Force (Join-Path $here "out") | Out-Null
$a = "`"$Project`" -run=pythonscript -script=`"$here\build_pcg_ecology.py`" -EnablePlugins=PCG -unattended $rhi -nosplash -nop4 -NoSound -stdout -abslog=`"$log`""
$t = Get-Date
$p = Start-Process $Engine -ArgumentList $a -WindowStyle Hidden -PassThru -Wait
$secs = [int]((Get-Date) - $t).TotalSeconds
Link "Pythagoras: released the Unreal editor slot (exit $($p.ExitCode), $secs s)."
"exit $($p.ExitCode) in $secs s"
