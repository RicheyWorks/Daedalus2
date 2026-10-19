# Crossing the Storm Belt (Kennel Isle chapter, contest)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelArkVoyage.java`,
test `KennelArkVoyageTest`. Follows G107 The Muster at Hull Bay and uses its roster; odds are G61, posts gated by G37/G65.

## Story

The hull-plank ark lifted from Hull Bay on the third dawn at the latest. Between Kennel Isle and the far plates lies
the storm belt, the ring of weather the shattering left behind. The first arks crossed it with hounds on watch, and the
logbook (G92) says why: "the hounds drink first; they are the ones who find the springs."

Six legs, one trouble each:

| Trouble | Post that answers | Toll if unanswered |
|---|---|---|
| Boarding gust | hatch guard | 3 hull |
| Crewman overboard | rescue swimmer | 2 hull, 2 water |
| Dry casks | spring finder | 4 water |
| Jammed signal line | deck runner | 2 hull, 1 water |

The ark starts with 10 hull and 10 water and arrives if neither runs out.

### NPC lines

> Keeper Wren (leg 1): "Posts, everyone. The belt does not wait for the slow."
>
> Old Harl (gust held): "She did not even bark. The hatch held."
>
> Keeper Wren (empty post): "No hound on that post. We pay for it in planks."
>
> Old Harl (casks dry): "No spring finder, no water. Turn back while the hull still floats." (fail: the casks ran dry)
>
> Keeper Wren (arrival): "Land. Count the hounds first, then the planks."

## Mechanic

- `storms(seed)`: six seeded troubles.
- `cross(roster, troubles, seed)`: per leg, the hound on the matching post rolls once against its G107 post odds; an
  answered trouble costs nothing, otherwise its toll is paid. Stops at the leg where hull or water reaches 0.
- `crossingTheStormBelt(hounds, seed)`: the chapter. G107 muster first (fails with "the ark never lifted: ..." if it
  does not lift), then the crossing with fresh seeds.

## Later (UNREAL-QUEUE, behind GATE)

Storm-belt skybox, a leg tracker with hull and water bars, a hound callout per trouble (the G102 binding's drill
delegate can drive the bark/animation), and a leg-by-leg replay from the server's voyage.
