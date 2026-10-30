#!/usr/bin/env python3
"""Teeth for AgentWalkService — the fog, the budget, and the live grid.

This class is a *benchmark surface*: "anything that speaks HTTP can compete: a shell script, an
RL policy, a student's first wall-follower". That framing is what makes it worth attacking, and
it is a different kind of target from the tickers. Almost everything here is a promise about what
the caller is **not** told, and a test written from the caller's side asks whether the walk works
— never whether it revealed too much. An agent that can see the whole maze still finds the goal,
faster and with a cleaner test log.

Four promises, all made in prose:

  * **The fog.** `view` lists the directions open *from the current cell* and nothing else. Leak
    the neighbouring cells' openings, or drop the in-bounds filter, and every blind solver
    silently becomes a sighted one — the benchmark still runs, the numbers are meaningless.
  * **The live grid.** Visibility is recomputed from the cache's current grid "on every step and
    view — never from a snapshot taken at open time", because a living maze erodes mid-walk. The
    difference is invisible on any maze that does not change, which is every maze in a unit test
    unless someone deliberately mutates one.
  * **The budget.** Default `4·rows·cols`, clamped to `[1, max-steps]`, and — the subtle half —
    an illegal move is rejected *without consuming budget*, because the view already told the
    caller which directions were open, so a wall-bump is a caller bug rather than exploration.
    A mutation that charges for it makes every honest agent slightly worse at the benchmark.
  * **The occupancy event.** `AgentSteppedEvent` is what makes an agent's footsteps raise traffic
    costs exactly like a player's. Drop it and the composition ADR-006 predicted quietly stops.

And the house-rule bounds: the agent store's size and idle TTL, the second of which was unpinned
on `GameSessionService` and on `MazeGenerationService` before this folder went looking.

Usage:  python3 mutants/agentteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
AW = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/AgentWalkService.java"

MUT = [
    (AW, "the fog leaks: every direction is reported open",
     "            if (grid.cell(walk.position()).isOpen(d) && grid.inBounds(walk.position().step(d))) {",
     "            if (true) {"),
    (AW, "the fog leaks past the grid edge (out-of-bounds openings reported)",
     "            if (grid.cell(walk.position()).isOpen(d) && grid.inBounds(walk.position().step(d))) {",
     "            if (grid.cell(walk.position()).isOpen(d)) {"),
    (AW, "walls are walkable (illegal steps accepted)",
     "            if (!grid.inBounds(to) || !grid.cell(walk.position()).isOpen(direction)) {",
     "            if (false) {"),
    # The first version of this mutation rewrote the guard's condition into an equivalent one
    # (`stepsUsed >= 0 && ...` is always true) and duly "survived", proving nothing. A wall bump
    # cannot be made to cost budget by editing the condition: the throw aborts the store's
    # compute, so nothing is written either way. Charging for it means *not* throwing and
    # returning a walk that stayed put with the step spent — which is also the more realistic
    # defect, because it is silent.
    (AW, "a wall bump silently costs a step instead of being refused",
     "            if (!grid.inBounds(to) || !grid.cell(walk.position()).isOpen(direction)) {\n"
     "                throw new IllegalArgumentException(\"no opening to the \" + direction + \" from (\"\n"
     "                        + walk.position().row() + \",\" + walk.position().col() + \")\");\n"
     "            }",
     "            if (!grid.inBounds(to) || !grid.cell(walk.position()).isOpen(direction)) {\n"
     "                return new Walk(walk.id(), walk.mazeId(), walk.position(),\n"
     "                        walk.stepsUsed() + 1, walk.budget(), walk.arrived());\n"
     "            }"),
    (AW, "the budget is never exhausted (walks run forever)",
     "            if (walk.stepsUsed() >= walk.budget()) {",
     "            if (false) {"),
    (AW, "the requested budget ignores the configured cap",
     "                : Math.max(1, Math.min(requestedBudget, maxSteps));",
     "                : Math.max(1, requestedBudget);"),
    (AW, "the default budget loses its max-steps clamp",
     "        int budget = requestedBudget == null ? Math.min(defaultBudget, maxSteps)",
     "        int budget = requestedBudget == null ? defaultBudget"),
    (AW, "an arrived agent may keep stepping",
     "            if (walk.arrived()) {",
     "            if (false) {"),
    (AW, "arrival is never noticed",
     "            return new Walk(walk.id(), walk.mazeId(), to, walk.stepsUsed() + 1,\n"
     "                    walk.budget(), to.equals(grid.goal()));",
     "            return new Walk(walk.id(), walk.mazeId(), to, walk.stepsUsed() + 1,\n"
     "                    walk.budget(), false);"),
    (AW, "expiry is never reported to the caller",
     "                !walk.arrived() && walk.stepsUsed() >= walk.budget());",
     "                false);"),
    (AW, "a footstep no longer raises traffic (the event is dropped)",
     "        events.publishEvent(new AgentSteppedEvent(this, after.mazeId(), after.id(),\n"
     "                after.position().step(direction.opposite()), after.position()));\n",
     ""),
    (AW, "the agent store loses its size bound",
     "                .maximumSize(maxAgents)\n", ""),
    (AW, "the agent store loses its idle expiry",
     "                .expireAfterAccess(idleTtl)\n", ""),
    (AW, "a walk on an evicted maze is served from thin air",
     "            var cached = gen.find(walk.mazeId());\n"
     "            if (cached == null) {\n"
     "                return null; // maze evicted — the walk dies with it\n"
     "            }",
     "            var cached = gen.find(walk.mazeId());\n"
     "            if (cached == null) {\n"
     "                return walk;\n"
     "            }"),
]

CLASSES = ("AgentWalkServiceTest", "AgentWalkContractTest", "AgentApiEndpointTest",
           "BoundedStoresTest", "TrafficServiceTest")
TESTS = ",".join(CLASSES)


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "test",
                        "-Dtest=" + TESTS,
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1800)
    return V.classify(p.returncode, p.stdout, V.failing_tests(p.stdout, *CLASSES))


V.restore_on_signal()
originals = {p: p.read_text() for p in {m[0] for m in MUT}}
V.snapshot(originals)
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:60s} -> SKIP (anchor x{orig.count(old)})", flush=True)
            survivors.append(name + " [anchor lost]")
            continue
        path.write_text(orig.replace(old, new))
        try:
            v = run_once()
        except subprocess.TimeoutExpired:
            v = "caught: timed out"
        finally:
            path.write_text(orig)
        if not V.is_catch(v):
            survivors.append(name)
        print(f"{name:60s} -> {v}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
