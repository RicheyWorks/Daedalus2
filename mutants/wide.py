#!/usr/bin/env python3
"""Re-check survivors against the WHOLE reactor: a guarantee may be pinned by a test in a
different module than the code it protects, which the per-module pass would miss."""
import subprocess, pathlib
import verdict as V
REPO = pathlib.Path(__file__).resolve().parent.parent
CASES = [
    ("leaderboard-order",
     "daedalus-core/src/main/java/com/daedalus/model/LeaderboardEntry.java",
     "int byScore = Long.compare(other.score, this.score);",
     "int byScore = Long.compare(this.score, other.score); // MUTANT"),
    ("replay-fidelity",
     "daedalus-core/src/main/java/com/daedalus/solver/SearchRecorder.java",
     "observer.accept(node);",
     "if (node % 2 == 0) observer.accept(node); // MUTANT"),
]
for name, rel, old, new in CASES:
    p = REPO / rel
    orig = p.read_text()
    assert old in orig, name
    p.write_text(orig.replace(old, new, 1))
    try:
        r = subprocess.run("mvn -B -ntp test -Dspotbugs.skip -Djacoco.skip=true "
                           "-Dcheckstyle.skip=true 2>&1",
                           shell=True, cwd=REPO, capture_output=True, text=True, timeout=2400)
        out = r.stdout + r.stderr
        # A red reactor is only a catch if a test actually failed in it.
        caught = V.is_catch(V.classify(0 if "BUILD SUCCESS" in out else 1, out))
        print(f"{'CAUGHT' if caught else '*** SURVIVED (whole reactor) ***':32} {name}", flush=True)
        for line in out.splitlines():
            if "<<< FAILURE" in line or "<<< ERROR" in line:
                print("    " + line.strip()[:140], flush=True)
    finally:
        p.write_text(orig)
