# SPDX-License-Identifier: MIT
"""Native Windows regressions for pc-job; no CIM process, editor, or bridge is used.

Capture the real launcher command with a CIM stand-in, then execute that exact cmd
line synchronously against repository-local synthetic scripts. Run with Python's
stdlib unittest; non-Windows hosts skip the native cases.
"""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent / "pc-job.ps1"
POWERSHELL = shutil.which("powershell.exe")


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "requires native Windows PowerShell and cmd")
class PcJobTest(unittest.TestCase):
    def setUp(self):
        # Stay inside the repo: pc-job intentionally refuses scripts below %TEMP%.
        self.temporary = tempfile.TemporaryDirectory(prefix="pc-job fixture ! ", dir=HERE)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo with spaces !"
        self.harness = self.repo / "engines" / "unreal" / "pc-job.ps1"
        self.harness.parent.mkdir(parents=True)
        shutil.copyfile(HARNESS, self.harness)
        self.script = self.repo / "tools" / "exit fixture !.py"
        self.script.parent.mkdir()
        self.script.write_text(
            "import json, sys\n"
            "print(json.dumps(sys.argv[2:]), flush=True)\n"
            "print('stderr fixture', file=sys.stderr, flush=True)\n"
            "sys.exit(int(sys.argv[1]))\n", encoding="utf-8"
        )
        self.local_data = self.root / "local data !"
        self.jobs = self.local_data / "Daedalus" / "jobs"
        self.capture = self.root / "command.json"
        self.launch = self.root / "capture launch.ps1"
        self.launch.write_text(r'''
param($Harness, $Capture, $LocalData, $ScriptPath, $EncodedArgs, [int]$CreateCode = 0, [uint32]$PidValue = 123, [switch]$ThrowCreate, [switch]$BlockReceipt, [switch]$StrictWarnings)
$ErrorActionPreference = "Stop"
if ($StrictWarnings) { $WarningPreference = "Stop" }
$env:LOCALAPPDATA = $LocalData
function New-CimInstance {
    [CmdletBinding()] param($ClassName, [switch]$ClientOnly, $Property)
    if ($Property.ShowWindow -ne 7) { throw "job window must be visible-minimized" }
    return $Property
}
function Invoke-CimMethod {
    [CmdletBinding()] param($ClassName, $MethodName, $Arguments)
    $Arguments | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Capture -Encoding UTF8
    if ($ThrowCreate) { throw "synthetic CIM transport failure" }
    if ($BlockReceipt) {
        $receipt = [regex]::Match($Arguments.CommandLine, 'job-[0-9]{4}-[0-9]{6}-[a-f0-9]{32}').Value
        New-Item -ItemType Directory -Path (Join-Path $LocalData "Daedalus\jobs\$receipt.started") | Out-Null
    }
    return @{ ReturnValue = $CreateCode; ProcessId = $PidValue }
}
$rawArgs = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($EncodedArgs))
& $Harness -Start -Script $ScriptPath -ScriptArgs $rawArgs
''', encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def powershell(self, *args, env=None):
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-File", *map(str, args)],
            capture_output=True, text=True, env=env, timeout=20
        )

    def start(self, raw_args='0 "argument with spaces !"', script=None, create_code=0, pid=123, throw=False, block_receipt=False, strict_warnings=False):
        args = [self.launch, "-Harness", self.harness, "-Capture", self.capture,
                "-LocalData", self.local_data, "-ScriptPath", script or self.script.relative_to(self.repo),
                "-EncodedArgs", base64.b64encode(raw_args.encode()).decode(),
                "-CreateCode", create_code, "-PidValue", pid]
        if throw:
            args.append("-ThrowCreate")
        if block_receipt:
            args.append("-BlockReceipt")
        if strict_warnings:
            args.append("-StrictWarnings")
        result = self.powershell(*args)
        command = json.loads(self.capture.read_text(encoding="utf-8-sig")) if self.capture.exists() else None
        return result, command

    def run_command(self, command, env=None):
        previous = set(self.jobs.glob("*.exit"))
        result = subprocess.run(command["CommandLine"], capture_output=True, text=True, env=env, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        markers = list(set(self.jobs.glob("*.exit")) - previous)
        self.assertEqual(len(markers), 1)
        self.assertFalse(list(self.jobs.glob("*.tmp")))
        return markers[0]

    def wait(self, job_id=None, tail=False):
        env = os.environ.copy()
        env["LOCALAPPDATA"] = str(self.local_data)
        args = [self.harness, "-Tail" if tail else "-Wait", "-Seconds", 0]
        if job_id is not None:
            args.extend(["-Id", job_id])
        return self.powershell(*args, env=env)

    def test_child_codes_and_literal_arguments(self):
        for code in (0, 1, 23):
            with self.subTest(code=code):
                started, command = self.start(f'{code} "argument with spaces !" "(literal) & value"')
                self.assertEqual(started.returncode, 0, started.stderr)
                self.assertIn("started job-", started.stdout)
                marker = self.run_command(command)
                self.assertEqual(marker.read_text().strip(), f"done {code}")
                log = marker.with_suffix(".log").read_text()
                self.assertIn('["argument with spaces !", "(literal) & value"]', log)
                self.assertIn("stderr fixture", log)
                waited = self.wait(marker.stem)
                self.assertEqual(waited.returncode, code, waited.stdout + waited.stderr)
                self.assertTrue(waited.stdout.startswith(f"DONE {code}\n"), waited.stdout)
                marker.unlink()

    def test_powershell_child_code(self):
        script = self.script.with_suffix(".ps1")
        script.write_text('param([int]$Code, [string]$Message)\nWrite-Output $Message\nexit $Code\n')
        started, command = self.start('23 "PowerShell message !"', script.relative_to(self.repo))
        self.assertEqual(started.returncode, 0, started.stderr)
        marker = self.run_command(command)
        self.assertEqual(marker.read_text().strip(), "done 23")
        self.assertIn("PowerShell message !", marker.with_suffix(".log").read_text())

    def test_environment_errorlevel_cannot_forge_success(self):
        started, command = self.start('23 "literal !"')
        self.assertEqual(started.returncode, 0, started.stderr)
        env = os.environ.copy()
        env["ERRORLEVEL"] = "0"
        marker = self.run_command(command, env=env)
        self.assertEqual(marker.read_text().strip(), "done 23")

    def test_setup_failure_completes_without_running_child(self):
        started, command = self.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        # The repo can disappear after Start validated it but before cmd begins.
        command["CommandLine"] = command["CommandLine"].replace(
            f'cd /d "{self.repo}"', f'cd /d "{self.repo / "missing directory"}"')
        marker = self.run_command(command)
        self.assertEqual(marker.read_text().strip(), "done 1")
        self.assertFalse(marker.with_suffix(".log").exists())
        self.assertEqual(self.wait(marker.stem).returncode, 1)

    def test_log_setup_failure_completes_without_running_child(self):
        started, command = self.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        # An existing directory cannot be opened as the log file.
        job_id = started.stdout.split()[1]
        log = self.jobs / (job_id + ".log")
        log.mkdir()
        marker = self.run_command(command)
        self.assertNotEqual(marker.read_text().strip(), "done 0")
        self.assertEqual(self.wait().returncode, 1)

    def test_implicit_wait_selects_setup_failure_without_a_log(self):
        started, command = self.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        old_log = self.jobs / "job-old.log"
        old_exit = old_log.with_suffix(".exit")
        old_log.write_text("old successful child\n")
        old_exit.write_text("done 0")
        for path in (old_log, old_exit):
            os.utime(path, (1, 1))
        command["CommandLine"] = command["CommandLine"].replace(
            f'cd /d "{self.repo}"', f'cd /d "{self.repo / "missing directory"}"')
        marker = self.run_command(command)
        self.assertFalse(marker.with_suffix(".log").exists())
        waited = self.wait()
        self.assertEqual(waited.returncode, 1, waited.stdout + waited.stderr)
        self.assertTrue(waited.stdout.startswith("DONE 1\n"), waited.stdout)
        self.assertNotIn("old successful child", waited.stdout)

    def test_interpreter_startup_failure_is_nonzero(self):
        started, command = self.start()
        self.assertEqual(started.returncode, 0, started.stderr)
        executable = shutil.which("python.exe")
        command["CommandLine"] = command["CommandLine"].replace(
            f'"{executable}"', f'"{self.repo / "missing python.exe"}"')
        marker = self.run_command(command)
        self.assertEqual(marker.read_text().strip(), "done 9009")
        self.assertEqual(self.wait(marker.stem).returncode, 9009)

    def test_cim_failure_never_reports_started(self):
        for code, pid, throw in ((2, 0, False), (0, 0, False), (0, 123, True)):
            with self.subTest(code=code, pid=pid, throw=throw):
                result, _ = self.start(create_code=code, pid=pid, throw=throw)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("started job-", result.stdout)
                self.assertFalse(list(self.jobs.glob("*.exit")))

    def test_accepted_launch_survives_receipt_failure(self):
        started, command = self.start('23 "accepted once"', block_receipt=True, strict_warnings=True)
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assertIn("Do not restart", " ".join(started.stdout.split()))
        receipt = next(line for line in started.stdout.splitlines() if line.startswith("started job-"))
        job_id = receipt.split()[1]
        self.assertIn("pid=123", receipt)
        self.assertTrue((self.jobs / (job_id + ".started")).is_dir())
        marker = self.run_command(command)
        self.assertEqual(marker.stem, job_id)
        waited = self.wait(job_id)
        self.assertEqual(waited.returncode, 23, waited.stdout + waited.stderr)
        self.assertTrue(waited.stdout.startswith("DONE 23"))

    def test_unique_starts_do_not_reuse_a_marker(self):
        first, command = self.start()
        marker = self.run_command(command)
        second, _ = self.start()
        self.assertEqual(second.returncode, 0, second.stderr)
        first_id, second_id = first.stdout.split()[1], second.stdout.split()[1]
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(marker.stem, first_id)
        self.assertTrue(self.wait(second_id).stdout.startswith("RUNNING " + second_id))
        self.assertTrue(self.wait().stdout.startswith("RUNNING " + second_id))

    def test_wait_rejects_invalid_markers_and_tail_stays_read_only(self):
        self.jobs.mkdir(parents=True)
        for content in ("", "done 0 garbage", "done 999999999999999999999", "done 0\ndone 23"):
            with self.subTest(content=content):
                marker = self.jobs / "job-invalid.exit"
                marker.write_text(content)
                result = self.wait(marker.stem)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertTrue(result.stdout.startswith("FAILED job-invalid invalid exit marker"))
        (self.jobs / "job-failed.exit").write_text("done 23")
        (self.jobs / "job-failed.log").write_text("child failed\n")
        result = self.wait("job-failed", tail=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("child failed", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
