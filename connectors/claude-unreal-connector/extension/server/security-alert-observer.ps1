# SPDX-License-Identifier: MIT
# One read-only Norton observation. The caller owns command correlation and its
# absolute subprocess deadline; this provider never launches or controls a build.
# No input, settings, screenshots, upload, retry, or background service is used.
param([string]$ArtifactPath = '', [switch]$RequestScreenshot)

$ErrorActionPreference = 'Stop'
$MaxWindows = 8
$MaxNodes = 24
$MaxTitle = 256
$MaxText = 1024
$BudgetMs = 700
$script:ArtifactSeen = $false
$script:ArtifactPattern = ''

function Write-Observation([bool]$available, [string]$reason, $windows) {
    [pscustomobject]@{ available = $available; reason = $reason; observed_at = [DateTime]::UtcNow.ToString('o'); windows = @($windows) } |
        ConvertTo-Json -Compress -Depth 5
}

function Protect-AlertText([string]$value, [int]$limit) {
    if (-not $value) { return '' }
    # UIA is read only from a matching Norton window. Retain alert/build-file
    # snippets, not account/profile/navigation text. Identifiers are redacted.
    $alert = '(?i)block(?:ed|ing)?|quarantin|threat|malware|suspicious|sonar|reputation|security risk|access denied|prevented|detected|sandbox|analy[sz](?:ing|ed|is)|scan(?:ning|ned)?|evaluat|under review|safe'
    $artifact = '(?i)\.(?:exe|dll|obj|pdb|cpp|c|h|hpp|py|js|ps1|uproject|uplugin)\b'
    $parts = New-Object 'System.Collections.Generic.List[string]'
    foreach ($line in ($value -split '[\r\n]+')) {
        $containsCurrent = $script:ArtifactPattern -and [regex]::IsMatch($line, $script:ArtifactPattern)
        if ($line -notmatch $alert -and $line -notmatch $artifact -and -not $containsCurrent) { continue }
        # Preserve only an actually witnessed exact caller artifact. Never echo
        # context as evidence when it was absent from the Norton window.
        $safe = $line
        $marker = [string][char]31 + 'CURRENT_ARTIFACT_' + [guid]::NewGuid().ToString('N') + [char]31
        if ($containsCurrent) {
            $script:ArtifactSeen = $true
            $safe = [regex]::Replace($safe, $script:ArtifactPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $marker })
        }
        # Unknown absolute paths are omitted entirely; a different file with
        # the same basename must not become current-artifact evidence.
        $safe = [regex]::Replace($safe, '(?i)(?:[A-Z]:[\\/]|\\\\)[^\r\n"<>|]*', '[path]')
        $safe = [regex]::Replace($safe, '(?i)/(?:Users|home)/[^\r\n"<>|]*', '[path]')
        $safe = [regex]::Replace($safe, '(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[email]')
        $safe = [regex]::Replace($safe, '(?i)([A-Z]:\\Users\\)[^\\\s]+', '$1[user]')
        $safe = [regex]::Replace($safe, '(?i)(/(?:Users|home)/)[^/\s]+', '$1[user]')
        $safe = [regex]::Replace($safe, '(?i)https?://\S+', '[url]')
        $safe = [regex]::Replace($safe, '(?i)\b(?:user(?:name)?|account|email|signed in as)\s*[:=]\s*[^,;\r\n]+', '[identity]')
        $safe = $safe.Replace($marker, $ArtifactPath)
        $safe = [regex]::Replace($safe, '[\x00-\x08\x0b\x0c\x0e-\x1f]', '')
        if ($safe.Length -gt $limit) { $safe = $safe.Substring(0, $limit) }
        [void]$parts.Add($safe.Trim())
        if (($parts -join "`n").Length -ge $limit) { break }
    }
    $text = $parts -join "`n"
    if ($text.Length -gt $limit) { $text = $text.Substring(0, $limit) }
    return $text
}

