#!/usr/bin/env python3
"""Teeth check for GeneratorInvariantFuzzTest (ADR-007 idea 9).

The fuzz found zero violations on its first run. A property test that has never
seen a failure is indistinguishable from a property test that cannot fail, so
this harness breaks one real generator six different ways -- once per property
the fuzz claims to enforce -- and records whether the fuzz notices.

Safety machinery, learned the hard way. The first version reverted only in a
`finally` at the very end, held no lock, and was launched under a wrapper that
got killed mid-run. The orphaned process kept mutating the same file while a
second copy ran, and the "6/6 caught" it printed was the product of two
interleaved runs -- unusable. So:

  * a lock file refuses a second concurrent run;
  * a pristine sidecar copy is written before the first mutation and restored on
    startup, so a killed run is repaired by the next one rather than leaving a
    sabotaged generator in the tree;
  * the source is restored after every mutation, not once at the end;
  * SIGTERM and SIGINT restore before exiting.

Usage:  python3 mutants/fuzzteeth.py
"""

import os
import pathlib
import re
import signal
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TARGET = REPO / "daedalus-core/src/main/java/com/daedalus/engine/generators/BinaryTreeGenerator.java"
PRISTINE = pathlib.Path("/tmp/fuzzteeth-pristine.java")
LOCK = pathlib.Path("/tmp/fuzzteeth.lock")
TEST = "GeneratorInvariantFuzzTest"

CARVE = "                grid.carve(grid.cell(p), choice);"
RNG = "        Random rng = new Random(seed);"
FINISH = "        stats.finish(true);"

ISLAND = """        if (rows > 5 && cols > 5) {
            for (Point q : new Point[] {new Point(2, 2), new Point(2, 3)}) {
                for (Direction d : Direction.values()) {
                    grid.cell(q).close(d);
                    Point n = q.step(d);
                    if (grid.inBounds(n)) grid.cell(n).close(d.opposite());
                }
            }
            grid.carve(grid.cell(new Point(2, 2)), Direction.EAST);
        }
"""

# (label, substring the fuzz should print, anchor, replacement)
MUTATIONS = [
    ("one-sided opening", "asymmetric wall",
     CARVE, "                grid.cell(p).open(choice);"),
    ("opening off the grid edge", "opening leaves the grid",
     CARVE, CARVE + "\n                if (c == 0) grid.cell(p).open(Direction.WEST);"),
    ("seed mixed with the clock", "not deterministic",
     RNG, "        Random rng = new Random(seed + System.nanoTime());"),
    ("seed ignored entirely", "identical maze for two different seeds",
     RNG, "        Random rng = new Random(42L);"),
    ("carve both directions (cycles)", "fills the grid but is not a tree",
     CARVE, CARVE + "\n                if (canN && canE) {"
            "\n                    grid.carve(grid.cell(p), Direction.NORTH);"
            "\n                    grid.carve(grid.cell(p), Direction.EAST);"
            "\n                }"),
    ("walled-off two-cell island", "stranded habitable cells",
     FINISH, ISLAND + FINISH),
]


def acquire_lock():
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        holder = LOCK.read_text().strip()
        if holder.isdigit() and pathlib.Path("/proc", holder).exists():
            sys.exit(f"another fuzzteeth run is live (pid {holder}); refusing to mutate")
        print(f"stale lock from pid {holder}; taking it over")
        LOCK.unlink()
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)


def restore():
    if PRISTINE.exists():
        TARGET.write_text(PRISTINE.read_text())


def short(fqn):
    """`com.daedalus.server.FooTest.barBaz` -> `FooTest.barBaz`."""
    parts = fqn.split(".")
    return ".".join(parts[-2:]) if len(parts) > 1 else fqn


def run_test():
    proc = subprocess.run(
        ["mvn", "-B", "-ntp", "-pl", "daedalus-core,daedalus-server", "-am",
         "test", "-Dtest=" + TEST, "-Dsurefire.failIfNoSpecifiedTests=false",
         "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
        cwd=REPO, capture_output=True, text=True, timeout=1800)
    return proc.returncode == 0, proc.stdout + proc.stderr


def main():
    acquire_lock()
    if PRISTINE.exists():
        print("a previous run left a sidecar; restoring the generator before starting")
        restore()
    PRISTINE.write_text(TARGET.read_text())
    original = PRISTINE.read_text()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: (restore(), LOCK.unlink(missing_ok=True),
                                       sys.exit("interrupted; generator restored")))

    results = []
    try:
        for name, expect, old, new in MUTATIONS:
            if original.count(old) != 1:
                results.append((name, expect, "SKIPPED (anchor not unique)", []))
                print(f"{name:34s} -> SKIPPED, anchor matched {original.count(old)} times")
                continue
            TARGET.write_text(original.replace(old, new))
            try:
                passed, output = run_test()
            finally:
                restore()
            if passed:
                verdict = "SURVIVED  <-- the fuzz did not notice"
            else:
                verdict = ("caught, right reason" if expect.lower() in output.lower()
                           else "caught, but NOT via '" + expect + "'")
            # `[ERROR] Tests run: 3, Failures: 1 ... <<< FAILURE` is surefire's summary line,
            # not a test name; the dot check drops it and keeps the fully-qualified methods.
            failures = sorted({short(m) for m in
                               re.findall(r"\[ERROR\]\s+(\S+)[^\n]*?<<< (?:FAILURE|ERROR)", output)
                               if "." in m})
            results.append((name, expect, verdict, failures))
            print(f"{name:34s} -> {verdict}")
    finally:
        restore()
        PRISTINE.unlink(missing_ok=True)
        LOCK.unlink(missing_ok=True)
        print("\nrestored", TARGET.name)

    print("\n=== summary ===")
    for name, expect, verdict, failures in results:
        print(f"{name:34s} | expects: {expect:38s} | {verdict}")
        for f in failures:
            print(f"{'':34s} |   failing test: {f}")
    bad = [r for r in results if not r[2].startswith("caught")]
    print(f"\n{len(results) - len(bad)}/{len(results)} mutations caught")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
