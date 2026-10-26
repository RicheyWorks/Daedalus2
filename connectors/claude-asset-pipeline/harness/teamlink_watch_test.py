# SPDX-License-Identifier: MIT
"""Run the PowerShell health observer with HTTP/sleep stand-ins. No broker process actions."""
from pathlib import Path
import os,shutil,subprocess,tempfile,unittest
PS=shutil.which('powershell.exe')
HARNESS=Path(__file__).resolve().parents[1]/'teamlink.ps1'
@unittest.skipUnless(os.name=='nt' and PS,'requires Windows PowerShell')
class WatchTest(unittest.TestCase):
    def test_recovery_and_down_are_truthful_without_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);script=root/'fixture.ps1'
            script.write_text(r'''param($Harness,$Root,[switch]$Down)
$env:LOCALAPPDATA=$Root
$env:USERPROFILE=$Root
$global:Calls=0
function Invoke-RestMethod {
 param($Uri,$TimeoutSec)
 $global:Calls++
 if ($Down -or $global:Calls -eq 2) { throw "synthetic observation timeout" }
 return @{ok=$true;last=$global:Calls;pid=123;since="fixture"}
}
function Start-Sleep {param($Seconds)}
function Invoke-CimMethod { throw "must never launch a broker" }
function Get-CimInstance { throw "must never infer dead process" }
function Stop-Process { throw "must never stop a broker" }
& $Harness -Watch -Checks 3
exit $LASTEXITCODE
''',encoding='utf-8')
            for down in (False,True):
                args=[PS,'-NoProfile','-File',str(script),str(HARNESS),str(root)]
                if down:args.append('-Down')
                result=subprocess.run(args,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,2 if down else 0,result.stdout+result.stderr)
                self.assertIn('unavailable',result.stdout)
                self.assertIn('no restart attempted',result.stdout)
                if not down:
                    self.assertIn('last=1',result.stdout);self.assertIn('last=3',result.stdout)
                self.assertNotIn('must never',result.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
