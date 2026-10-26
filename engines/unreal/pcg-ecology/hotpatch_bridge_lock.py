# Unwedge: a Remote Execution run_command never returned while holding the serialize lock (deadlock introduced by
# the earlier hot-patch). Stop that RemoteExecution so the stuck call raises and releases the lock; the next call
# reconnects. Then install a lock that never waits forever: on timeout the call falls back to running in-process.
import sys, threading, time
b = sys.modules["claude_unreal_bridge"]
old = b._remote.get("rx")
try:
    if old: old.stop()
except Exception as e:
    pass
b._remote.update(rx=None, node=None)
lock = threading.Lock()
def _run_remote(code, box, want, b=b, lock=lock):
    got_lock = lock.acquire(timeout=30)
    try:
        if not got_lock:
            box["fallback"] = "Remote Execution busy >30 s"; return
        got = b._remote_node(want)
        if got is None:
            box["fallback"] = b._remote["error"]; return
        rx, _node = got
        box["reply"] = rx.run_command(b._wrap(code), unattended=True)
    except Exception as e:
        box["fallback"] = "Remote Execution failed: %s" % e
        try: b._remote["rx"] and b._remote["rx"].stop()
        except Exception: pass
        b._remote.update(rx=None, node=None)
    finally:
        if got_lock: lock.release()
        box["done"] = True
b._remote_lock = lock; b._run_remote = _run_remote
time.sleep(0.5)
result = {"old_lock_still_locked": getattr(b, "_pyth_old", None), "running": len(b._running)}
