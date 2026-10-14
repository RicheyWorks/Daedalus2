# SPDX-License-Identifier: MIT
"""Native launcher-only tests. CIM is stubbed; never execute -Run or touch Unreal."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
PS = shutil.which("powershell.exe")


@unittest.skipUnless(os.name == "nt" and PS, "requires Windows PowerShell")
class UnrealLaunchTest(unittest.TestCase):
    def test_run_preparation_failure_publishes_terminal_marker(self):
        with tempfile.TemporaryDirectory(prefix="build prepare ! ", dir=HERE) as root:
            root = Path(root)
            harness = root / "repo" / "engines" / "unreal" / "unreal-job.ps1"
            harness.parent.mkdir(parents=True)
            shutil.copyfile(HERE.parent / "unreal-job.ps1", harness)
            # Any accidental build entry is visible and fails the test.
            sentinel = root / "build-was-called"
            (harness.parent / "setup-unreal.ps1").write_text(
                '"unexpected" | Set-Content -LiteralPath "' + str(sentinel) + '"\nexit 0\n')
            wrapper = root / "fixture.ps1"
            wrapper.write_text(r'''param($Harness, $Root, [int]$GitCode)
$env:LOCALAPPDATA = Join-Path $Root "data"
function git { Write-Error "synthetic git progress stderr"; $global:LASTEXITCODE = $GitCode; "synthetic pull" }
& $Harness -Run -Id "build-prepare" -Project (Join-Path $Root "project\Realm.uproject")
exit $LASTEXITCODE
''', encoding="utf-8")
            project = root / "project"
            project.mkdir()
            # Git failure must stop before config writes. With successful git, the
            # missing Config directory forces a preparation exception before build.
            for git_code in (23, 0):
                with self.subTest(git_code=git_code):
                    old_log = root / "data" / "Daedalus" / "jobs" / "build-prepare.log"
                    if old_log.exists():
                        old_log.unlink()
                    result = subprocess.run([PS, "-NoProfile", "-File", str(wrapper),
                                             str(harness), str(root), str(git_code)],
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    jobs = root / "data" / "Daedalus" / "jobs"
                    self.assertEqual((jobs / "build-prepare.exit").read_text().strip(), "done 1")
                    log = (jobs / "build-prepare.log").read_text(encoding="utf-8-sig")
                    self.assertIn("JOB STOPPED", log)
                    if git_code:
                        self.assertIn("git pull failed", log)
                    else:
                        self.assertNotIn("git pull failed", log)
                        self.assertIn("synthetic git progress stderr", log)
                    self.assertFalse(sentinel.exists())
                    self.assertFalse((project / "Config").exists())

    def test_completion_writer_replaces_marker_without_temp_residue(self):
        with tempfile.TemporaryDirectory(prefix="build marker ! ", dir=HERE) as root:
            root = Path(root)
            source = (HERE.parent / "unreal-job.ps1").read_text()
            function = "function Write-Completion" + source.split("function Write-Completion", 1)[1].split("function BuildToolsBusy", 1)[0]
            script = root / "writer.ps1"
            script.write_text('param($Jobs)\n$ErrorActionPreference = "Stop"\n$Id = "build-fixture"\n'
                              + function + '\nWrite-Completion 23\nWrite-Completion 2\n', encoding="utf-8")
            result = subprocess.run([PS, "-NoProfile", "-File", str(script), str(root)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((root / "build-fixture.exit").read_text().strip(), "done 2")
            self.assertFalse(list(root.glob("*.tmp")))

    def test_wait_failure_markers_and_live_diagnostics(self):
        with tempfile.TemporaryDirectory(prefix="build wait ! ", dir=HERE) as root:
            root = Path(root)
            env = os.environ.copy()
            env["LOCALAPPDATA"] = str(root)
            jobs = root / "Daedalus" / "jobs"
            jobs.mkdir(parents=True)
            log = jobs / "build-fixture.log"
            marker = log.with_suffix(".exit")
            for content, expected in (("done 23", 23), ("done 2", 2), ("", 1),
                                      ("done 0 extra", 1), ("done 99999999999999999", 1),
                                      ("done 0\ndone 23", 1)):
                with self.subTest(marker=content):
                    marker.write_text(content)
                    # A stale success log must never override a failed marker.
                    log.write_text("BUILD SUCCESSFUL\n")
                    result = subprocess.run([PS, "-NoProfile", "-File", str(HERE.parent / "unreal-job.ps1"),
                                             "-Wait", "-Id", "build-fixture", "-Seconds", "0"],
                                            env=env, capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    self.assertIn("BUILD FAILED", result.stdout)
                    self.assertNotIn("BUILD OK", result.stdout)
            log.write_text("file.cpp: error C1234: synthetic compiler failure\n")
            for complete in (False, True):
                if complete:
                    marker.write_text("done 0")
                else:
                    marker.unlink()
                result = subprocess.run([PS, "-NoProfile", "-File", str(HERE.parent / "unreal-job.ps1"),
                                         "-Wait", "-Id", "build-fixture", "-Seconds", "0"],
                                        env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 1 if complete else 0, result.stdout + result.stderr)
                self.assertIn("BUILD FAILED" if complete else "RUNNING", result.stdout)

    def test_identity_and_refusals(self):
        with tempfile.TemporaryDirectory(prefix="unreal launch ! ", dir=HERE) as root:
            root = Path(root)
            harness = root / "engines" / "unreal" / "unreal-job.ps1"
            harness.parent.mkdir(parents=True)
            shutil.copyfile(HERE.parent / "unreal-job.ps1", harness)
            wrapper = root / "launch.ps1"
            wrapper.write_text(r'''param($Harness, $Capture, $LocalData, [int]$Code, [uint32]$PidValue, [switch]$ThrowCreate, [switch]$Fast)
$ErrorActionPreference = "Stop"
$env:LOCALAPPDATA = $LocalData
function Get-Date { param($Format) return "1013-220000" }
function New-CimInstance {
 [CmdletBinding()] param($ClassName, [switch]$ClientOnly, $Property)
 if ($Property.ShowWindow -ne 7) { throw "unexpected window style" }
 return $Property
}
function Invoke-CimMethod {
 [CmdletBinding()] param($ClassName, $MethodName, $Arguments)
 $Arguments | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Capture -Encoding UTF8
 if ($ThrowCreate) { throw "synthetic transport failure" }
 return @{ ReturnValue = $Code; ProcessId = $PidValue }
}
& $Harness -Start -Fast:$Fast -Project "C:\fixture with spaces !\Realm.uproject"
''', encoding="utf-8")
            ids = []
            for code, pid, throws, fast in ((0, 123, False, False), (0, 124, False, True),
                                            (2, 0, False, False), (0, 0, False, False),
                                            (0, 123, True, False)):
                with self.subTest(code=code, pid=pid, throws=throws, fast=fast):
                    capture = root / "command.json"
                    args = [PS, "-NoProfile", "-File", str(wrapper), "-Harness", str(harness),
                            "-Capture", str(capture), "-LocalData", str(root / "data"),
                            "-Code", str(code), "-PidValue", str(pid)]
                    if throws:
                        args.append("-ThrowCreate")
                    if fast:
                        args.append("-Fast")
                    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
                    command = json.loads(capture.read_text(encoding="utf-8-sig"))["CommandLine"]
                    # Captured only: running this command would build/reopen Unreal.
                    self.assertIn(' -Run -Id build-', command)
                    self.assertEqual(command.endswith(" -Fast"), fast)
                    if code == 0 and pid and not throws:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        match = re.search(r"started (build-1013-220000-[a-f0-9]{32}) pid=(\d+)", result.stdout)
                        self.assertIsNotNone(match, result.stdout)
                        self.assertEqual(int(match[2]), pid)
                        self.assertIn(match[1], command)
                        ids.append(match[1])
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn("started build-", result.stdout)
            self.assertEqual(len(ids), 2)
            self.assertNotEqual(ids[0], ids[1], "same-second launches must not share logs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
