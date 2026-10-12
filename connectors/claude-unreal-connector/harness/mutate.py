# SPDX-License-Identifier: MIT
"""Break the connector on purpose, one way at a time, and require the suites to notice.
(CSRBT tools/mutate_run_all.py: a catalogue of (name, file, old, new, why), each applied to a scratch copy.)

A mutant is KILLED when run_all goes red against it, and it SURVIVED when everything stays green, which means
the suites cannot see that break: a finding to fix with a new check. An anchor that doesn't match exactly once
is inconclusive (the code moved; fix the catalogue). Results go to ledgers/mutants.json.

    python -m harness.mutate            # every mutant
    python -m harness.mutate --list
    python -m harness.mutate --only 3   # one mutant; the ledger is not written
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from harness import ledger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ("plugin", "tests", "extension", "harness")
BR = "plugin/ClaudeUnrealBridge/Content/Python/claude_unreal_bridge.py"
EXT = "extension/server/index.js"

MUTANTS = [
    ("nested ticks re-enter the pump", BR, "    if _pumping:\n        return\n", "",
     "take_high_res_screenshot ticks Slate inside the call: 'generator already executing'"),
    ("a waiting command is never stepped again", BR,
     "        for gen, req, box in list(_running):\n            _step(gen, req, box)\n",
     "        for gen, req, box in list(_running):\n            pass\n",
     "screenshots, Play and add-ons wait across ticks"),
    ("the policy is ignored", BR, "    if not POLICY.get(risk, False):", "    if False:",
     "a READ-only bridge must refuse MUTATE and DESTRUCTIVE"),
    ("request_id replay is off", BR, "    if rid is not None and rid in _replies:", "    if False:",
     "a client retry would run an import twice"),
    ("an error is reported as ok", BR,
     '    return {"id": req.get("id"), "status": "error", "message": "%s: %s" % (type(e).__name__, e),',
     '    return {"id": req.get("id"), "status": "ok", "message": "%s: %s" % (type(e).__name__, e),',
     "a failed command must not look like success"),
    ("Python runs attended", BR, "rx.run_command(_wrap(code), unattended=True)", "rx.run_command(_wrap(code), unattended=False)",
     "attended, a modal dialog freezes the editor and the bridge"),
    ("DESTRUCTIVE without MUTATE is allowed", BR,
     '    if "DESTRUCTIVE" in allowed and "MUTATE" not in allowed:', "    if False:",
     "the ladder: destroying needs permission to change"),
    ("an unknown command answers ok", BR,
     '_finish(box, {"id": req.get("id"), "status": "error", "code": "UNKNOWN",',
     '_finish(box, {"id": req.get("id"), "status": "ok", "code": "UNKNOWN",',
     "a typo must not look like success"),
    ("screenshots come back as text", EXT, "if (typeof result.image_png_base64 === 'string') {", "if (false) {",
     "Claude must see the viewport, not base64"),
    ("the result of Claude's code is dropped", BR, "            result = json.loads(text[len(RESULT_MARK):])",
     "            result = None", "execute_python returns `result`"),
    ("Remote Execution off is silent", BR,
     '        out["note"] = box["fallback"] + "; ran directly, so a modal dialog would block the editor"\n', "",
     "the agent must know dialogs could block"),
    ("register forgets the declared risk", BR, "    RISK_OF[name] = risk\n", "",
     "an add-on declared READ stays usable under a READ policy"),
]


def scratch():
    d = tempfile.mkdtemp(prefix="cuc_mutant_")
    for c in COPY:
        shutil.copytree(os.path.join(ROOT, c), os.path.join(d, c), ignore=shutil.ignore_patterns("__pycache__"))
    return d


def run(i, verbose=False):
    name, rel, old, new, why = MUTANTS[i]
    d = scratch()
    try:
        p = os.path.join(d, rel)
        with open(p, encoding="utf-8") as f:
            src = f.read()
        if src.count(old) != 1:
            return {"name": name, "verdict": "inconclusive", "detail": "anchor matches %d times" % src.count(old)}
        with open(p, "w", encoding="utf-8") as f:
            f.write(src.replace(old, new))
        r = subprocess.run([sys.executable, "-m", "harness.run_all", "--root", d, "--no-ledger", "-j", "3"],
                           cwd=d, env=dict(os.environ, PYTHONPATH=d), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=900)
        out = r.stdout.decode("utf-8", "replace")
        if verbose:
            print(out)
        red = [l.split()[1] for l in out.splitlines() if l[:6].strip() in ("FAIL", "FAIL*", "SHORT", "EMPTY")]
        if r.returncode != 0:
            return {"name": name, "verdict": "killed", "detail": "red: " + ", ".join(red)}
        return {"name": name, "verdict": "SURVIVED", "detail": "every suite stayed green: " + why}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", type=int)
    a = ap.parse_args(argv)
    if a.list:
        for i, m in enumerate(MUTANTS):
            print("%2d  %-45s %s" % (i, m[0], m[4]))
        return 0
    idx = [a.only] if a.only is not None else range(len(MUTANTS))
    rows = []
    for i in idx:
        row = run(i, verbose=a.only is not None)
        rows.append(row)
        print("%-12s %-45s %s" % (row["verdict"], row["name"], row["detail"]))
    killed = sum(1 for r in rows if r["verdict"] == "killed")
    if a.only is None:
        ledger.record_mutants("bridge", rows)
    print("%d/%d" % (killed, len(rows)))
    return 0 if killed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
