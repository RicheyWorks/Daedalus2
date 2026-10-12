# SPDX-License-Identifier: MIT
"""Send a Python file to the Claude Unreal bridge (127.0.0.1:9877) and print the reply."""
import socket, json, sys
code = open(sys.argv[1], encoding="utf-8-sig").read()
s = socket.create_connection(("127.0.0.1", 9877), timeout=float(sys.argv[2]) if len(sys.argv) > 2 else 300)
s.sendall((json.dumps({"id": "pythagoras-" + sys.argv[1][-20:], "type": "execute_python", "params": {"code": code}}) + "\n").encode())
b = b""
while not b.endswith(b"\n"):
    c = s.recv(65536)
    if not c: break
    b += c
print(b.decode()[:6000])
