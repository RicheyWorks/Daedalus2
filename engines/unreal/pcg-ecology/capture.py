import socket,json,time,base64,sys
def call(m,t=15):
    s=socket.create_connection(("127.0.0.1",9877),timeout=t); s.sendall((json.dumps(m)+"\n").encode()); b=b""
    while not b.endswith(b"\n"):
        c=s.recv(1<<20)
        if not c: break
        b+=c
    return json.loads(b)
r=call({"id":"pyth-cap","type":sys.argv[2],"params":{"width":1600,"height":900,"async":True}})
jid=r["result"]["job_id"]
for i in range(90):
    j=call({"id":"pyth-cap","type":"job_result","params":{"job_id":jid}},30)
    if j["result"]["state"]=="done":
        rep=j["result"]["reply"]
        if rep.get("status")!="ok": print(rep); sys.exit(1)
        open(sys.argv[1],"wb").write(base64.b64decode(rep["result"]["image_png_base64"])); print("ok",rep["result"]["bytes"]); break
    time.sleep(1)
