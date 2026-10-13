# DCS 1: cast scripts, what a realm's NPCs say

Richey (2026-10-13): every realm has dialogue boxes; old school FF1 windows, new school Animal Crossing bubbles.
The words come from one file per realm, `Content/Casts/<realm>.dcs`, one script per character of REALM-CASTS.md.

## Where it lives
- `DaedalusCastScriptCore.h`: `Cast` (parser), `Conversation` (place + flags, one-line Save/Restore). Pure C++17;
  `core-test/cast_script_test.cpp` 35/35 plays the quest chains.
- `ADaedalusTalker` (Public/DaedalusTalker.h): an NPC actor; Interact talks through `ADaedalusHero::Speak`; the choice
  comes back through `OnDialogueChoice`; flags a script sets are shared per cast per world (the Echo Choir sings once
  the Curator's `heartstone_done` is set). `Progress` is the save line. Art `Mob_<cast>_<who>` when Sol's export
  shipped (spaces and dashes to `_`), a labelled block until then.
- Casts shipped: gallery-city (12), parcels (12), bricks (12), labyrinth (12). The 8-bit realm keeps its DRR `npc` lines.
- Play scenario `cast`: Curator Vell's three talks (decline, accept, finish) and the Choir hearing the flag.

## The format
```
DCS 1
cast GALLERY-CITY
who Curator Vell                 a character; its script follows until the next 'who'
voice 3 0.95                     pitch 0..11, rate 0.5..2 (default from the name)
step start                       the script runs from 'start' each talk
if heartstone -> waiting         at a step's start: a flag set earlier jumps elsewhere
say ...                          a line; the box pages it
ask Will you? | Of course=accept | Not now=later      up to four choices, each naming a step
set heartstone                   a flag on this character (and, through the host, the cast)
goto other                       jump
end                              the talk closes
```
Every goto / if / choice target must exist; a script needs `start`; a step can't be empty. Refusals: "line N: why".

## Open
- Placement in the worlds is an import turn (Sol's casts + my layout pass); scripts are ready before the models.
- Rewards named in lines (a Frame Plate, honey, a plate) are words until the realm's inventory Intent runs them:
  the talker will emit `give:<ID>` through the hero's satchel in the next slice.
