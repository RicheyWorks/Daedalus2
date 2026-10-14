# SPDX-License-Identifier: MIT
"""Capture the editor viewport through the Epic MCP server to a PNG on disk (the stdio proxy cannot carry the
base64 reply; a file can).

    python tools/unreal_mcp/capture.py out.png [x y z pitch yaw]
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Mcp  # noqa: E402


def main(argv):
    out = argv[0]
    args = {"annotations": {"gridSpacing": 0, "gridExtent": 0, "gridHeight": 0, "maxLabelDistance": 0, "classFilter": None, "maxLabels": 0}, "bShowUI": False}
    if len(argv) >= 6:
        x, y, z, pitch, yaw = (float(v) for v in argv[1:6])
        args["captureTransform"] = {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0}}
    m = Mcp(timeout=120)
    r = m.call("EditorToolset.EditorAppToolset", "CaptureViewport", **args)
    img = r.get("image", {}) if isinstance(r, dict) else {}
    data = img.get("data", "")
    if not data:
        print("no image: %s" % json.dumps(r)[:300])
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(base64.b64decode(data))
    print("%s %d bytes cam=%s" % (out, os.path.getsize(out), r.get("cameraLocation")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
