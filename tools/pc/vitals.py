# SPDX-License-Identifier: MIT
"""PC vitals without a UI (Richey 02:49, TMOG): one JSON line per sample with system RAM, CPU, and the top
processes by memory/CPU, from Windows performance counters and the process table — the same numbers the Task
Manager TMOG summary shows, readable by the harness and the diagnostic.

    python tools/pc/vitals.py                 # one sample, printed
    python tools/pc/vitals.py --watch 60      # a sample every 60 s appended to %LOCALAPPDATA%/Daedalus/vitals.jsonl
    python tools/pc/vitals.py --alarm 90      # exit 2 when RAM use is over 90 % (for job scripts to check)
"""
import json
import os
import subprocess
import sys
import time

PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]
SCRIPT = r"""
$os = Get-CimInstance Win32_OperatingSystem
$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
$procs = Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 12 Id, ProcessName, @{n='mb';e={[int]($_.WorkingSet64/1MB)}}, @{n='cpu_s';e={[int]$_.CPU}}
$cm = Get-Counter '\Memory\Committed Bytes','\Memory\Commit Limit' -ErrorAction SilentlyContinue
$committed = [int](($cm.CounterSamples | ? { $_.Path -like '*Committed Bytes' }).CookedValue/1MB)
$limit = [int](($cm.CounterSamples | ? { $_.Path -like '*Commit Limit' }).CookedValue/1MB)
$gpu = $null
try { $gpu = (& nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>$null) } catch {}
[pscustomobject]@{
  total_mb = [int]($os.TotalVisibleMemorySize/1KB); free_mb = [int]($os.FreePhysicalMemory/1KB)
  cpu_pct = $cpu; gpu = $gpu; top = $procs; committed_mb = $committed; commit_limit_mb = $limit
} | ConvertTo-Json -Depth 4 -Compress
"""


def sample():
    out = subprocess.run(PS + [SCRIPT], capture_output=True, text=True, timeout=60)
    d = json.loads(out.stdout.strip() or "{}")
    d["when"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    d["ram_pct"] = round(100.0 * (d["total_mb"] - d["free_mb"]) / max(d["total_mb"], 1), 1) if d.get("total_mb") else None
    editor = next((p for p in d.get("top", []) if p["ProcessName"].lower().startswith("unrealeditor")), None)
    d["editor_mb"] = editor["mb"] if editor else None
    d["commit_pct"] = round(100.0 * d["committed_mb"] / d["commit_limit_mb"], 1) if d.get("commit_limit_mb") else None
    return d


def main(argv):
    watch = int(argv[argv.index("--watch") + 1]) if "--watch" in argv else 0
    alarm = float(argv[argv.index("--alarm") + 1]) if "--alarm" in argv else None
    path = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Daedalus", "vitals.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    while True:
        d = sample()
        line = "%s ram %s%% (%s MB free) commit %s%% (%s/%s MB) cpu %s%% editor %s MB gpu %s" % (d["when"], d["ram_pct"], d.get("free_mb"), d.get("commit_pct"), d.get("committed_mb"), d.get("commit_limit_mb"), d.get("cpu_pct"), d["editor_mb"], (d.get("gpu") or "-"))
        print(line, flush=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(d) + "\n")
        worst = max(d["ram_pct"] or 0, d.get("commit_pct") or 0)
        if alarm is not None and worst > alarm:
            print("ALARM ram %s%% / commit %s%% > %s%%" % (d["ram_pct"], d.get("commit_pct"), alarm), flush=True)
            if not watch:
                return 2
        if not watch:
            return 0
        time.sleep(watch)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
