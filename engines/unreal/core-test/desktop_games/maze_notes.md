# Desktop maze and adventure ports

## Current display-name checkpoint, 2026-10-15

Player-facing titles and descriptions are listed in [The Daedalus arcade](../../../../docs/DESKTOP-ARCADE.md).
Code `4c1c2aa62f681a3ed8d947df9f5c20cedfe0c585` makes display-only naming
changes. The focused MSVC registry/UI/ID check passed123/123. Stable IDs/classes,
originals, rules, input, saves, art and license notices are preserved. Historical
franchise names below are technical source attribution, not current player copy.
The earlier full-suite receipt remains pinned to its earlier commit; current
Unreal/native/controller/text-fit and content provenance are unverified.


## Previous portable verification, 2026-10-15

Code `fe6d0ec6f6fb19671f244cdaca73c707b2bb3630` passes all seven portable
MSVC C++17 suites serially: 394,774 reported assertions, including 162 new polish
checks across all eleven families. Existing source fixtures remain unchanged;
Python oracles were not rerun. Exact source/test/binary pins and commands are in
[the v5 install packet](../../../../docs/desktop-games-polish-install.json).

This compiles game cores and Driver only. Current Unreal actor/Slate/UHT/module,
native load/rendering/focus, physical-controller gameplay and E2E acceptance are
unverified. Earlier cycle sections below retain their historical source-only
stage; their uncompiled/untested statements do not describe this checkpoint.
New shooter polish checks use public seeded sessions, not forced private-vector
saturation. Star host disk-write failure/recovery remains unexecuted.


Native polish cycle 4 (2026-10-15, claims 31229/31230): `ZeldaGame` now derives
remaining roster/key objective, labelled ground key, Moblin HP, sword readiness,
current hurt timer and distinct victory/defeat/fresh retry text. Direct Pad flags
mirror the existing Slate merge before source analog/facing precedence. All sword
collision still occurs before movement, cooldown 18/hurt timer 45 remain, and
enemy AI, scores, drop/key RNG and prior loss-before-win/key repair are unchanged.
The shield remains decorative. At hurt timer 1 the new label says it expires
before the next live collision pass; terminal controls/ready labels are gated.
No gameplay state/timers or new shield/inventory behavior were added. Dungeon,
Pac-Man and shared helper bytes match prior checkpoint 81ffdd84 exactly.

Uncompiled/untested: no game/oracle/editor, test or build execution. Later checks
include opposing/mixed Pad/stick/facing, sword-before-move and timer 18/1/0,
hurt timer 45/1/0, four-roster/key pickup/death transitions, no duplicate drops,
terminal/fresh reset and actual frame readability. Current canonical coverage and
exact install/deferred-validation packet are the existing DESKTOP-PYTHON-GAMES.md
and docs/desktop-games-polish-install.json; old receipts below are historical.

Native polish cycle 2 (2026-10-14, claims hub 31185/31186): Pac-Man now guards only
lethal unfrightened-ghost collisions for exactly 90 subsequent live steps after a
nonterminal death. This explicit native rule extension leaves movement, ghost
updates/random calls, pellets/fright/captures, scores, loss-before-win and ghost
revival ordering unchanged. Initial run/terminal death have no guard; Reset clears it and
terminal steps freeze. A cyan halo/counter, remaining dot/power counts and fresh
Action/Fire/Jump/host R retry explain existing state. Dungeon cycle 1 and Zelda
are unchanged by this continuation. No tests/builds/CI/Unreal/Play were run.
Later validation must check the protected 90th step versus vulnerable 91st,
frightened captures during grace, terminal/reset and last-dot/lethal ordering.

Native polish cycle 1 checkpoint (2026-10-14, dedicated minigame owner): Dungeon has an
original Threadlight Passage lantern circuit in its existing room. Map/start/
movement/collision/Action reset remain source-derived, but ordered Fire/Jump
interaction, local terminal completion, seed permutations and feedback are new
native design. They are uncompiled/untested and outside the historical Python
parity evidence below. Pac-Man/Zelda were unchanged at that checkpoint. Architecture/story, before/
after, per-game backlog and operator requirements are in the existing canonical
[DESKTOP-PYTHON-GAMES.md](../../../../docs/DESKTOP-PYTHON-GAMES.md), with a source-only
install packet at `docs/desktop-games-polish-install.json`. No dedicated tests,
builds, CI, editor or gameplay were run to make this documentation update.

These ports use the actual Desktop collection. They do not replace it with the
unrelated repository ComputerPets or Minesweeper projects. All three families
have one discovered source variant, so these are also their latest baselines.
The Desktop originals were read only and remain unchanged.

