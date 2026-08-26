# ADR-003: Desktop Testing Policy — Thin Shell, No UI Automation

**Status:** Accepted (amended 2026-07-31, docs refreshed 2026-08-26)
**Date:** 2026-07-28
**Deciders:** Richmond (RicheyWorks)
**Prompted by:** TESTING.md (2026-07-28 reactor gap audit), gap P3

---

## Context

On 2026-07-28 `daedalus-desktop` had four test methods across the launcher and theme
manager — near-zero coverage (measured 5.9% instruction) against a reactor whose core
module sits above 90%. The gap audit's finding was that this needs *a deliberate policy,
not necessarily more tests*: leaving the module's posture undocumented invites either
guilt-driven test theater or a slow accretion of untested logic, and neither failure
mode announces itself. As of 2026-08-26 the module has ten test methods and a 0.09
floor; `MainController` is still untested.

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
   costs more than its coverage is worth. Launcher and theme tests stay; generation/solve
   logic that left the FX thread lives in `DesktopWork` (six tests, 2026-07-31).
3. **The module is not exempt at 0.00.** A 2026-07-31 amendment replaced the visible
   `<jacoco.check.minimum>0.00</jacoco.check.minimum>` with a small real floor (0.09) and
   ceiling (0.14) — a deletion guard, not the absence of one. `MainController` is still
   untested; the floor is not high enough to notice a rendering regression.
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
