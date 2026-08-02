#!/usr/bin/env python3
"""Teeth for the plugin-unload fix.

Two things need pinning and they pull in opposite directions. The unload has to actually remove
what a plugin contributed -- and it has to remove *nothing else*, because a removal path reachable
from teardown is a removal path that could take a built-in with it. A fix for a leak that deletes
`recursive-backtracker` on shutdown would be strictly worse than the leak.

Mutation 4 is the one that pulls the other way: it drops the built-in refusal from
`GeneratorRegistry.unregister`. Nothing about the leak-fixing behaviour changes, so every
"the plugin's generators are gone" assertion still passes.
"""
import pathlib, re, subprocess
import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
MGR = REPO / "daedalus-plugin-runtime/src/main/java/com/daedalus/plugin/runtime/PluginManager.java"
GEN = REPO / "daedalus-core/src/main/java/com/daedalus/engine/generators/GeneratorRegistry.java"
SOL = REPO / "daedalus-core/src/main/java/com/daedalus/solver/solvers/SolverRegistry.java"

MUT = [
    (MGR, "shutdown stops unregistering anything (the leak returns)",
     "            for (PluginRegistry.Entry e : registry.all()) {\n"
     "                unregisterContributions(e.manifest().id(), bootedGenerators, bootedSolvers);\n"
     "            }",
     "            // mutation: contributions left in the registry"),
    (MGR, "only STARTED plugins are unloaded (failures leak)",
     "            for (PluginRegistry.Entry e : registry.all()) {\n"
     "                unregisterContributions(e.manifest().id(), bootedGenerators, bootedSolvers);\n"
     "            }",
     "            for (PluginRegistry.Entry e : registry.all()) {\n"
     "                if (e.state() != PluginLifecycle.STOPPED) { continue; }\n"
     "                unregisterContributions(e.manifest().id(), bootedGenerators, bootedSolvers);\n"
     "            }"),
    # First attempt at this mutation re-read the snapshot at the same point, which is a no-op,
    # and it duly "survived" while proving nothing. A mutation has to move the bracket: take the
    # snapshot AFTER registerAlgorithms so anything a plugin registers from start() falls outside
    # the diff and is never attributed to it.
    (MGR, "the diff brackets only registerAlgorithms, not start()",
     "                registry.advance(e.manifest().id(), PluginLifecycle.REGISTERED);",
     "                registry.advance(e.manifest().id(), PluginLifecycle.REGISTERED);\n"
     "                generatorsBefore = generators.ids();"),
    (GEN, "the built-in refusal is dropped from unregister",
     "        if (builtInIds.contains(id)) {",
     "        if (false) {"),
    (SOL, "solver contributions are never removed",
     "        return solvers.remove(id) != null;",
     "        return false;"),
]


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-plugin-runtime", "-am", "test",
                        "-Dtest=PluginUnloadTest,RegistryCollisionTest",
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1200)
    failed = sorted({m for m in re.findall(
        r"(?:PluginUnloadTest|RegistryCollisionTest)\.(\w+)", p.stdout)
        if m not in ("java", "class", "lambda")})
    return V.classify(p.returncode, p.stdout, failed)


V.restore_on_signal()
originals = {p: p.read_text() for p in {m[0] for m in MUT}}
V.snapshot(originals)
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
        if not V.is_catch(verdict):
            survivors.append(name)
        print(f"{name:56s} -> {verdict}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
