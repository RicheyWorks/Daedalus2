# ADR-055: Creatures from the art library, and fast incremental Unreal builds

Status: accepted, 2026-10-12

## Why

Richmond: "the building in unreal needs to advance significantly we have deployment dates to hit we have to speed
up." Two gaps stood out. The world had the Blender team's 97 shipped creatures sitting unused while foes were still
grey cones, and every C++ change cost a six-minute BuildPlugin.

## Decision

**Creatures are assembled, not imported twice.** A shipped `Mob_<Name>` is a set of part meshes with offsets baked
in: one shared origin, bottom at z = 0, front toward +Y. `DaedalusMob::Build` finds the parts under
`/Game/Daedalus/Art/Mob/<Name>` (asset registry, cached), attaches them untransformed under one component turned
-90° to face +X, and returns the model height. A newly shipped creature needs no code.

**Foes wear their art.**
- BLIGHT_SLIME → `Mob_BlightSlime` ×1.7, SHARDBACK → `Mob_Shardback` ×1.35, DUST_WISP → `Mob_DustWisp` ×1.6,
  STONE_KNIGHT → `Mob_StoneKnight` ×1.
- The crystal stays as the root and collision shape, hidden. Hits, sight lines, A* routes and the harness's numbers
  are unchanged.
- A small inverted crystal over the head keeps the kind's colour and the orange telegraph; the body swells as it
  winds up, flinches when hit, and shrinks away when it dies.
- The art sits on the ground under the hovering collision shape; the wisp floats, centred on it.
- With no art shipped, the crystal shows as before.

**Wildlife.** `ADaedalusCritter` grazes, wanders a few metres at a time and drifts back toward home, turns away
from ledges, walls and trees (the A* port's step-up and step-down limits), and bolts from the hero when shy (cows,
horses, caribou, bears, crocodiles and tapirs only look). Far animals think once a second. The world dresser puts
out herds of 1–4 on suitable ground: meadow animals on grass, lizards, jerboas, scorpions and crabs on sand,
mountain goats, marmots, snow foxes and caribou on stone and snow. They're placed nearest the start first, up to
`MaxCritters` (60).

**Fast builds.** `unreal-job.ps1 -Start -Fast` runs `setup-unreal.ps1 -Build -Fast -Open`:
- it mirrors Source, Content and Resources over the compiled plugin, keeping Binaries and Intermediate;
- it builds only the editor target (`Build.bat UnrealEditor Win64 Development -Project=…`), straight into the
  plugin's Binaries;
- a compile error stops it; a locked DLL says Unreal is still open; anything else falls back to the full
  BuildPlugin.

## Proven

- The first fast run compiled all 17 plugin files clean in 95 s (versus about six minutes for BuildPlugin, which
  builds the game target too). Its link failed because the editor was still open; see AUTOMATION-LESSONS.
- Scenario `wild`: herds out, several species, every animal built from shipped parts, wandering, a shy one bolting,
  and all four foe kinds wearing art.

## Found: the art library would render grey in a packaged game

The live log warned for every Mob material: "missing usage flag Nanite! Default Material will be used in game."
All 1588 material instances in the library are parented to the Interchange plugin's `MI_Default_Opaque_DS`. Its base
`M_Default` has no Nanite usage flag, and engine content can't be saved, so the editor sets the flag on the fly but
a packaged build draws them in the default material. This blocks deployment.

- The project now owns `/Game/Daedalus/Materials/Gltf/M_Default` (with Nanite and instanced usage) and its
  `MI_Default_Opaque_DS`.
- **New imports** are moved onto it by the pipeline (`sides.UNREAL_IMPORT`). The judge rejects any material still on
  the engine plugin's base, and a stand-in canary (`engine_parent`) proves it can say no (e2e 21/21).
- **The 1588 already shipped** are moved by `daedalus_nanite_materials.run()`. It writes every old parent to
  `Saved/Daedalus/nanite-materials.json` before changing anything, so `undo()` restores them. This runs once
  Richmond OKs the bulk change.

## Held

- **Legs that walk.** Parts pivot at the model origin, so a leg can't swing about its hip yet. That waits on the
  Blender team shipping per-part pivots (or sockets).
- **Birds and fish.** They wait for flight and water: the dresser places land animals only.
