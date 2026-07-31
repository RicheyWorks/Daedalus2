#!/usr/bin/env python3
"""Teeth for DesktopWorkTest.

Four mutations. Two SURVIVED the first version of the tests, and both were tests weaker than
their own names:

1. *Job runs eagerly at construction.* `theGenerateJobDoesNothingUntilItIsCalled` asserted only
   that the returned Callable was non-null, so a mutation that generated the maze immediately
   and returned it from the lambda was invisible — the exact defect the class exists to prevent,
   since eager work just moves the UI freeze from the Task to the button click. The service
   publishes an event per generation, so the test now counts events before and after `call()`.

2. *Wrapped cause not unwrapped.* The test asserted `contains("ida-star")`, which cannot fail:
   an ExecutionException's own message is its cause's toString, so the wrapped string contains
   every substring the unwrapped one does. It now asserts equality with the expected message and
   the absence of the wrapper class name.

Usage:  python3 mutants/deskteeth.py
"""

import pathlib, re, subprocess
REPO = pathlib.Path("/root/daedalus-work/repo")
W = REPO / "daedalus-desktop/src/main/java/com/daedalus/desktop/ui/DesktopWork.java"
MUT = [
 ("job runs eagerly at construction",
  "        return () -> generation.generate(generatorId, rows, cols, seed);",
  "        var eager = generation.generate(generatorId, rows, cols, seed);\n        return () -> eager;"),
 ("budget refusal dressed as a crash",
  "        if (cause instanceof SolverBudgetExceededException budget) {\n            return budget.getMessage();\n        }",
  ""),
 ("wrapped cause not unwrapped",
  "        Throwable cause = failure instanceof java.util.concurrent.ExecutionException\n                ? failure.getCause() : failure;",
  "        Throwable cause = failure;"),
 ("blank message hides the type",
  "                        ? cause == null ? \"unknown error\" : cause.getClass().getSimpleName()",
  "                        ? \"\""),
]
orig = W.read_text()
survivors = []
try:
    for name, old, new in MUT:
        if orig.count(old) != 1:
            print(f"{name:36s} -> SKIP (anchor x{orig.count(old)})", flush=True); continue
        W.write_text(orig.replace(old, new))
        try:
            p = subprocess.run(["mvn","-B","-ntp","-pl","daedalus-desktop","test",
                "-Dtest=DesktopWorkTest","-Dsurefire.failIfNoSpecifiedTests=false",
                "-Dcheckstyle.skip","-Dspotbugs.skip","-Djacoco.skip"],
                cwd=REPO, capture_output=True, text=True, timeout=600)
            failed = sorted({m for m in re.findall(r"DesktopWorkTest\.(\w+)", p.stdout)})
            v = "SURVIVED" if p.returncode==0 else "caught by " + ", ".join(failed[:2])
        except subprocess.TimeoutExpired:
            v = "caught: timed out"
        finally:
            W.write_text(orig)
        if v == "SURVIVED": survivors.append(name)
        print(f"{name:36s} -> {v}", flush=True)
finally:
    W.write_text(orig); print("restored")
print(f"\n{len(MUT)-len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
