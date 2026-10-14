# SPDX-License-Identifier: MIT
"""Import a folder of Sol's rigged GLBs (a cast or a bestiary) into the open editor, ONE FILE PER BRIDGE CALL.

    python tools/unreal_play/import_cast.py <folder> [--root /Game/Daedalus/Art/Creatures] [--place REALM]

2026-10-13 22:19: importing 22 creatures inside one execute_python call blocked the game thread for the whole
import (frame counter stuck at 0), the GPU watchdog fired (Aftermath timeout, DRED no breadcrumb) and the editor
died. One GLB per call lets the editor tick, render and answer the watchdog between files; each call is ~2 s.
--place REALM then stands the imported creatures in the realm's outer ring (daedalus_realm_ground.place_creatures),
also one bridge call. Idempotent (SHA stamp per asset). Lives in the repo (ADR-045).
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "engines", "unreal", "DaedalusLink", "Content", "Python"))
from asset_pipeline import wire  # noqa: E402
import daedalus_import_cast as IC  # noqa: E402  (pure helpers: plan, sha)


def call(code, timeout=120):
    r = wire.call(wire.UNREAL, "execute_python", code=code, timeout=timeout)
    err = r.get("stderr") or r.get("error") or ""
    return (r.get("stdout") or ""), err


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print("usage: import_cast.py <folder with Mob_*.glb> [--root <content path>] [--place REALM]")
        return 2
    folder = args[0]
    root = argv[argv.index("--root") + 1] if "--root" in argv else IC.CAST_ROOT
    place = argv[argv.index("--place") + 1] if "--place" in argv else ""
    plan = IC.plan(folder)
    print("%d GLBs in %s -> %s" % (len(plan), folder, root), flush=True)
    if not plan:
        print('import: no planned assets; refusing empty success', flush=True)
        return 2
    _, setup_error = call("import importlib, daedalus_import_cast\nimportlib.reload(daedalus_import_cast)\n", 30)
    if setup_error:
        print('import: setup failed; no import dispatched\nERR '+str(setup_error)[-600:],flush=True)
        return 2
    counts = {"imported": 0, "skipped": 0, "failed": 0}
    if "--one-per-call" in argv:   # the slow, safe fallback: one bridge round trip per file
        for i, (aid, glb, sha) in enumerate(plan, 1):
            t0 = time.time()
            code = ("import daedalus_import_cast as C\n"
                    "s, made = C.import_one(%r, r'%s', %r, False, %r)\n"
                    "print(s, sum(1 for a in made if a['class'] == 'SkeletalMesh'), ','.join(a['name'] for a in made if a['class'] == 'AnimSequence'))\n") % (aid, glb, sha, root)
            out, err = call(code, 180)
            status = (out.split() or ["failed"])[0]
            if err:
                print("ERR", aid, err[:400], flush=True)
                print('import: outcome unknown; stopping without next import or placement',flush=True)
                return 2
            if status not in counts:
                print('import: unrecognized terminal status; stopping without next import',flush=True)
                return 2
            counts[status if status in counts else "failed"] += 1
            print("%2d/%d %-9s %s  %.1fs" % (i, len(plan), status, aid, time.time() - t0), flush=True)
            time.sleep(0.5)
    else:   # one call, one editor tick per file: daedalus.steps (the bridge advances the generator per tick)
        t0 = time.time()
        code = ("import daedalus_import_cast as C\n"
                "PLAN = %r\n"
                "def steps():\n"
                "    counts = {'imported': 0, 'skipped': 0, 'failed': 0}\n"
                "    for aid, glb, sha in PLAN:\n"
                "        s, made = C.import_one(aid, glb, sha, False, %r)\n"
                "        if s not in counts: raise ValueError('unknown import status: ' + str(s))\n"
                "        counts[s] += 1\n"
                "        yield '%%s %%s' %% (s, aid)\n"
                "    return {'counts': counts, 'planned': len(PLAN)}\n") % ([(a, g, h) for a, g, h in plan], root)
        r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="import_cast", timeout=max(120, 15 * len(plan)))
        res = r   # wire.call returns the command result: {steps, yielded, result, error, seconds}
        for line in res.get("yielded", []):
            print("  " + line, flush=True)
        summary = res.get('result')
        final = summary.get('counts') if isinstance(summary, dict) else None
        valid = (isinstance(final, dict) and set(final) == set(counts) and
                 all(type(n) is int and n >= 0 for n in final.values()) and
                 type(summary.get('planned')) is int and summary['planned'] == len(plan) and
                 sum(final.values()) == len(plan))
        if res.get('error') is not None or not valid:
            print('import: outcome unknown; terminal counts unavailable; no placement or retry', flush=True)
            print('ERR '+str(res.get('error') or 'incomplete terminal result')[-600:], flush=True)
            return 2
        counts = final
        print("steps=%s seconds=%s (one tick per file, one round trip)" % (res.get("steps"), res.get("seconds", round(time.time() - t0, 1))), flush=True)
    print("import: %d imported, %d skipped, %d failed" % (counts["imported"], counts["skipped"], counts["failed"]), flush=True)
    if counts['failed']:
        return 1
    if place:
        out, err = call("import importlib, daedalus_realm_ground as R\nimportlib.reload(R)\nprint(R.place_creatures(%r))\n" % place, 300)
        print(out[-1500:], ("ERR " + err[:800]) if err else "", flush=True)
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
