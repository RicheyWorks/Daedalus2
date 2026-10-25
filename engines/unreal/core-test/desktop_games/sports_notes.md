# Desktop sports ports

Both cores implement the shared `daedalus::desktop::Game` interface in
`DesktopGames/DaedalusDesktopSportsCore.h`: `FootballGame` and `DodgeBallGame`.
Original Desktop files are unchanged. The latest source revision is the baseline.

| Game | Canonical local source | Modified UTC | SHA256 |
| --- | --- | --- | --- |
| Football | `C:\Users\730ri\OneDrive\Desktop\football_pygame_ce.py` | 2026-05-02 08:11:27 | `7b013f8151aa1c815ba0947c2d5d39cf559467106cde60aacca29df936ca3ebe` |
| Super Dodge Ball Tournament | `C:\Users\730ri\OneDrive\Desktop\super_dodge_ball_fixed.py` | 2026-05-02 08:24:56 | `359b4bc045b00186e9d3ee915863de214453b22df8b81a881402ee6b49d21cb6` |

The older Dodge Ball file is `super_dodge_ball.py` (2026-05-01 02:57:36 UTC).
Its features are not substituted for the later fixed revision.

## Source behavior preserved

Football keeps the 800x600 field; blue human and red CPU; 90-second match;
human speed 3.5; CPU speed 2.8 times 0.9 pursuit; unnormalized diagonal movement;
keyboard direction precedence; per-axis 0.15 deadzone before stick override
beyond 0.2 on either axis;
12-frame kick cooldown; kick speed 8; contact deflection speed 6 at distance
strictly below 20; ball friction 0.96 and wall restitution 0.8; strict goal
windows `x<50` / `x>750`, `220<y<380`; goal placement reset; final win/loss/draw;
full restart. The source allows kicks from any distance. That quirk remains.
The source floating timer is retained, including its possible extra final frame.

Dodge Ball keeps all eight countries, their colors/power/speed values and three
roster variants; six players with three HP each; simultaneous control of all
three human players; side restrictions; per-axis 0.15 stick deadzone;
keyboard/stick movement precedence followed by separate D-pad/hat override;
base-lane jump arcs; up-held charge to 60; the `charge>30` super threshold;
normal/power speed 8.5/12; throw cooldown 14/22 with Germany 28 and Russia 32;
all eight country throw vectors and both Japan/Australia variants; nearest living
target selection; 24-radius loose pickup; normal/power/jumping catch radii;
source CPU pursuit, defensive wiggle, charging and both probabilistic throw paths;
ball friction 0.985, bounds and 0.6 bounce; loose-ball stopping threshold;
one/two-HP hits at strict radius 18; knockout; cumulative match score; four-round
tournament flow and a fresh tournament reset; burst particles, HP dots, charge
meters, possession rings and country uniform details.

Source quirks retained: jumps return to the original spawn lane, both teams can
take friendly hits, holding Fire can immediately rethrow a caught ball, and
opponents may repeat between tournament rounds. There is no new teammate-switch,
bracket, multiplayer or persistent leaderboard feature.

## Deliberate changes

### Courtyard teammate passing

V / pad Y / LB sends a fresh pass to the next living teammate in cyclic P1/P2/P3
order, skipping knockouts. This changes the holder and its existing roster power/
speed traits; control still moves the whole team together. The native Dodge-only
override uses DashPressed and leaves held Dash false, with Shift/B jump and all
throw/confirm mappings intact. The pass action opens title/continues results via
the existing DashPressed rules; it does not confirm country selection.

A valid pass from an existing Playing step takes priority over simultaneous fresh
Fire; a refused pass falls back to the original throw path. Validate possession,
cooldown and recipient first, then attach a local ball copy through UpdateBall,
aim from the hand and use the unchanged normal Throw. Zero-length aim is refused
before mutation. Motion, drag and bounce use the original UpdateBall. There is no
homing or remote handoff. Only the intended receiver catches automatically; all
other human catches/hits are skipped during a tagged pass, making it harmless to
the passing team. CPU interception and damage retain their normal behavior.

The receiver gets at least 14 cooldown steps after movement ticking, so held Fire
cannot immediately rethrow the same catch. Tags clear before normal rethrows/CPU
ownership, on hits/stop/round reset and Reset. A receiver that becomes unavailable
leaves the pass harmless until it stops or changes ownership; a miss uses ordinary
loose-ball recovery. One private recipient index is added, with read-only feedback.
The existing readiness line names the recipient and a blue ring marks it in flight.
No scoring, roster, country, tournament, save or default attack rule is changed.

