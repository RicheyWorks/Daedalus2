# SPDX-License-Identifier: MIT
# Answers the Unreal Editor's startup dialogs so nobody has to click them.
#
# Runs beside the editor (setup-unreal.ps1 -Open starts it) for up to -Minutes, or until the Claude Unreal Bridge
# answers on 127.0.0.1:9877 and stays quiet for a while. Each known dialog gets the answer a person would give:
#   "Missing <Project> Modules ... rebuild them now?"   Yes (Enter: the default button)
#   "Restore Packages"                                  skip restoring (Escape)
#   "Error" ("<Project> could not be compiled")         OK (Enter), logged as a build failure to look at
# Unknown dialogs are logged, not answered. What worked live (UE 5.8.3, Windows 11): bring the dialog to the front
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
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint f, UIntPtr e);
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
    public static bool Press(IntPtr h, byte vk) {
        keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero);   // Alt tap: lets us take focus
        SetForegroundWindow(h);
        System.Threading.Thread.Sleep(250);
        if (GetForegroundWindow() != h) return false;
        keybd_event(vk, 0, 0, UIntPtr.Zero); keybd_event(vk, 0, 2, UIntPtr.Zero);
        return true;
    }
}
"@

$Rules = @(
    @{ Match = '^Missing .* Modules$'; Key = 0x0D; Say = 'rebuild: Yes' },
    @{ Match = '^Restore Packages'; Key = 0x1B; Say = 'restore packages: skip' },
    @{ Match = '^Error$'; Key = 0x0D; Say = 'error box: OK (if it says could not be compiled, the build failed: read the setup log)' }
)
function Note($m) { "$(Get-Date -Format s) $m" | Out-File -FilePath $Log -Append -Encoding utf8 }

function BridgeUp {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", 9877); $c.Close(); return $true } catch { return $false }
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
                $ok = [DlgWatch]::Press($w.Key, [byte]$rule.Key)
                Start-Sleep -Milliseconds 800
                Note ("'{0}' -> {1} (pressed={2}, closed={3})" -f $w.Value, $rule.Say, $ok, -not [DlgWatch]::IsWindow($w.Key))
            } elseif (-not $seen.ContainsKey($w.Value) -and $w.Value -notmatch 'Unreal Editor|^Unreal Engine$') {
                $seen[$w.Value] = $true
                Note "left alone: '$($w.Value)'"
            }
        }
    }
    if (BridgeUp) {
        if (-not $upSince) { $upSince = Get-Date; Note "bridge is up" }
        elseif (((Get-Date) - $upSince).TotalSeconds -gt 60) { Note "editor ready; done"; break }
    }
    Start-Sleep -Milliseconds 700
}
Note "stopped"