| Family | Canonical path relative to `C:\Users\730ri\OneDrive\Desktop` | SHA-256 |
| --- | --- | --- |
| Dungeon Prototype | `PythonGames\main.py` | `cbf19aa131cfe9815f36ef4812638cf0992141666d4eb3a0fce0b92e662e99a4` |
| Pac-Man | `pacman.py` | `6cad8d138888c7a18d80e0e034546a49e57618610ac3e5dcce9886a7358ad8ed` |
| Zelda adventure prototype | `zelda.py` | `713f6de7c27a92d65fdedd77a6c15a7e80a964d098d5ba209dbf32e648cc9bdd` |

## Native bindings

`DesktopGames/DaedalusDesktopMazeCore.h` defines
`daedalus::desktop::DungeonGame`, `PacmanGame`, and `ZeldaGame`, each implementing
the common `Game` interface. `Reset(seed)` starts a fresh playable session;
`Step(Input)` advances exactly one source-style 60 Hz frame; `Render(Frame&)`
provides bounded procedural draw commands; `GetStatus()` provides score, lives
or health, terminal flags, and a control note. There are no Unreal types,
Pygame imports, asset loads, persistence, threads, or unbounded event loops.

Directions use `Left/Right/Up/Down` and sanitized `AxisX/AxisY`. Zelda's sword is
an edge action: `FirePressed`, `ActionPressed`, or `JumpPressed`. The attack
executes before player movement, matching the source KEYDOWN order, and has the
source 18-frame cooldown. Pac-Man and Zelda accept one of those press events to
restart after win or game over; held buttons alone do not restart. Dungeon's
`ActionPressed` resets its prototype. The Daedalus adapter chooses/starts the
game instead of reproducing the Python standalone TITLE screen.

Snapshots are available through const getters. Internal boundary cases in the
native tests use a test peer, not an exposed mutable gameplay API. Zelda retains
four source enemies, at most 128 rocks and 16 collectibles; its actual repaired
session can create at most nine collectibles. Pac-Man has four ghosts and a
fixed 304-collectible array represented by a bounded vector. Render commands use
the shared 4,096-command cap. Animation phases are bounded.

## Historical baseline preserved rules and deliberate repairs

The following baseline predates the explicitly identified native polish above.
Its original-source facts and old verification pins remain historical evidence.

**Dungeon:** exact seven source rows, 40-pixel tiles, starting green 40x40 box at
`(80,80)`, 5 pixels per frame per digital axis, and X-before-Y movement. The source
is a movement prototype, with no enemies, score, or win condition; none was
invented. Repairs: the source's rows have different lengths and `is_wall` can
index beyond a row/map; missing cells and out-of-range positions are solid.
Collision checks all corners of the player box rather than only its top-left
point, preventing overlap with walls. Left-stick movement is an adapter
enhancement. Rendering missing cells as solid also fills the original blank
right-hand margin.

**Pac-Man:** all 31x28 source map characters and 304 dot coordinates are retained,
as are the 2.5-pixel player and 2-pixel ghost speeds, buffered directions, digital
direction precedence, dominant-axis stick directions, mouth cycle, four ghost
colors, 5% random-turn and 60% unfrightened-chase probabilities, 300-frame
frightening, source +10/+50/+200 scores, three lives and all-captured-ghost
respawn. `pygame.Rect` coordinate truncation is modeled before collision tests.

The source has defects that prevent its advertised loop:

- Player `(280,460)` and ghosts are positioned between cells, causing wall
  overlaps. They now start at the centers of those same source tiles: player
  `(290,470)`; ghosts `(290,230)`, `(250,290)`, `(290,290)`, `(330,290)`.
- The source maze has a 296-dot connected component and an isolated eight-dot
  ghost pen. Only the wall at column 9, row 14 is opened, without adding a dot,
  connecting every original dot. The checked-in map itself remains exact.
- The power-pellet branch requires a space character; there are no spaces.
  Four existing dots at `(1,1)`, `(26,1)`, `(1,29)`, `(26,29)` are promoted to
  fixed pellets. The total remains 304; an all-collectibles run scores 3,200
  before ghost captures rather than the original no-pellet 3,040.
- The 620-pixel map was clipped by the 600-pixel display. Native coordinates
  remain source pixels; the frame is 800x660 with HUD below the maze. Movement
  is bounded to the map rather than the source's larger blank display region.
- Restart now recreates dots and pellets; the source removes them from globals
  permanently. End-screen keyboard restart is repaired. A stacked collision
  consumes at most one life in a frame, and defeat cannot be overwritten by a
  simultaneous win. There is no new tunnel-warp mechanic.

Ghost direction choices are injected in source fixture cases. Runtime uses the
common portable RNG, with uniform direction shuffling, and does not reproduce
Python's seeded random stream or call-consumption order. Ghost respawn retains
the source's frightened-state behavior; it is not presented as original arcade
AI or ghost behavior.

**Zelda:** source Link spawn `(400,450)`, speed 3.5, six half-hearts, source 0.707
diagonal scale and two-level stick deadzone, directional attack rectangles,
18-frame attack cooldown, 45-frame damage grace, immediate sword collision,
octorok shooting/random movement, two-hit chasing moblin, near-player charging
armos, rocks at 2.5 pixels per frame, source four-enemy roster and positions,
initial three rupees and heart, +50 enemy score, 40% rupee drop chance, +10
rupee score, and heart +2 clamped at six are preserved. Map trees, rocks, water
and cave remain decorative, as in the source. **The shield is decorative in the
source; no damage-blocking shield mechanic was invented.**

