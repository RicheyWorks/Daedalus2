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
