# G57: Bellows Shift

Contest gap G57 (Hephaestus, Oct 19 2026). Before the Anvil and Quench (G19) you pull a blank, and the Caldera Forge firebed has to sit in that metal's working band. The bellows keep it there. ISLAND.md names them: "Great Forge, anvil ring, bellows (forgeox), quench tub". Drydock Master Brannoc Slagg tells every apprentice the same thing: "Forgeox on the bellows buys you time. Don't waste it."

Code: `daedalus-core/src/main/java/com/daedalus/world/forge/ForgeBellows.java`.
Tests: `ForgeBellowsTest` (11 tests).

## Rules

| Rule | Value |
|------|-------|
| Shift | 120 ticks of 250 ms (30 s) |
| Firebed start | 600 °C |
| Bed loss per tick | `(heat − 20) / 40`, never below 20 °C ambient |
| Caldera draught | seeded `SplittableRandom(seed ^ 0xBE11)`, a gust on about 1 tick in 12, −30 °C |
| Pump | +30 °C × (100 + 15 × forgeox) / 100. At most 2 oxen, matching livestock.json `forgeox_bellows` (the test reads it) |
| Working band | the G19 metal's `targetC ± bandC` (copper 700±45 … starmetal 1100±25) |
| Cinder | heat above `targetC + 3 × bandC`: −1 of 3 coal and −120 °C. When the last coal goes, the fire is out and the bed cools 40 °C a tick |
| Tier | in-band per mille: STEADY ≥ 850, WARM ≥ 600, FITFUL ≥ 300, otherwise COLD |
| readyToPull | the fire is alive and the bed ends the shift in band |
| forgeSpeedPm | 1000 + 150 per ox (ISLAND.md: +30% with both head) |

`steadyHand(plan)` is the bellows master's input: pump only when the bed would otherwise fall below target. With it, copper and bronze hold STEADY on every seed. Steel tops out at WARM without help. Starmetal stays FITFUL or COLD unless the oxen work, which is what "buys you time" means in play. Pumping every tick throws three cinders and kills the fire.

## Ties

- G19 TemperForge: same metals and bands. A STEADY shift leaves the blank ready to pull.
- G42 q_forge_temper: forgeox must be watered and fed to work (livestock.json `requires`). The host passes in how many oxen are working.
- Brannoc's shift-bell lines live in `ForgeBellows.line`.

## Engine

The host owns the plan and judges the pump inputs it receives. A bellows actor on Prop_ForgeBellows_Basalt drives the pump, the firebed glow follows the heat, and a forgeox animation plays while it works. The Unreal binding belongs on UNREAL-QUEUE.md.
