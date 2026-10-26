# Driver: batches of 8 via the bridge, RAM check + recovery pause before each, resumable, time budget.
import subprocess, sys, json, time, ctypes, os
D = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver"
BUDGET = float(sys.argv[1]) if len(sys.argv) > 1 else 360; MINGB = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
class MS(ctypes.Structure):
    _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong)] + [(k, ctypes.c_ulonglong) for k in "tafxyzw"]
def free():
    s = MS(); s.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)); return s.a / 2**30
T0 = time.time(); log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
while time.time() - T0 < BUDGET:
    w = 0
    while free() < MINGB and w < 30: time.sleep(5); w += 5     # let memory recover
    if free() < MINGB: log("RAM %.2f GB < %.2f after 30 s pause: stopping (progress kept)" % (free(), MINGB)); break
    log("batch start, RAM %.2f GB" % free())
    r = subprocess.run([sys.executable, D + r"\ds_ue_send.py", D + r"\ds_canopy_ue.py", "90"], capture_output=True, text=True)
    log(r.stdout.strip()[-400:])
    try: res = json.loads(r.stdout.strip().splitlines()[-1])["result"]["result"]
    except Exception: log("bad reply, stopping"); break
    if res.get("remaining", 1) == 0: log("ALL DONE"); break
    time.sleep(3)
log("driver end")
