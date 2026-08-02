"""One place to decide whether a mutation was actually caught.

Every harness in this folder used to answer that question with "Maven exited non-zero", which
is not the same question. A mutation is caught when a *test* fails because of it. A build that
dies before any test runs — unresolvable parent POM, empty local repository, a fork killed for
memory, a timeout — also exits non-zero, and reads identically.

That is not hypothetical. `retentionteeth.py`'s first run printed a confident **4/4 caught**
while all four builds were failing in POM resolution, having executed no tests at all. The
older guard here (`if not failed and "COMPILATION ERROR" in stdout`) does not cover it: none of
those failures print that phrase.

So the rule this module enforces is: **no named failing test, no catch.** A harness that cannot
say which test caught the mutation has not observed a catch, it has observed the colour red.
Reporting that as a survivor-free run is worse than reporting nothing, because the whole point
of the exercise is to find out which guarantees are unpinned — and a false catch is a guarantee
you now believe is pinned when it is not.
"""

import hashlib
import pathlib
import re
import signal

#: Surefire prints one of these on the line naming a failing test class or method.
_SUREFIRE_FAILURE = re.compile(r"<<< (FAILURE|ERROR)")


def failing_tests(stdout, *class_names):
    """Method names of the given test classes that Surefire reported as failing.

    Only lines Maven itself prefixed `[ERROR]` are considered. That restriction is the whole
    correctness of this function, and it was learned the hard way: a `Class.method` match
    anywhere in stdout used to count, and **a passing test that logs a stack trace names its
    own method in that trace**. `TrafficTickContractTest` deliberately makes a tick throw, the
    service logs the exception as designed, and the frame
    `at ...TrafficTickContractTest.aTickThatThrows...` appeared in every single run — so every
    mutation was reported as "caught by aTickThatThrows...", including mutations that test never
    exercises. It happened to be harmless there (each of those mutations was genuinely caught by
    some other test), but it is the same failure this module exists to prevent, one level down:
    a catch attributed to a test that did not catch it, and — for any build that dies after the
    logging but before a real failure — a catch attributed to no failure at all.

    Output from the forked test JVM (logback lines, their stack traces) arrives unprefixed;
    Surefire's own failure lines and its end-of-run summary both come through Maven with the
    `[ERROR]` prefix. Filtering on it separates the two exactly.
    """
    pattern = r"(?:" + "|".join(re.escape(c) for c in class_names) + r")\.(\w+)"
    lines = [ln for ln in stdout.splitlines() if ln.startswith("[ERROR]")]
    return sorted({m for m in re.findall(pattern, "\n".join(lines))
                   if m not in ("java", "class", "lambda")})


def _diagnostic(out):
    for line in out.splitlines():
        if "ERROR" in line and "Help" not in line and line.strip() != "[ERROR]":
            return line.strip()[:90]
    return "no diagnostic line found"


def classify(returncode, out, failed=None):
    """Verdict string for one mutation run.

    `failed` is the list of named failing tests; pass None to have it inferred from Surefire's
    own failure markers, which is all `run.py` and `wide.py` can see across a whole reactor.
    """
    if returncode == 0:
        return "SURVIVED"
    have_names = failed is not None
    if not have_names:
        failed = _SUREFIRE_FAILURE.findall(out)
    if not failed:
        return "NOT A CATCH -- build failed before any test: " + _diagnostic(out)
    if have_names:
        return "caught by " + ", ".join(f[:44] for f in failed[:2])
    return "caught (%d test failure%s)" % (len(failed), "" if len(failed) == 1 else "s")


def is_catch(verdict_text):
    """True only for verdicts that represent an observed test failure."""
    return verdict_text.startswith("caught")


def restore_on_signal():
    """Make a kill signal raise, so the harness's `finally` still restores the source tree.

    Every harness here edits production source in place and undoes it in a `finally`. That
    covers exceptions and it covers Ctrl-C, because SIGINT already raises KeyboardInterrupt.
    It does not cover SIGTERM, whose default action is to end the process outright — and
    SIGTERM is exactly what a wrapper `timeout` sends. A run killed that way leaves the last
    mutation **welded into the tree**, and the damage does not announce itself: the next run
    snapshots the mutated file as its own baseline, so it restores *to the mutation*, reports
    that mutation as `SKIP (anchor x0)` (the anchor it looks for is the code it replaced), and
    reports every other mutation as caught — because the welded-in defect fails tests all by
    itself. A harness whose failure mode is a green-looking sweep on a broken tree is worse
    than no harness. Observed here on 2026-08-02, in this folder, at a cost of one confusing
    hour: `trafficteeth.py` timed out under a 2-minute wrapper mid-mutation and the next run
    read 8/9 caught against a tree with quiet-tick retirement disabled.
    """
    def _raise(signum, _frame):
        raise KeyboardInterrupt("received signal %d — restoring sources" % signum)

    for sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, _raise)
        except (ValueError, AttributeError, OSError):
            pass  # not the main thread, or the platform lacks it — best effort

#: Sidecars for hard-killed runs. `restore_on_signal` covers SIGTERM; nothing covers SIGKILL, an
#: OOM, or a container that goes away, and each of those leaves a mutation welded into the tree.
_PRISTINE = pathlib.Path(__file__).resolve().parent / ".pristine"


def _sidecar(path):
    return _PRISTINE / (hashlib.sha1(str(path).encode()).hexdigest() + ".txt")


def snapshot(paths):
    """Heal anything a previous run left mutated, then record pristine copies of `paths`.

    Call once, before the first mutation, with the same paths the harness will edit. Two things
    happen. Any sidecar already on disk is from a run that died before its `finally` — its
    content is written back to the file it came from and the sidecar is removed, so the *next*
    run repairs what the last one broke even after a SIGKILL. Then fresh sidecars are written for
    this run. `release()` deletes them on a clean exit.

    This is `fuzzteeth.py`'s pristine-sidecar idea, moved somewhere every harness gets it. It was
    written twice on 2026-08-02 after the same failure twice: a killed run welds its mutation in,
    the next run snapshots the mutated file as its own baseline, and the sweep that follows is
    measured against a broken tree while reporting almost everything caught.
    """
    _PRISTINE.mkdir(exist_ok=True)
    healed = []
    for side in sorted(_PRISTINE.glob("*.txt")):
        target, _, content = side.read_text(encoding="utf-8").partition("\n")
        try:
            victim = pathlib.Path(target)
            if victim.exists() and victim.read_text(encoding="utf-8") != content:
                victim.write_text(content, encoding="utf-8")
                healed.append(victim.name)
        finally:
            side.unlink()
    if healed:
        print("healed from an interrupted run: " + ", ".join(healed), flush=True)
    for path in paths:
        _sidecar(path).write_text(str(path) + "\n" + pathlib.Path(path).read_text(encoding="utf-8"),
                                  encoding="utf-8")
    return healed


def release():
    """Drop this run's sidecars — call from the same `finally` that restores the sources."""
    for path in _PRISTINE.glob("*.txt"):
        path.unlink()
