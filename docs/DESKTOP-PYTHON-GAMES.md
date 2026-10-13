# Desktop Python games into Daedalus

The user-confirmed collection is on the assessed Windows redirected Desktop:
`C:\Users\730ri\OneDrive\Desktop`. `PythonGames/main.py` is the Dungeon Prototype;
21 loose scripts are beside the folder. **22 scripts represent 11 game families.**
Original files are reference inputs and are never edited by this port. No Git metadata
was found in the collection or its Desktop/ancestor directories.

## Latest source revisions

The user explicitly selected the last revision. Selection combines UTC modification
timestamps, revision filenames and code evolution; creation time alone is misleading
for copied/OneDrive files. Full SHA-256 pins are in `desktop-games-sources.json`.

| ID | Canonical source | Latest evidence | Port owner / backlog |
| --- | --- | --- | --- |
| pong | `pong (1).py` | May 1 04:32 UTC; adds controller to earlier `pong.py` | Pilot; root |
| dungeon | `PythonGames/main.py` | Sole script, April 25 | Maze slice |
| asteroids | `asteroids_pygame_ce.py` | May 2 08:17; later than `(1)`, adds controller | Shooter slice |
| football | `football_pygame_ce.py` | Sole script, May 2 | Sports slice |
| pacman | `pacman.py` | Sole script, May 1 | Maze slice |
| sega_shooter | `sega_space_shooter.py` | Sole script, May 1 | Shooter slice |
| shadow_ninja | `shadow_ninja_platform_fixed.py` | May 2 08:22; after numbered revisions, platform/spawn fixes | Platformer slice |
| star_shooter | `star_shootergpt1_fixed.py` | April 29; after all six other revisions, save-state restoration added | Shooter slice |
| dodge_ball | `super_dodge_ball_fixed.py` | May 2 08:24; after earlier tournament script | Sports slice |
| contra | `contra.py` | Sole file contains two full versions; later controller version is canonical | Platformer slice |
| zelda | `zelda.py` | Sole script, May 1 | Maze slice |

All are Python/Pygame; many source headers specify Pygame CE. The `(1)/(2)/(3)` and
`fixed` scripts are revisions, not extra games. The unrelated ComputerPets/Minesweeper
work is not a substitute for this collection. The native catalog contains these eleven games.
The user's next requested additions are SudokuPro and BlackJackPro: thirteen requested game
families in total, with the two Java additions assessed separately below.

## Shared runtime integration

Inspection of 67 native and 657 core/server files at baseline `ba17f688` found no generic
minigame registry. The new local catalog serves these ports only. World discovery and HUD
remain the existing `ADaedalusUsable::Nearest`, `Prompt` and `Use` seam; the new arcade
cabinet derives from that class. This eleven-game slice introduces no alternate world interaction
or Java service.
Portable C++17 `Game` objects share input, status and bounded drawing commands; Slate is
the Unreal presentation adapter. Original Python imports/display loops do not run in Unreal.

Each core update is a source-style 60 Hz frame. The driver accepts finite nonnegative
elapsed time, performs at most eight steps per call, preserves one-shot input edges and
drops excess hitch catch-up. Pause clears input/time debt; restart resets all session state.
Gamepad axes, keyboard directions and D-pad fields are separate. The presentation adapter
maps them per game so source-specific additive input and hat precedence are retained.

`ADaedalusDesktopArcade` is placeable and Blueprintable with `InitialGameId`, `InitialSeed`,
per-instance `CabinetId` and optional automatic advance. Blueprint bindings expose catalog,
select/restart, input, advance, pause, state, Star difficulty and native save/resume/leaderboard.
Do not drive a second clock while `bAutoAdvance` is enabled. The Slate host clears held inputs
on focus loss, bounds draw commands and defers close cleanup. The placeholder is an engine
cube; there is no imported cabinet mesh, character rig or new audio integration.

Star persistence is scoped to `Saved/DaedalusDesktopGames`: validated `DGS1` run state and
`DGL1` top-ten score/wave/difficulty records. Leaderboard writes reload/merge fresh records;
failed or malformed reads are refused. Failed run writes retain the pending payload, retry at
five-second intervals while advancing and block session replacements until success. Close/reopen
preserves the pending request, but RAM cannot survive actor EndPlay/process loss when the OS
refuses writing. New/restarted native runs deliberately retain the previous saved run; the Python
new-game path deletes it. The port never reads or overwrites the Python originals' home save files.
Per-game controls/features and intentional repairs are documented with each test family.

