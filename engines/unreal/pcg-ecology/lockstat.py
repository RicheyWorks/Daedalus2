import sys
b=sys.modules["claude_unreal_bridge"]
lk=b._remote_lock
result={"locked":lk.locked(),"running":[(r.get("id"),r.get("type")) for _g,r,_b in list(b._running)],"queued":b._jobs.qsize(),"rx":str(b._remote.get("rx"))}
