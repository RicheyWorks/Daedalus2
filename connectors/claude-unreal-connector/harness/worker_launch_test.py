# SPDX-License-Identifier: MIT
"""Worker launch checks use stand-ins only; never start a real worker."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "connectors/claude-unreal-connector/extension/server/background-worker-launch.py"
START_SCRIPT = ROOT / "engines/unreal/start-background-worker.ps1"
spec = importlib.util.spec_from_file_location("background_worker_launch", LAUNCHER)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class WorkerLaunchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="worker launch '")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jobs = self.root / "Daedalus/jobs"
        self.jobs.mkdir(parents=True)
        self.worker = self.jobs / "lodworker.py"
        self.worker.write_text("# fixture only\n", encoding="utf-8")
        self.python = self.root / "python.exe"
        self.python.touch()
        self.startup = SimpleNamespace(dwFlags=32, wShowWindow=0)
        self.popen = Mock(return_value=SimpleNamespace(pid=501))
        for target, name, value in [
            (launcher.platform, "system", lambda: "Windows"),
            (launcher.sys, "executable", str(self.python)),
            (launcher.subprocess, "STARTUPINFO", lambda: self.startup),
            (launcher.subprocess, "STARTF_USESHOWWINDOW", 1),
            (launcher.subprocess, "CREATE_NEW_CONSOLE", 16),
            (launcher.subprocess, "Popen", self.popen),
        ]:
            p = patch.object(target, name, value, create=True)
            p.start()
            self.addCleanup(p.stop)
        p = patch.dict(launcher.os.environ, {"LOCALAPPDATA": str(self.root)})
        p.start()
        self.addCleanup(p.stop)

    def test_fixed_worker_gets_visible_minimized_console_and_separate_append_logs(self):
        output = self.jobs / "lodworker.out"
        errors = self.jobs / "lodworker.err"
        jsonl = self.jobs / "lodworker.jsonl"
        output.write_bytes(b"old output\n")
        errors.write_bytes(b"old error\n")
        jsonl.write_bytes(b'{"old_job":"in-progress"}\n')
        handles = []

        def spawn(args, **options):
            self.assertEqual(args, [str(self.python), str(self.worker)])
            self.assertEqual(options["cwd"], str(self.jobs))
            self.assertIs(options["shell"], False)
            self.assertIs(options["close_fds"], True)
            self.assertEqual(options["stdin"], subprocess.DEVNULL)
            self.assertEqual(options["creationflags"], 16)
            self.assertEqual(options["creationflags"] & 0x08000000, 0)  # CREATE_NO_WINDOW
            self.assertEqual(options["startupinfo"].dwFlags, 33)
            self.assertEqual(options["startupinfo"].wShowWindow, 7)
            self.assertEqual(options["stdout"].name, str(output))
            self.assertEqual(options["stderr"].name, str(errors))
            self.assertIsNot(options["stdout"], options["stderr"])
            handles.extend([options["stdout"], options["stderr"]])
            options["stdout"].write(b"new output\n")
            options["stderr"].write(b"new error\n")
            return SimpleNamespace(pid=501)

        self.popen.side_effect = spawn
        self.assertEqual(launcher.launch_worker(), 501)
        self.assertEqual(output.read_bytes(), b"old output\nnew output\n")
        self.assertEqual(errors.read_bytes(), b"old error\nnew error\n")
        self.assertEqual(jsonl.read_bytes(), b'{"old_job":"in-progress"}\n')
        self.assertTrue(all(h.closed for h in handles))

    def test_repeated_launches_preserve_previous_output(self):
        def spawn(args, **options):
            options["stdout"].write(b"next run\n")
            return SimpleNamespace(pid=501)
        self.popen.side_effect = spawn
        launcher.launch_worker()
        launcher.launch_worker()
        self.assertEqual((self.jobs / "lodworker.out").read_bytes(), b"next run\nnext run\n")
        self.assertEqual(self.popen.call_count, 2)

    def test_missing_worker_prevents_process_and_log_creation(self):
        self.worker.unlink()
        with self.assertRaisesRegex(RuntimeError, "lodworker.py is unavailable"):
            launcher.launch_worker()
        self.popen.assert_not_called()
        self.assertFalse((self.jobs / "lodworker.out").exists())

    def test_non_python_or_missing_executable_is_rejected(self):
        for executable in [self.root / "pythonw.exe", self.root / "missing/python.exe", Path("python.exe")]:
            with self.subTest(executable=executable), patch.object(launcher.sys, "executable", str(executable)):
                with self.assertRaisesRegex(RuntimeError, "absolute python.exe"):
                    launcher.launch_worker()
        self.popen.assert_not_called()

    def test_relative_jobs_root_is_rejected(self):
        with patch.dict(launcher.os.environ, {"LOCALAPPDATA": "relative"}):
            with self.assertRaisesRegex(RuntimeError, "absolute LOCALAPPDATA"):
                launcher.launch_worker()
        self.popen.assert_not_called()

    def test_non_windows_reports_unavailable_without_opening_logs(self):
        with patch.object(launcher.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(RuntimeError, "unavailable on this platform"):
                launcher.launch_worker()
        self.popen.assert_not_called()
        self.assertFalse((self.jobs / "lodworker.out").exists())

    def test_process_creation_failure_closes_handles_and_keeps_old_logs(self):
        output = self.jobs / "lodworker.out"
        output.write_bytes(b"previous\n")
        handles = []
        def fail(args, **options):
            handles.extend([options["stdout"], options["stderr"]])
            raise OSError("fixture process denied")
        self.popen.side_effect = fail
        with self.assertRaisesRegex(OSError, "fixture process denied"):
            launcher.launch_worker()
        self.assertEqual(output.read_bytes(), b"previous\n")
        self.assertTrue(all(h.closed for h in handles))

    def test_cli_rejects_arbitrary_worker_argument(self):
        errors = io.StringIO()
        with patch.object(launcher.sys, "argv", [str(LAUNCHER), "unrelated.py"]), contextlib.redirect_stderr(errors):
            self.assertEqual(launcher.main(), 1)
        self.assertEqual(json.loads(errors.getvalue())["status"], "unavailable")
        self.popen.assert_not_called()


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(os.name == "nt" and (shutil.which("pwsh") or shutil.which("powershell")), "Windows PowerShell fixture")
class WorkerStartScriptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="worker start '")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jobs = self.root / "Daedalus/jobs"
        self.jobs.mkdir(parents=True)
        (self.jobs / "lodworker.py").touch()
        self.python = self.root / "python.exe"
        self.python.touch()

    def run_fixture(self, setup=""):
        command = f"""
