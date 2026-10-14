# Desktop sports ports

## Native polish cycle 3: Football — source only, 2026-10-14

Claims hub 31211/31212 cover `FootballGame` only and the existing canonical
docs/install packet. Shared `sports_detail` helpers and all `DodgeBallGame` bytes
remain unchanged. The original Football SHA256 below was read and verified.

Football now reports each goal's scorer for 90 cosmetic live steps and each
accepted/cooldown-rejected kick press for 12. Counters include the event step plus
89/11 subsequent live steps respectively; result screens freeze them, and Reset/fresh match clears
them. Scorer/goal highlights, a kick ring, actual ready/cooldown labels,
DEFEND/ATTACK labels and mapped fresh controls explain the original rules.
Goal reset clears stale kick feedback but retains the existing player cooldown.
No countdown or cue blocks simulation: immediate goal/position reset, floating
90-second clock, strict scoring/contact geometry and original physics remain.
Kick acceptance precedes movement/decrement and normally displays cooldown 11
on its first frame. Later contact can overwrite its velocity; the receipt does
not promise ball trajectory. Remote kicks remain legal.

Direct core Pad flags now OR into human keyboard flags locally, matching existing
Slate behavior. Right/down precedence, unnormalized diagonals, per-axis deadzone
and stick override remain. This is a native input enhancement; the original has
no hat input. CPU pursuit and shared/Dodge input logic remain unchanged. Fresh
Fire/Action after title/result resets and immediately advances play without a
same-step kick; host R/Restart returns to title via the existing Reset.

**Uncompiled/untested.** No tests, builds, CI, game/oracle execution, editor or
Play occurred in this pass. Historical receipts below apply to their baseline.
Later validation must check 90/12-step cue expiry/freeze/reset, ignored/accepted
presses at cooldown 1/0, goal with a live cooldown, final-step goals and each
win/loss/draw, held buttons versus fresh edges, Pad/right-down/stick precedence,
physics/clock equivalence without Pad, frame bounds and actual readability.
The existing [DESKTOP-PYTHON-GAMES.md](../../../../docs/DESKTOP-PYTHON-GAMES.md)
and `docs/desktop-games-polish-install.json` hold the coverage and exact source
installation/deferred-validation record. No characters/assets/audio were added.

Both cores implement the shared `daedalus::desktop::Game` interface in
`DesktopGames/DaedalusDesktopSportsCore.h`: `FootballGame` and `DodgeBallGame`.
Original Desktop files are unchanged. The latest source revision is the baseline.

| Game | Canonical local source | Modified UTC | SHA256 |
| --- | --- | --- | --- |
| Football | `C:\Users\730ri\OneDrive\Desktop\football_pygame_ce.py` | 2026-05-02 08:11:27 | `7b013f8151aa1c815ba0947c2d5d39cf559467106cde60aacca29df936ca3ebe` |
| Super Dodge Ball Tournament | `C:\Users\730ri\OneDrive\Desktop\super_dodge_ball_fixed.py` | 2026-05-02 08:24:56 | `359b4bc045b00186e9d3ee915863de214453b22df8b81a881402ee6b49d21cb6` |

The older Dodge Ball file is `super_dodge_ball.py` (2026-05-01 02:57:36 UTC).
Its features are not substituted for the later fixed revision.

## Historical baseline source behavior preserved

The original-source facts below remain applicable; newer feedback/direct Pad
changes are identified above and are outside the old validation receipts.

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

## Historical baseline native evidence

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
  keyboard and D-pad Up/Down edges. Football has no source hat input; cycle 3
  now mirrors the existing host merge for direct native Pad flags as described above.
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
