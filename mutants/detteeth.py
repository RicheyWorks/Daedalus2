#!/usr/bin/env python3
"""Teeth for DeterminismGoldenTest.

A golden-file test is unusually easy to make worthless, because everything it checks passes
through one canonicalisation function. Blind that function and every digest still compares
equal to every other digest — the test goes green and checks nothing. So three of these five
mutations attack the canonicaliser rather than the product, and two attack the product.

The recorded file is the oracle, and it was written by a different JVM. That is the whole point:
these mutations are checked against a comparison that genuinely crosses a process boundary.
"""
import pathlib, re, subprocess
import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
TST = REPO / "daedalus-server/src/test/java/com/daedalus/server/DeterminismGoldenTest.java"
GEN = REPO / "daedalus-core/src/main/java/com/daedalus/engine/generators/RecursiveBacktrackerGenerator.java"
GOLD = REPO / "daedalus-server/src/test/resources/determinism-golden.json"

MUT = [
    # --- the product ---
    (GEN, "a generator's seeding changed by one",
     "return GrowingTreeEngine.run(rows, cols, seed, stats, GrowingTreePolicies.newest());",
     "return GrowingTreeEngine.run(rows, cols, seed + 1, stats, GrowingTreePolicies.newest());"),
    (GOLD, "one recorded digest edited",
     '"GET /maze/{id}hardest-route"',
     '"GET /maze/{id}hardest-route-renamed"'),
    # --- the canonicaliser ---
    (TST, "the canonicaliser redacts everything",
     "        if (node.isObject()) {",
     "        if (true) {\n"
     "            return JSON.createObjectNode();\n"
     "        }\n"
     "        if (node.isObject()) {"),
    (TST, "UUID redaction removed (ids leak back into digests)",
     '            return JSON.getNodeFactory().textNode(\n'
     '                    UUID_ANYWHERE.matcher(node.asText()).replaceAll("<uuid>"));',
     "            return node;"),
    (TST, "an exclusion added for something substantive",
     'Set.of("elapsedMs");',
     'Set.of("elapsedMs", "path", "visited", "explored");'),
]


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "-am", "test",
                        "-Dtest=DeterminismGoldenTest",
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1800)
    failed = sorted({m for m in re.findall(r"DeterminismGoldenTest\.(\w+)", p.stdout)
                     if m not in ("java", "class")})
    return V.classify(p.returncode, p.stdout, failed)


V.restore_on_signal()
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
        if not V.is_catch(verdict):
            survivors.append(name)
        print(f"{name:52s} -> {verdict}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
