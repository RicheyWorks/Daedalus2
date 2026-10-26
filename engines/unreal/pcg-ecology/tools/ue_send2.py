# SPDX-License-Identifier: MIT
"""Send a Python file to the Claude Unreal bridge (127.0.0.1:9877) and print the reply.

Fix (2026-10-12): the editor ticks slowly when it is in the background (~3 fps), so a blocking call could
outlive the client timeout and the reply was lost (bridge log: ConnectionResetError in _client). We now
submit with async:true (the bridge answers at once with a job id from its socket thread) and poll
job_result, which never touches the game thread, until done or the deadline passes.
Fix 2: unattended Remote Execution can hand back ANOTHER caller's reply when two bots run code at once
(seen live: our query returned the art queue's import result). We run in-process (unattended=False):
replies are tied to our job id. Our scripts open no dialogs, so the modal risk does not apply.
usage: python ue_send.py file.py [deadline_s=600] [key=value ...]   (key=value become globals, e.g. PYTH_YEARS=120)
"""
import socket, json, sys, time

def call(msg, timeout=15):
    s = socket.create_connection(("127.0.0.1", 9877), timeout=timeout)
    s.sendall((json.dumps(msg) + "\n").encode())
    b = b""
    while not b.endswith(b"\n"):
        c = s.recv(65536)
        if not c: break
        b += c
    s.close()
    return json.loads(b.decode())

def run(path, deadline=600.0, extra=None):
    code = open(path, encoding="utf-8-sig").read()
    if extra:
        code = "".join("%s = %r\n" % (k, v) for k, v in extra.items()) + code
    rid = "pythagoras-%s-%d" % (path.replace("\\", "/").split("/")[-1], int(time.time()))
    r = call({"id": rid, "type": "execute_python", "params": {"code": code, "async": True, "timeout": deadline, "unattended": False}})
    jid = (r.get("result") or {}).get("job_id")
    if not jid:
        return r
    end = time.time() + deadline
    while time.time() < end:
        j = call({"id": rid, "type": "job_result", "params": {"job_id": jid}})
        res = j.get("result") or {}
        if res.get("state") == "done":
            return res.get("reply")
        if j.get("status") != "ok":
            return j
        time.sleep(1.0)
    return {"status": "error", "message": "still running after %ss (job %s)" % (deadline, jid)}

if __name__ == "__main__":
    dl = float(sys.argv[2]) if len(sys.argv) > 2 and "=" not in sys.argv[2] else 600.0
    extra = {}
    for a in sys.argv[2:]:
        if "=" in a:
            k, v = a.split("=", 1)
            try: v = float(v)
            except ValueError: pass
            extra[k] = v
    print(json.dumps(run(sys.argv[1], dl, extra))[:8000])
