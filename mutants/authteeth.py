#!/usr/bin/env python3
"""Teeth for ProdAuthPostureTest.

The posture test passes today because prod's chain is default-deny. That is exactly the state in
which a test like this can be worthless — everything is closed, so an assertion that things are
closed cannot tell a working guard from a decorative one. These mutations open holes of the kind
a real change would open, plus one that adds an endpoint nobody classified.

Round two aims at what round one missed. The first version of the test filled its expectation
table in from what the running server answered, so it agreed with a live bug — four endpoints the
README documents as public were being refused in prod — and its source scanner silently skipped
two annotation forms. Mutations 4-8 target the assertions added to close those two gaps.
"""
import pathlib, re, subprocess
import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
SEC = REPO / "daedalus-server/src/main/java/com/daedalus/server/config/ProdSecurityConfig.java"
CTL = REPO / "daedalus-server/src/main/java/com/daedalus/server/controller/InsightController.java"
CMP = REPO / "daedalus-server/src/main/java/com/daedalus/server/controller/CampaignController.java"
DOC = REPO / "README.md"
TST = REPO / "daedalus-server/src/test/java/com/daedalus/server/config/ProdAuthPostureTest.java"

MUT = [
    (SEC, "maze/* widened to maze/** (the realistic slip)",
     '.requestMatchers(HttpMethod.GET, "/api/v1/maze/*").permitAll()',
     '.requestMatchers(HttpMethod.GET, "/api/v1/maze/**").permitAll()'),
    (SEC, "default-deny flipped to default-allow",
     ".anyRequest().authenticated()",
     ".anyRequest().permitAll()"),
    (CTL, "a new endpoint nobody classified",
     '    @GetMapping("/maze/{id}/ghost")',
     '    @GetMapping("/maze/{id}/unclassified-new-thing")\n'
     '    public ResponseEntity<String> unclassifiedNewThing(@PathVariable UUID id) {\n'
     '        return ResponseEntity.ok("hi");\n'
     '    }\n\n'
     '    @GetMapping("/maze/{id}/ghost")'),

    # --- round two ---
    (SEC, "the spectator permalink closed again (the original bug)",
     '.requestMatchers(HttpMethod.GET, "/api/v1/session/*").permitAll()',
     '.requestMatchers(HttpMethod.GET, "/api/v1/session/*").authenticated()'),
    (DOC, "README quietly reclassifies the ghost racer",
     '| `GET` | `/api/v1/maze/{id}/ghost` | public |',
     '| `GET` | `/api/v1/maze/{id}/ghost` | required |'),
    (DOC, "README drops a row (the two-missing-rows defect)",
     '| `GET` | `/api/v1/tournament?generator=&size=&mazes=&braid=` | required |',
     '| `GET` | `/api/v1/tournament-DROPPED` | required |'),
    # Both of these go on CampaignController rather than PluginController. Putting a bare
    # @GetMapping on PluginController collides with the bare one already there, so Spring
    # refuses to start and the run goes red for the wrong reason — a crash is not a catch.
    (CMP, "an endpoint declared with a bare @GetMapping",
     '    @GetMapping("/campaign")',
     '    @GetMapping\n'
     '    public ResponseEntity<String> bareNewThing() {\n'
     '        return ResponseEntity.ok("hi");\n'
     '    }\n\n'
     '    @GetMapping("/campaign")'),
    (CMP, "an endpoint declared with @GetMapping(value = ...)",
     '    @GetMapping("/campaign")',
     '    @GetMapping(value = "/campaign-extra")\n'
     '    public ResponseEntity<String> valueFormNewThing() {\n'
     '        return ResponseEntity.ok("hi");\n'
     '    }\n\n'
     '    @GetMapping("/campaign")'),
    (TST, "the source scanner narrowed back to parenthesised-literal only",
     '"@(Get|Post|Put|Patch|Delete)Mapping\\\\b\\\\s*(\\\\(([^)]*)\\\\))?"',
     '"@(Get|Post|Put|Patch|Delete)Mapping\\\\s*(\\\\(\\\\s*\\"?([^\\")]*)\\"?\\\\s*\\\\))"'),
]

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
            p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "test",
                                "-Dtest=ProdAuthPostureTest",
                                "-Dsurefire.failIfNoSpecifiedTests=false",
                                "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                               cwd=REPO, capture_output=True, text=True, timeout=900)
            failed = sorted({m for m in re.findall(r"ProdAuthPostureTest\.(\w+)", p.stdout)
                             if m not in ("java", "class")})
            verdict = V.classify(p.returncode, p.stdout, failed)
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
