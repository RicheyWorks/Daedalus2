# G104: Rivet Line

Contest gap G104 (Hephaestus, Oct 19 2026). G24 Ark Drydock counts rivets per seam, and each missing rivet costs that seam 10 strength. Until now nothing made the rivets. This is the line where they're headed.

Code: `daedalus-core/src/main/java/com/daedalus/world/forge/RivetLine.java`.
Tests: `RivetLineTest` (9 tests).

## Rules

| Rule | Value |
|------|-------|
| Tray | one rivet per hole: `plates × 4` (SKIFF 24, BARGE 40, LONGARK 56) |
| Ready | each rivet hits setting heat at a seeded moment, 1500–2450 ms (`SplittableRandom(seed ^ 0x51E7)`, 50 ms steps) |
| Window | 800 ms at setting heat |
| Seat | set before ready: SPOILED (it won't upset). Set after the window, or with fewer than 2 strikes: LOOSE. Inside the window, 2 strikes: SNUG, 3 or more: TIGHT. No set at all: SPOILED |
| Per seam | the TIGHT + SNUG count of that seam's four holes, in ArkDrydock seam order. The list goes straight into `ArkDrydock.Ark.rivets` |

`master(tray)` is the reference run: every rivet set the moment it's ready, three strikes each, so every seam gets 4 rivets.

## Brannoc on the line

- Every hole filled: "Every hole filled hot. She'll hold the void."
- A quarter or more spoiled: "You're hitting them before they glow. Wait for the colour."
- Three quarters or more good: "A few loose heads. Drill them out or the seams pay for it."
- Otherwise his npcs.json line: "Hull wants tempered rivets, not soft iron."

## Ties

- G24 `ArkDrydock.seamStrength` reads the rivet list directly. The test checks that two spoiled rivets cost seam 0 exactly 2 × 10.
- G19/G57 come first: temper the plates, then head the rivets, then launch.

## Engine

A rivet tray actor at the drydock slip: rivets glow up on their own schedule, the player sets each one with a dolly and strikes it, and the seam lights up when its fourth rivet seats. The Unreal binding belongs on UNREAL-QUEUE.md.
