#!/usr/bin/env python3
"""Teeth for ErrorContractTest.

An error-shape test is easy to write and easy to write badly: assert a 400 comes back, and the
assertion passes whether the body is a problem detail or Boot's default. These mutations put
each of the five gaps the audit found back, one at a time.

Mutation 4 is the one that matters most. It removes the 405 handler *and* the roster entry that
covers it, so the only thing left that can notice is `noGeneratedRequestEscapesTheContract` --
the test whose cases are derived from the controller sources rather than listed by hand. If that
mutation survives, the generated test is decorative and the roster is doing all the work.
"""
import pathlib, re, subprocess
import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
HND = REPO / "daedalus-server/src/main/java/com/daedalus/server/web/ApiExceptionHandler.java"
REG = REPO / "daedalus-core/src/main/java/com/daedalus/engine/generators/GeneratorRegistry.java"
TST = REPO / "daedalus-server/src/test/java/com/daedalus/server/web/ErrorContractTest.java"

MUT = [
    (HND, "the unknown-algorithm handler removed (500 returns)",
     "    @ExceptionHandler(UnknownAlgorithmException.class)",
     "    // @ExceptionHandler(UnknownAlgorithmException.class)   // mutation: handler unregistered"),
    (REG, "the registry throws a bare NoSuchElementException again",
     'new com.daedalus.engine.UnknownAlgorithmException(\n'
     '                "generator", id, generators.keySet().stream().sorted().toList())',
     'new NoSuchElementException("No generator registered with id: " + id)'),
    (HND, "the missing-parameter handler removed (Boot default returns)",
     "    @ExceptionHandler(MissingServletRequestParameterException.class)",
     "    // @ExceptionHandler(MissingServletRequestParameterException.class)   // mutation: handler unregistered"),
    (HND, "the unmapped-path handler removed",
     "    @ExceptionHandler(NoResourceFoundException.class)",
     "    // @ExceptionHandler(NoResourceFoundException.class)   // mutation: handler unregistered"),
    (HND, "the 415 handler removed",
     "    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)",
     "    // @ExceptionHandler(HttpMediaTypeNotSupportedException.class)   // mutation: handler unregistered"),
    (HND, "the 404 body lists only the first three valid ids",
     'pd.setProperty("known", ex.known());',
     'pd.setProperty("known", ex.known().stream().limit(3).toList());'),
    (HND, "the detail string carries the exception through",
     '"No " + ex.kind() + " is registered with id \'" + ex.id() + "\'"',
     'ex.toString()'),
    (TST, "the source scanner narrowed so most mappings are missed",
     '"@(Get|Post|Put|Patch|Delete)Mapping\\\\b\\\\s*(\\\\(([^)]*)\\\\))?"',
     '"@(Delete)Mapping\\\\b\\\\s*(\\\\(([^)]*)\\\\))?"'),
]

# Mutation 4 in the docstring: handler + roster entry, so only the generated test can catch it.
ROSTER_405 = ('                new Case("wrong http verb", HttpMethod.GET, '
              '"/api/v1/maze/" + mazeId + "/live",\n                        null, null),\n')
PAIRED = [
    (HND, "the 405 handler removed", "    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)",
     "    // @ExceptionHandler(HttpRequestMethodNotSupportedException.class)   // mutation: handler unregistered"),
    (TST, "", ROSTER_405, ""),
]


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "-am", "test",
                        "-Dtest=ErrorContractTest", "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1200)
    failed = sorted({m for m in re.findall(r"ErrorContractTest\.(\w+)", p.stdout)
                     if m not in ("java", "class")})
    return V.classify(p.returncode, p.stdout, failed)


ALL_FILES = {m[0] for m in MUT} | {m[0] for m in PAIRED}
V.restore_on_signal()
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
        if not V.is_catch(verdict):
            survivors.append(name)
        print(f"{name:56s} -> {verdict}", flush=True)

    # The paired mutation: remove the handler AND the roster case that names it.
    label = "405 handler + its roster entry removed together"
    ok = all(originals[p].count(old) == 1 for p, _, old, _ in PAIRED)
    if not ok:
        print(f"{label:56s} -> SKIP (anchor lost)", flush=True)
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
        if not V.is_catch(verdict):
            survivors.append(label)
        print(f"{label:56s} -> {verdict}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    print("restored")

total = len(MUT) + 1
print(f"\n{total - len(survivors)}/{total} caught; survivors: {survivors or 'none'}")
