#!/usr/bin/env python3
"""Teeth for the prod surface that has no annotation to scan.

`ProdAuthPostureTest` is the strongest security test in this repo and it is blind to one thing by
construction. Its completeness half walks `controller/**.java` and extracts `@…Mapping`
annotations, so a file served off the classpath can never appear in its table — not because
anybody forgot a row, but because a static resource has no annotation to find. The gap is not in
the table. It is in what the table is *able* to contain.

**What was sitting in the gap.** The README publishes the web UI as "served at `/`". In prod it
answered **401**: `anyRequest().authenticated()` is fail-closed, and a static resource is a
request like any other. Measured on a prod-profile boot, not inferred.

That is worse than an outage, because it lands on a feature this project had already fixed once
at the layer below. `ProdSecurityConfig` opens `GET /api/v1/session/{id}`, its tour, the ghost run
and the agent re-poll, and argues the case at length — a spectator link only the operator can open
is not a spectator link, and until 2026-07-31 those endpoints "did not work in prod at all". But
the link the UI hands out is `https://host/#session={id}`: origin root plus a fragment. Every
endpoint on that carefully-reasoned list was reachable, and the page that calls them was not. The
feature still did not work. **The fix had been applied to the half that had a test.**

So the mutations here attack both directions. Reverting the allowlist puts prod back in the exact
state it shipped in — if that is not caught, the new test is decoration. And widening it to a glob
is the opposite failure, the one the enumeration exists to prevent: a static directory served by
`/**` publishes whatever later lands in it, which is the same slip as a `*` matcher becoming `**`
that `authteeth.py` already guards on the API side.

**First run: 4 of 5.** The survivor was the method scope — dropping `HttpMethod.GET` from the
matcher, so every verb on that path is permitted. It survived because the first version of the
new test's table was keyed on paths alone, with GET assumed on every row, and the table cannot
catch a distinction it does not express. The fix is not just adding write rows: `POST /` fails
either way, and the failure that matters is *which layer* refuses it. With the method scope, the
security layer answers 401. Without it, security says yes and the servlet layer answers 405. So
405 is deliberately excluded from the refused set — the property being pinned is "the security
layer is the thing that said no", not "the request did not succeed". **Now 5 of 5.**

Usage:  python3 mutants/staticteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
PROD = REPO / "daedalus-server/src/main/java/com/daedalus/server/config/ProdSecurityConfig.java"

ALLOW = '                        .requestMatchers(HttpMethod.GET, "/", "/index.html").permitAll()\n\n'

MUT = [
    # The bug exactly as it shipped: no row for the page at all.
    (PROD, "the web UI goes back to 401 in prod (the state it shipped in)",
     ALLOW, ""),
    # Half a fix is the more likely regression, because "/" is what a person types and
    # "/index.html" is what the welcome-page forward resolves to.
    (PROD, "only the forwarded name is public, not the one a browser asks for",
     '.requestMatchers(HttpMethod.GET, "/", "/index.html").permitAll()',
     '.requestMatchers(HttpMethod.GET, "/index.html").permitAll()'),
    (PROD, "only the typed name is public, not the one the forward resolves to",
     '.requestMatchers(HttpMethod.GET, "/", "/index.html").permitAll()',
     '.requestMatchers(HttpMethod.GET, "/").permitAll()'),
    # The opposite failure: the enumeration becomes a directory glob.
    (PROD, "the allowlist becomes a glob over everything",
     '.requestMatchers(HttpMethod.GET, "/", "/index.html").permitAll()',
     '.requestMatchers(HttpMethod.GET, "/**").permitAll()'),
    # The method is part of the decision — GET is a read, POST to a static path is not.
    (PROD, "the UI allowlist stops being method-scoped",
     '.requestMatchers(HttpMethod.GET, "/", "/index.html").permitAll()',
     '.requestMatchers("/", "/index.html").permitAll()'),
]

# Not mutated, deliberately: `theUiIsActuallyServedAndNotJustUnrefused` asserts the body prod
# hands back is the UI (has an <html> tag, carries the `#session=` share-link machinery, and is
# not a stub). Nothing in this repo's *source* can be edited to produce "prod answers 200 with
# something that is not the page" — that failure arrives from packaging, a resource-handler
# change or a misrouted welcome page, none of which is a line to flip. A mutation that cannot be
# written is worth saying out loud rather than faking with an inert edit; see the `unloadteeth.py`
# lesson on no-op mutations reading exactly like genuine gaps.

CLASSES = ("ProdStaticSurfacePostureTest", "ProdAuthPostureTest", "ProdProfileBootTest",
           "SecurityConfigProfileTest")
TESTS = ",".join(CLASSES)


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "test",
                        "-Dtest=" + TESTS,
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=2400)
    return V.classify(p.returncode, p.stdout, V.failing_tests(p.stdout, *CLASSES))


V.restore_on_signal()
originals = {p: p.read_text() for p in {m[0] for m in MUT}}
V.snapshot(originals)
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:64s} -> SKIP (anchor x{orig.count(old)})", flush=True)
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
        print(f"{name:64s} -> {v}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
