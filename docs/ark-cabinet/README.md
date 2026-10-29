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
| `signal` | The Signal Web | G413 `SignalWeb` | Hex on a 3x3 web |
| `net` | The Net Mending | G419 `NetMending` | Dots and Boxes on a 2x2 net |
| `cargo` | The Cargo Shuffle | G422 `CargoShuffle` | solo Rush Hour style 6x6 hold, 3 moves |
| `blocks` | The Hold Blocks | G426 `HoldBlocks` | solo Klotski 4x4, moves like `BD` (block, R/L/D/U) |
| `ferry` | The Ferry Watch | G412 `FerryWatch` | solo, 3 crew + 3 raiders, 2-seat ferry, loads like `1,1` |
| `cube` | The Signal Cube | G435 `SignalCube` | solo pocket cube from a fixed scramble, turns like `R`, `U2`, `F'` |
| `masts` | The Four Masts | G432 `FourMasts` | solo Hanoi, 4 sails on 4 masts, moves like `1,4` |
| `crawler` | The Deck Crawler | G409 `DeckCrawler` | Langton's crab on a 21x21 deck, 300 steps; `1`/`10`/`100`/`back` |
| `hoards` | The Two Hoards | G354 `TwoHoards` | Wythoff, hoards 5 and 9 (up to 30 each); `1,k`, `2,k` or `3,k` for both |
| `skittles` | The Skittle Row | G411 `SkittleRow` | Kayles, rows 3, 5, 7 (up to 40 skittles); `row,spot,count` with count 1 or 2 |
| `galley` | The Galley Stack | G428 `GalleyStack` | solo pancake flips, 6 plates (2 to 8); type `k` to flip the top k |
| `pegs` | The Peg Board | G366 `PegBoard` | solo peg solitaire on the 15-hole triangle (side 2 to 5); type `from,to` |
| `lock` | The Lock Pegs | G362 `LockPegs` | solo Mastermind, 4 pegs in 6 colours, 10 tries; type e.g. `1122`; Knuth hints open any lock in 5 |

The cabinet plays seat 2 itself using each piece's own exact solver, so these default boards are
kept small enough for perfect play.

On bigger Chalk Grid, Hammock Rows and Signal Web boards (past each solver's cap) the cabinet uses a
one-ply lookahead: it takes a move that wins at once, else blocks the other side's immediate win,
else plays the first free move. It does not plan further ahead.

Solo games (Cargo Shuffle, Hold Blocks, Ferry Watch, Signal Cube, Four Masts) count solving as a win for
player 1. Their hints come from the piece's own shortest plan or solve, except Ferry Watch and Four
Masts: those pieces only plan from the start, so the adapter runs a small breadth-first search from the
current position using the piece's own safety rule (Ferry Watch) or the stacking rule (Four Masts, capped
at 65536 states). The merged pieces are unchanged. The Deck Crawler is a watch-the-pattern toy: the
show ends at its step budget or if the crab reaches the deck edge.

## How to play

Build `daedalus-core` the usual way, then:

```
java -cp daedalus-core/target/classes com.daedalus.world.ark.cabinet.ArkCabinetDemo          # keyboard play
java -cp daedalus-core/target/classes com.daedalus.world.ark.cabinet.ArkCabinetDemo --demo   # attract mode
```

Keyboard play: type a game id from the menu. You are player 1 (X, the first seat); the cabinet is
player 2 (The Cargo Shuffle is solo: solving it is a win). Each game prints its move format (square, post, cord, column or tray number, `row,col`, or
a crate letter and start such as `B4`). Type `hint` for the cabinet's suggestion, `quit` to leave.

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

`ArkCabinetAutoplayTest` plays every slot cabinet-vs-cabinet to its end and checks Two Hoards and Skittle Row perfect play against brute-force game trees.
