# SPDX-License-Identifier: MIT
"""Capture the editor viewport through the Epic MCP server to a PNG on disk.

Both this client and the stdio proxy require a complete native HTTP reply. Saving
to disk does not bypass a native response-transfer reset. Failed calls are not replayed.

    python tools/unreal_mcp/capture.py out.png [x y z pitch yaw]
"""
import base64
import json
import os
import sys

if __package__:
    from .client import Mcp
    from .transport import TransportFailure
else:
    from client import Mcp
    from transport import TransportFailure


def main(argv):
    out = argv[0]
    args = {"annotations": {"gridSpacing": 0, "gridExtent": 0, "gridHeight": 0, "maxLabelDistance": 0, "classFilter": None, "maxLabels": 0}, "bShowUI": False}
    if len(argv) >= 6:
        x, y, z, pitch, yaw = (float(v) for v in argv[1:6])
        args["captureTransform"] = {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0}}
    try:
        m = Mcp(timeout=120)
        r = m.call("EditorToolset.EditorAppToolset", "CaptureViewport", **args)
    except TransportFailure as error:
        sys.stderr.write(json.dumps({"error": str(error), "data": error.data}) + "\n")
        return 1
    img = r.get("image", {}) if isinstance(r, dict) else {}
    data = img.get("data", "")
    if not data:
        print("no image: %s" % json.dumps(r)[:300])
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(base64.b64decode(data))
    print("%s %d bytes cam=%s" % (out, os.path.getsize(out), r.get("cameraLocation")))
    sys.stderr.write(json.dumps({"transfer": getattr(m, "last_transfer", {})}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
