#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One-command, read-only status of a long-running Unreal producer.

Prints PID liveness, last saved chunk, saved counts, next index, pace (min/chunk) and ETA to a target,
free RAM against a floor, team-link lease age/remaining, and any failure.json under the run root.
It never writes, signals a process, or touches locks; the broker is only read with GET /locks.

  python producer_status.py --launch-dir <boss-launch-dir> [--run-root <dir>] [--target 10000] [--json]

Exit: 0 healthy, 1 attention (dead PID, failure.json, RAM under floor, lease under 10 min), 2 bad input.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path


def parse_time(s: str) -> dt.datetime:
    s = s.strip().replace("Z", "+00:00")
    # Python 3.10 fromisoformat takes at most 6 fractional digits; launchers write 7.
    if "." in s:
        head, rest = s.split(".", 1)
        i = 0
        while i < len(rest) and rest[i].isdigit():
            i += 1
        s = head + "." + rest[:i][:6].ljust(6, "0") + rest[i:]
    t = dt.datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                             capture_output=True, text=True, check=False).stdout
        return f'"{pid}"' in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def free_ram_gb() -> float | None:
    if os.name == "nt":
        class MS(ctypes.Structure):
            _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                        ("avail", ctypes.c_ulonglong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                        ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
        m = MS(); m.len = ctypes.sizeof(MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):  # type: ignore[attr-defined]
            return m.avail / 2**30
        return None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 2**20
    except OSError:
        pass
    return None


def read_milestones(log: Path) -> list[dict]:
    rows = []
    if not log.exists():
        return rows
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and "milestone" in row:
            rows.append(row)
    return rows


def read_locks(broker: str, timeout: float = 3.0) -> dict | None:
    try:
        with urllib.request.urlopen(broker.rstrip("/") + "/locks", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def build_status(launch_dir: Path, run_root: Path | None, broker: str, target: int, ram_floor: float,
                 now: dt.datetime | None = None, alive=pid_alive, ram=free_ram_gb, locks=read_locks) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    launch = json.loads((launch_dir / "launch.json").read_text(encoding="utf-8-sig"))
    pid = int(launch.get("pid", 0))
    start = parse_time(launch["start"])
    log = launch_dir / "stdout.log"
    rows = read_milestones(log)
    saved = [r for r in rows if r.get("milestone") == "CHUNK_SAVED"]
    other = [r for r in rows if r.get("milestone") != "CHUNK_SAVED"]
    st: dict = {"pid": pid, "alive": alive(pid), "start_utc": start.isoformat(),
                "uptime_h": round((now - start).total_seconds() / 3600, 2), "chunks_saved_this_run": len(saved)}
    if saved:
        last = saved[-1]
        st.update(last_chunk=last.get("chunk"), saved_counts=last.get("saved_counts", {}),
                  next_index=last.get("next_index"))
        log_mtime = dt.datetime.fromtimestamp(log.stat().st_mtime, dt.timezone.utc)
        pace = (log_mtime - start).total_seconds() / 60 / len(saved)
        st["pace_min_per_chunk"] = round(pace, 2)
        st["last_save_age_min"] = round((now - log_mtime).total_seconds() / 60, 1)
        counts = [v for v in st["saved_counts"].values() if isinstance(v, int)]
        per_chunk = None
        if len(saved) > 1 and saved[0].get("saved_counts") and counts:
            first = min(v for v in saved[0]["saved_counts"].values() if isinstance(v, int))
            per_chunk = (min(counts) - first) / (len(saved) - 1)
        if per_chunk and counts and target > min(counts):
            st["eta_h_to_target"] = round((target - min(counts)) / per_chunk * pace / 60, 1)
    if other:
        st["last_other_milestone"] = other[-1]
    failures = sorted(str(p) for p in (run_root or launch_dir).rglob("failure.json")) if (run_root or launch_dir).exists() else []
    st["failure_json"] = failures
    g = ram()
    st["free_ram_gb"] = None if g is None else round(g, 2)
    lk = locks(broker)
    st["locks"] = {k: {"holder": v.get("holder"), "age_s": v.get("age_s"), "left_s": v.get("left_s")}
                   for k, v in (lk or {}).items() if isinstance(v, dict)} if lk is not None else None
    reasons = []
    if not st["alive"]:
        reasons.append("pid not running")
    if failures:
        reasons.append("failure.json present")
    if g is not None and g < ram_floor:
        reasons.append(f"free RAM {g:.1f} GB under {ram_floor} GB floor")
    for k, v in (st["locks"] or {}).items():
        if isinstance(v.get("left_s"), (int, float)) and v["left_s"] < 600:
            reasons.append(f"lease {k} has {v['left_s']:.0f}s left")
    st["attention"] = reasons
    return st


def render(st: dict) -> str:
    c = st.get("saved_counts", {})
    lines = [f"PID {st['pid']} {'alive' if st['alive'] else 'NOT RUNNING'}, up {st['uptime_h']} h",
             f"chunk {st.get('last_chunk')} saved ({st['chunks_saved_this_run']} this run), "
             + ", ".join(f"{k} {v}" for k, v in c.items()) + f", next {st.get('next_index')}",
             f"pace {st.get('pace_min_per_chunk')} min/chunk, last save {st.get('last_save_age_min')} min ago"
             + (f", ETA {st['eta_h_to_target']} h to target" if "eta_h_to_target" in st else ""),
             f"free RAM {st['free_ram_gb']} GB"]
    if st["locks"] is None:
        lines.append("locks: broker unreachable")
    for k, v in (st["locks"] or {}).items():
        lines.append(f"lease {k}: {v['holder']} age {v['age_s']}s left {v['left_s']}s")
    lines.append("failure.json: " + (", ".join(st["failure_json"]) or "none"))
    lines.append("ATTENTION: " + "; ".join(st["attention"]) if st["attention"] else "OK")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--launch-dir", required=True, type=Path, help="folder with launch.json and stdout.log")
    ap.add_argument("--run-root", type=Path, help="tree to search for failure.json (default: launch dir)")
    ap.add_argument("--broker", default="http://127.0.0.1:9890")
    ap.add_argument("--target", type=int, default=10000)
    ap.add_argument("--ram-floor", type=float, default=3.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not (a.launch_dir / "launch.json").exists():
        print(f"no launch.json in {a.launch_dir}", file=sys.stderr)
        return 2
    st = build_status(a.launch_dir, a.run_root, a.broker, a.target, a.ram_floor)
    print(json.dumps(st, indent=2) if a.json else render(st))
    return 1 if st["attention"] else 0


if __name__ == "__main__":
    sys.exit(main())
