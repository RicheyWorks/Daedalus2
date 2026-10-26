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

## Optional Target rally

Mode3 adds placement goals to the existing full-height practice return wall.
Ordered ball-center windows are inclusive[60,220], [230,390] and[400,560] in the
original court coordinates. They are deliberately broad, separate160px bands.
Only a real guarded outgoing right-wall bounce at centerX732 can clear the next
window, consume one goal and reverse the ball normally. Other placements still
reflect. There is no positional/edge-hit aiming rule: actual paddle displacement
at contact adds spin to existing vertical velocity, and intervening wall bounces
can reverse it. Existing140px paddle, Vx4, spin cap4, radius contact and120-step
serve are reused; no new movement, input or reflection physics is introduced.

PlayerScore records0..3 cleared windows. PrepareServe leaves it intact through a
miss while resetting the ordinary rally; CPU score stays0. Third clearance freezes
the course and reuses the existing fresh rematch gate, which returns before motion
or serve skipping. Reset/mode change clears goals and retains the selected mode;
active native choice remains a no-op. The five-return celebration remains mode1
only, so course feedback describes real cleared goals. Match0, practice1 and
First to5mode2 retain their complete branches/configuration.

Existing practice layout gains wall segments/numbers, target count and completion
in the same slots. Miss recovery explicitly retains progress. Native checked mode
row uses MakeMode; actor header is comment-only, with no actor/input API/registry/
builder/save changes. Old practice and quick-match invalid upper bound changes
from3 to4 because3 is now valid; those full suites are not rerun by this slice.
Native controls/focus, viewport fit and human placement learning remain pending.

`desktop_pong_target_rally` / `pong_target_rally_test.cpp` passed 61/61 strict
single-TU MSVC C++17 checks. A bounded public-input controller clears all3 windows
in1033 steps with3 actual paddle returns and no pose/score writes to its route
instance. It previews17 fixed impact-axis choices on short game copies; this
demonstrates reachability, not human aiming difficulty. Checks cover inclusive
band endpoints, wrong/incoming contacts, single-event scoring, preserved misses,
serve/replay/reset, short0/1/2 companions, render/status purity and Driver cleanup.
No old parity/spin/practice/quick suites or old-header proof repeated. Updated
invalid-bound literals in the two old test files are source-reviewed only.

## Optional First to 5

Mode 2 adds a short match with a clear finish: the first side to five points wins.
Modes 0 (endless Match) and 1 (Rally practice) retain their rules and presentation.
The new native checked button uses the existing MakeMode option/focus path.
Match paddles, AI, ball speed, collision, spin and point/serve rules are reused.
The opening has the same 45-step preparation used after a match point; existing
fresh Fire/Jump/Action serves early and launches on the following frame. Paddles
stay live while preparing.

At the fifth point the whole game state freezes. A fresh Fire/Jump/Action starts
another First to 5 match; the reset edge cannot also move a paddle or skip its
preparation. Held controls alone do not replay. Native R/Restart retains the mode
and uses the established reset/input cleanup. A separate 90-pixel score strip
above the 600-pixel court gives an 800x690 frame and a clear result overlay.

No persisted result, save format, actor implementation or new input API is added.
The former invalid-option checks in the practice test now use 3, since 2 is valid;
the focused quick-match check covers that boundary through both core and Driver.
Native module/Slate compile, checkbox focus/release, viewport/fonts, physical play
and difficulty/feel remain acceptance work.

`desktop_pong_quick_match` / `pong_quick_match_test.cpp` passed 151/151 strict
single-TU MSVC checks: two controlled five-goal rounds through actual Step, result
freeze/three replay edges, serve timing, score-strip/neutral-opening cues, mode3
refusal through core/Driver and 80 paired preterminal physics steps against Match.
Mode0's six-command opening and mode1's layout have focused companions. The two
updated invalid-option expectations are covered by the new boundary checks; the
unaffected bulk of the prior practice/parity/spin suites was not repeated.
No original fixtures, Python sources or save formats changed; no engine/native run.