`desktop_dodge_pass` / `dodge_pass_test.cpp` passed 70/70 strict single-TU MSVC
C++17 checks: the three-player cycle, KO skipping, zero-aim refusal, post-tick
catch cooldown, ordinary friendly-hit companion, CPU catch/hit, misses, input
priority, round cleanup, read purity and Driver pause/catch-up edges. No broad
sports fixtures or engine build were repeated. Native binding/focus,
receiver-ring readability and human pass/throw feel remain unverified.

### Courtyard native How to play

Courtyard now reuses the existing native paused help modal (button / F1 /
left-stick click), rather than adding more court labels. Its own title, intro and
progress branches explain shared trio movement, nearest target, held catch/rethrow
versus fresh pad X/RB throw, jump catch, stick/hat charging and four-round results.
They bypass Star's save instructions. Existing scroll, focus, held-accept repeat
protection and pending-save notices/fences are retained.

Dodge's Over flag marks a match result within a continuing tournament. Its help
Resume button therefore permits that retained result, without advancing it;
another fresh gameplay press performs the existing continuation. Other games'
terminal-resume restrictions are unchanged. Return paused still leaves play paused.
No game core, input adapter, actor state/save or new modal framework changed.

This native Slate-only slice receives focused source/control-flow review and
whitespace checks. Engine compilation, physical help/resume/scroll focus, held
input isolation and viewport acceptance are deferred to the sole native owner.
Portable sports or source fixtures cannot establish those native behaviors and
were not rerun for this slice.

### Courtyard throw target

Human possession now shows small inward chevrons at the current nearest living
opponent and names its C1/C2/C3 slot in the existing readiness line. The cue uses
the same Nearest selector as AimAndThrow, including its stable lower-index ties.
It follows the actual quantized/airborne drawing position. Ready throws use cyan;
cooldown snapshots are muted. It is suppressed for nonplaying phases, CPU/loose/
airborne balls, invalid possession and no living opponent. The title's former
edition tagline instead teaches the automatic target rule; no extra helper row.

This is a current selection, not a lock or predicted trajectory. Fresh presses
select before movement; held rethrows can select later in the step. Country supers
still change throw vectors and friendly hits remain possible. Rendering/status
do not mutate game data or consume randomness. No controls, AI, physics, charge,
scoring, tournament or save behavior changes. Football is unchanged.

`desktop_dodge_target` / `dodge_target_test.cpp` passed 233/233 strict single-TU
MSVC checks: all three holders, stable ties/dead/moving targets, suppression,
cooldown styling, quantized airborne alignment/layering and actual fresh normal
throw direction. Extra rendering/status calls preserve paired future state for
24 steps across all eight countries. No old physics fixtures or full sports suite
rerun, no engine build/editor/native acceptance. Visibility at native scale and
human interpretation of a changing target remain unverified.

### Courtyard stick country selection

The country picker now accepts a vertical stick flick beyond 0.6, once per tilt.
Both axes must center within 0.3 before the next choice. A stick gesture that
opens the picker is consumed; a neutral button/key entry permits a fresh flick.
This completes the existing stick title-entry flow without scrolling past choices
while the stick is held. Up/Down key and hat edges retain their current priority;
a simultaneous stick gesture is consumed even when a digital edge wins.

The original axes are untouched for match movement and charge. Hat-only Up still
does not charge, while original stick Up beyond 0.5 still does. Confirmation,
country stats, tournament/RNG behavior and reset are retained. The existing
selection line/status names stick flicks rather than adding a helper row.

`desktop_dodge_country_stick` / `dodge_country_stick_test.cpp` checks actual title
entry, centering/thresholds/held gestures, wrapping and mixed inputs, Reset,
confirmation and the live stick/hat charge distinction. Native stick hardware,
layout and player acceptance remain unverified.

Strict serial single-TU MSVC C++17 passed 48/48 focused checks: actual title
entry, strict engage/inclusive release thresholds, held/reversed/jittered tilts,
horizontal centering, wrapping, mixed digital priorities, reset, chosen roster,
confirmation and unchanged live charge companions. No old sports bulk or source
fixtures were rerun; the native adapter is unchanged.

### Courtyard tournament finish

After round four, a dedicated scorecard declares the overall tournament win,
opponent win or draw from the existing cumulative match wins. Each team has a
large count and a four-segment win bar. The opponent panel represents all four
opponents, while the smaller last-match line still names the final country and
match winner. Earlier round results retain their existing match headline.

