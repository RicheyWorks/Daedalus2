# SPDX-License-Identifier: MIT
"""A stand-in for Epic's remote_execution.py (the client half of Unreal's Python Remote Execution), so the
bridge's unattended path is tested without Unreal. It answers like the editor: run_command returns
{"success", "result", "output": [{"type", "output"}]} and records whether the call asked for unattended.
Set ENABLED = False to act as an editor with Remote Execution switched off (no node answers)."""
import contextlib
import io
import socket

ENABLED = True
CALLS = []
PROJECT_ROOT = None   # host.py points this at the stand-in project


class RemoteExecution(object):
    def __init__(self, config=None):
        self._open = False

    def start(self):
        self._open = True

    def stop(self):
        self._open = False

    @property
    def remote_nodes(self):
        if not ENABLED:
            return []
        return [{"node_id": "node-1", "project_root": PROJECT_ROOT, "machine": socket.gethostname()}]

    def open_command_connection(self, node_id):
        CALLS.append(("open", node_id))

    def run_command(self, command, unattended=True, exec_mode="ExecuteFile", raise_on_failure=False):
        CALLS.append(("run", unattended))
        import unreal
        buf = io.StringIO()
        ok, err = True, None
        with contextlib.redirect_stdout(buf):
            try:
                exec(compile(command, "<remote>", "exec"), {"unreal": unreal, "__name__": "__main__"})
            except Exception as e:
                ok, err = False, "%s: %s" % (type(e).__name__, e)
        out = [{"type": "Info", "output": line} for line in buf.getvalue().splitlines()]
        return {"success": ok, "result": err or "None", "output": out}
