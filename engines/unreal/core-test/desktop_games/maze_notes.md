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
is a movement prototype, with no enemies, score, or win condition. The existing
native Threadlight chapter adds three ordered lanterns and an exit within that
room; it is an original extension, not source parity. It awards no score or realm
reward. Repairs: the source's rows have different lengths and `is_wall` can
index beyond a row/map; missing cells and out-of-range positions are solid.
Collision checks all corners of the player box rather than only its top-left
point, preventing overlap with walls. Left-stick movement is an adapter
enhancement. Rendering missing cells as solid also fills the original blank
right-hand margin.

### Selecting Threadlight circuits

The cabinet's focusable **Next circuit** button starts the next of the six existing
lantern orders, wrapping from circuit 6 to 1. The current circuit number appears in
the existing progress/status text. Restart and the original Action reset replay the
selected order. Switching is deliberate, never automatic on completion, and clears
the current lights, clock and optional trail. This is a desktop-only choice, not a
world Dungeon quest, save or reward.

`DungeonGame::NextCircuitSeed` converts any uint32 seed to a canonical next-order
seed in 0..5 rather than incrementing a possibly signed host seed. Slate rechecks
the active game and pending-save fence, then calls the existing `StartGame` path;
it returns play focus only after success. The actor's normal seed/input/pause
lifecycle is reused without new actor API or persistence changes.

`desktop_dungeon_circuit` / `dungeon_circuit_test.cpp` checks the six order choices,
full-width seeds, changed second lantern after Hall, fresh-circuit reset and
same-circuit replay via public input/Driver. It does not rerun the trail navigation
suite or establish native button, controller/focus or play-feel acceptance.

Strict serial single-TU MSVC C++17 passed 181/181 focused checks. The previous
trail/navigation and source-parity suites were not rerun; movement, lighting,
completion, timer and reset implementations are unchanged. Native acceptance is
still pending.

### Optional Threadlight trail

Shift / pad Y (also the existing V / LB aliases) toggles a quiet dotted route to
the lantern marked NEXT, then EXIT after all three are lit. The route starts off;
reset returns it to off. It never moves the player or lights a target. J/Space or
pad A/X still performs each interaction; K/Enter or pad B still resets the circuit.
Toggling alone does not start the clock. Once movement or interaction has started,
a toggle consumes its ordinary simulation frame. Completion freezes the trail
with the rest of the chapter until a deliberate reset.

A bounded four-neighbour search uses at most 140 player-sized anchors and checks
the full 40x40 box. An unaligned position connects safely to its lower grid anchor
by decreasing X then Y. Dots are drawn behind the hero and lanterns. The guide is
derived during rendering and has no saved data, RNG, auto-interaction, movement
rule or world Dungeon dependency. Pac-Man and Zelda remain unchanged.

`desktop_dungeon_trail` / `dungeon_trail_test.cpp` follows the rendered route using
ordinary movement across all six seed orders, explicitly lights each lantern and
EXIT, and compares guide-on/off progress. It also covers an unaligned connector,
wrong-order interaction, render purity, toggling, timer/reset priority, completion
and Driver pause/held-input edges. This focused portable check does not establish
native layout, controller or human navigation acceptance.

Strict single-TU MSVC C++17 passed 236/236 checks. The unchanged test compiled
against the exact prior Maze header at `0b1b95038` passed 14/28, with fourteen
expected failures; absent paths stop traversal sections early. No fixtures were
regenerated. The normalized Pac-Man/Zelda suffix remains identical (472 lines).

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
  simultaneous win. The source view retains its blocked outer boundary; native
  play's paired passage is described below.

Ghost direction choices are injected in source fixture cases. Runtime uses the
common portable RNG, with uniform direction shuffling, and does not reproduce
Python's seeded random stream or call-consumption order. Ghost respawn retains
the source's frightened-state behavior; it is not presented as original arcade
AI or ghost behavior.

### Glowtrail's paired passage

The two outer openings in row 14 now connect in native play. Walk through either
matching blue gate to emerge on the other side. Player and living pursuers use
the same 560-pixel maze period and keep movement overshoot; the 800-pixel frame
and sidebar at X580 are separate presentation space. No new action or mode is
needed. This is an original native extension, not source replay equivalence.

Only a whole quantized 16x16 collision box fitting row 14 may use the passage.
Adjacent walls and ordinary out-of-map lookups stay solid. Candidate positions
are bounded around the seam, so distant invalid test actors cannot fold into the
maze. Player turn probes, ghost choices and actual movement share that rule.
Ghost chase still compares ordinary coordinates; no new AI/pathfinding or RNG
draws are added.

Contact uses the original rectangle overlap plus the translated opposite-edge
rectangle for eligible actors. Pickups retain their strict 12-pixel Euclidean
radius with periodic horizontal distance in the passage. Map characters, all
304 dots, scores, lives, power/grace timers, one-lethal-hit settlement, respawn,
completion and seeded replay rules remain intact. Dead ghosts remain stationary.

Matching gate brackets render behind dots and actors; mirrored silhouettes make
the crossing continuous. The existing canvas clips the frame's left boundary.
A black gutter mask follows all actors and precedes the sidebar, clipping right
overflow with existing draw commands. No new native renderer, art or asset needed.

Pure-source helper calls explicitly disable both RepairDoor and UseTunnels.
The pinned fixture contents are unchanged; native defaults enable the repaired
maze and passage. Source-only evidence remains separate from native rendering,
physical input and human chase/escape acceptance.

`desktop_pacman_tunnel` / `pacman_tunnel_test.cpp` passed 108/108 strict single-TU
MSVC checks, including the 60 PAC-only pinned source cases in disabled mode.
Focused native cases cover two-way overshoot/probes, row/candidate fences,
quantized seam contact, ordinary off-passage contact, damage/capture/grace,
strict circular pickup distance and both edge dots once, unchanged RNG call
counts, dead actors, terminal/reset behavior and presentation/mask order/purity.
No broad maze suite, repeated full-map traversal, old-header proof, fixture
regeneration or engine/editor/native playtest ran for this extension.

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
