#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rebuild-runbook orchestrator (BOARD GUARDS-AND-REBUILD-RUNBOOK.md section 2). Dry-run by default.

Order: (1) rebuild_delta since the built base (report only), (2) preflight on the target worktree, (3) gates,
(4) plugin backup + manifest, (5) UBT, (6) build_receipt write + verify, (7) report JSON/MD.

  dry-run (default)   : plans every step, runs NOTHING (no git, no bridge, no copy, no UBT).
  --execute           : phase A: steps 1-4 for real, then prints the manual editor close steps and stops.
  --execute --editor-closed --resume <phaseA report.json>
                      : phase B: re-checks lease/producer/RAM and that the bridge no longer answers, then
                        5-6 and the final report. Phase A gates must have passed in that report.

It never kills, closes or launches a process, never touches locks (GET /locks only) and never edits pins.
The UBT command is not guessed: it must be given as a JSON list in --ubt-command-file, copied from the runbook
or the latest recorded rebuild. Exit 0 ok/planned, 1 refused or a step failed, 2 bad input.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "producer_status"))
import producer_status  # noqa: E402

SCHEMA = "daedalus.rebuild-orchestration.v1"
RAM_FLOOR_GB = 3.0

# Read-only editor probe for the bridge. Uses its own names only (never the reserved global `b`).
EDITOR_PROBE = r'''
import json, unreal
_ueb_dirty = list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
_ueb_les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
_ueb_play = bool(_ueb_les.is_in_play_in_editor()) if _ueb_les else None
print("UEB_STATE " + json.dumps({"dirty": len(_ueb_dirty), "play": _ueb_play}))
'''

CLOSE_STEPS = """Manual editor close (runbook 2.4), then phase B:
  1. Save only explicitly owned assets. Do not discard anything.
  2. Quit the editor normally (File > Exit). Never force-kill.
  3. Confirm it has exited, then re-run with --execute --editor-closed --resume <this report.json>.
After UBT (runbook 2.6): normal clean reopen, detached, WITH the small map arg; never
-AutoDeclinePackageRecovery or -unattended. Then one harmless native read through the bridge."""


class Env:
    """Real side effects. Tests inject a fake with the same methods."""

    def run(self, cmd, cwd=None, log=None):
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace", check=False)
        out = (p.stdout or "") + (p.stderr or "")
        if log:
            Path(log).write_text(out, encoding="utf-8")
        return p.returncode, out

    def locks(self, broker):
        try:
            with urllib.request.urlopen(broker.rstrip("/") + "/locks", timeout=3) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            return None

    def bridge_state(self, port):
        """dict {dirty, play}, or None when the bridge does not answer."""
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=10)
        except OSError:
            return None
        try:
            msg = {"id": "rebuild-orchestrator-probe", "type": "execute_python", "params": {"code": EDITOR_PROBE, "unattended": False}}
            s.sendall((json.dumps(msg) + "\n").encode())
            buf = b""
            while not buf.endswith(b"\n"):
                c = s.recv(65536)
                if not c:
                    break
                buf += c
        finally:
            s.close()
        text = buf.decode("utf-8", "replace")
        i = text.find("UEB_STATE ")
        if i < 0:
            return {"error": text[:300]}
        j = text.find("}", i)
        try:
            return json.loads(text[i + 10:j + 1].replace('\\"', '"'))
        except ValueError:
            return {"error": text[i:i + 300]}

    def producer(self, launch_dir, run_root):
        return producer_status.build_status(Path(launch_dir), Path(run_root) if run_root else None,
                                            "http://127.0.0.1:9", 10**9, RAM_FLOOR_GB, locks=lambda _b: {})

    def ram(self):
        return producer_status.free_ram_gb()

    def backup(self, src, dest):
        src, dest = Path(src), Path(dest)
        if dest.exists():
            raise FileExistsError(dest)
        rows = []
        for f in sorted(p for p in src.rglob("*") if p.is_file()):
            rel = f.relative_to(src).as_posix()
            if not (rel.startswith("Binaries/") or rel.endswith(".uplugin")):
                continue
            t = dest / rel
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, t)
            rows.append({"path": rel, "size": f.stat().st_size, "sha256": hashlib.sha256(f.read_bytes()).hexdigest()})
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "backup-manifest.json").write_text(json.dumps({"source": str(src), "files": rows}, indent=2), encoding="utf-8")
        return rows


