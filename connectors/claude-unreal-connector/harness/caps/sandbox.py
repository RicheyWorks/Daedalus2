# SPDX-License-Identifier: MIT
"""Run risky probes in a throwaway headless editor, so a crash never takes the user's editor down.

Two live crashes (UE 5.8.3) came from creating assets with unknown factories inside the user's open editor. The
sweeps now run in UnrealEditor-Cmd: the open editor starts it (through execute_python), it loads the same project
with no window and no rendering (-nullrhi), runs the probe script, and writes:
  <out>.progress   one line per item BEFORE it is tried, so after a crash the last line names the culprit
  <out>.json       the results, when it finishes
  <out>.log        its stdout/stderr

Use, from execute_python in the open editor (this file's text is sent as the code, then):
    result = sandbox_start(probe_source, "factories")        # -> {"pid", "out"}
    result = sandbox_poll("<out>")                            # -> {"running", "progress_last", "result"?}
"""
import json
import os
import subprocess
import tempfile
import time

import unreal


def _editor_cmd():
    eng = unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_dir())
    for name in ("UnrealEditor-Cmd.exe", "UnrealEditor-Cmd"):
        for sub in ("Binaries/Win64", "Binaries/Linux", "Binaries/Mac"):
            p = os.path.join(eng, sub, name)
            if os.path.exists(p):
                return p
    raise RuntimeError("UnrealEditor-Cmd not found under " + eng)


def sandbox_start(probe_source, tag="sweep"):
    """Write the probe script and launch the headless editor on it. Returns at once."""
    root = os.path.join(tempfile.gettempdir(), "claude-unreal-sandbox")
    os.makedirs(root, exist_ok=True)
    out = os.path.join(root, "%s-%d" % (tag, int(time.time())))
    script = out + ".py"
    wrapper = (
        "import json, traceback\n"
        "OUT = %r\n"
        "def progress(line):\n"
        "    with open(OUT + '.progress', 'a', encoding='utf-8') as f:\n"
        "        f.write(line + '\\n'); f.flush()\n"
        "try:\n"
        "%s\n"
        "    payload = result\n"
        "except Exception as e:\n"
        "    payload = {'error': repr(e), 'trace': traceback.format_exc()}\n"
        "with open(OUT + '.json', 'w', encoding='utf-8') as f:\n"
        "    json.dump(payload, f, default=repr)\n"
    ) % (out, "\n".join("    " + ln for ln in probe_source.splitlines()))
    with open(script, "w", encoding="utf-8") as f:
        f.write(wrapper)
    project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path())
    log = open(out + ".log", "w", encoding="utf-8")
    args = [_editor_cmd(), project, "-run=pythonscript", "-script=" + script, "-unattended", "-nullrhi",
            "-nosplash", "-nopause", "-nosound", "-stdout", "-FullStdOutLogOutput"]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    return {"pid": p.pid, "out": out}


def _alive(pid):
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], capture_output=True, text=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def sandbox_poll(out, pid=None):
    """Where the sandbox has got to: still running, the last item it started, and its result when done."""
    prog = []
    if os.path.exists(out + ".progress"):
        with open(out + ".progress", encoding="utf-8") as f:
            prog = f.read().splitlines()
    res = None
    if os.path.exists(out + ".json"):
        with open(out + ".json", encoding="utf-8") as f:
            res = json.load(f)
    tail = ""
    if os.path.exists(out + ".log"):
        with open(out + ".log", encoding="utf-8", errors="replace") as f:
            tail = f.read()[-3000:]
    running = _alive(pid) if pid else res is None
    crashed = res is None and not running
    return {"running": running, "crashed": crashed, "items_started": len(prog),
            "progress_last": prog[-1] if prog else None, "result": res,
            "log_tail": tail if crashed else tail[-600:]}
