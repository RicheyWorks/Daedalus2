# SPDX-License-Identifier: MIT
"""End to end as Claude sees it: the MCP extension (extension/server/index.js), driven over stdio by
tests/client.js, against the bridge on the stand-in editor. Prints the client's checks and n/m last.

    python -m harness.e2e
"""
import os
import subprocess
import sys

from harness.standin import ROOT, standin


def main(root=ROOT):
    with standin(root) as port:
        r = subprocess.run(["node", os.path.join(root, "tests", "client.js"), str(port)],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
    sys.stdout.write(r.stdout.decode("utf-8", "replace"))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
