# Copy of Daedalus2-pcg-ecology/engines/unreal/pcg-ecology/ue_send.py (async job + poll, unattended=False), id prefix disk-saver.
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

def run(path, deadline=600.0):
    code = open(path, encoding="utf-8-sig").read()
    rid = "disk-saver-%s-%d" % (path.replace("\\", "/").split("/")[-1], int(time.time()))
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
    dl = float(sys.argv[2]) if len(sys.argv) > 2 else 600.0
    print(json.dumps(run(sys.argv[1], dl))[:8000])
