# Rigs 2026-10-30 (blender-team; Buffffff 59376 and the Prismheart fun-round lane)

Headless segment rigs for the figures that were flagged "rig pending". Built by `tools/blender/games/game_items.py --game rigs_20261030` using the kit frame/mover split (`K.split_movers`). Everything is staged NOT READY in `bot-team/staging/games-20261030/rigs_20261030` (60 assets, 35 with socket sidecars).

**Shared Prism humanoid rig.** The root frame (torso and pelvis) carries `SOCKET_Hinge_<Part>` at each pivot. The movers are Head, ArmR, ArmL, LegR, LegL and a held prop (HeldR or HeldL), for 8 parts with the root.
- Rigged: Navigator Wren, Prismchime Warden, Railwright Ossian, Dockmother Imelda, Greenkeeper Talwyn, and the Safe, Bold and LayUp caddies.
- Pose library: Idle, Point, Shrug, Cheer, Chalk and Scold, as Blender euler degrees per hinge in the frame spec `poses`. The open pose (the hinge sidecar `open_*`) is Point.
- Daedalus hook: sidecar_cpp reads the hinges; the core verdict picks a pose id.

**Gantry crane.** The frame travels along Y on the rail.
- `SOCKET_Slide_Trolley`: slides X from -2.4 to +2.4 m.
- `SOCKET_Slide_Hook`: hoists Z from -6 to 0 m.

**Checks.** check_kit and sidecar_cpp report 0 problems (51 hinges, 26/26 tests).

**Sheets.** `segments.png` shows every rig part. `poses.png` is a preview only, not shipped: each figure in Point, plus Ossian in all 6 poses, posed with the same pivots. On review I reduced Cheer from 150 to 135 degrees because the arms crossed over the head.

The static `Mob_*` assets stay as they were. Rigged sets are named `<Mob>_Rig*`.
