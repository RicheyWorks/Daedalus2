# Throwable sports (WZ25) - contest gap G11

Owner: art-master-flex. Scoring core for the `Prop_Sport_*` throwable props from `tools/blender/voxel_props.py`. Separate from the Dodge Ball arcade cabinet.

- Core: `daedalus-core/src/main/java/com/daedalus/world/sports/ThrowableSports.java` (pure, JDK-only, deterministic per seed).
- Data: `data/sports/throwables-v1.json` (16 balls, catch/basketball/baseball rules).
- Test: `daedalus-core/src/test/java/com/daedalus/world/sports/ThrowableSportsTest.java` (12 tests).

## Games
- **Catch**: chance = 0.5 + 0.5*skill - ball difficulty - 0.015/m, 0 past 30 m. 1 point per catch, +1 on every 3rd catch in a row.
- **Basketball**: chance = (0.85 - 0.06/m) * (0.6 + 0.4*skill), max 12 m; 2 points, 3 from 6.75 m out.
- **Baseball/softball**: swing offset ms: <=25 home run, <=60 double (early) / single (late), <=110 foul (no strike-out on fouls), else strike. 3 strikes an out, 3 outs an inning; runners advance by the hit's base count.

## Daedalus tie-in
Companions and pets join island festival games: a pet catcher gets +0.15 on fetch balls (frisbee, tennis, soccer, beach, dodgeballs), so a Kennel Isle dog is a real teammate.

## Note for the prop owner
`voxel_props.py`'s `throwable` flag tests `"Ball" in name`, so `Basketball`, `Volleyball` and `Dodgeball_*` (lowercase "ball") come out `throwable: false`. This data file lists them explicitly; the flag fix belongs to the prop owner.

## Later (editor)
Hoop/glove/bat actors call the core; queued in BOARD\UNREAL-QUEUE.md.