function Read-NortonAccessibility([IntPtr]$handle, [uint32]$expectedPid, $watch) {
    $element = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
    if (-not $element) { throw 'Accessibility unavailable' }
    $queue = New-Object 'System.Collections.Generic.Queue[object]'
    $queue.Enqueue([pscustomobject]@{ element = $element; depth = 0 })
    $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
    $snippets = New-Object 'System.Collections.Generic.List[string]'
    $visited = 0
    while ($queue.Count -gt 0 -and $visited -lt $MaxNodes) {
        if ($watch.ElapsedMilliseconds -ge $BudgetMs) { throw 'Observation budget exhausted' }
        $entry = $queue.Dequeue()
        $current = $entry.element.Current
        # Check each accessibility element's process before fetching its Name.
        if ([uint32]$current.ProcessId -ne $expectedPid) { continue }
        $visited++
        $name = [string]$current.Name
        if ($name.Length -gt 2048) { $name = $name.Substring(0, 2048) }
        $safe = Protect-AlertText $name $MaxText
        if ($safe -and -not $snippets.Contains($safe)) { [void]$snippets.Add($safe) }
        if (($snippets -join "`n").Length -ge $MaxText) { break }
        if ($entry.depth -ge 4) { continue }
        $child = $walker.GetFirstChild($entry.element)
        $siblings = 0
        while ($child -and $siblings -lt $MaxNodes -and $queue.Count + $visited -lt $MaxNodes) {
            if ($watch.ElapsedMilliseconds -ge $BudgetMs) { throw 'Observation budget exhausted' }
            $queue.Enqueue([pscustomobject]@{ element = $child; depth = $entry.depth + 1 })
            $siblings++
            $child = $walker.GetNextSibling($child)
        }
    }
    return Protect-AlertText ($snippets -join "`n") $MaxText
}

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        Write-Observation $false 'unsupported_platform' @(); exit 0
    }
    $absolute = $ArtifactPath -match '^[A-Za-z]:[\\/]' -or $ArtifactPath -match '^\\\\[^\\/]+\\[^\\/]+\\'
    if (-not $absolute -or $ArtifactPath.Length -gt 1024 -or $ArtifactPath -match '[\x00-\x1f"<>|?*]') {
        Write-Observation $false 'artifact_context_unavailable' @(); exit 0
    }
    try { $ArtifactPath = [IO.Path]::GetFullPath($ArtifactPath) }
    catch { Write-Observation $false 'artifact_context_unavailable' @(); exit 0 }
    $script:ArtifactPattern = '(?i)(?<![A-Za-z0-9_\\/])' + [regex]::Escape($ArtifactPath) + '(?=$|[\s"'',;)])'
    # Named lookup only: never inspect unrelated process command lines or paths.
    $processErrors = @()
    $nortonProcesses = @(Get-Process -Name 'NortonUI', 'Norton' -ErrorAction SilentlyContinue -ErrorVariable processErrors)
    if (@($processErrors | Where-Object { $_.FullyQualifiedErrorId -notmatch '^NoProcessFoundForGivenName' }).Count) {
        Write-Observation $false 'inspection_unavailable' @(); exit 0
    }
    $candidateNames = @{}
    $candidatePids = New-Object 'System.Collections.Generic.HashSet[uint32]'
    foreach ($candidate in $nortonProcesses) {
        if ($candidate.ProcessName -notin @('NortonUI', 'Norton')) { continue }
        $candidateNames[[uint32]$candidate.Id] = [string]$candidate.ProcessName
        [void]$candidatePids.Add([uint32]$candidate.Id)
    }
    if ($candidatePids.Count -eq 0) {
        Write-Observation $true 'no_matching_processes' @(); exit 0
    }
    if (-not ('DaedalusNortonReadOnlyWindows' -as [type])) {
        Add-Type @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
public static class DaedalusNortonReadOnlyWindows {
    private delegate bool EnumProc(IntPtr h, IntPtr data);
    [DllImport("user32.dll", SetLastError=true)] private static extern bool EnumWindows(EnumProc callback, IntPtr data);
    [DllImport("user32.dll", SetLastError=true)] private static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("kernel32.dll", EntryPoint="SetLastError")] private static extern void ResetLastError(uint error);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)] private static extern int GetWindowText(IntPtr h, StringBuilder text, int count);
    public static List<IntPtr> Matching(HashSet<uint> pids, int maximum) {
        var result = new List<IntPtr>();
        bool truncated = false;
        bool ok = EnumWindows((h, data) => {
            uint pid;
            if (GetWindowThreadProcessId(h, out pid) == 0) return true;
            // PID filtering precedes visibility/title/accessibility inspection.
            if (!pids.Contains(pid) || !IsWindowVisible(h)) return true;
            result.Add(h);
            if (result.Count >= maximum) { truncated = true; return false; }
            return true;
        }, IntPtr.Zero);
        if (!ok && !truncated) throw new Win32Exception(Marshal.GetLastWin32Error());
        return result;
    }
    public static uint Pid(IntPtr h) {
        uint pid;
        if (GetWindowThreadProcessId(h, out pid) == 0) throw new Win32Exception(Marshal.GetLastWin32Error());
        return pid;
    }
    public static string Title(IntPtr h, int maximum) {
        var text = new StringBuilder(maximum + 1);
        ResetLastError(0); // Empty titles must not inherit an unrelated prior error.
        if (GetWindowText(h, text, text.Capacity) == 0 && Marshal.GetLastWin32Error() != 0)
            throw new Win32Exception(Marshal.GetLastWin32Error());
        return text.ToString();
    }
}
'@
    }
    $handles = @([DaedalusNortonReadOnlyWindows]::Matching($candidatePids, $MaxWindows))
    if (-not $handles.Count) { Write-Observation $true 'no_matching_windows' @(); exit 0 }
    Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $windows = New-Object 'System.Collections.Generic.List[object]'
    foreach ($handle in $handles) {
        if ($watch.ElapsedMilliseconds -ge $BudgetMs) { throw 'Observation budget exhausted' }
        $windowPid = [DaedalusNortonReadOnlyWindows]::Pid($handle)
        if (-not $candidatePids.Contains($windowPid)) { throw 'Window ownership changed' }
        $script:ArtifactSeen = $false
        $title = Protect-AlertText ([DaedalusNortonReadOnlyWindows]::Title($handle, $MaxTitle)) $MaxTitle
        $text = Read-NortonAccessibility $handle $windowPid $watch
        if ([DaedalusNortonReadOnlyWindows]::Pid($handle) -ne $windowPid) { throw 'Window ownership changed' }
        $screenshot = @{ status = 'not_requested'; reason = 'capture_not_requested' }
        if ($RequestScreenshot) { $screenshot = @{ status = 'unavailable'; reason = 'capture_not_supported_by_read_only_observer' } }
        [void]$windows.Add([pscustomobject]@{
            pid = $windowPid; processName = $candidateNames[$windowPid]; hwnd = $handle.ToInt64()
            title = $title; text = $text; visible = [DaedalusNortonReadOnlyWindows]::IsWindowVisible($handle)
            matched_path = $(if ($script:ArtifactSeen) { $ArtifactPath } else { $null })
            screenshot = $screenshot
        })
    }
    Write-Observation $true 'observed' $windows.ToArray()
} catch {
    # No raw provider exception text, escalation, alternate capture, or retry.
    Write-Observation $false 'inspection_unavailable' @()
    exit 0
}
