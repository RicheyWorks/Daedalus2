# SPDX-License-Identifier: MIT
# Observes Unreal startup blockers without choosing recovery, rebuild, or dismissal actions.
#
# Runs beside the editor (setup-unreal.ps1 -Open starts it) for up to -Minutes, or until the Claude Unreal Bridge
# answers on 127.0.0.1:9877 and stays quiet for a while. Known blockers are logged and exit with code 2:
#   "Missing <Project> Modules"                        module_rebuild_required
#   "Restore Packages"                                  recovery_required (preserve/compare autosaves)
#   "Error"                                              modal_blocked (inspect its contents)
# Unknown dialogs are logged, not answered. Norton windows are never answered either: they are noted in
# %TEMP%\daedalus-norton.log (title and time) so Claude can tell you one is waiting and what it is about. What worked live (UE 5.8.3, Windows 11): bring the dialog to the front
# and press the real Enter key. Posted WM_COMMAND and UI Automation did not reach these dialogs.
param(
    [int]$Minutes = 12,
    [string]$Log = (Join-Path $env:TEMP "daedalus-dialog-watch.log")
)
Add-Type @"
using System; using System.Collections.Generic; using System.Runtime.InteropServices; using System.Text;
public static class DlgWatch {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    public static List<KeyValuePair<IntPtr, string>> Titled(HashSet<uint> pids) {
        var list = new List<KeyValuePair<IntPtr, string>>();
        EnumWindows((h, l) => {
            uint pid; GetWindowThreadProcessId(h, out pid);
            if (pids.Contains(pid) && IsWindowVisible(h)) {
                var s = new StringBuilder(512); GetWindowText(h, s, 512);
                if (s.Length > 0) list.Add(new KeyValuePair<IntPtr, string>(h, s.ToString()));
            }
            return true;
        }, IntPtr.Zero);
        return list;
    }
}
"@

$Rules = @(
    @{ Match = '^Restore Packages'; State = 'recovery_required' },
    @{ Match = '^Missing .* Modules$'; State = 'module_rebuild_required' },
    @{ Match = '^Error$'; State = 'modal_blocked' }
)
function Note($m) { "$(Get-Date -Format s) $m" | Out-File -FilePath $Log -Append -Encoding utf8 }

function BridgeUp {
    $client = New-Object Net.Sockets.TcpClient
    try { return ($client.ConnectAsync("127.0.0.1", 9877).Wait(250) -and $client.Connected) }
    catch { return $false }
    finally { $client.Dispose() }
}

Note "watching for $Minutes min"
$end = (Get-Date).AddMinutes($Minutes)
$seen = @{}
$upSince = $null
while ((Get-Date) -lt $end) {
    $pids = New-Object 'System.Collections.Generic.HashSet[uint32]'
    foreach ($p in Get-Process UnrealEditor -ErrorAction SilentlyContinue) { [void]$pids.Add([uint32]$p.Id) }
    if ($pids.Count -gt 0) {
        foreach ($w in [DlgWatch]::Titled($pids)) {
            $rule = $Rules | Where-Object { $w.Value -match $_.Match } | Select-Object -First 1
            if ($rule) {
                Note ("BLOCKED state={0} hwnd={1} title='{2}' action=none; owner review required" -f $rule.State, [long]$w.Key, $w.Value)
                exit 2
            } elseif (-not $seen.ContainsKey($w.Value) -and $w.Value -notmatch 'Unreal Editor|^Unreal Engine$') {
                $seen[$w.Value] = $true
                Note "left alone: '$($w.Value)'"
            }
        }
    }
    # Norton: report, never click. Security prompts are yours to answer.
    $npids = New-Object 'System.Collections.Generic.HashSet[uint32]'
    foreach ($p in Get-Process NortonUI, NortonSvc -ErrorAction SilentlyContinue) { [void]$npids.Add([uint32]$p.Id) }
    if ($npids.Count -gt 0) {
        foreach ($w in [DlgWatch]::Titled($npids)) {
            if (-not $seen.ContainsKey("norton:" + $w.Value)) {
                $seen["norton:" + $w.Value] = $true
                Note "NORTON window (left for you): '$($w.Value)'"
                "$(Get-Date -Format s) $($w.Value)" | Out-File -FilePath (Join-Path $env:TEMP "daedalus-norton.log") -Append -Encoding utf8
            }
        }
    }
    if (BridgeUp) {
        if (-not $upSince) { $upSince = Get-Date; Note "bridge listener observed; editor readiness unverified" }
        elseif (((Get-Date) - $upSince).TotalSeconds -gt 60) { Note "listener remained up; inspect health before dispatch"; break }
    }
    Start-Sleep -Milliseconds 700
}
Note "stopped"