This fixes the misleading final presentation where a 1-3 tournament could end
under a large last-match victory headline. Status includes the overall result but
retains its match-based Over/Won flags. No score, phase, RNG, physics, opponent
selection, continuation or saved-data behavior changes. A fresh result press still
returns to title; country confirmation starts a new four-round score.

The focused `desktop_dodge_tournament` / `dodge_tournament_test.cpp` checks actual
four-round settlement, including opposite final-match/tournament outcomes and a
2-2 draw, earlier rounds, terminal freeze/pure presentation and clean new play.
Native font/layout, controller and human acceptance remain pending.

Strict serial single-TU MSVC C++17 passed 145/145 focused checks: 3-1 with a final
loss, 1-3 with a final win, 2-2 draw and both sweeps, all through actual lethal Step
settlement; earlier-result headings and match flags, bars, held terminal freeze,
read purity and paired fresh-country future state. No prior sports bulk or source
oracle was rerun. This presentation slice leaves gameplay implementations intact.

### Football target practice

An optional Target practice mode uses the existing movement, directional kick,
ball drag/bounce and human deflection. Match remains the default with its original
90-second CPU duel. Native checked Match / Target practice controls reuse the
cabinet's existing SetGameOption path. Selecting the active mode is a no-op;
changing mode or Restart starts over. Reset retains the selected mode.

Practice places the ball at (600,300) and the player behind it at (560,300), with
no CPU or running match clock. Move around the ball to aim, then press J/Space
or pad A/X. The three goal pockets are center, upper, lower; the required pocket
glows gold and cleared pockets turn mint. One kick launches each attempt. A goal
within 22 pixels of the required pocket clears it; other goals, own goals and
settled shots produce a friendly retry without losing cleared targets. Flight
settles at speed <=0.12 or 240 steps, so a shot that stops short cannot stall.
The ordinary source goal boundaries remain strict (220 < Y < 380).

Result feedback lasts 60 steps, then sets up the next ball automatically. A fresh
kick/Action press skips that wait to aiming without kicking. K/Enter or pad B
also sets up the same target again during a live shot. Clearing all three ends
the round; a fresh kick/Action starts a clean practice round. Held buttons alone
cannot replay or repeatedly kick. Progress is session-only, with no persistent
best, new save format, leaderboard, loss state or invented rewards.

The aim cue shows the initial kick direction; player contact can still deflect
the ball during flight. This original practice loop is a native extension, not
a Python parity claim. Dodge Ball remains unchanged. Native mode focus, actual
font/layout, controller and play feel remain acceptance work.

`desktop_football_practice` / `football_practice_test.cpp` passed 370/370 strict
single-TU MSVC checks, including only the 74 existing Football source cases from
`sports_parity.txt`, a real three-pocket route with settled/off-target retries,
mode/input/pause/reset checks and the default match ending after 5,401 steps.
The same test with the exact prior Sports header at `66b042f2b` passed 322/352,
with thirty expected failures; absent practice ends the route section early.
Dodge Ball's normalized 454-line suffix is unchanged. No fixture regenerated,
full sports suite, Unreal build, editor or runtime acceptance was performed.

### Source repairs and limits

- **Stalled loose-ball repair:** source side limits `x<=360` / `x>=440` and pickup
  distance `<24` make a stationary ball in `[384,416]` unreachable. Only an
  unowned, nonairborne ball in that strip moves to reachable `x=380` or `420`.
  Tests reproduce the source stall and prove both sides can retrieve the repair.
  Airborne and possessed balls are unchanged.
- Analog input is finite and clamped to `[-1,1]`; NaN/infinity cannot poison state.
- Ball ownership uses a six-player index instead of pointers. Reset clears state,
  input edges and particles. Dead-player possession is cleared immediately.
- Particles have a 256-entry cap and frames use the shared 4,096-command cap.
  Particle draws are still consumed at capacity for stable native replay.
- Football clamps the exhausted display timer to zero.
- The shared deterministic native RNG differs from Python's Mersenne Twister.
  AI probabilities/ranges and opponent eligibility are preserved; the exact
  Python seed-to-session random sequence is not. No statistical balance claim
  is made from the parity fixtures.
- Common drawing commands approximate the source's ellipses/arcs with small
  rectangles/lines. Source circle/rectangle uniforms, country colors, ball,
  court, HUD and gameplay geometry remain. No external textures or models are
  copied. The source's Nintendo-style descriptor is a reference, not proof
  that any brand/character/license rights transfer to Daedalus.

## Native evidence

