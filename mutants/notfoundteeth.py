#!/usr/bin/env python3
"""Teeth for the 404 body work.

Two things need proving. First, that reverting any single call site to
`ResponseEntity.notFound().build()` is caught -- and specifically caught by the *generated* test
rather than the roster, because 27 sites cannot be kept in a roster and stay honest. Second,
that the distinctions the change introduced are actually asserted: several of those 27 were
answering different questions with the same empty body, and collapsing them back must go red.

Mutation 3 runs the other way. It makes the multiplayer-off 404 *more* informative, which reads
like an improvement and is a disclosure bug: the endpoint has to look absent, not disabled.
"""
import pathlib, re, subprocess

REPO = pathlib.Path("/root/daedalus-work/repo")
MZC = REPO / "daedalus-server/src/main/java/com/daedalus/server/controller/MazeController.java"
INS = REPO / "daedalus-server/src/main/java/com/daedalus/server/controller/InsightController.java"
RNF = REPO / "daedalus-server/src/main/java/com/daedalus/server/web/ResourceNotFoundException.java"
CLS = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/ComplexityLabService.java"
TST = REPO / "daedalus-server/src/test/java/com/daedalus/server/web/ErrorContractTest.java"

MUT = [
    (INS, "one site reverted to an empty 404 (hardest-route)",
     "        if (route == null) throw ResourceNotFoundException.maze(id);\n"
     "        return ResponseEntity.ok(route);",
     "        return route == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(route);"),
    (INS, "the ghost's two different 404s collapsed back into one",
     "            throw gen.find(id) == null ? ResourceNotFoundException.maze(id)",
     "            throw true ? ResourceNotFoundException.maze(id)"),
    (MZC, "multiplayer-off given an honest message (a disclosure bug)",
     "        if (!sessions.multiplayerEnabled()) throw ResourceNotFoundException.session(id);",
     '        if (!sessions.multiplayerEnabled()) throw new ResourceNotFoundException(\n'
     '                "session", String.valueOf(id),\n'
     '                "Multiplayer is disabled on this server; set '
     'daedalus.session.multiplayer=true.");'),
    (CLS, "the complexity lab swallows the unknown generator again",
     "        MazeGenerator generator = registry.require(generatorId);",
     "        MazeGenerator generator;\n"
     "        try {\n"
     "            generator = registry.require(generatorId);\n"
     "        } catch (RuntimeException unknown) {\n"
     "            return null;\n"
     "        }"),
    (RNF, "the maze 404 loses its detail sentence",
     '                "No maze " + id + " is available. Mazes are held in a bounded cache and are "\n'
     '                        + "evicted as newer ones arrive, so a maze that existed earlier may be "\n'
     '                        + "gone; generate it again with the same seed to get an identical one.");',
     "                null);"),
    (TST, "the empty-404 exemption reopened while unused",
     "    private static final boolean ALLOW_EMPTY_404 = false;",
     "    private static final boolean ALLOW_EMPTY_404 = true;"),
]

# The load-bearing pair: revert a call site AND drop the roster entry that names it, so only
# `noGeneratedRequestEscapesTheContract` can see it.
PAIRED = [
    (MZC, "", "        if (c == null) throw ResourceNotFoundException.maze(id);",
     "        if (c == null) return ResponseEntity.notFound().build();"),
    (TST, "", '                new Case("evicted maze", HttpMethod.GET, "/api/v1/maze/" '
              '+ UUID_SHAPED,\n                        null, null),\n', ""),
]


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "-am", "test",
                        "-Dtest=ErrorContractTest,ComplexityLabServiceTest",
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1200)
    failed = sorted({m for m in re.findall(r"(?:ErrorContractTest|ComplexityLabServiceTest)"
                                           r"\.(\w+)", p.stdout)
                     if m not in ("java", "class")})
    if p.returncode == 0:
        return "SURVIVED"
    if not failed and "COMPILATION ERROR" in p.stdout:
        return "BROKEN BUILD (not a catch)"
    return "caught by " + ", ".join(failed[:2])


ALL_FILES = {m[0] for m in MUT} | {m[0] for m in PAIRED}
originals = {p: p.read_text() for p in ALL_FILES}
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:56s} -> SKIP (anchor x{orig.count(old)})", flush=True)
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
        print(f"{name:56s} -> {verdict}", flush=True)

    label = "a call site reverted + its roster entry dropped"
    # MazeController has five identical `if (c == null) throw ...maze(id)` lines; mutating all
    # five at once is still exactly the regression under test.
    counts = [originals[p].count(old) for p, _, old, _ in PAIRED]
    if 0 in counts:
        print(f"{label:56s} -> SKIP (anchor lost {counts})", flush=True)
        survivors.append(label + " [anchor lost]")
    else:
        for p, _, old, new in PAIRED:
            p.write_text(originals[p].replace(old, new))
        try:
            verdict = run_once()
        except subprocess.TimeoutExpired:
            verdict = "timed out"
        finally:
            for p, text in originals.items():
                p.write_text(text)
        if verdict.startswith(("SURVIVED", "BROKEN")):
            survivors.append(label)
        print(f"{label:56s} -> {verdict}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    print("restored")

total = len(MUT) + 1
print(f"\n{total - len(survivors)}/{total} caught; survivors: {survivors or 'none'}")
