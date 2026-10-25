# Pong moving-paddle spin

This is an intentional native gameplay improvement, separate from pinned Python
source parity. Before it, aligned rallies kept |Vy|=3 regardless of paddle motion,
while the CPU followed at 4 pixels per step. This limited direct control over returns; it did not
make scoring globally impossible, since early serves can exploit CPU position.

At a real incoming player-paddle contact, actual paddle displacement after the
existing input merge and arena clamp adds half that displacement to vertical ball
velocity, bounded to `[-7, 7]`. Neutral contact preserves the current angle. Moving
against a boundary adds no spin; partial clamping uses only the actual movement.
CPU AI, CPU returns, horizontal speed, collision windows, scoring and endless match
behavior remain unchanged. Existing serve setup retains vertical velocity, so spin
(including a deliberately flat return) carries into the next rally.

Status text and a post-contact cue teach moving at impact. The initial render still
contains the original six commands. Canonical source, oracle and eleven parity
fixtures are unchanged; their contact case is neutral and remains source-faithful.

`pong_spin_test.cpp` covers keyboard/Pad/analog and combined controls, neutral/CPU/
outgoing contacts, clamps, finite input handling, velocity caps, presentation purity,
the existing serve window and one bounded real-Reset scoring route (at most 420
steps). Parent's pre-change private probe found the same input return at frame 201:
baseline kept Vy −3 and CPU caught it at 335; candidate Vy −6 missed at 335 and scored at 349.
That probe was a single deterministic policy, not a general balance or live-play proof.

Compile only this C++17 test with the plugin Public include path, then run it and
the existing `pong_test.cpp` against unchanged `pong_parity.txt`. Replaying the new
test unchanged against the preceding header should fail the new spin/agency checks.
Native Slate/controller play and broader balance remain unverified by portable checks.

Focused evidence: strict single-TU MSVC C++17 `/W4 /WX /permissive- /Od` passed
36/36 spin checks (real return201, point349) and the existing30/30 Pong checks
covering all11 unchanged source fixtures. The new test compiled unchanged against
the prior header passed23/36, failing13 spin/guidance/agency checks as expected.
CMake target: `desktop_pong_spin`. No engine build, editor or live play was run.

## Optional Rally practice

Mode 0 remains the existing endless Match. Mode 1 is a separate beginner loop:
140-pixel paddle, a gentler 4-pixel horizontal launch/vertical spin cap, and a
full-height right return wall. The ball's radius counts for forgiving player
edge contact. Only player returns increment rally/best; wall returns never add
points. Every fifth accepted return gives a short celebration. A miss clears
the rally, keeps best and prepares another centered gentle serve. No opponent
points, lives or failure screen are added.

Practice opens and retries with a two-second countdown; existing Fire/Jump/Action
edges serve early, always launching on the next fixed frame. Paddles stay live
during preparation. A dedicated score strip sits above the unchanged 600-pixel
court in an 800x720 frame. Match retains its 800x600 six-command opening and all
prior AI, collision, score, spin and serve behavior.

Native Match/Rally practice controls use the existing option API and Slate toggle
style, with bound checked state and native focus. Pressing the selected mode is
a no-op; changing mode or Restart deliberately resets the session best. Misses
preserve it. There is no Pong saved-run format or durable best claim.

`pong_practice_test.cpp` / `desktop_pong_practice` uses public existing state and
virtual option APIs for bounded serve/contact/retry fixtures, render/status
purity and Driver mode/pause/input cleanup. A real-Reset tracking policy reaches
two returns within a 1,200-step cap without per-step rendering. Native checkbox
release/focus, viewport scaling and actual human/controller play remain pending;
portable rendering commands are not native visual acceptance.

Strict single-TU MSVC /W4 /WX /permissive- passed 74/74 practice checks. The exact
pre-feature Pong header at 07b3c1fe4 passed 20/74 (54 expected failures), compiling
the same test unchanged through a private include overlay. Existing Match suites
were run once for this change: parity30/30 and moving-paddle spin36/36 (real return
201, point349). No source fixture was regenerated, no production header reverted,
and no engine/UHT build, editor, service or broad suite was run.
