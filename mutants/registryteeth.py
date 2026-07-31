#!/usr/bin/env python3
"""Teeth for the algorithm-id collision guard.

The guard is four lines, and three of the four ways to get it wrong leave a test suite green:

  * throw, but only after the map has already been overwritten -- the exception is reported and
    the built-in is gone anyway;
  * guard one registry and not the other, which is easy because they are separate classes with
    separate maps and one test file;
  * guard the plugin path but leave the constructor unguarded, so duplicate built-ins still
    vanish silently at startup.

Mutation 1 is the important one: it keeps the throw and puts the corruption *before* it. A test
that only asserts "an exception was raised" passes.
"""
import pathlib, re, subprocess

REPO = pathlib.Path("/root/daedalus-work/repo")
GEN = REPO / "daedalus-core/src/main/java/com/daedalus/engine/generators/GeneratorRegistry.java"
SOL = REPO / "daedalus-core/src/main/java/com/daedalus/solver/solvers/SolverRegistry.java"
EXC = REPO / "daedalus-core/src/main/java/com/daedalus/engine/DuplicateAlgorithmException.java"

MUT = [
    (GEN, "throws, but overwrites the incumbent first",
     "        MazeGenerator incumbent = generators.putIfAbsent(gen.id(), gen);",
     "        MazeGenerator incumbent = generators.put(gen.id(), gen);"),
    (GEN, "the guard is removed entirely (silent shadowing returns)",
     "        if (incumbent != null) {",
     "        if (false) {"),
    (SOL, "solvers left unguarded while generators are protected",
     "        if (incumbent != null) {",
     "        if (false) {"),
    (GEN, "the constructor bypasses the guard",
     "        builtIn.forEach(this::register);",
     "        builtIn.forEach(g -> generators.put(g.id(), g));"),
    (EXC, "the message stops naming who holds the id",
     '        super("A " + kind + " with id \'" + id + "\' is already registered ("\n'
     '                + incumbent.getName() + "); " + rejected.getName() + " was refused. "',
     '        super("Duplicate id. "'),
]


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-core", "test",
                        "-Dtest=RegistryCollisionTest",
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=900)
    failed = sorted({m for m in re.findall(r"RegistryCollisionTest\.(\w+)", p.stdout)
                     if m not in ("java", "class", "lambda")})
    if p.returncode == 0:
        return "SURVIVED"
    if not failed and "COMPILATION ERROR" in p.stdout:
        return "BROKEN BUILD (not a catch)"
    return "caught by " + ", ".join(f[:40] for f in failed[:2])


originals = {p: p.read_text() for p in {m[0] for m in MUT}}
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:52s} -> SKIP (anchor x{orig.count(old)})", flush=True)
            survivors.append(name + " [anchor lost]")
            continue
        path.write_text(orig.replace(old, new))
        try:
            verdict = run_once()
        except subprocess.TimeoutExpired:
            verdict = "timed out"
        finally:
            path.write_text(orig)
        if verdict.startswith(("SURVIVED", "BROKEN")):
            survivors.append(name)
        print(f"{name:52s} -> {verdict}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
