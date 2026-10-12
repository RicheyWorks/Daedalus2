# Blender team brief: assets for Daedalus

Updated 2026-10-12. From Claude (Unreal side). You build in Blender; Claude ships your work into Unreal with
the asset pipeline and checks it in the game.

## The world, in one paragraph

The biggest world in the galaxy was hit by a meteor. Its pieces float inside a bubble like a fishbowl globe, and
people live on them: dig for resources, build like Minecraft, help each other, Animal Crossing warmth. Arks (flying
ships) can latch onto pieces and tow them together. Everything is blocky: **one cube = 1 metre**. Halo-style
combat, Zelda II sword play, Ghost hover bikes.

## Set up (once per machine)

1. Install the Claude Blender Connector: <https://github.com/RicheyWorks/claude-blender-connector>.
   - Close Blender, then in PowerShell run:
     `irm https://raw.githubusercontent.com/RicheyWorks/claude-blender-connector/main/install.ps1 | iex`
   - Or go to Releases → `claude_blender_bridge.zip` (Blender: Edit → Preferences → Add-ons → Install from Disk,
     then enable it) and `blender-connector.mcpb` (double-click, install in Claude).
   - Check: in Blender's 3D Viewport press **N**, then open the **Claude** tab. It should say *Listening on
     127.0.0.1:9876*.
2. Blender 4.3+ (tested on 4.3.1 and 5.2).

## Rules every asset must follow (the pipeline's judge checks these)

| Rule | Why |
|---|---|
| **Metres, 1 Blender unit = 1 m = one cube.** Apply scale (Ctrl+A → Scale) before export. | The judge compares sizes in cm after import; unapplied scale gets baked per object and fails |
| **Origin at the bottom centre** (where it stands on the ground). | Things are placed on cube tops |
| **Facing −Y in Blender** (Blender's front view). | Unreal's forward after the Y/Z swap |
| **Modifiers are fine**: they are applied on export. | |
| **Triangle budget:** props ≤ 3k, creatures ≤ 6k, vehicles ≤ 12k, buildings ≤ 15k. | A metaverse full of players |
| **Materials: 1 to 3 slots, flat colours (vertex colour or one base colour each).** No image textures yet. | Matches the voxel look; the judge counts slots and they must survive import |
| **Names:** `Kind_Name`, no spaces: `Prop_Lantern`, `Mob_SporeHound`, `Veh_Warthog`, `Tool_Pickaxe`. | The pipeline names the Unreal asset from it |
| **One asset = one collection** named like the asset; put helper objects outside it. | The pipeline exports by object list |
| **Blocky style:** cubes and bevelled boxes; no smooth sculpts. | The look |

## What to build, in priority order

### 1. Tools and hands (needed now: digging just went live)
- `Tool_Pickaxe` (≈ 0.9 m long, wooden handle, stone head). Then `Tool_Pickaxe_Iron`, `Tool_Pickaxe_Gold`,
  `Tool_Pickaxe_Starmetal` (glowing cyan), the same shape with a different head colour.
- `Tool_Shovel`, `Tool_Axe`.
- `Wpn_Blaster` (≈ 0.7 m, Halo-ish rifle silhouette, blocky), `Wpn_Sword` (≈ 1.1 m, Zelda II feel).

### 2. Ore and resource pickups (small, about 0.35 m, chunky gems)
- `Item_Coal`, `Item_Copper`, `Item_Iron`, `Item_Gold`, `Item_Crystal`, `Item_Starmetal`, `Item_ShieldCore`
  (glowing blue hex), `Item_Overshield` (gold).
- Colours: coal #34343A · copper #C8703A · iron #C9B49C · gold #F2C230 · crystal #A070FF · starmetal #7FE3FF.

### 3. Foes (replacing today's coloured cones)
- `Mob_BlightSlime` (low blob, green #59D940, ~0.8 m), `Mob_Shardback` (stony beetle with crystal back spikes,
  ~1.3 m), `Mob_DustWisp` (floating pale wisp, ~0.7 m), `Mob_StoneKnight` (dark armoured knight, ~2.4 m).
- Each needs a clear **front**; separate objects for the parts that move: `_Body`, `_Head`, `_ArmL`, `_ArmR`,
  `_LegL`, `_LegR`.

### 4. Vehicles
- `Veh_Ghost`, the hover bike (≈ 2.6 m long, purple #5C389E, twin guns at the front of the side pods).
- `Veh_Warthog`, a 3-seat buggy with a rear gunner turret (≈ 4.5 m).
- `Veh_Ark`, the flying ship that tows islands (≈ 20 m): hull, sails or balloons, **a big front grapple claw** as
  its own object (`Veh_Ark_Claw`).

### 5. The cosy town (Animal Crossing feel)
- `Bld_NewsBoard` (the town's notice board), `Bld_Shop`, `Bld_Cottage` (3 colourways), `Prop_Bench`,
  `Prop_Lantern`, `Prop_Mailbox`, `Prop_Well`, `Prop_FlowerPot`, `Prop_Fence` (1 m segment).

### 6. Sky and the bubble
- `Sky_MeteorChunk_A/B/C` (floating debris rocks outside the bubble, 5–20 m).
- `Sky_ShatteredPlanet` (the broken mother world seen from inside the bubble, huge, low-poly).

## How we talk: the handoff folder

Everything goes through one folder on Richmond's PC, which every bot and person can read and write:
`C:\Users\730ri\projects\bot-team\art\`

| File | Who writes it | What it is |
|---|---|---|
| `BRIEF.md` | Claude | This brief: rules and the asset list |
| `QUEUE.md` | everyone | The board: one row per asset, with its status |
| `<Kind>\<Asset>.blend` | Blender team | The work |
| `NOTES\<Asset>.md` | both | Questions and answers about one asset (optional) |

**The status flow in `QUEUE.md`** (change only the Status and Notes cells of your row):

`TODO` → `DOING (<who>)` → `READY` → `SHIPPED` or `REJECTED: <check that failed>` → (fix) → `READY` again

1. Take a `TODO` row: set it to `DOING (your name)`.
2. Save the `.blend` in `art\<Kind>\<Asset>.blend`, then set the row to `READY`. If Blender stays open with the
   connector listening, that's even better: Claude can export straight from it.
3. Claude checks the board, runs the pipeline (Blender export → Unreal import → judge) and writes `SHIPPED` (with
   the triangle count) or `REJECTED: <the failed check>` into the row.
4. Rejected: fix what the check names, then set the row to `READY` again.

Questions go in `NOTES\<Asset>.md`; Claude answers there. Richmond can relay anything urgent in chat.

## Need ideas or a reference?

Ask Claude in your session: "show me the foe list", "what colours does the world use", "how big is a cube". The
block colours are in `daedalus-core/.../export/BlockColors.java` of the Daedalus2 repo.
