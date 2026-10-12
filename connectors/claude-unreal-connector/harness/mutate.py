# SPDX-License-Identifier: MIT
"""Break the connector on purpose, one way at a time, and require the suites to notice.
(CSRBT tools/mutate_run_all.py: a catalogue of (name, file, old, new, suite, why) applied to a scratch copy.)

KILLED: the named suite goes red against the mutant. SURVIVED: it stays green, so it can't see that break,
which is a finding to fix with a new check. Inconclusive: the anchor doesn't match exactly once (the code
moved; fix the catalogue). Mutants run in parallel, each against only the suite that should catch it.
Results go to ledgers/mutants.json.

    python -m harness.mutate [-j 6] [--list] [--only N]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import ledger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ("plugin", "tests", "extension", "harness")
BR = "plugin/ClaudeUnrealBridge/Content/Python/claude_unreal_bridge.py"
EXT = "extension/server/index.js"
SUITE = {"e2e": ["-m", "harness.e2e"], "contract": ["-m", "harness.contract"], "walk": ["-m", "harness.walk", "--standin"]}

MUTANTS = [
    ("nested ticks re-enter the pump", BR, "    if _pumping:\n        return\n", "", "e2e",
     "take_high_res_screenshot ticks Slate inside the call ('generator already executing')"),
    ("a waiting command is never stepped again", BR,
     "        for gen, req, box in list(_running):\n            _step(gen, req, box)\n",
     "        for gen, req, box in list(_running):\n            pass\n", "e2e",
     "screenshots, Play and add-ons wait across ticks"),
    ("the policy is ignored", BR, "    risk = RISK_OF.get(req.get(\"type\"), \"MUTATE\")\n    if not POLICY.get(risk, False):",
     "    risk = RISK_OF.get(req.get(\"type\"), \"MUTATE\")\n    if False:", "contract",
     "a READ-only bridge must refuse MUTATE and DESTRUCTIVE"),
    ("batch skips the per-item policy", BR, "        risk = RISK_OF.get(name, \"MUTATE\")\n        if not POLICY.get(risk, False):",
     "        risk = RISK_OF.get(name, \"MUTATE\")\n        if False:", "contract",
     "a batch can't smuggle a DESTRUCTIVE command past a MUTATE policy"),
    ("request_id replay is off", BR, "    if rid is not None and rid in _replies:", "    if False:", "contract",
     "a client retry would run an import twice"),
    ("an error is reported as ok", BR,
     '    return {"id": req.get("id"), "status": "error", "message": "%s: %s" % (type(e).__name__, e),',
     '    return {"id": req.get("id"), "status": "ok", "message": "%s: %s" % (type(e).__name__, e),', "e2e",
     "a failed command must not look like success"),
    ("Python runs attended", BR, "rx.run_command(_wrap(code), unattended=True)",
     "rx.run_command(_wrap(code), unattended=False)", "e2e",
     "attended, a modal dialog freezes the editor and the bridge"),
    ("DESTRUCTIVE without MUTATE is allowed", BR,
     '    if "DESTRUCTIVE" in allowed and "MUTATE" not in allowed:', "    if False:", "contract",
     "the ladder: destroying needs permission to change"),
    ("an unknown command answers ok", BR,
     '_finish(box, {"id": req.get("id"), "status": "error", "code": "UNKNOWN",',
     '_finish(box, {"id": req.get("id"), "status": "ok", "code": "UNKNOWN",', "contract",
     "a typo must not look like success"),
    ("screenshots come back as text", EXT, "if (typeof result.image_png_base64 === 'string') {", "if (false) {", "e2e",
     "Claude must see the viewport, not base64"),
    ("the result of Claude's code is dropped", BR, "            result = json.loads(text[len(RESULT_MARK):])",
     "            result = None", "e2e", "execute_python returns `result`"),
    ("Remote Execution off is silent", BR,
     '        out["note"] = box["fallback"] + "; ran directly, so a modal dialog would block the editor"\n', "",
     "e2e", "the agent must know dialogs could block"),
    ("register forgets the declared risk", BR, "    RISK_OF[name] = risk\n", "", "contract",
     "an add-on declared READ must stay usable under a READ policy"),
    ("Remote Execution reads the unreal API off the game thread", BR,
     "        got = _remote_node(want)",
     "        got = _remote_node(os.path.normcase(os.path.abspath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))))",
     "e2e", "found live on UE 5.8.3: unattended mode silently fell back to attended"),
    ("batch skips the per-item policy check", BR,
     "        if not POLICY.get(risk, False):\n            raise PermissionError(", "        if False:\n            raise PermissionError(",
     "contract", "a batch must not smuggle DESTRUCTIVE past a MUTATE policy"),
    ("async answers only after the job finishes", BR, "        if params.get(\"async\"):", "        if False:",
     "contract", "a long import must not meet a client timeout"),
    ("batch is not one undo step", BR, "    with unreal.ScopedEditorTransaction(p.get(\"transaction\", \"Claude batch\")):",
     "    with contextlib.nullcontext():", "contract", "one batch, one undo"),
    ("a command is dropped from list_commands", BR,
     '                          "risk": RISK_OF.get(n, "MUTATE")} for n in sorted(COMMANDS)],',
     '                          "risk": RISK_OF.get(n, "MUTATE")} for n in sorted(COMMANDS) if n != "save"],',
     "walk", "every command must be discoverable"),
]


def run(i):
    name, rel, old, new, suite, why = MUTANTS[i]
    d = tempfile.mkdtemp(prefix="cuc_mutant_")
    try:
        for c in COPY:
            shutil.copytree(os.path.join(ROOT, c), os.path.join(d, c), ignore=shutil.ignore_patterns("__pycache__"))
        p = os.path.join(d, rel)
        with open(p, encoding="utf-8") as f:
            src = f.read()
        if src.count(old) != 1:
            return {"name": name, "verdict": "inconclusive", "detail": "anchor matches %d times" % src.count(old)}
        with open(p, "w", encoding="utf-8") as f:
            f.write(src.replace(old, new))
        r = subprocess.run([sys.executable] + SUITE[suite], cwd=d, env=dict(os.environ, PYTHONPATH=d),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        fails = [l for l in r.stdout.decode("utf-8", "replace").splitlines() if l.startswith("FAIL")]
        if r.returncode != 0:
            return {"name": name, "verdict": "killed", "detail": "%s: %s" % (suite, (fails[0] if fails else "red")[5:90])}
        return {"name": name, "verdict": "SURVIVED", "detail": "%s stayed green: %s" % (suite, why)}
    except subprocess.TimeoutExpired:
        return {"name": name, "verdict": "killed", "detail": "%s hung (timeout)" % suite}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=6)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", type=int)
    a = ap.parse_args(argv)
    if a.list:
        for i, m in enumerate(MUTANTS):
            print("%2d  %-45s [%s] %s" % (i, m[0], m[4], m[5]))
        return 0
    idx = [a.only] if a.only is not None else list(range(len(MUTANTS)))
    with ThreadPoolExecutor(max_workers=max(1, a.j)) as pool:
        rows = list(pool.map(run, idx))
    for row in rows:
        print("%-12s %-45s %s" % (row["verdict"], row["name"], row["detail"]))
    killed = sum(1 for r in rows if r["verdict"] == "killed")
    if a.only is None:
        ledger.record_mutants("bridge", rows)
    print("%d/%d" % (killed, len(rows)))
    return 0 if killed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
