# SPDX-License-Identifier: MIT
# Window harness for the Unreal connector (Windows). It works outside the editor, so it still works while a
# modal dialog has frozen the editor's game thread and with it the in-editor bridge.
#   -Op list                              every visible top-level window of UnrealEditor processes, each with a
#                                         PNG (PrintWindow, so a covered window is captured too) as JSON
#   -Op input -Hwnd N -Keys "enter"       bring window N to the front and press keys (enter, escape, tab, space,
#                                         left, right, up, down, alt+f4, or several separated by spaces)
#   -Op input -Hwnd N -X 120 -Y 80        click at (X, Y) inside window N, in the window's own pixels (as in its PNG)
#   -Op input -Hwnd N -Action close       ask window N to close (WM_CLOSE: the same as clicking its X)
#   -Op input -Hwnd N -Action minimize|restore|maximize
#   -Op input -Hwnd N -Action move -X 100 -Y 100 [-W 1200 -H 800]   move (and size) window N on screen
# Output: one JSON object on stdout.
param(
    [ValidateSet("list", "input", "workers")][string]$Op = "list",
    [long]$Hwnd = 0,
    [string]$Keys = "",
    [int]$X = -1,
    [int]$Y = -1,
    [ValidateSet("", "close", "minimize", "restore", "maximize", "move")][string]$Action = "",
    [int]$W = 0,
    [int]$H = 0,
    [int]$MaxImages = 6
)
$ErrorActionPreference = "Stop"
$workerConsoles = $null
if ($Op -eq 'list' -or $Op -eq 'workers') {
    # Kept separate from editor windows: the dialog watcher must never press keys on a worker console.
    . (Join-Path $PSScriptRoot 'worker-console.ps1')
    $workerConsoles = Invoke-DaedalusWorkerConsoleCheck
    if ($Op -eq 'workers') {
        @{ ok = $true; worker_consoles = $workerConsoles } | ConvertTo-Json -Depth 5 -Compress
        exit 0
    }
}
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class DaedalusWin {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint f, UIntPtr e);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    public static List<IntPtr> Windows(HashSet<uint> pids) {
        var list = new List<IntPtr>();
        EnumWindows((h, l) => {
            uint pid; GetWindowThreadProcessId(h, out pid);
            if (pids.Contains(pid) && IsWindowVisible(h)) list.Add(h);
            return true;
        }, IntPtr.Zero);
        return list;
    }
    public static string Text(IntPtr h) { var s = new StringBuilder(512); GetWindowText(h, s, 512); return s.ToString(); }
    public static string Cls(IntPtr h) { var s = new StringBuilder(256); GetClassName(h, s, 256); return s.ToString(); }
    // Windows only lets a process take the foreground in some cases; a tap of Alt first satisfies it.
    public static bool Front(IntPtr h) {
        if (IsIconic(h)) ShowWindow(h, 9);
        keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero);
        SetForegroundWindow(h);
        System.Threading.Thread.Sleep(150);
        return GetForegroundWindow() == h;
    }
}
"@

function Get-EditorPids {
    $set = New-Object 'System.Collections.Generic.HashSet[uint32]'
    foreach ($p in Get-Process UnrealEditor -ErrorAction SilentlyContinue) { [void]$set.Add([uint32]$p.Id) }
    return , $set
}

function Get-Png([IntPtr]$h, [int]$w, [int]$hgt) {
    if ($w -le 0 -or $hgt -le 0) { return $null }
    $bmp = New-Object System.Drawing.Bitmap $w, $hgt
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    $ok = [DaedalusWin]::PrintWindow($h, $hdc, 2)   # PW_RENDERFULLCONTENT: works for DirectX-drawn windows
    $g.ReleaseHdc($hdc); $g.Dispose()
    if (-not $ok) { $bmp.Dispose(); return $null }
    # Keep images small enough to send: scale the longest edge to at most 1400 px.
    $scale = [Math]::Min(1.0, 1400.0 / [Math]::Max($w, $hgt))
    if ($scale -lt 1.0) {
        $small = New-Object System.Drawing.Bitmap ([int]($w * $scale)), ([int]($hgt * $scale))
        $g2 = [System.Drawing.Graphics]::FromImage($small); $g2.DrawImage($bmp, 0, 0, $small.Width, $small.Height); $g2.Dispose()
        $bmp.Dispose(); $bmp = $small
    }
    $ms = New-Object System.IO.MemoryStream
    $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
    return [pscustomobject]@{ png = [Convert]::ToBase64String($ms.ToArray()); scale = $scale }
}

$VK = @{ enter = 0x0D; return = 0x0D; escape = 0x1B; esc = 0x1B; tab = 0x09; space = 0x20; left = 0x25; up = 0x26;
         right = 0x27; down = 0x28; alt = 0x12; ctrl = 0x11; shift = 0x10; f4 = 0x73; y = 0x59; n = 0x4E }

function Send-Chord([string]$chord) {
    $parts = $chord.ToLower().Split("+")
    $codes = foreach ($p in $parts) { if (-not $VK.ContainsKey($p)) { throw "unknown key '$p' (known: $($VK.Keys -join ', '))" }; [byte]$VK[$p] }
    foreach ($c in $codes) { [DaedalusWin]::keybd_event($c, 0, 0, [UIntPtr]::Zero) }
    [array]::Reverse($codes)
    foreach ($c in $codes) { [DaedalusWin]::keybd_event($c, 0, 2, [UIntPtr]::Zero) }
    Start-Sleep -Milliseconds 80
}

