#!/usr/bin/env python3
"""Teeth for TournamentServiceTest and SampleStatsTest (ADR-007 ideas 10 and 7).

Eight mutations. Six were caught immediately; the two listed first were **survivors**, and both
pointed at a test that was weaker than it looked:

1. *Excluded solvers still publish stats.* The test ran 21x21 dungeons, where IDA* refuses from
   the very first maze — so "excluded" and "no samples collected" were the same state, and a
   mutation publishing statistics whenever two samples existed changed nothing observable. The
   fix was to find a configuration exercising the real case: measured, IDA* finishes **five**
   19x19 dungeons before its third refusal. The test moved there, and `Standing` grew a
   `completed` count so the distinction is visible in the report too.

2. *Adversarial picks the wrong extreme.* The assertion was `worstGap >= bestGap`, and the
   mutation made both extremes search for the minimum — so they collapsed onto the same maze and
   `min >= min` held. The test now requires distinct seeds and a strict inequality.

Neither mutation was exotic; both were the obvious way to get the feature subtly wrong, and both
passed a suite that looked thorough. A survivor is a message about the test, not the code.

Usage:  python3 mutants/tourteeth.py
"""

import pathlib, re, subprocess

REPO = pathlib.Path("/root/daedalus-work/repo")
T = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/TournamentService.java"
S = REPO / "daedalus-core/src/main/java/com/daedalus/theory/SampleStats.java"
CAP = 600

MUT = [
 # Both of these SURVIVED the first version of the tests. See the docstring.
 (T, "excluded solvers still publish stats",
  "                    excluded ? null : SampleStats.summarise(toArray(samples)),",
  "                    samples.size() < 2 ? null : SampleStats.summarise(toArray(samples)),"),
 (T, "adversarial picks the wrong extreme",
  "            if (wa[i] - wb[i] > wa[worst] - wb[worst]) {",
  "            if (wa[i] - wb[i] < wa[worst] - wb[worst]) {"),
 (T, "never exclude a refusing solver",
  "                if (refusals.get(solver.id()) >= REFUSALS_BEFORE_EXCLUSION) {",
  "                if (false) {"),
 (T, "ties never reported",
  "            if (!d.distinguishable()) {", "            if (false) {"),
 (T, "excluded solvers sort first",
  "        standings.sort(Comparator\n                .comparing((Standing s) -> s.excluded())",
  "        standings.sort(Comparator\n                .comparing((Standing s) -> !s.excluded())"),
 (S, "normal quantile instead of t",
  "        return degreesOfFreedom >= 1 && degreesOfFreedom < T95.length\n                ? T95[degreesOfFreedom] : NORMAL_95;",
  "        return NORMAL_95;"),
 (S, "distinguishable always true",
  "        boolean distinguishable = summary.low() > 0 || summary.high() < 0;",
  "        boolean distinguishable = true;"),
 (S, "population sd (n denominator)",
  "        return Math.sqrt(sum / (values.length - 1));",
  "        return Math.sqrt(sum / values.length);"),
]

TESTS = "TournamentServiceTest,SampleStatsTest"
originals = {T: T.read_text(), S: S.read_text()}
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:38s} -> SKIP (anchor x{orig.count(old)})", flush=True); continue
        path.write_text(orig.replace(old, new))
        try:
            p = subprocess.run(["mvn","-B","-ntp","-pl","daedalus-server","-am","test",
                f"-Dtest={TESTS}","-Dsurefire.failIfNoSpecifiedTests=false",
                "-Dcheckstyle.skip","-Dspotbugs.skip","-Djacoco.skip"],
                cwd=REPO, capture_output=True, text=True, timeout=CAP)
            failed = sorted({m for m in re.findall(r"(?:TournamentServiceTest|SampleStatsTest)\.(\w+)", p.stdout)})
            verdict = "SURVIVED" if p.returncode == 0 else "caught by " + ", ".join(failed[:2])
        except subprocess.TimeoutExpired:
            verdict = f"caught: still running after {CAP}s"
        finally:
            path.write_text(orig)
        if verdict == "SURVIVED":
            survivors.append(name)
        print(f"{name:38s} -> {verdict}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    print("restored")
print(f"\n{len(MUT)-len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
