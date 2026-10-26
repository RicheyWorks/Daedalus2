# SPDX-License-Identifier: MIT
"""Run the bridge against the stand-in editor (tests/host.py) on a free port, for the length of a with-block.

    with standin(root) as port:
        call("ping", port=port)

`root` is a checkout of the connector (the default is this one), so the mutant runner can point it at a
scratch copy with a deliberate bug in it."""
import contextlib
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def standin(root=ROOT, seconds=300):
    port = free_port()
    proc = subprocess.Popen([sys.executable, os.path.join(root, "tests", "host.py"), str(port), str(seconds)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                break
            except OSError:
                if proc.poll() is not None:
                    raise RuntimeError("the stand-in host exited: " + proc.stdout.read().decode(errors="replace"))
                time.sleep(0.1)
        yield port
    finally:
        proc.kill()
        proc.wait()
