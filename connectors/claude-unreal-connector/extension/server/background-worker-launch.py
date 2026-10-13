# SPDX-License-Identifier: MIT
"""Launch only the installed Daedalus LOD worker in a minimized console."""

import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def launch_worker():
    if platform.system() != "Windows":
        raise RuntimeError("worker console startup is unavailable on this platform")

    executable = Path(sys.executable)
    if (not executable.is_absolute() or
            executable.name.lower() not in {"python.exe", "python3.exe"} or
            not executable.is_file()):
        raise RuntimeError("an existing absolute python.exe or python3.exe is required")

    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    if not local_app_data.is_absolute():
        raise RuntimeError("an absolute LOCALAPPDATA directory is required")
    jobs = local_app_data / "Daedalus" / "jobs"
    worker = jobs / "lodworker.py"
    if not worker.is_file():
        raise RuntimeError("the installed Daedalus jobs/lodworker.py is unavailable")

    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 7  # SW_SHOWMINNOACTIVE: preserve a visible console without taking focus.
    # Append separately. Opening these handles never truncates a previous run or the worker's JSONL.
    with (jobs / "lodworker.out").open("ab") as output, (jobs / "lodworker.err").open("ab") as errors:
        process = subprocess.Popen(
            [str(executable), str(worker)], cwd=str(jobs), stdin=subprocess.DEVNULL,
            stdout=output, stderr=errors, startupinfo=startup,
            creationflags=subprocess.CREATE_NEW_CONSOLE, shell=False, close_fds=True,
        )
    return process.pid


def main():
    try:
        if len(sys.argv) != 1:
            raise RuntimeError("this launcher accepts no script or process arguments")
        print(json.dumps({"status": "worker_started", "pid": launch_worker()}))
        return 0
    except (OSError, RuntimeError) as error:
        print(json.dumps({"status": "unavailable", "reason": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
