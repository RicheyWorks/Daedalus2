#!/usr/bin/env python3
"""Teeth for the coverage ratchet.

Two directions, one per limit. The floor is the familiar half — it must still fail when coverage
regresses. The ceiling is the new half and the one worth proving, because a ratchet that never
demands a bump is indistinguishable from the twelve-point-slack floor this replaced.

Only the server module is mutated; the rule lives in the parent pom and applies identically to
all five, so proving it on one is proving the mechanism.
"""
import pathlib, re, subprocess

REPO = pathlib.Path(__file__).resolve().parent.parent
POM = REPO / "daedalus-server/pom.xml"
orig = POM.read_text()

CASES = [
    # Chase the measured ratio: this case only simulates a regression while the floor it sets is
    # genuinely above actual coverage. It was 0.95 when coverage was 94.63%, which as of the
    # 08-02 contract suites (95.10%) would have passed and reported a false survivor — the
    # value-based twin of the anchor drift mutants/README.md warns about.
    ("floor set above actual (simulates a regression)", 0.97, 0.99, "minimum"),
    ("floor left stale 12 points low (the audited bug)", 0.79, 0.82, "maximum"),
]

results = []
try:
    for name, floor, ceiling, expect in CASES:
        t = re.sub(r"<jacoco\.check\.minimum>[0-9.]+</jacoco\.check\.minimum>",
                   f"<jacoco.check.minimum>{floor}</jacoco.check.minimum>", orig, count=1)
        t = re.sub(r"<jacoco\.check\.ceiling>[0-9.]+</jacoco\.check\.ceiling>",
                   f"<jacoco.check.ceiling>{ceiling}</jacoco.check.ceiling>", t, count=1)
        POM.write_text(t)
        try:
            p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "-am",
                                "verify", "-Dcheckstyle.skip", "-Dspotbugs.skip"],
                               cwd=REPO, capture_output=True, text=True, timeout=1500)
            out = p.stdout
            violated = [l.strip() for l in out.splitlines() if "Rule violated" in l]
            if p.returncode == 0:
                verdict = "SURVIVED — the build passed"
            else:
                hit = any(expect in v for v in violated)
                verdict = (f"caught via {expect}" if hit
                           else "failed, but NOT on the expected limit: " + str(violated[:2]))
        except subprocess.TimeoutExpired:
            verdict = "timed out"
        finally:
            POM.write_text(orig)
        results.append((name, verdict))
        print(f"{name:48s} -> {verdict}", flush=True)
        for v in violated[:2]:
            print(f"{'':48s}    {v[:150]}", flush=True)
finally:
    POM.write_text(orig)
    print("restored")

bad = [n for n, v in results if not v.startswith("caught")]
print(f"\n{len(results)-len(bad)}/{len(results)} caught; problems: {bad or 'none'}")
