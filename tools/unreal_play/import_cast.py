# SPDX-License-Identifier: MIT
"""Import a realm cast folder (Sol's rigged GLBs) into the open editor through the bridge.

    python tools/unreal_play/import_cast.py "C:\\Users\\730ri\\Documents\\Codex\\2026-10-13\\parcels-buildout\\cast"

Runs daedalus_import_cast.import_folder inside the editor (idempotent by manifest SHA). Lives in the repo (ADR-045).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402


def main(argv):
    if not argv:
        print("usage: import_cast.py <folder with Mob_*.glb>")
        return 2
    folder = argv[0].replace("\\", "\\\\")
    code = "import importlib, daedalus_import_cast as C\nimportlib.reload(C)\nprint(C.import_folder(r'%s'))\n" % argv[0]
    r = wire.call(wire.UNREAL, "execute_python", code=code, timeout=900)
    print((r.get("stdout") or "")[-4000:])
    err = r.get("stderr") or r.get("error") or ""
    if err:
        print("ERR", err[:1200])
    return 0 if "0 failed" in (r.get("stdout") or "") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
