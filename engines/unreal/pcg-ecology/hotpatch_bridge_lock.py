# Hot-patch the running bridge (no restart): serialize Remote Execution run_command calls.
import sys, threading
b = sys.modules.get("claude_unreal_bridge")
if getattr(b, "_pyth_locked", False):
    result = "already patched"
else:
    lock = threading.Lock()
    def _run_remote(code, box, want, b=b, lock=lock):
        try:
            got = b._remote_node(want)
            if got is None:
                box["fallback"] = b._remote["error"]; return
            rx, _node = got
            with lock:
                box["reply"] = rx.run_command(b._wrap(code), unattended=True)
        except Exception as e:
            box["fallback"] = "Remote Execution failed: %s" % e
            b._remote.update(rx=None, node=None)
        finally:
            box["done"] = True
    b._remote_lock = lock; b._run_remote = _run_remote; b._pyth_locked = True
    result = "patched"