## Pong pilot parity and polish

The oracle reads the pinned latest `pong (1).py`, reviews/extracts only its numeric update
statements and executes those statements with synthetic keys/controller values. It never
imports Pygame, opens a display, runs the original loop or reads user save data.
Eleven source cases cover keyboard, both keys, analog/deadzone, sequential AI movement,
first contacts and scoring. C++ matches those states exactly.

Intentional enhancements: keyboard overshoot clamps to the playfield, collision direction
guards prevent repeated paddle/wall flip-flops, counters saturate instead of overflowing,
and the host supplies explicit pause/restart/close cleanup. No artificial winning threshold
is added to the source's endless Pong match. These repairs are tested separately from parity.

## Source identity and Blender handoff

The scripts draw procedural ships, characters, particles and maps; inspected code does not
load external sprite/model assets. No original Blender meshes or rigs were supplied.
Use source palettes/silhouettes as gameplay references: Contra's
blue-shirt/bandana gunner; Shadow Ninja's dark mask/outfit and sword/stars; football and
dodge-ball team colors; source ship/UFO/boss silhouettes. Pong and the dungeon prototype
need no invented character model.

CONTRA, Pac-Man and Zelda are explicitly branded source references. Their names/likenesses
are not claimed as original RicheyWorks characters; external asset rights/provenance were
not supplied. The native drawing adapter is a provisional source-faithful reference, not a
claim of cleared production art. Blender creates original production characters/cabinets and
records their provenance; commercial use needs original assets or verified rights. Claude owns
Unreal animation blending, materials, interactions and gameplay polish. A mesh export alone
does not prove rig compatibility, animation playback, collisions or gameplay. Existing Daedalus
limits remain metres, applied scale,
bottom-center origin, -Y front, blocky/beveled forms and bounded material/triangle budgets.

## Evidence stages and acceptance

The inventory and actual source hashes are recorded; native tests, source oracle cases,
Unreal UHT/object/reflection compile, plugin link/load and live gameplay are separate stages.
All six strict local MSVC suites passed. The five source fixture families contain 1,507 reviewed
source cases (11 Pong, 239 maze, 299 sports, 323 platformers, 635 shooters), with controlled
providers rather than whole original Python loops. Six cosmetic Star particle-count fields are
excluded from parity. Deterministic native replay uses its own RNG, not Python's random stream.
Isolated Unreal 5.8.3 UHT, actor/widget object compilation and actual generated reflection object
compilation passed; `desktop-games-unreal-compile.json` records the compiled source revision,
manifest and object hashes. This is not plugin linking/loading or editor/live play evidence.
Do not label all games complete merely because catalog entries exist. The backlog tracks
source-pinned, native-tested, runtime-wrapped, compiled and Claude live-accepted independently.

Claude/unreal-team owns editor placement, plugin load and live play. Blender owns agreed
character creation; a delivered message or broker receipt is not acceptance. No shared editor
lease, restart, second editor, source-script launch, installation or source-original edit is
performed by these ports. Active audio and other teams' RPG work remain separate.

Acceptance should cover every registered game: enter through Interact, select, play core
actions/scoring/win/loss, pause/resume, restart, switch games and exit; verify held/edge input,
controller/focus loss, pawn replacement and EndPlay. Record exact build head and screenshots
or gameplay evidence. Inspect latest-specific settings/save features where present. Source
defect repairs and any deferred host persistence/audio must be explicitly visible in handoff.

## Commercial cabinet requirement

The user's intended product is a purchasable NFT arcade cabinet with broad commercial reuse
of the user's own code and assets. `CabinetId` identifies a placed instance; game selection is
independent of it. Future entitlement and licensing terms need their own implementation and
review. This port does not change repository licenses or grant rights to third-party names,
characters or artwork. No token issuance, contract, wallet, listing, payment, sale or token gate
is implemented. Playtest access remains available without token ownership.

## Pilot and remaining effort

Pong is the smallest useful playable pilot: one arena, two paddles, a ball, score and controller
input, with no character rig or external asset dependency. It proves cabinet interaction,
input isolation, frame presentation and exit cleanup before character-heavy games are accepted.
The other native cores are available in the same catalog, but every game still needs live
acceptance against its latest-specific actions and repaired source defects.