The original key pickup branch is never exercised because no key is created,
so its win condition instead produces endless new moblins. The last of the
four original enemies now drops a key at its defeat location. Collecting it
after defeating the roster completes the existing win condition. The endless
moblin append is removed. Defeated enemies cannot reward twice, dead rocks are
removed the same frame, terminal states stop updates and rewards, and end-screen
keyboard restart resets health, enemies, rocks, pickups, key and messages.
Winning cannot overwrite death in the same frame. Bob animation wraps its phase;
the visual sine behavior is retained. RNG sequences and rare overload suppression
at the explicit entity cap are adaptations, not Python replay equivalence.

## Source tests and limits of evidence

`maze_source_oracle.py --desktop <Desktop> --write` regenerates
`maze_parity.txt` only after checking all three exact SHA-256 pins. Without
`--write`, it checks that regenerated cases equal the committed fixture.
It selects reviewed numeric class methods and `is_wall` through AST, then uses
controlled rectangle, key and random stubs. It does not import Pygame, launch
the source scripts, create displays, run their main/event loops or install
dependencies. The 239 source cases include exact map rows, safe wall lookups,
Pac movement/collision/ghost choice cases, and Zelda movement, attack rectangles,
enemy movement and projectile bounds. They do not claim equivalence of the
entire Python main loop or seeded RNG.

Native `maze_test.cpp` passes 288 checks, including those 239 source cases plus
the intentional repairs, damage/cooldown/score transitions, capacities,
terminal freezes, resets, finite bounded rendering and sixteen 3,000-frame
sessions. A complete native Pac traversal collects all 304 items with exact
3,200 score and a single win. That traversal isolates ghosts outside the map
to test movement/scoring solvability; live adversarial ghost play remains a
separate acceptance check. Zelda's native combat replay exercises the source
four-enemy health roster, final-enemy key, victory, and restart through actual
`Step` calls from controlled collision positions.

Local evidence: MSVC C++17 `/W4 /WX /permissive-` builds the native test, and both
the test and source fixture regeneration pass. Native tests are distinct from
Unreal UHT/UBT compilation, input/focus integration, and live gameplay. These
remain the Unreal owner's acceptance stages; no editor or second editor was
opened by this port work.

## Blender character handoff reference

No new art was created. All source visuals are procedural Python draw calls,
with no external sprites or meshes in these three scripts. Native rendering
preserves colors and silhouettes using the shared rectangles, circles, lines
and triangles; ellipses and multi-vertex polygons are approximated. It is not
a pixel-identical screen replay.

- Dungeon: an unadorned bright-green 40x40 player square against gray dungeon
  walls; no source character face, costume, or backstory exists. A character
  interpretation needs design selection rather than a claim of preserved detail.
- Pac-Man: yellow disk with directional animated mouth; red, pink, cyan and
  orange rounded ghosts with white eyes, blue while frightened. These reference
  recognizable branded characters. Do not label them original Daedalus art or
  presume permission for public branded asset distribution.
- Zelda: source Link has green tunic and pointed green hat, peach face, small
  black eyes, steel sword with gold tip and gray shield; enemies are red
  octorok, green/brown moblin and gray armored armos. These are explicitly
  Zelda-inspired branded identities. Blender should preserve the actual source
  references for scoped review while flagging provenance before public assets;
  it should not silently substitute a wholly different character.

For a later art binding, the gameplay needs directional walking/idle and sword
action with cooldown-driven attack state; ghost alive/frightened/color states;
Link health/invincibility flash and enemy alive/hit-flash/kind states. There is
no skeleton, rig, animation file, art license grant, Blender acceptance, Unreal
compile result, or live playtest approval supplied by this core port.

## Glowtrail power-window iteration — 2026-10-15, pootscoot-desktop-games

Source9f55ac5f adds one private const snapshot shared by Render/GetStatus: count
living frightened pursuers with positive timers and report their minimum timer.
Labels580,304/327 sit below grace280; terminal result320 is mutually exclusive.
This is source-layout reasoning, not native text-fit/screenshot evidence.
Captured pursuers freeze clocks; revival preserves them. A maximum/global timer
could suggest safety while another pursuer wakes. Timer1 expires in the next ghost
update before collision. The cue uses simulation steps, not wall-clock seconds.
Step/Reset/ghost/RNG/score/input/save bodies stay intact. Twelve static invariants
and source review pass; new compile/tests/native checks are deferred.

Deferred cases: none active; mixed living/dead/unequal clocks;300/2/1→0; pickup
refresh; all-captured revival; terminal suppression; repeated Render/GetStatus
versus identical state/RNG progression. Reuse existing maze access/Driver/input.
