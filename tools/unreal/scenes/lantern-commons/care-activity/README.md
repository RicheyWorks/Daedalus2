# Optional garden care R12

The original plant quest remains0collect/1carry/2plant. Only after stage2, the
existing garden panel offers **Collect water**. Within2.4m of the small blue-topped
barrel, E carries water for the current session. It then offers **Tend the flower**:
E within2.4m of the original pink planter saves CareComplete, shows **Flower tended**
and reveals two additional bluebells around the unchanged original poppy. Existing
gardenkeeper guidance reflects whether water is carried or care is complete.

No new reward, reset, timer, shared inventory, chart edit or farming system. The
existing non-consuming E and its pause/settings/field/dialogue guards remain.
Barrel shifted within the owned care grouping to(-2700,-1500,20.15), separating
its input zone from the kiosk. Four imported designs/other assets are unchanged.

Persistence uses ONE additive CareComplete bool in the existing version1
SG_CommonsGarden and Daedalus_LanternCommons_Garden_v1 slot. Existing version and
planting stage schema are retained, and the original CommitGardenStage graph is
unchanged. HasWater is session-only: leaving before tending requires free water
recollection. Success is displayed only after SaveGameToSlot returns true. A
failure retains water and prior local completion, with a nearby E retry. No file
transactionality guarantee or reward duplication. Existing player save files were
only hashed for protection; no gameplay load/save API was invoked while building.

This is BUILT/COMPILED/SAVED, not runtime acceptance. The intended missing-field
default for old saves, actual E flow, bloom transition, UI and persistence have
not been exercised in Play/reload under the user's build-only direction. Feeder,
compost and apple crate still have no behavior. No reimports or new save system.
Five exact native graph recipes and saved owned Blueprint/SaveGame/map accompany
the receipt. Source reference correction: native typed Blueprint refPath requires
the full /Game/.../Asset.Asset identity; the shortened package path was refused
before the first graph tool ran, then only the remaining read was completed.
