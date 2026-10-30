#!/usr/bin/env python3
"""Teeth for the two audit tests: ConfigCoverageTest and BoundedStoresTest's cache scan.

These tests assert an absence ("no undocumented keys", "no unbounded caches"), which is the
shape most at risk of being vacuous. So the mutations reintroduce the exact defects the audit
found, plus one that breaks the scanners themselves.
"""
import pathlib, re, subprocess
import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
YML = REPO / "daedalus-server/src/main/resources/application.yml"
SVC = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/TournamentService.java"

MUT = [
 (YML, "the original dead-key bug, restored",
  "  maze:\n    cache:\n      max-size: ${DAEDALUS_MAZE_CACHE_MAX:5000}\n      idle-ttl: ${DAEDALUS_MAZE_CACHE_TTL:2h}",
  "  cache:\n    maze-cache-size: 256\n    maze-cache-ttl-minutes: 30"),
 (YML, "a whole feature block undocumented",
  "  tournament:\n    max-mazes: ${DAEDALUS_TOURNAMENT_MAX_MAZES:24}",
  "  tournament:\n    unrelated-key: 1\n    max-mazes-typo: ${DAEDALUS_TOURNAMENT_MAX_MAZES:24}"),
 (SVC, "an unbounded cache slips in",
  "                .maximumSize(maxCached).expireAfterAccess(idleTtl).build();",
  "                .expireAfterAccess(idleTtl).build();"),
]

TESTS = "ConfigCoverageTest,BoundedStoresTest"
V.restore_on_signal()
originals = {YML: YML.read_text(), SVC: SVC.read_text()}
V.snapshot(originals)
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:38s} -> SKIP (anchor x{orig.count(old)})", flush=True)
            continue
        path.write_text(orig.replace(old, new))
        try:
            p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "test",
                                f"-Dtest={TESTS}", "-Dsurefire.failIfNoSpecifiedTests=false",
                                "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                               cwd=REPO, capture_output=True, text=True, timeout=600)
            failed = sorted({m for m in re.findall(
                r"(?:ConfigCoverageTest|BoundedStoresTest)\.(\w+)", p.stdout)})
            verdict = V.classify(p.returncode, p.stdout, failed)
        except subprocess.TimeoutExpired:
            verdict = "caught: timed out"
        finally:
            path.write_text(orig)
        if not V.is_catch(verdict):
            survivors.append(name)
        print(f"{name:38s} -> {verdict}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")
print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
