# G87: Forge Commissions

Contest gap G87 (Hephaestus, Oct 19 2026). This is the Great Forge's order board. The anvil (G19) and the grade sheets (ForgeGrades) say how good a piece is; the board says who wants it and what they'll pay.

Code: `daedalus-core/src/main/java/com/daedalus/world/forge/ForgeCommissions.java`.
Tests: `ForgeCommissionsTest` (11 tests).

## The board

`board(day)` pins three commissions drawn from `SplittableRandom(day ^ 0xC0331)`. Each one has:

| Field | Draw |
|-------|------|
| Patron | Drydock Master Brannoc Slagg, Quartermaster Hesper Coalhand, Old Keeper Ysolde Anvilward, Ottar Flintwick (Kennel Isle warden), Captain Mira Sootvane of Storm Anchorage |
| Weapon | SWORD or BLASTER (ForgeGrades) |
| Metal | copper, bronze, iron, steel or starmetal: the metals the Great Forge tempers |
| Minimum tier | STANDARD 40%, FINE 40%, CRUDE 10%, MASTERWORK 10%. These are ForgeGrades' own tier names, and the test checks the thresholds 20/50/80/95 |
| Due | 1–3 shifts |
| Price | metal price (12/18/26/40/90) × tier factor (60/100/150/250%), plus 25% for a one-shift rush |

## Delivery

`deliver(order, piece, shiftsTaken, regard)` is pure:

- Wrong weapon, wrong metal or temper below the minimum: no pay, regard −3, and the patron complains.
- Late: half the price, no tip, regard +1.
- On time: the full price plus a tip of `price × (temper − minimum) × (50 + regard) / 10000`, regard +5. A patron who thinks well of you tips up to three times what a cold one does.

`Ledger.record` books the coins, moves the patron's regard (0..100, starting at 50) and counts paid deliveries. A master smith who dual-quenches at the anvil (`TemperForge.idealRun`) fills every order on ten days of boards. That test runs the real G19 anvil.

## Engine

An order-board actor at the forge workbench shows the three pins (patron portrait, weapon, metal, tier, due). Handing a graded piece to the patron calls `Ledger.record` and plays the patron's line. The Unreal binding belongs on UNREAL-QUEUE.md.

## C++ core (G98)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusForgeCommissionsCore.h` ports the board to header-only C++17 with no Unreal types. It contains `CommissionBoard`, `Deliver`, `CommissionLedger`, patron titles and lines, and `Encode` (the CMS 1 order line and the CMD 1 delivery line), and it uses ForgeGradesCore for the `Grade` sheet. `core-test/forge_commissions_core_test.cpp` passes 7 checks under MSVC /W4 /WX and g++ -Werror with ASan/UBSan. Its `--write` plays 100 seeded days into one running ledger and writes `forge_commissions_parity.txt` (300 deliveries, with every verdict represented). `ForgeCommissionsParityTest` replays the same days in Java and compares the two line by line. Java gains `Commission.encode()` and `Delivery.encode()`.
