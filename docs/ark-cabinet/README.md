# The Ark Games Cabinet (G493)

A player-facing arcade cabinet that bundles the most showable ark turn games behind one menu.
Source: `daedalus-core/src/main/java/com/daedalus/world/ark/cabinet/`. Source only; nothing is hosted.

## Games in this build

| id | Game | Wraps | Board |
|----|------|-------|-------|
| `chalk` | The Chalk Grid | G421 `ChalkGrid` | 3x3, three in a row |
| `hammock` | The Hammock Rows | G416 `HammockRows` | 4x4 rack, three in a line (Connect Four style) |
| `seeds` | The Seed Trays | G418 `SeedTrays` | Kalah, 3 trays of 3 seeds a side |
| `hardtack` | The Hardtack Bar | G414 `HardtackBar` | Chomp on a 4x5 bar |

The cabinet plays seat 2 itself using each piece's own exact solver, so these default boards are
kept small enough for perfect play.

## How to play

Build `daedalus-core` the usual way, then:

```
java -cp daedalus-core/target/classes com.daedalus.world.ark.cabinet.ArkCabinetDemo          # keyboard play
java -cp daedalus-core/target/classes com.daedalus.world.ark.cabinet.ArkCabinetDemo --demo   # attract mode
```

Keyboard play: type a game id from the menu. You are player 1 (X, the first seat); the cabinet is
player 2. Each game prints its move format (square number, column number, tray number, or
`row,col`). Type `hint` for the cabinet's suggestion, `quit` to leave.

## In-world hook

`ArkCabinet.ARCADE_NAME` and `arcadeDescription()` give the machine's name and sign text for the
ark's mess deck. Finishing any game completes quest `q_ark_cabinet` (`ArkCabinet.quest(game)`).

## Adding a game

1. Write an adapter implementing `ArkCabinetGame` (id, title, rules, legalMoves, play, toMove,
   over, winner, render, hint). Keep the live position in the adapter and call the merged piece
   for every rule and solver step; do not copy its logic.
2. Register it: `cabinet.register("id", "Title", "one-line pitch", MyGame::new)`, or add a line
   to `ArkCabinet.standard()`.
3. Add scripted-move tests for legal moves, an illegal move, a win and the hint.