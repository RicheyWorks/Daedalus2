# SPDX-License-Identifier: MIT
# One bounded sweep of the allowlisted Daedalus worker's dedicated classic console.
# Dot-source for the provider; invoke directly for a JSON result. No editor calls.
param([switch]$InspectOnly)

. (Join-Path $PSScriptRoot 'worker-console-policy.ps1')

function Initialize-DaedalusWorkerConsoleNative {
    if ('DaedalusWorkerConsoleNative' -as [type]) { return }
    Add-Type -ErrorAction Stop -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
public static class DaedalusWorkerConsoleNative {
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool FreeConsole();
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool AttachConsole(uint pid);
    [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint GetConsoleProcessList(uint[] list, uint count);
    [DllImport("shell32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CommandLineToArgvW(string cmd, out int count);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr mem);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr hwnd, StringBuilder text, int length);
    [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr hwnd, uint command);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
    [DllImport("user32.dll")] static extern bool IsWindow(IntPtr hwnd);
    [DllImport("user32.dll")] static extern bool ShowWindowAsync(IntPtr hwnd, int command);
    [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetProcessTimes(IntPtr handle, out long created, out long exited, out long kernel, out long user);
    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int kind);
    [DllImport("kernel32.dll")] static extern bool SetStdHandle(int kind, IntPtr handle);

    sealed class StandardHandles {
        readonly IntPtr input = GetStdHandle(-10), output = GetStdHandle(-11), error = GetStdHandle(-12);
        public void Restore() {
            SetStdHandle(-10, input); SetStdHandle(-11, output); SetStdHandle(-12, error);
        }
    }

    public sealed class Window {
        public long Hwnd;
        public uint OwnerProcessId;
        public string ClassName;
        public bool Visible;
        public bool Minimized;
        public long OwnerWindow;
        public uint[] Members;
    }
    public static string[] Arguments(string command) {
        if (String.IsNullOrWhiteSpace(command)) return new string[0];
        int count;
        IntPtr mem = CommandLineToArgvW(command, out count);
        if (mem == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
        try {
            var result = new string[count];
            for (int i=0; i<count; i++) result[i] = Marshal.PtrToStringUni(Marshal.ReadIntPtr(mem, i * IntPtr.Size));
            return result;
        } finally { LocalFree(mem); }
    }
    public static Window Describe(long value) {
        IntPtr hwnd = new IntPtr(value);
        if (!IsWindow(hwnd)) return null;
        uint owner;
        GetWindowThreadProcessId(hwnd, out owner);
        var text = new StringBuilder(256);
        GetClassName(hwnd, text, text.Capacity);
        return new Window { Hwnd=value, OwnerProcessId=owner, ClassName=text.ToString(),
            Visible=IsWindowVisible(hwnd), Minimized=IsIconic(hwnd), OwnerWindow=GetWindow(hwnd, 4).ToInt64() };
    }
    static uint[] Members() {
        // A dedicated worker console has two clients while this helper is attached: worker and helper.
        var list = new uint[64];
        uint count = GetConsoleProcessList(list, (uint)list.Length);
        if (count == 0) throw new Win32Exception(Marshal.GetLastWin32Error());
        if (count > list.Length) throw new InvalidOperationException("console membership exceeds inspection limit");
        uint self = (uint)System.Diagnostics.Process.GetCurrentProcess().Id;
        var result = new System.Collections.Generic.List<uint>();
        for (int i=0; i<count; i++) if (list[i] != self) result.Add(list[i]);
        return result.ToArray();
    }
    public static Window Console(uint worker) {
        // Only this short-lived helper detaches. The worker stays alive with its handles and logs intact.
        var streams = new StandardHandles();
        try {
            FreeConsole();
            if (!AttachConsole(worker)) throw new Win32Exception(Marshal.GetLastWin32Error());
            Window window = Describe(GetConsoleWindow().ToInt64());
            if (window != null) window.Members = Members();
            return window;
        } finally { FreeConsole(); streams.Restore(); }
    }
    static bool AliveAt(IntPtr process, long expected) {
        if (process == IntPtr.Zero || WaitForSingleObject(process, 0) != 258) return false;
        long created, exited, kernel, user;
        // CIM timestamps have microsecond precision; retain handles and compare at that precision.
        return GetProcessTimes(process, out created, out exited, out kernel, out user) && created / 10 == expected / 10;
    }
    public static bool Minimize(long hwnd, uint worker, long workerCreated, uint owner, long ownerCreated) {
        IntPtr workerHandle = OpenProcess(0x101000, false, worker);
        if (workerHandle == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
        IntPtr ownerHandle = IntPtr.Zero;
        try {
            ownerHandle = OpenProcess(0x101000, false, owner);
            if (ownerHandle == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
            var streams = new StandardHandles();
            try {
                FreeConsole();
                if (!AttachConsole(worker)) throw new Win32Exception(Marshal.GetLastWin32Error());
                Window window = Describe(hwnd);
                uint[] clients = Members();
                if (GetConsoleWindow().ToInt64() != hwnd || window == null || window.OwnerProcessId != owner ||
                    window.OwnerWindow != 0 || window.ClassName != "ConsoleWindowClass" || !window.Visible ||
                    clients.Length != 1 || clients[0] != worker ||
                    !AliveAt(workerHandle, workerCreated) || !AliveAt(ownerHandle, ownerCreated)) return false;
                if (!window.Minimized && !ShowWindowAsync(new IntPtr(hwnd), 7)) return false; // SW_SHOWMINNOACTIVE
                for (int i=0; i<10; i++) {
                    Window after = Describe(hwnd);
                    if (!AliveAt(workerHandle, workerCreated) || !AliveAt(ownerHandle, ownerCreated) ||
                        after == null || after.OwnerProcessId != owner || after.ClassName != "ConsoleWindowClass") return false;
                    if (after.Minimized) return true;
                    System.Threading.Thread.Sleep(25);
                }
                return false;
            } finally { FreeConsole(); streams.Restore(); }
        } finally {
            if (workerHandle != IntPtr.Zero) CloseHandle(workerHandle);
            if (ownerHandle != IntPtr.Zero) CloseHandle(ownerHandle);
        }
    }
}
'@
}

function ConvertTo-DaedalusWorkerProcess($Process) {
    if (-not $Process) { return $null }
    [pscustomobject]@{
        ProcessId = $Process.ProcessId
        CreationDate = $Process.CreationDate
        SessionId = $Process.SessionId
        ExecutablePath = $Process.ExecutablePath
        CommandLine = $Process.CommandLine
        Arguments = @([DaedalusWorkerConsoleNative]::Arguments([string]$Process.CommandLine))
    }
}

function New-DaedalusWorkerConsoleProvider([switch]$InspectOnly) {
    Initialize-DaedalusWorkerConsoleNative
    @{
        InspectOnly = [bool]$InspectOnly
        GetProcesses = {
            @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'python3.exe'" -ErrorAction Stop |
                ForEach-Object { ConvertTo-DaedalusWorkerProcess $_ })
        }
        GetProcess = {
            param($ProcessId)
            ConvertTo-DaedalusWorkerProcess (Get-CimInstance Win32_Process -Filter "ProcessId = $([uint32]$ProcessId)" -ErrorAction Stop)
        }
        GetConsole = { param($ProcessId) [DaedalusWorkerConsoleNative]::Console([uint32]$ProcessId) }
        GetWindow = { param($WindowHandle) [DaedalusWorkerConsoleNative]::Describe([long]$WindowHandle) }
        Minimize = {
            param($WindowHandle, $Worker, $Owner)
            [DaedalusWorkerConsoleNative]::Minimize([long]$WindowHandle,
                [uint32]$Worker.ProcessId, ([datetime]$Worker.CreationDate).ToUniversalTime().ToFileTimeUtc(),
                [uint32]$Owner.ProcessId, ([datetime]$Owner.CreationDate).ToUniversalTime().ToFileTimeUtc())
        }
    }
}

function Invoke-DaedalusWorkerConsoleCheck([switch]$InspectOnly) {
    try {
        $provider = New-DaedalusWorkerConsoleProvider -InspectOnly:$InspectOnly
        $jobs = Join-Path $env:LOCALAPPDATA 'Daedalus\jobs'
        $session = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
        Invoke-DaedalusWorkerConsoleSweep -Provider $provider -JobsRoot $jobs -CurrentSessionId $session
    } catch {
        [pscustomobject]@{ status = 'unavailable'; reason = $_.Exception.Message; workers = @() }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    Invoke-DaedalusWorkerConsoleCheck -InspectOnly:$InspectOnly | ConvertTo-Json -Depth 5 -Compress
}
