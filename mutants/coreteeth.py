#!/usr/bin/env python3
"""The two new core tests exist so daedalus-core guards its own guarantees. Prove it:
re-run the mutations that previously survived a core-only run."""
import subprocess, pathlib
import verdict as V
REPO = pathlib.Path(__file__).resolve().parent.parent
CASES = [
    ("leaderboard-order",
     "daedalus-core/src/main/java/com/daedalus/model/LeaderboardEntry.java",
     "int byScore = Long.compare(other.score, this.score);",
     "int byScore = Long.compare(this.score, other.score); // MUTANT"),
    ("replay-fidelity-half",
     "daedalus-core/src/main/java/com/daedalus/solver/SearchRecorder.java",
     "observer.accept(node);",
     "if (node % 2 == 0) observer.accept(node); // MUTANT"),
    ("replay-fidelity-onedrop",
     "daedalus-core/src/main/java/com/daedalus/solver/SearchRecorder.java",
     "observer.accept(node);",
     "if (node != 5) observer.accept(node); // MUTANT: drops a single expansion"),
]
for name, rel, old, new in CASES:
    p = REPO / rel
    orig = p.read_text()
    assert old in orig, name
    p.write_text(orig.replace(old, new, 1))
    try:
        r = subprocess.run("mvn -B -ntp -pl daedalus-core test -Dspotbugs.skip "
                           "-Dcheckstyle.skip=true -Djacoco.skip=true 2>&1",
                           shell=True, cwd=REPO, capture_output=True, text=True, timeout=1200)
        out = r.stdout + r.stderr
        # A red reactor is only a catch if a test actually failed in it.
        caught = V.is_catch(V.classify(0 if "BUILD SUCCESS" in out else 1, out))
        print(f"{'CAUGHT (core-only)' if caught else '*** STILL SURVIVES ***':26} {name}", flush=True)
        for line in out.splitlines():
            if "<<< FAILURE" in line:
                print("    " + line.strip()[:130], flush=True)
                break
    finally:
        p.write_text(orig)
