# Battlefield ecology: demo and benchmark (ADR-061)

Run after `mvn -pl daedalus-core package`:

```
java -cp daedalus-core/target/classes com.daedalus.world.battlefield.BattlefieldDemo docs/battlefield/demo.png
java -cp daedalus-core/target/classes com.daedalus.world.battlefield.BattlefieldBench 256 300
```

The demo is a deterministic encounter (seed 42, 40x30 cells of 1 m). U is the squad, T is the threat, C is the chosen
cover and * is fire:
1. Contact: the squad picks cover at the wood's south-west edge (1250, 1650).
2. A blast lands on that cover; the crater is bare and its rim is alight, so cover moves to (1250, 1150), north and
   away from the flames.
3. The fire spreads downwind for a few ticks.
4. Twenty years later the burn scar has regrown up the meadow -> scrub -> pine -> oak ladder.

`demo.png` shows the four frames.

## Latency on BLACKBEARD (256x256 grid, burning, 300 iterations)

| operation | median | p99 |
|---|---|---|
| tick | 303 us | 532 us |
| bestCover, 15 m radius | 295 us | 493 us |
| concealmentBetween, full diagonal | 2.8 us | 6.9 us |
| DBE 1 write + read | 824 us | 2920 us |

All of these fit easily inside the director's ~1 s decision budget (ADR-060), and none of them run on the frame path.
