#!/usr/bin/env python3
"""RD jukebox load harness (stdlib only).

Scenarios, run concurrently against a local realm server:
  panel   - a panel open: GET /config + /seeds + /radio/stations
  arrange - GET /arrangement over seeds x genres x render options (cached hits, 202s, unknowns)
  relay   - open a radio relay stream, read ~64 KB, close
Reports per scenario: count, p50/p95/p99 latency (ms), errors (5xx/timeouts/conn), 429s (rate limited, counted apart).
usage: load.py BASE_URL [seconds] [panel_workers] [arrange_workers] [relay_workers]
"""
import json, random, statistics, sys, threading, time, urllib.request, urllib.error

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8088"
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 30
WORKERS = dict(panel=int(sys.argv[3]) if len(sys.argv) > 3 else 20,
               arrange=int(sys.argv[4]) if len(sys.argv) > 4 else 30,
               relay=int(sys.argv[5]) if len(sys.argv) > 5 else 6)
API = BASE + "/api/v1/jukebox"
SEEDS = ["e00015", "e00084", "e00165", "e00153", "e00601", "e02014"]
GENRES = ["original", "jazz", "rock", "reggae"]
OPTS = ["", "&format=flac", "&preset=harman&vinyl=50", "&preset=crossfeed"]
lock = threading.Lock()
stats = {k: {"lat": [], "ok": 0, "err": 0, "r429": 0, "codes": {}} for k in WORKERS}

def get(url, timeout=10, read=None):
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read(read) if read else r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = 0
    return code, (time.perf_counter() - t) * 1000

def record(kind, code, ms):
    with lock:
        s = stats[kind]
        s["codes"][code] = s["codes"].get(code, 0) + 1
        if code == 429: s["r429"] += 1
        elif code == 0 or code >= 500: s["err"] += 1
        else: s["ok"] += 1; s["lat"].append(ms)

stations = []
def worker(kind, stop):
    rnd = random.Random()
    while time.time() < stop:
        if kind == "panel":
            tot, worst = 0, 200
            for p in ("/config", "/seeds", "/radio/stations?lat=47.6062&lon=-122.3321"):
                c, ms = get(API + p); tot += ms
                if c != 200: worst = c
            record(kind, worst, tot)
        elif kind == "arrange":
            src = "token:1" if rnd.random() < .1 else "seed:" + rnd.choice(SEEDS)
            c, ms = get(f"{API}/arrangement?source={src}&genre={rnd.choice(GENRES)}&studio={str(rnd.random() < .5).lower()}{rnd.choice(OPTS)}")
            record(kind, c, ms)
        else:
            if not stations: time.sleep(.2); continue
            c, ms = get(f"{API}/radio/stream/{rnd.choice(stations)}", timeout=15, read=64 * 1024)
            record(kind, c, ms)

def pct(xs, p):
    if not xs: return float("nan")
    xs = sorted(xs); return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]

if __name__ == "__main__":
    try:
        st = json.load(urllib.request.urlopen(API + "/radio/stations?lat=47.6062&lon=-122.3321", timeout=20))["stations"]
        stations.extend(s["id"] for s in st[:8])
    except Exception as e:
        print("no stations:", e)
    stop = time.time() + SECS
    ts = [threading.Thread(target=worker, args=(k, stop), daemon=True) for k, n in WORKERS.items() for _ in range(n)]
    t0 = time.time(); [t.start() for t in ts]; [t.join() for t in ts]; el = time.time() - t0
    out = {}
    print(f"{BASE}  {el:.0f}s  workers {WORKERS}")
    print(f"{'scenario':8} {'n':>6} {'rps':>6} {'p50':>8} {'p95':>8} {'p99':>8} {'err%':>6} {'429%':>6}  codes")
    for k, s in stats.items():
        n = s["ok"] + s["err"] + s["r429"]
        row = dict(n=n, rps=round(n / el, 1), p50=round(pct(s["lat"], 50), 1), p95=round(pct(s["lat"], 95), 1),
                   p99=round(pct(s["lat"], 99), 1), errPct=round(100 * s["err"] / max(n, 1), 2), r429Pct=round(100 * s["r429"] / max(n, 1), 2),
                   codes=s["codes"])
        out[k] = row
        print(f"{k:8} {n:6} {row['rps']:6} {row['p50']:8} {row['p95']:8} {row['p99']:8} {row['errPct']:6} {row['r429Pct']:6}  {s['codes']}")
    print("JSON " + json.dumps(out))
