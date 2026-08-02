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

import re

#: Surefire prints one of these on the line naming a failing test class or method.
_SUREFIRE_FAILURE = re.compile(r"<<< (FAILURE|ERROR)")


def failing_tests(stdout, *class_names):
    """Method names of the given test classes that Surefire reported as failing."""
    pattern = r"(?:" + "|".join(re.escape(c) for c in class_names) + r")\.(\w+)"
    return sorted({m for m in re.findall(pattern, stdout)
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