try {
    $pids = Get-EditorPids
    if ($pids.Count -eq 0) { @{ ok = $true; windows = @(); worker_consoles = $workerConsoles; note = "no UnrealEditor is running" } | ConvertTo-Json -Depth 5 -Compress; exit 0 }
    if ($Op -eq "list") {
        $out = @(); $n = 0
        # Largest window first: that is the main editor; dialogs and popups follow.
        $wins = foreach ($hw in [DaedalusWin]::Windows($pids)) {
            $r = New-Object DaedalusWin+RECT; [void][DaedalusWin]::GetWindowRect($hw, [ref]$r)
            # A minimised window's rect is tiny: rank it by its restored size so the editor still comes first.
            $area = ($r.Right - $r.Left) * ($r.Bottom - $r.Top)
            if ([DaedalusWin]::IsIconic($hw)) { $area = 1e9 }
            [pscustomobject]@{ h = $hw; r = $r; area = $area }
        }
        $wins = @($wins | Where-Object { $_.area -gt 400 } | Sort-Object area -Descending)
        for ($i = 0; $i -lt $wins.Count; $i++) {
            # Not $w / $h: PowerShell names ignore case, and the typed [int]$W / [int]$H parameters would swallow them.
            $win = $wins[$i]; $width = $win.r.Right - $win.r.Left; $height = $win.r.Bottom - $win.r.Top
            $entry = [ordered]@{ hwnd = [long]$win.h; title = [DaedalusWin]::Text($win.h); class = [DaedalusWin]::Cls($win.h);
                                 main = ($i -eq 0); minimized = [DaedalusWin]::IsIconic($win.h);
                                 x = $win.r.Left; y = $win.r.Top; width = $width; height = $height }
            if ($n -lt $MaxImages -and -not [DaedalusWin]::IsIconic($win.h)) {
                $img = Get-Png $win.h $width $height
                if ($img) { $entry.png = $img.png; $entry.image_scale = $img.scale; $n++ }
            }
            $out += [pscustomobject]$entry
        }
        @{ ok = $true; foreground = [long][DaedalusWin]::GetForegroundWindow(); windows = $out; worker_consoles = $workerConsoles } | ConvertTo-Json -Depth 5 -Compress
    } else {
        $h = [IntPtr]$Hwnd
        $owned = [DaedalusWin]::Windows($pids) | Where-Object { $_ -eq $h }
        if (-not $owned) { throw "window $Hwnd is not an open Unreal Editor window (call editor_windows again)" }
        $did = @()
        if ($Action) {
            switch ($Action) {
                "close"    { [void][DaedalusWin]::PostMessage($h, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) }   # WM_CLOSE
                "minimize" { [void][DaedalusWin]::ShowWindow($h, 6) }
                "restore"  { [void][DaedalusWin]::ShowWindow($h, 9) }
                "maximize" { [void][DaedalusWin]::ShowWindow($h, 3) }
                "move"     {
                    $r = New-Object DaedalusWin+RECT; [void][DaedalusWin]::GetWindowRect($h, [ref]$r)
                    $cw = if ($W -gt 0) { $W } else { $r.Right - $r.Left }; $ch = if ($H -gt 0) { $H } else { $r.Bottom - $r.Top }
                    [void][DaedalusWin]::SetWindowPos($h, [IntPtr]::Zero, $X, $Y, $cw, $ch, 0x0014)   # NOZORDER|NOACTIVATE
                }
            }
            $did += $Action
            Start-Sleep -Milliseconds 400
            $still = [bool]([DaedalusWin]::Windows($pids) | Where-Object { $_ -eq $h })
            @{ ok = $true; hwnd = $Hwnd; did = $did; window_still_open = $still } | ConvertTo-Json -Compress
            exit 0
        }
        $front = [DaedalusWin]::Front($h)
        if ($X -ge 0 -and $Y -ge 0) {
            $r = New-Object DaedalusWin+RECT; [void][DaedalusWin]::GetWindowRect($h, [ref]$r)
            [void][DaedalusWin]::SetCursorPos($r.Left + $X, $r.Top + $Y)
            Start-Sleep -Milliseconds 60
            [DaedalusWin]::mouse_event(0x02, 0, 0, 0, [UIntPtr]::Zero); [DaedalusWin]::mouse_event(0x04, 0, 0, 0, [UIntPtr]::Zero)
            $did += "click $X,$Y"
            Start-Sleep -Milliseconds 120
        }
        foreach ($chord in ($Keys -split "\s+" | Where-Object { $_ })) { Send-Chord $chord; $did += $chord }
        Start-Sleep -Milliseconds 400
        $still = [bool]([DaedalusWin]::Windows($pids) | Where-Object { $_ -eq $h })
        @{ ok = $true; hwnd = $Hwnd; brought_to_front = $front; did = $did; window_still_open = $still } | ConvertTo-Json -Compress
    }
} catch {
    @{ ok = $false; message = $_.Exception.Message } | ConvertTo-Json -Compress
    exit 1
}
