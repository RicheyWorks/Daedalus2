# SPDX-License-Identifier: MIT
"""The walk robot: drive every command the bridge lists, with arguments formed only from its declared params,
and account for every one. (CSRBT tools/harness_walk.py, for an Unreal bridge.)

Buckets: driven (answered ok), refused (the bridge's policy said no: code REFUSED), declined (above
--max-risk, so the walker did not send it), excluded (named in EXCLUDE with a reason), unschemable (a
required param the pools can't form), failed (any other error). The identity

    discovered == driven + refused + declined + excluded + unschemable + failed

must hold, or the run says UNACCOUNTED and fails. A new command with no way to drive it shows up as
unschemable or failed instead of silently passing. Writes ledgers/walk.json under the target's name and prints
n/m last, n being the commands accounted for without failure.

    python -m harness.walk --standin
    python -m harness.walk --port 9877 --max-risk SENSITIVE_READ --target live
"""
import argparse
import sys

from harness import ledger
from harness.client import call

RISKS = ("READ", "SENSITIVE_READ", "MUTATE", "DESTRUCTIVE")

# Commands the walker does not send, each with its reason. A reasonless exclusion is a failure.
EXCLUDE = {
    "test.freeze": "stops the stand-in's ticks on purpose (the frozen-editor canary in tests/client.js)",
    "test.remote_off": "switches the stand-in's Remote Execution off for the rest of the run",
    "test.policy": "changes the bridge's policy; harness.contract drives it on purpose",
    "job_result": "needs a job id from an async call; harness.contract drives it",
}

# Every bridge must list these. A bridge that silently drops one fails the walk, which otherwise only drives
# what is listed and could not notice a command vanishing.
CORE = ("ping", "list_commands", "get_level_info", "get_actor_info", "execute_python", "viewport_screenshot",
        "play", "stop", "save", "output_log", "capture_view", "batch", "job_result")

# How to form a value for a declared param, by name first, then by type. A target can add pools with --pool.
POOLS = {
    "code": "result = 1 + 1",
    "name": "@first_actor",     # resolved from get_level_info
    "limit": 5, "lines": 20, "width": 320, "height": 180, "from": 2,
    "filter": "Display", "folder": "", "who": "walker", "simulate": False,
    "commands": [{"type": "ping"}, {"type": "get_level_info", "params": {"limit": 1}}], "transaction": "walk",
    "keep_going": False,
}
BY_TYPE = {"int": 1, "bool": False, "str": ""}


def form(params, first_actor):
    """Arguments for a command from its declared params, or (None, the param it can't form)."""
    args = {}
    for pname, spec in (params or {}).items():
        required = "required" in str(spec)
        if pname in POOLS:
            v = POOLS[pname]
            args[pname] = first_actor if v == "@first_actor" else v
        else:
            kind = str(spec).split()[0] if spec else "str"
            if kind in BY_TYPE and not required:
                continue   # optional and unknown: leave it to the command's default
            if kind in BY_TYPE:
                args[pname] = BY_TYPE[kind]
            else:
                return None, pname
        if required and args.get(pname) in (None, ""):
            return None, pname
    return args, None


def walk(port, host="127.0.0.1", max_risk="DESTRUCTIVE", target="standin"):
    man = call("list_commands", host=host, port=port)
    if man.get("status") != "ok":
        print("FAIL list_commands: %s" % man.get("message"))
        return 1
    commands = man["result"]["commands"]
    level = call("get_level_info", {"limit": 1}, host=host, port=port)
    actors = (level.get("result") or {}).get("actors") or []
    first_actor = actors[0]["label"] if actors else ""
    cap = RISKS.index(max_risk)
    rows, buckets = [], {k: 0 for k in ("driven", "refused", "declined", "excluded", "unschemable", "failed")}
    for c in commands:
        name, risk = c["name"], c.get("risk", "MUTATE")
        if name in EXCLUDE:
            bucket, detail = "excluded", EXCLUDE[name]
        elif RISKS.index(risk) > cap:
            bucket, detail = "declined", "%s is above --max-risk %s" % (risk, max_risk)
        else:
            args, missing = form(c.get("params"), first_actor)
            if args is None:
                bucket, detail = "unschemable", "can't form required param %r" % missing
            else:
                r = call(name, args, host=host, port=port, timeout=60)
                if r.get("status") == "ok":
                    bucket, detail = "driven", "ok"
                elif r.get("code") == "REFUSED":
                    bucket, detail = "refused", r.get("message", "")
                else:
                    bucket, detail = "failed", (r.get("message") or "")[:160]
        buckets[bucket] += 1
        rows.append({"command": name, "risk": risk, "bucket": bucket, "detail": detail})
        print(("PASS " if bucket != "failed" else "FAIL ") + "%-28s %-14s %-11s %s" % (name, risk, bucket, detail[:70]))
    discovered = len(commands)
    accounted = sum(buckets.values())
    listed = {c["name"] for c in commands}
    missing = [n for n in CORE if n not in listed]
    for n in missing:
        print("FAIL core command %s is not listed" % n)
    buckets["failed"] += len(missing)
    if accounted != discovered:
        print("FAIL UNACCOUNTED: discovered %d, accounted %d" % (discovered, accounted))
    for r in rows:
        if r["bucket"] == "excluded" and not r["detail"]:
            print("FAIL %s is excluded without a reason" % r["command"])
            buckets["failed"] += 1
    ledger.record("walk", target, {"discovered": discovered, "max_risk": max_risk, "buckets": buckets, "rows": rows})
    good = discovered - buckets["failed"] - buckets["unschemable"]
    print("%d/%d" % (good, discovered))
    return 0 if good == discovered and accounted == discovered else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--standin", action="store_true", help="walk the stand-in editor (no Unreal needed)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9877)
    ap.add_argument("--max-risk", default="DESTRUCTIVE", choices=RISKS)
    ap.add_argument("--target", default=None, help="name for the ledger entry (default: standin or live)")
    a = ap.parse_args(argv)
    if a.standin:
        from harness.standin import standin
        with standin() as port:
            return walk(port, max_risk=a.max_risk, target=a.target or "standin")
    return walk(a.port, a.host, a.max_risk, a.target or "live")


if __name__ == "__main__":
    sys.exit(main())
