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


MIN_FREE_GB = 4.0   # a headless editor takes 2-4 GB; the user's machine has shown memory pressure


def free_memory_gb():
    """Available physical memory, from Windows (GlobalMemoryStatusEx); None off Windows."""
    if os.name != "nt":
        return None
    import ctypes

    class MEMSTAT(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MEMSTAT()
    m.dwLength = ctypes.sizeof(MEMSTAT)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 1024.0 ** 3


def _sandbox_running():
    if os.name != "nt":
        return False
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq UnrealEditor-Cmd.exe", "/NH"], capture_output=True, text=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return "UnrealEditor-Cmd.exe" in r.stdout


def sandbox_start(probe_source, tag="sweep", launch=True):
    """Write the probe script and launch the headless editor on it. Returns at once.
    Refuses when another sandbox is running or less than MIN_FREE_GB of RAM is free (no memory crashes)."""
    free = free_memory_gb()
    if free is not None and free < MIN_FREE_GB:
        raise RuntimeError("only %.1f GB of RAM free; a sandbox needs %.0f GB. Close something (Blender, a browser) "
                           "or run the probe in the open editor" % (free, MIN_FREE_GB))
    if _sandbox_running():
        raise RuntimeError("a sandbox editor is already running; wait for it (one at a time keeps memory safe)")
    root = os.path.join(tempfile.gettempdir(), "claude-unreal-sandbox")
    os.makedirs(root, exist_ok=True)
    out = os.path.join(root, "%s-%d" % (tag, int(time.time())))
    script = out + ".py"
    wrapper = (
        "import json, traceback\n"
        "OUT = %r\n"
        "import os as _os\n"
        "SKIP_EXTRA = set(open(OUT + '.skip').read().split()) if _os.path.exists(OUT + '.skip') else set()\n"
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
    if not launch:
        return {"pid": None, "out": out}
    project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path())
    log = open(out + ".log", "w", encoding="utf-8")
    args = [_editor_cmd(), project, "-run=pythonscript", "-script=" + script, "-unattended", "-nullrhi",
            "-nosplash", "-nopause", "-nosound", "-stdout", "-FullStdOutLogOutput"]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    return {"pid": p.pid, "out": out}


SUPERVISOR = r'''
import os, subprocess, sys
base, cmd, project = sys.argv[1], sys.argv[2], sys.argv[3]
for attempt in range(int(sys.argv[4]) if len(sys.argv) > 4 else 25):
    if os.path.exists(base + ".progress"):
        os.replace(base + ".progress", base + ".progress.%d" % attempt)
    with open(base + ".log", "w", encoding="utf-8") as log:
        subprocess.run([cmd, project, "-run=pythonscript", "-script=" + base + ".py", "-unattended", "-nullrhi",
                        "-nosplash", "-nopause", "-nosound", "-stdout"], stdout=log, stderr=subprocess.STDOUT,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if os.path.exists(base + ".json"):
        break
    prog = open(base + ".progress").read().splitlines() if os.path.exists(base + ".progress") else []
    if not prog:
        open(base + ".supervisor", "a").write("attempt %d crashed before any item; giving up\n" % attempt)
        break
    with open(base + ".skip", "a") as f:
        f.write(prog[-1] + "\n")
    open(base + ".supervisor", "a").write("attempt %d crashed on %s\n" % (attempt, prog[-1]))
open(base + ".supervisor", "a").write("done\n")
'''


def sandbox_supervise(probe_source, tag="sweep", attempts=25):
    """Like sandbox_start, but a supervisor process reruns the sandbox after each crash, skipping the item that
    crashed it (the probe must skip names in SKIP_EXTRA and call progress(name) before each item). The crashed
    items are the findings: <out>.supervisor lists them, <out>.json holds the rest."""
    started = sandbox_start(probe_source, tag, launch=False)
    out = started["out"]
    with open(out + "_supervisor.py", "w", encoding="utf-8") as f:
        f.write(SUPERVISOR)
    project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path())
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    p = subprocess.Popen([unreal.get_interpreter_executable_path(), out + "_supervisor.py", out, _editor_cmd(),
                          project, str(attempts)], creationflags=flags)
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