| Work | Relative remaining effort | Evidence / dependency |
| --- | --- | --- |
| Pong cabinet pilot | Smallest | Core source parity; cabinet placement and live input/exit acceptance remain |
| Dungeon, Asteroids, Football | Small to medium | Procedural geometry and compact rules; no imported source meshes |
| Maze, Zelda, Sega, Dodge Ball | Medium | Map/collision or boss/tournament paths and game-specific controls |
| Contra, Shadow Ninja, Star Shooter | Larger | Compound actions, bosses, animation needs; Star settings/save/menu/leaderboard |
| Original Blender production art | Separate asset work | No supplied rigs; silhouette, materials, rig/animation budgets need owner acceptance |
| Multiplayer/world-screen cabinet | Separate runtime work | Current overlay is standalone-only and pauses its local world |

These are comparative scope estimates, not dates or staffing promises. Native rule tests do
not reduce rendering, physical-controller, rigging or multiplayer acceptance to a checkbox.

## Next Java additions: observed API facts

Keep Java authoritative for both games. The proposed C++ adapters perform asynchronous
requests, bounded validation, presentation and lifecycle cleanup, with per-session serialized
commands and cancellation/generation guards against stale responses. These are integration
requirements, not implemented functionality in this eleven-game PR. No Java rules are rewritten.

**SudokuPro**: [repository at assessed main](https://github.com/RicheyWorks/sudokupro/tree/973c73a35f8659a17022232f0996d4ffb0095997)
uses Java 17/Maven, Spring Boot REST and a raw WebSocket; JavaFX is a network client.
`GET /api/session` returns player identity, CSRF metadata and a WebSocket ticket. Native
REST/WebSocket HTTP Basic credentials are supported; mutating REST also sends the XSRF-TOKEN
cookie and named CSRF header. The alternative WebSocket ticket expires after 60 seconds and
is single-use. Keep credentials out of actor properties, save files and logs.

`POST /api/game/new` accepts difficulty 1..5 plus chaos/mirror/timeAttack settings and returns
the authoritative board. REST supports fetch, save, resume and bounded saved-list queries.
Moves, undo, redo and sync use `/ws/game?gameId=<encoded>`; there is no observed REST move
endpoint. A move includes row/column, old/new values and type, and Java stamps its source.
The protocol has no operation IDs: do not silently retry mutations after an uncertain response;
reconcile through sync/state instead. Bound boards to 81 cells and preserve server-owned timer,
givens, notes/variants and legal move projection. No service was launched in this assessment.
The assessed head's [CI run](https://github.com/RicheyWorks/sudokupro/actions/runs/38087377620)
was blocked before jobs by the account payment/spending limit, so it supplies no new test pass.

**BlackJackPro**: [repository at assessed main](https://github.com/RicheyWorks/BlackJackPro/tree/1ec1801ac635e62945072974cbe8c78398a17849)
has a pure Java `Engine`, Swing and libGDX/Android presentation. It builds Java 17 bytecode
with JDK 21. There is no implemented HTTP/auth/database/server API at this pin. Its engine
already provides bet/deal/hit/stand/double/split/surrender/insurance legality and commands,
outcomes, net results and statistics. A small Java facade is required before an HTTP bridge
can be useful; coordinate its ownership and authoritative source pin before implementation.

The facade must project visible cards, legal actions and authoritative results. Do not serialize
`Engine.dealer()` or `liveRoundState()` wholesale: these expose the hidden hole card and future
shoe. Each mutable Engine/Shoe session needs a single serialized command owner. Use only
simulated credits; no real-money/crypto wagering, wallet, cash-out or financial integration.
Local `BlackJackPro-buff` has substantial uncommitted core/UI/build changes beyond the clean
main pin and must be preserved. The assessed head's [CI run](https://github.com/RicheyWorks/BlackJackPro/actions/runs/37192929132)
failed build/test and UI jobs; cause is not established from the available job metadata.
Historical README counts are not current CI evidence. No Java tests or services were run.

Neither Java repository supplies imported Blender character rigs at the assessed pins. Existing
procedural cards/boards, palettes and personality data can inform an original cabinet brief;
new meshes and animation compatibility remain separately accepted art/runtime work.
