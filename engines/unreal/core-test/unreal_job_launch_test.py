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
