# ADR-003: Desktop Testing Policy — Thin Shell, No UI Automation

**Status:** Accepted
**Date:** 2026-07-28
**Deciders:** Richmond (RicheyWorks)
**Prompted by:** TESTING.md (2026-07-28 reactor gap audit), gap P3

---

## Context

`daedalus-desktop` has four test methods across the launcher and theme manager — near-zero
coverage (measured 5.9% instruction on 2026-07-28) against a reactor whose core module sits
above 90%. The gap audit's finding was that this needs *a deliberate policy, not necessarily
more tests*: leaving the module's posture undocumented invites either guilt-driven test
theater or a slow accretion of untested logic, and neither failure mode announces itself.

The candidate remedies were TestFX-style UI automation, a coverage push on the module as it
stands, or an architectural rule that makes low desktop coverage *correct* rather than
tolerated.

## Decision

`daedalus-desktop` stays a **thin JavaFX shell**, and that is enforced by policy rather than
by UI tests:

1. **Any logic that grows in `MainController` (or any desktop class) moves down into
   `daedalus-core`**, where the property tests, hostile fixtures, and the coverage ratchet
   already live. The desktop module composes; it does not compute.
2. **No TestFX / UI-automation suite.** For a single-developer desktop shell, its flakiness
   costs more than its coverage is worth. The four existing tests (launcher wiring, theme
   manager) stay as-is.
3. **The module is exempt from the JaCoCo ratchet**, as a visible
   `<jacoco.check.minimum>0.00</jacoco.check.minimum>` in its pom — exemption as code, not
   as a missing property.
4. **The tripwire that revisits this ADR:** the first time a bug report is *in* desktop
   logic, that logic moves to core in the fix commit and gets tested there. If that keeps
   happening, the shell is no longer thin and this policy is failing — reopen it.

## Consequences

- Desktop coverage will read as near-zero indefinitely. That is the documented, intended
  posture, not drift — reviewers should check pull requests against rule 1 instead of asking
  for desktop tests.
- The policy costs one thing deliberately: a genuine JavaFX wiring regression (an fxml id
  rename, a broken binding) will surface at launch, not in CI. Accepted — the shell is
  launched constantly during development, and the alternative is the TestFX flakiness this
  ADR rejects.
- Rule 1 keeps the interesting logic under the strongest part of the suite, which is where
  the four shipped bugs behind easy fixtures were actually caught.