$ErrorActionPreference = 'Stop'
$env:LOCALAPPDATA = {ps_quote(self.root)}
. {ps_quote(START_SCRIPT)}
$fixtureProcesses = @()
$fixtureCreates = 0
$fixtureStartup = $null
$fixtureCommand = ''
function New-DaedalusWorkerConsoleProvider {{ param([switch]$InspectOnly) @{{ GetProcesses = {{ $fixtureProcesses }} }} }}
function New-CimInstance {{ param($ClassName, [switch]$ClientOnly, $Property, $ErrorAction) $script:fixtureStartup = $Property; [pscustomobject]$Property }}
function Invoke-CimMethod {{
    param($ClassName, $MethodName, $Arguments, $ErrorAction)
    $script:fixtureCreates++; $script:fixtureCommand = $Arguments.CommandLine
    [pscustomobject]@{{ ReturnValue = 0; ProcessId = 777 }}
}}
{setup}
try {{ $result = Start-DaedalusBackgroundWorker -Python {ps_quote(self.python)} }}
catch {{ $result = [pscustomobject]@{{ status = 'unavailable'; reason = $_.Exception.Message }} }}
@{{ result = $result; creates = $fixtureCreates; startup = $fixtureStartup; command = $fixtureCommand }} | ConvertTo-Json -Depth 5 -Compress
"""
        result = subprocess.run([shutil.which("pwsh") or shutil.which("powershell"), "-NoProfile", "-NonInteractive", "-Command", command],
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def process(self, script):
        return f"""$fixtureProcesses = @([pscustomobject]@{{ ProcessId = 88; CreationDate = [datetime]::UtcNow;
SessionId = [System.Diagnostics.Process]::GetCurrentProcess().SessionId; ExecutablePath = {ps_quote(self.python)};
CommandLine = 'fixture nonempty'; Arguments = @({ps_quote(self.python)}, {ps_quote(script)}) }})"""

    def test_exact_existing_worker_is_left_running(self):
        result = self.run_fixture(self.process(self.jobs / "lodworker.py"))
        self.assertEqual(result["result"]["status"], "already_running")
        self.assertEqual(result["result"]["pids"], [88])
        self.assertEqual(result["creates"], 0)

    def test_unrelated_python_does_not_suppress_minimized_detached_launcher(self):
        result = self.run_fixture(self.process(self.jobs / "other.py"))
        self.assertEqual(result["result"], {"status": "launcher_requested", "launcher_pid": 777})
        self.assertEqual(result["creates"], 1)
        self.assertEqual(result["startup"], {"ShowWindow": 7})
        self.assertEqual(result["command"], f'"{self.python}" "{LAUNCHER}"')

    def test_denied_process_inspection_aborts_launch(self):
        result = self.run_fixture("function New-DaedalusWorkerConsoleProvider { param([switch]$InspectOnly) @{ GetProcesses = { throw 'fixture process access denied' } } }")
        self.assertEqual(result["result"]["status"], "unavailable")
        self.assertIn("fixture process access denied", result["result"]["reason"])
        self.assertEqual(result["creates"], 0)

    def test_failed_wmi_creation_is_reported(self):
        result = self.run_fixture("function Invoke-CimMethod { param($ClassName, $MethodName, $Arguments, $ErrorAction) $script:fixtureCreates++; [pscustomobject]@{ ReturnValue = 2; ProcessId = 0 } }")
        self.assertEqual(result["result"]["status"], "unavailable")
        self.assertIn("WMI return 2", result["result"]["reason"])
        self.assertEqual(result["creates"], 1)


if __name__ == "__main__":
    unittest.main()
