# End-to-end regression sweep

Exercises every ADR-006 feature against a **running server**, reporting a pass/fail matrix
with evidence. Each check continues past failures so one break cannot hide the rest.

    # The sweep generates well over the default 30-mazes-per-minute budget, so run the
    # server with the generous test-profile limits or it will throttle itself mid-run.
    SPRING_PROFILES_ACTIVE=test java -jar daedalus-server/target/daedalus-server-*-exec.jar &
    python3 sweep/api-sweep.py      # 14 checks, API level
    node    sweep/ui-sweep.js       # 16 checks, real browser (needs playwright)

Why it exists: features were verified individually in the batch that built them, but later
consolidation work modified services those earlier features depend on (`LivingMazeService`,
`TrafficService`, `MazeBreeder`). Nothing exercised all ten together until this.

## Writing checks that are worth trusting

Three rules, each learned by getting it wrong here:

1. **Assert the documented contract, not a plausible one.** Three checks "failed" on first
   run against correct behaviour: an illegal agent step answers 400 (documented) not 409,
   ASCII is content-negotiated on `/maze/{id}` not a `/ascii` path, and `join` 404s by
   design when the multiplayer flag is off.
2. **Read the body, not just the status.** `POST /session/{id}/move` answers `200` with a
   boolean — `false` means refused. Checking the status alone read a correctly-refused
   wall-teleport as an accepted one.
3. **Never wait on a condition that may already be true.** Waiting for `state.ghost` to be
   set passed instantly on the previous stage's ghost, then raced the reload that cleared
   it. Clear the state first, then wait for it to become true.

**A helper that hides the real failure is worse than the failure.** The maze-generating helper
used to return the error body on a non-200, so every downstream check died with
`TypeError: string indices must be integers` — a message that says nothing about the 429 that
actually caused it. It now raises with the status and body.

A flaky sweep is worse than no sweep. When a check flakes, chase it: the one flake here was
a real race in the client — an in-flight poll response reinstating the maze the player had
just navigated away from.