def check_gates(a, env, phase):
    """List of {gate, ok, detail}. phase 'A' needs a live clean editor; phase 'B' needs the bridge gone."""
    g = []
    lk = env.locks(a.broker)
    holder = ((lk or {}).get("unreal") or {}).get("holder")
    g.append({"gate": "unreal lease held by owner", "ok": holder == a.owner,
              "detail": f"holder={holder!r} owner={a.owner!r}" if lk is not None else "broker unreachable"})
    st = env.bridge_state(a.bridge_port)
    if phase == "A":
        ok = isinstance(st, dict) and st.get("dirty") == 0 and st.get("play") is False
        g.append({"gate": "editor state read OK: 0 dirty, not Play", "ok": ok, "detail": st if st is not None else "bridge did not answer"})
    else:
        g.append({"gate": "editor closed: bridge no longer answers", "ok": st is None, "detail": st})
    p = env.producer(a.producer_launch_dir, a.producer_run_root)
    last = p.get("last_other_milestone")
    boundary = (not p.get("alive")) and p.get("chunks_saved_this_run", 0) > 0 and not p.get("failure_json") and last is None
    why = "running (mid-chunk)" if p.get("alive") else ("failure.json present" if p.get("failure_json") else
          ("no CHUNK_SAVED" if not p.get("chunks_saved_this_run") else ("last milestone not CHUNK_SAVED" if last else "stopped after saved chunk")))
    g.append({"gate": "producer stopped at a saved boundary", "ok": boundary,
              "detail": f"pid {p.get('pid')} {why}, last chunk {p.get('last_chunk')}, next {p.get('next_index')}"})
    r = env.ram()
    g.append({"gate": f"free RAM > {RAM_FLOOR_GB} GB", "ok": r is not None and r > RAM_FLOOR_GB, "detail": r})
    return g


def plan(a):
    py = sys.executable or "python"
    tools = Path(a.repo) / "tools" / "unreal_preflight"
    run = Path(a.run_dir)
    ubt = json.loads(Path(a.ubt_command_file).read_text(encoding="utf-8")) if a.ubt_command_file else None
    return {
        "delta": [py, str(tools / "rebuild_delta" / "rebuild_delta.py"), a.base, a.target],
        "preflight": [py, str(tools / "preflight.py")],
        "ubt": ubt,
        "receipt_write": [py, str(tools / "build_receipt" / "build_receipt.py"), "write", "--repo", a.repo, "--plugin", a.plugin,
                          "--dll", a.dll, "--ubt-log", str(run / "ubt.log"), "--backup-dll",
                          str(Path(a.backup_root) / a.stamp / "Binaries" / "Win64" / Path(a.dll).name),
                          "--base", a.base, "--out", str(run / "build-receipt.json")],
        "receipt_verify": [py, str(tools / "build_receipt" / "build_receipt.py"), "verify", "--receipt",
                           str(run / "build-receipt.json"), "--plugin", a.plugin],
    }


def write_report(a, rep):
    run = Path(a.run_dir)
    run.mkdir(parents=True, exist_ok=True)
    j = run / f"rebuild-orchestration-{rep['phase']}.json"
    j.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    md = [f"# Rebuild orchestration ({rep['mode']}, phase {rep['phase']})", "", f"result: **{rep['result']}**", ""]
    for s in rep["steps"]:
        md.append(f"- {s['n']}. {s['step']}: {s['status']}" + (f" ({s['detail']})" if s.get("detail") not in (None, "") else ""))
    j.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return j