MSVC 2022, C++17, `/W4 /WX /permissive-`: **283,709 checks pass**.
There are **299 executed-Python source cases** in `sports_parity.txt`: movement,
kick, friction/bounce, all 48 country/slot/side rosters, all country super/charge
variants, jump/charge boundaries, catch and pickup thresholds, and damage.
Additional integration tests cover strict goal boundaries, single score awards,
team elimination, all four tournament rounds, restart, nonfinite input handling,
the loose-ball regression, country visuals, command/entity bounds, and two
identical 12,000-step native replays. Check counts include repeated invariant
checks; they do not represent that many independent gameplay scenarios.

`sports_source_oracle.py` SHA-checks the latest files, extracts only reviewed AST
constants/classes/methods, actual `get_axis`/`get_hat` functions and the two damage
assignments, and supplies controlled controller/drawing stubs. Deadzone cases
include stick `(0.8,0.1)` and `(0.15,0.8)` in both games; Dodge cases prove
neutral-stick D-pad Up does not charge, while D-pad Right plus stick Up moves
right and charges. It does not import pygame, run the original module, create a
display, execute a game loop or install anything. Regeneration requires the
user's original local files; CI consumes the checked-in fixtures.

Add the finalized test through the central CMake helper:

```cmake
desktop_test(desktop_sports sports_test.cpp sports_parity.txt)
```

The executable takes the fixture path as its only argument. Source regeneration:

```powershell
python sports_source_oracle.py --desktop 'C:\Users\730ri\OneDrive\Desktop' --output sports_parity.txt
```

## Exact host/Claude bindings and acceptance

- Construct `FootballGame` / `DodgeBallGame` via the shared registry; call
  `Reset(seed)`, then `Step(Input)` at the host's bounded 60 Hz cadence.
- Keyboard movement maps to `Left/Right/Up/Down`, the original stick to
  `AxisX/AxisY`, and D-pad/hat to separate `PadLeft/PadRight/PadUp/PadDown`.
  Apply the per-axis 0.15 deadzone before the 0.2 stick movement override.
  Dodge Ball then overrides movement with a nonzero pad vector internally.
  **Do not overwrite original `AxisX/AxisY` with pad values:** charge reads
  original stick Y or keyboard Up, so D-pad Up alone never charges and D-pad
  Right plus stick Up moves right while charging. Country selection accepts
  keyboard and D-pad Up/Down edges. Football has no source hat input.
- `FirePressed` = source kick/throw keydown. `Fire` = held throw/catch for Dodge
  Ball. `ActionPressed` = confirm/continue/restart. `Jump`/`JumpPressed` = source
  Shift/B jump. Dodge country selection uses Up/Down edges, while title can also
  respond to stick motion over 0.6. Pass pressed edges only once across catch-up
  substeps; held controls may persist. For source controller parity, Dodge
  `FirePressed` includes A/X/RB, but held `Fire` (catch/backup) includes A only;
  keyboard Space/Z supplies both. The adapter must preserve that distinction.
- `GetStatus()` exposes score, living human roster members and result flags;
  `Render(Frame&)` outputs 800x600 procedural commands. Dodge `Over/Won` refers
  to a **match** result; keep the session open so confirm can continue the next
  tournament round. `Data.Mode` distinguishes Title/selection/play/results.
- Football acceptance: start, move/kick, score both goals, see timer/result,
  restart without retained scores or velocities.
- Dodge acceptance: select all eight countries; verify three matching uniforms
  and roster stats; pick up, normal throw, charge/super throw, jump/catch and KO;
  verify all four rounds and cumulative score; recover a center-strip loose ball;
  restart; close/reopen without stale ownership/input.

No UHT/UBT compile, Slate/UMG rendering, packaged runtime, editor playtest, or
Claude/Blender acceptance is established by these native tests. Shared Unreal
wrapper/registry, publication, CI and owner coordination remain root-owned.

## Blender requirements grounded in source

Football has simple 12-pixel blue/red circle players with white outlines and an
8-pixel white ball with black outline. Upgrade as readable top-down athletes,
keeping those team silhouettes/colors and the source's field dimensions; no
named character model exists in this source.

Dodge Ball has 14-pixel circle players, country-specific colors and procedural
uniform/headwear accents: USA red stripe/white dots/blue cap; Japan white disc
and headband; Brazil gold disc/green band; Germany black/red/gold stripes and
black cap; UK white cross and curved headwear; Russia white/blue/red stripes and
brown hat; China gold dots/red cap; Australia white dots/brown wide hat. Preserve
country readability and three-player rosters. Required animation states: idle,
movement, holding/charging, normal/super throw, jump, catch, hit and KO.
No original external character images, rigs, meshes, audio assets or texture
license files are loaded by these scripts. Blender work is a future owner task;
no artwork or acceptance is claimed here.
