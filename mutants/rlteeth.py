#!/usr/bin/env python3
"""Teeth for RateLimitCoverageTest.

Three mutations, one per direction the check guards: an unmetered write endpoint (the original
gap — POST /session/{id}/move sustained 201 requests/s unthrottled while its twin stopped at
1200/min), a budget naming an instance application.yml never defines (which silently limits
nothing), and a configured limiter no endpoint names (a budget guarding nothing). All three are
caught.

Usage:  python3 mutants/rlteeth.py
"""

import pathlib, re, subprocess
import verdict as V
REPO = pathlib.Path(__file__).resolve().parent.parent
C = REPO / "daedalus-server/src/main/java/com/daedalus/server/controller/MazeController.java"
Y = REPO / "daedalus-server/src/main/resources/application.yml"
MUT = [
 (C, "the original gap: move unmetered", '    @PerKeyRateLimit("sessionMove")\n    public ResponseEntity<Boolean> move(', '    public ResponseEntity<Boolean> move('),
 (C, "budget names a missing instance", '@PerKeyRateLimit("sessionMove")', '@PerKeyRateLimit("sessionMoveTypo")'),
 (Y, "a limiter guarding nothing", "      sessionMove:\n        limit-for-period: 1200", "      orphanBudget:\n        limit-for-period: 5\n        limit-refresh-period: 1m\n        timeout-duration: 0\n        register-health-indicator: false\n      sessionMove:\n        limit-for-period: 1200"),
]
originals = {C: C.read_text(), Y: Y.read_text()}
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:34s} -> SKIP (anchor x{orig.count(old)})", flush=True); continue
        path.write_text(orig.replace(old, new))
        try:
            p = subprocess.run(["mvn","-B","-ntp","-pl","daedalus-server","test",
                "-Dtest=RateLimitCoverageTest","-Dsurefire.failIfNoSpecifiedTests=false",
                "-Dcheckstyle.skip","-Dspotbugs.skip","-Djacoco.skip"],
                cwd=REPO, capture_output=True, text=True, timeout=600)
            failed = sorted({m for m in re.findall(r"RateLimitCoverageTest\.(\w+)", p.stdout)})
            v = V.classify(p.returncode, p.stdout, failed)
        except subprocess.TimeoutExpired:
            v = "caught: timed out"
        finally:
            path.write_text(orig)
        if not V.is_catch(v): survivors.append(name)
        print(f"{name:34s} -> {v}", flush=True)
finally:
    for path, text in originals.items(): path.write_text(text)
    print("restored")
print(f"\n{len(MUT)-len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