def orchestrate(a, env):
    p = plan(a)
    mode = "execute" if a.execute else "dry-run"
    phase = "B" if a.editor_closed else "A"
    rep = {"schema": SCHEMA, "mode": mode, "phase": phase, "owner": a.owner, "base": a.base, "target": a.target,
           "stamp": a.stamp, "utc": dt.datetime.now(dt.timezone.utc).isoformat(), "steps": [], "result": "planned"}
    steps = rep["steps"]

    def add(n, step, status, detail=None, cmd=None):
        steps.append({"n": n, "step": step, "status": status, "detail": detail, "cmd": cmd})

    def fail(msg, kind="failed"):
        rep["result"] = kind
        rep["reason"] = msg
        return rep

    if not a.execute:
        add(1, "rebuild_delta", "planned", cmd=p["delta"])
        add(2, "preflight", "planned", cmd=p["preflight"])
        add(3, "gates", "planned", "lease, editor 0 dirty/not Play, producer at saved boundary, RAM")
        add(4, "backup", "planned", str(Path(a.backup_root) / a.stamp))
        add(5, "ubt", "planned" if p["ubt"] else "missing --ubt-command-file", cmd=p["ubt"])
        add(6, "build_receipt write + verify", "planned", cmd=[p["receipt_write"], p["receipt_verify"]])
        add(7, "report", "planned")
        return rep

    run = Path(a.run_dir)
    run.mkdir(parents=True, exist_ok=True)
    if phase == "A":
        rc, out = env.run(p["delta"], cwd=a.repo, log=run / "rebuild-delta.txt")
        add(1, "rebuild_delta", "ok" if rc == 0 else f"exit {rc}", out.strip()[-400:], p["delta"])
        if rc != 0:
            return fail("rebuild_delta failed")
        rc, out = env.run(p["preflight"], cwd=a.repo, log=run / "preflight.txt")
        add(2, "preflight", "ok" if rc == 0 else f"exit {rc}", out.strip()[-400:], p["preflight"])
        if rc != 0:
            return fail("preflight reported errors")
        gates = check_gates(a, env, "A")
        rep["gates"] = gates
        add(3, "gates", "ok" if all(x["ok"] for x in gates) else "REFUSED", "; ".join(x["gate"] for x in gates if not x["ok"]))
        if not all(x["ok"] for x in gates):
            return fail("gate refused", "refused")
        rows = env.backup(a.plugin, Path(a.backup_root) / a.stamp)
        add(4, "backup", "ok", f"{len(rows)} files -> {Path(a.backup_root) / a.stamp}")
        add(5, "ubt", "awaiting manual editor close", CLOSE_STEPS)
        rep["result"] = "awaiting_editor_close"
        return rep

    # phase B
    if not a.resume or not Path(a.resume).exists():
        return fail("resume report missing", "refused")
    prev = json.loads(Path(a.resume).read_text(encoding="utf-8"))
    if prev.get("schema") != SCHEMA or prev.get("result") != "awaiting_editor_close" or prev.get("stamp") != a.stamp:
        return fail("resume report is not a passed phase A for this stamp", "refused")
    add(1, "rebuild_delta", "done in phase A")
    add(2, "preflight", "done in phase A")
    gates = check_gates(a, env, "B")
    rep["gates"] = gates
    add(3, "gates", "ok" if all(x["ok"] for x in gates) else "REFUSED", "; ".join(x["gate"] for x in gates if not x["ok"]))
    if not all(x["ok"] for x in gates):
        return fail("gate refused", "refused")
    add(4, "backup", "done in phase A")
    if not p["ubt"]:
        return fail("no --ubt-command-file: the UBT command is never guessed", "refused")
    rc, out = env.run(p["ubt"], log=run / "ubt.log")
    ok = rc == 0 and "Result: Succeeded" in out
    add(5, "ubt", "ok" if ok else f"exit {rc}", "Result: Succeeded" if ok else out.strip()[-400:], p["ubt"])
    if not ok:
        rep["restore_hint"] = f"runbook: restore backup {Path(a.backup_root) / a.stamp}, reopen old build, report BLOCKED"
        return fail("UBT failed")
    rc, out = env.run(p["receipt_write"], log=run / "receipt-write.txt")
    if rc == 0:
        rc2, out2 = env.run(p["receipt_verify"], log=run / "receipt-verify.txt")
    add(6, "build_receipt write + verify", "ok" if rc == 0 and rc2 == 0 else "failed",
        (out if rc else out2).strip()[-300:], [p["receipt_write"], p["receipt_verify"]])
    if rc != 0 or rc2 != 0:
        return fail("build receipt failed")
    add(7, "report", "ok", CLOSE_STEPS.split("After UBT", 1)[1].strip())
    rep["result"] = "ok"
    return rep


def parse(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="clean origin/main worktree at the target commit")
    ap.add_argument("--base", required=True, help="sha of the last rebuilt commit")
    ap.add_argument("--target", default="HEAD")
    ap.add_argument("--plugin", required=True, help="live plugin folder (…/Plugins/DaedalusLink)")
    ap.add_argument("--dll", required=True, help="live UnrealEditor-DaedalusLink.dll")
    ap.add_argument("--backup-root", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--owner", required=True, help="team-link name that must hold the unreal lease")
    ap.add_argument("--producer-launch-dir", required=True)
    ap.add_argument("--producer-run-root")
    ap.add_argument("--ubt-command-file", help="JSON list: the exact UBT command from the runbook")
    ap.add_argument("--broker", default="http://127.0.0.1:9890")
    ap.add_argument("--bridge-port", type=int, default=9877)
    ap.add_argument("--stamp", default=dt.datetime.now().strftime("%Y%m%dT%H%M%S"))
    ap.add_argument("--execute", action="store_true", help="really run steps (default is dry-run)")
    ap.add_argument("--editor-closed", action="store_true", help="phase B: I closed the editor normally")
    ap.add_argument("--resume", help="phase A report json (required with --editor-closed)")
    a = ap.parse_args(argv)
    if a.editor_closed and not a.execute:
        ap.error("--editor-closed needs --execute")
    return a


def main(argv=None, env=None):
    a = parse(argv)
    rep = orchestrate(a, env or Env())
    path = write_report(a, rep) if a.execute else None
    if rep["result"] == "awaiting_editor_close":
        print(CLOSE_STEPS)
    print(json.dumps({"result": rep["result"], "reason": rep.get("reason"), "report": str(path) if path else None,
                      "steps": [(s["n"], s["step"], s["status"]) for s in rep["steps"]]}, indent=1))
    return 0 if rep["result"] in ("ok", "planned", "awaiting_editor_close") else 1


if __name__ == "__main__":
    sys.exit(main())
