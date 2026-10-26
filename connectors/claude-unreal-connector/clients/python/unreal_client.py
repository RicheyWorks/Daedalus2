#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Talk to the Claude Unreal Bridge from any agent or script: no MCP needed, standard library only.

    from unreal_client import call
    call("ping")
    call("execute_python", code="result = len(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())")

Command line:
    python unreal_client.py ping
    python unreal_client.py list_commands
    python unreal_client.py execute_python code="print('hi')"
    python unreal_client.py viewport_screenshot width=1280 height=720 --save shot.png

Each call opens a connection, sends one JSON line {"id", "type", "params"} and reads one JSON line back (see
PROTOCOL.md). Raises BridgeError when the bridge answers with an error, and OSError when it can't be reached.
"""
import base64
import json
import os
import socket
import sys

HOST = os.environ.get("CLAUDE_UNREAL_HOST", "127.0.0.1")
PORT = int(os.environ.get("CLAUDE_UNREAL_PORT", "9877"))


class BridgeError(Exception):
    def __init__(self, reply):
        super().__init__(reply.get("message", "bridge error"))
        self.reply = reply


def call(command, timeout=600, host=HOST, port=PORT, **params):
    """Run one bridge command and return its result."""
    params.setdefault("bridge_timeout", timeout)
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall((json.dumps({"id": 1, "type": command, "params": params}) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = s.recv(1 << 20)
            if not chunk:
                break
            data += chunk
    reply = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
    if reply.get("status") != "ok":
        raise BridgeError(reply)
    return reply.get("result")


def _value(v):
    try:
        return json.loads(v)
    except ValueError:
        return v


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    save = None
    if "--save" in argv:
        i = argv.index("--save")
        save = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    params = dict(a.split("=", 1) for a in argv[1:])
    params = {k: _value(v) for k, v in params.items()}
    try:
        result = call(argv[0], **params)
    except BridgeError as e:
        print(e.reply.get("message"), file=sys.stderr)
        print(e.reply.get("traceback", ""), file=sys.stderr)
        return 1
    if isinstance(result, dict) and "image_png_base64" in result:
        png = base64.b64decode(result.pop("image_png_base64"))
        if save:
            with open(save, "wb") as f:
                f.write(png)
            result["saved"] = save
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
