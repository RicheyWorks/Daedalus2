#!/usr/bin/env python3
"""Teeth for the STOMP SEND refusal.

Mutation 1 is the whole reason the smoke test exists. It leaves `StompSendRejectionInterceptor`
perfectly correct and simply does not register it in `WebSocketConfig` -- which is exactly the
state the codebase was in until 2026-07-31, except that back then the class did not exist. A unit
test that constructs the interceptor and calls `preSend` cannot tell that state from a working
one. If mutation 1 survives, the unit tests are testing a class nobody uses.

Mutation 5 aims at the scanner's positive control. Narrowing the pattern to something that
matches nothing makes the "no @MessageMapping exists" sweep pass with more confidence and less
information, the same shape as the coverage ratchet that only enforced a floor.
"""
import pathlib, re, subprocess
import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
CFG = REPO / "daedalus-server/src/main/java/com/daedalus/server/config/WebSocketConfig.java"
ITC = REPO / "daedalus-server/src/main/java/com/daedalus/server/security/StompSendRejectionInterceptor.java"
TST = REPO / "daedalus-server/src/test/java/com/daedalus/server/security/StompSendRejectionTest.java"

MUT = [
    (CFG, "the interceptor is written but never registered",
     "                new StompSubscriptionAuthorizationInterceptor(sessions::find),",
     "                new StompSubscriptionAuthorizationInterceptor(sessions::find));\n"
     "        if (false) registration.interceptors("),
    (ITC, "the guard watches the wrong command",
     "!StompCommand.SEND.equals(accessor.getCommand())",
     "!StompCommand.BEGIN.equals(accessor.getCommand())"),
    (ITC, "refusal narrowed to session topics only (a partial rule)",
     "        throw new IllegalStateException(",
     "        if (accessor.getDestination() != null\n"
     "                && !accessor.getDestination().startsWith(\"/topic/session/\")) {\n"
     "            return message;\n"
     "        }\n"
     "        throw new IllegalStateException("),
    (ITC, "the frame is let through instead of refused",
     "        throw new IllegalStateException(\n"
     "                \"This STOMP surface is broadcast-only; clients may not SEND. \"\n"
     "                        + \"Destination was: \" + accessor.getDestination());",
     "        return message;"),
    (TST, "the mapping scanner narrowed to match nothing",
     '"^\\\\s*@(MessageMapping|SubscribeMapping|MessageExceptionHandler)\\\\b"',
     '"^\\\\s*@(NoSuchAnnotationAnywhere)\\\\b"'),
]


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "-am", "test",
                        "-Dtest=StompSendRejectionTest,WebSocketForgerySmokeTest,"
                        "WebSocketOwnershipSmokeTest",
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1800)
    failed = sorted({m for m in re.findall(
        r"(?:StompSendRejectionTest|WebSocketForgerySmokeTest|WebSocketOwnershipSmokeTest)"
        r"\.(\w+)", p.stdout) if m not in ("java", "class")})
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
