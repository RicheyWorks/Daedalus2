# Desktop maze and adventure ports

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

Directions use `Left/Right/Up/Down`, direct `PadLeft/PadRight/PadUp/PadDown`, and
sanitized `AxisX/AxisY`. Pac-Man merges direct hats with the existing digital tests,
retaining right/down last-test precedence and dominant-axis analog override.
`pacman_input_test.cpp` / target `desktop_pacman_input` checks the direct player
contract and a bounded 96-frame game/Driver route; no native Blueprint acceptance
is inferred. Zelda's sword is
an edge action: `FirePressed`, `ActionPressed`, or `JumpPressed`. The attack
executes before player movement, matching the source KEYDOWN order, and has the
source 18-frame cooldown. Pac-Man and Zelda accept one of those press events to
restart after win or game over; held buttons alone do not restart. Dungeon's
`ActionPressed` resets its prototype. The Daedalus adapter chooses/starts the
game instead of reproducing the Python standalone TITLE screen.

Pac-Man and Zelda's cabinet prompts name the physical bindings: pad A, Space,
Enter or R/Restart replays a completed/lost run with its original seed. Pad A,
Space or Enter also triggers Zelda's sword during play. Start keeps its existing
pause/resume role; no terminal retry binding or simulation rule was added.

Snapshots are available through const getters. Internal boundary cases in the
native tests use a test peer, not an exposed mutable gameplay API. Zelda retains
four source enemies, at most 128 rocks and 16 collectibles; its actual repaired
session can create at most nine collectibles. Pac-Man has four ghosts and a
fixed 304-collectible array represented by a bounded vector. Render commands use
the shared 4,096-command cap. Animation phases are bounded.

## Preserved rules and deliberate repairs

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

## Power-window display

Pacman's sidebar and status show how many living pursuers are frightened and the
ceiling seconds until the first of them recovers. Dead pursuers are excluded;
mixed timers use the shortest active timer. A steady final-second cue replaces
surprise expiry without changing the source 300-step effect, AI or collision rules.
Terminal results hide live countdowns. Presentation calls do not advance simulation.

`desktop_pacman_power` / `pacman_power_test.cpp` passed 34/34 checks with strict
single-TU MSVC C++17. It covers mixed/dead states, timer boundaries, a real power
pickup through 300 active steps, repeated presentation purity and future RNG/state.
A controlled MAX-instead-of-MIN timer variant failed seven checks as expected.
This offline evidence does not establish native layout or human playtest acceptance.

## Zelda lethal projectile settlement

After projectile cleanup, a lethal hit now ends the live step before overlapping
pickups can heal, award trinkets or grant a key. Nonlethal projectile pickups and
the existing pickup-before-enemy-contact order are preserved. A defeated run cannot
show positive health from a same-step heart; no collision/AI/reward rule is replaced.

`desktop_zelda_terminal` / `zelda_terminal_test.cpp` passed46/46 strict single-TU
MSVC checks. Small authored heart/trinket and last-enemy key fixtures use a real
2.5px rock arrival, plus nonlethal companions, cleanup, terminal freeze and fresh
replay/reset. The same test against the prior header passed40/46 and failed6
post-defeat pickup/health assertions as expected. No full maze suite, engine build,
editor or native gameplay was executed. Portable evidence is not runtime acceptance.
