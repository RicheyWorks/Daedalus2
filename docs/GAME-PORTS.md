# Source games into Daedalus: inventory and first port

This is a bounded source inventory, not a claim that every repository or game has been ported.
The first runtime pilot is **Minesweeper Retro: 8 by 8, 10 mines**. A second, engine-free
rules slice covers the actual Python ComputerPets care/ribbon game. Originals are preserved.

## What the source actually contains

Repository names and Python helper scripts do not establish a Python game. The inventory
used the first 100 accessible RicheyWorks repository entries, registered local projects,
and targeted source/manifests/tests/assets in the candidates below. It did not launch the
games, examine every ComputerPets variant, or audit all unrelated tools.

| Source | Verified implementation and reuse | Effort / disposition |
| --- | --- | --- |
| [minesweeper-pro](https://github.com/RicheyWorks/minesweeper-pro/tree/63156079e141bca2b0cd3a0f297bb6595b28c2d0) | Java/Spring and JavaFX; neighbor counts, reveal flood, flags, victory and score. Current GameService blob matches local older snapshot. | First small native board pilot. Challenge/powerups/adaptive/server features deferred. |
| [computerpets](https://github.com/RicheyWorks/computerpets/tree/8394667521edb4e2876658eae61b4aaee3145567) | Real Python 3.10+/PyQt6 virtual companion in `client/computerpets_client/life.py` and `play.py`; current remote and local relevant blobs match. Flagship Electron app and Java backend are separate. Care deltas, time decay and ribbon state are reusable. | Next small Python rules slice: one pet, Rui. Whole 221-species catalog and desktop-window behavior are substantial adaptations. |
| [BlackJackPro](https://github.com/RicheyWorks/BlackJackPro) | Java 21 pure core, Swing and libGDX/Android front ends. Shoe, legality, split/double/surrender/insurance, bankroll, seeded simulation and save tests; 24 palettes, 39 named characters and extensive dialogue. | Moderate rules/UI port. Richest existing human cast for later Blender work; retain one chosen cast and original payouts. |
| [sudokupro](https://github.com/RicheyWorks/sudokupro/tree/973c73a35f8659a17022232f0996d4ffb0095997) | Java 17 model/server and JavaFX client. `engine/live_engine.py` is an HTTP/WebSocket test client of the authoritative Java model. | Small/moderate board port, but not a standalone Python game. |
| [computerpets-siege](https://github.com/RicheyWorks/computerpets-siege/tree/f56f695) | TypeScript/React/canvas tower defense: three waves; Rui/Paint/Reed; costs, projectiles, damage, lives and treats. C# overlay remains a stub. | Moderate presentation/combat port. Fixed step is 1/60 second; spawn position/speed still use unseeded Math.random. |
| [ai-dungeon-master](https://github.com/RicheyWorks/ai-dungeon-master/tree/3a1ccd2db3bbe911d697861601b5e581a72581b7) | Java 17 RPG core, Spring service and Swing/CLI/Android clients. Combat, XP, quests, NPC disposition, companions, content packs and save rules. Character identity is written, with no supplied meshes/rigs found. | Large full port. **Astra/team-codex already owns native /v2 bridge PR46; do not duplicate it.** |
| [satellite-hacker](https://github.com/RicheyWorks/satellite-hacker/tree/93c9f05abec11dcf15789a0da2a344235b48803c) | Java 17/Spring/Redis/WebSocket signal puzzle and simulated bug-bounty rules. Dark static web interface. | Repair source baseline before port: invalid GameView Java and mismatched test API were found in inspected snapshot; WAVs are placeholders. |
| [HackAttack](https://github.com/RicheyWorks/HackAttack/tree/8c51c1f3403864f5438d856e779629e1700b5bf6) | Java socket/Swing/CLI challenge terminal. Seven simulated commands award 100 points once per globally shared flag. | Small terminal adaptation, shallow existing loop; separate Docker/vulnerable-container infrastructure from runtime. |
| [echoes](https://github.com/RicheyWorks/echoes/tree/30d3a9d0dac359c74cf3b355f9ac4228b41a1153) | Python workflow scheduler plus Rust filesystem/forensic framework. | Excluded: no game loop/characters identified. |

Except the explicitly verified current puzzle and ComputerPets heads, local source snapshots are bounded
observations, not assertions that every inspected checkout equals today's remote main.
BlackJackPro and ComputerPets have multiple active worktrees; no source checkout was reset.

## Runtime contract and pilot boundaries

DaedalusRealm targets UE 5.8. DaedalusLink is already a Runtime module with portable C++
cores, Slate views and `ADaedalusUsable` world interaction. The pilot adds new files only;
no existing hero, HUD, server, companion or audio source is replaced. The new usable actor
provides the existing E/Interact seam and its own board view; Claude places/binds it.

Unreal's built-in Python environment is **editor-only**, including the absence of gameplay
Python in PIE, Standalone and cooked executables. It is useful for asset/editor automation,
while these runtime rules belong in C++ and Blueprint presentation.
[Epic documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python)

The Minesweeper reference is `GameService.java` at
`63156079e141bca2b0cd3a0f297bb6595b28c2d0`, blob
`30e6e58ff5d0d3795bb64a209c82342ed227f605`.

- Mine placement happens **before** the first reveal. Desktop start protects the configured
  center cell and its 3x3 neighborhood; a dense board falls back to protecting only that cell.
  The pilot defaults to center (4,4). Its reset keeps the configured safe cell; the source
  desktop restart instead passes (0,0). This deliberate UI difference is exposed.
- Reveal floods zero neighbors without crossing flagged cells; mine hit loses with score zero.
- Victory means all safe cells revealed **or** every mine correctly flagged with no wrong flags.
- Score is `max(150 * mines - floor(elapsed_ms / 500), 0)` for the non-challenge pilot.
  Time begins at board creation, including time spent viewing the board.
- Terminal games ignore later actions. Invalid configuration leaves the previous board intact.
- Replay uses explicit row-major mine layouts and action timestamps. Portable deterministic
  generation replaces Java SecureRandom; **RNG outputs are not claimed bit-identical**.
- Account auth, multiplayer, Redis, analytics, leaderboards, adaptive mine counts, challenge
  lives, resurrection, shields, pencils, powerups and adaptive resizing are outside this slice.
  No server rewards, economy or NFT state are created by the local board.

`DaedalusMinesweeperCore.h` is standard C++17 with no Unreal dependency or exception requirement.
The additive actor/view exposes runtime actions for Blueprint and live acceptance. Portable
tests and source replay are evidence for rules, not evidence of UHT/UBT success or gameplay.

The Python follow-on is `DaedalusPetCareCore.h`, with explicit care actions, injected decay
time/random draws, ties-to-even numeric rounding, and a ribbon chase that applies one play
reward regardless of catch/arrival order. Its source oracle executes the pinned original
Python modules without Qt or GUI startup and checks twelve dependency blob hashes. Dialogue,
species catalogs, civil-clock selection, assets, persistence, entitlements and Unreal pet
actor/animation bindings remain outside this rules slice. The source rounds to integers on
every 33 ms application decay call, which freezes ordinary per-frame aging; this behavior is
preserved, with offline elapsed decay tested. Changing cadence requires a deliberate later
adaptation. This is a rules port, not a finished in-world pet.

## Blender: preserve Rui's identity first

Rui is the existing red panda: russet body, cream facial mask, dark legs and a large ringed
tail. Preserve bamboo snack and ribbon-pounce behavior. Relevant source is
[species.py](https://github.com/RicheyWorks/computerpets/blob/main/client/computerpets_client/species.py)
and the procedural Python drawing, not a new unrelated mascot. No supplied Blender mesh,
FBX/GLB/OBJ or rig was found in these inspected pet source trees.

The first model brief is one Rui character with idle, walk, sit/rest, eat, ribbon pounce and
hide/return states. Follow the existing Daedalus art brief: metres, applied scale, bottom-center
origin, -Y front, blocky/beveled style, <=6k creature triangles and 1-3 flat-color material slots.
Blender owns modeling/rigging; Claude owns import, binding, scale/collision/attachment checks
and live animation/gameplay acceptance. Existing runtime mob loading uses static meshes;
a skinned rig requires an explicit skeletal consumer and must not be declared working merely
because a GLB contains joints/clips.

ComputerPets notices say sprite/photo origins are unconfirmed and those images are not
offered under MIT until confirmed. Do not copy those pixels into production art. Root code
MIT versus Python package "All Rights Reserved" metadata also needs reconciliation before
distribution. This rules port creates no image assets or license-metadata edits.

Minesweeper has no source character/model to upgrade. Its visual identity is the grey
beveled tile board and classic number/flag/bomb presentation. Missing splash references
and empty audio files are not usable assets; no replacement character or sound is invented.

## Ownership, validation and handoff

The accepted team lanes assign native Unreal/editor/live builds to Claude/unreal-team;
cross-lane contributions use **draft PR + hub ping**. This work uses an isolated checkout
and new additive native files. Hub claims identify the scoped pilot and Python rules follow-on.
Active audio PR44 and Astra Dungeon Master PR46 remain separate.

Claude acceptance should record the exact PR head and:

1. Compile/UHT/UBT on UE 5.8, then place the new usable actor in a test area.
2. Enter with existing Interact, play reveal/flag/new board, and close with Escape/button.
3. Exercise safe flood, wrong flags, both win routes, loss, terminal immutability and score.
4. Verify pause/input focus and closing/end-play cleanup against other Daedalus overlays.
5. Record gameplay/screenshots and standalone or cooked runtime proof separately from native tests.

No editor is leased, restarted, imported into or taken over by this port author. Blender
availability and Claude live acceptance are handoff dependencies; a queued/requested owner
is not the same as confirmed acceptance. See PR validation notes for measured evidence.

Validation on 2026-10-13: installed MSVC 19.44, C++17 with `/W4 /WX`, and CTest **2/2**
passed. Minesweeper passed **124/124** checks over eleven Java-source layouts and 41 actions;
Rui care passed **1963/1963**, including 1954 executed Python cases. All six new plugin
source files passed preflight with zero errors. Independent review checked the relevant
installed UE 5.8 headers and fixed pawn-replacement pause/input cleanup. CI adds GCC/Clang
ASan/UBSan and MSVC fixture replay. None of this is UHT/UBT or live gameplay evidence.
The board supports mouse/keyboard play and gamepad entry/exit; full gamepad tile navigation
is not implemented. The local overlay is standalone-only, with no multiplayer replication.

Suggested remaining order: complete this board's live acceptance; bind Rui care/ribbon and
one verified character; then Blackjack one table/cast, Sudoku, Siege; repair Satellite before
porting it. HackAttack is an optional terminal attraction. Follow Astra's existing RPG bridge
instead of reimplementing that service. None of those follow-ons is claimed fully ported here.
