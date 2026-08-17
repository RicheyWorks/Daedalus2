# ADR-016: Packed `MazeGrid` — declined; the remaining D2 win already landed

**Status:** Decided — **declined** (long[] rewrite) / **accepted** (nibble +
allocation-free `MazeGraph`)
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Resolves:** CLRS hit-list D2 remaining half ("pack wall bits into a
`long[]` inside `MazeGrid`"). The solver-index half shipped 2026-07-18.

## Question

D2's first half replaced `HashMap<Point,…>` in the solvers with dense
arrays (1.42–1.72×). The leftover was packing each cell's four wall bits
into a `long[]` so neighbor scans and `copy()` become word-parallel. The
`MazeGrid` javadoc already records that a parallel `boolean[][] visited`
was *slower* than the `Cell` flag it mirrored. Is the wall-bitset rewrite
a different story?

## What was measured

`docs/evaluations/BitsetGridEval.java` — core-only, this machine (Java
22.0.2, Windows 11, 24 CPUs), 2026-08-17. Median of 21 after 8 warm-ups.

Neighbor sweep of the production `MazeGraph` (after this slice: coordinate
`isOpen`, no `Point`) versus the same walk over an `int[]` of 4-bit masks,
plus `MazeGrid.copy()` versus `Arrays.copyOf` of that `int[]`. Generation
and Dijkstra are the denominators.

| size | mazegraph sweep | packed sweep | copy vs packed-copy | generate (backtracker / Prim's) | Dijkstra |
|---:|---:|---:|---:|---:|---:|
| 32 | 65 µs | 42 µs | 206× | 0.13 / 0.47 ms | 0.39 ms |
| 64 | 75 µs | 191 µs | 144× | 0.63 / 1.0 ms | 0.47 ms |
| 128 | 222 µs | 65 µs | 23× | 2.3 / 3.2 ms | 1.6 ms |
| 256 | 957 µs | 509 µs | 32× | — | — |

(64² packed-slower is JIT noise; 128–256 are the useful rows.)

A packed sweep is a couple of hundred microseconds faster at the sizes the
API serves. `copy()` is tens of times slower than a memcpy — and still a
fraction of a millisecond against a **2 s** living tick. Dijkstra at 128²
is 1.6 ms; shaving 150 µs off the neighbor walk is a 10% footnote on a
path that is not the bottleneck.

The rewrite would also replace `Cell[][]`, which every generator, the
breeder, the sealer, and the plugin SPI touch via `grid.cell(...)`.

## Decision

**Decline the `long[]` `MazeGrid`.** Same honesty as the visited-array
removal and as ADR-011: do not ship a textbook packing for a quantity that
is already cheap.

**Keep the two cheap D2 leftovers that do pay without a new representation:**

- `Cell` stores walls in a nibble, not an `EnumSet`. Four bits were an
  object per cell.
- `MazeGraph.neighbors` walks `MazeGrid.isOpen(row, col, dir)` and integer
  coordinates. The class javadoc already claimed allocation-free; the
  method still boxed a `Point` per hop. That is now true.

Those keep `cell()` as the generator API and make the graph seam match its
own comment.

## Re-fire

Re-measure, do not assume, if any of these become true:

- generation or `copy()` is measured as the bottleneck of a request (not
  of a 2 s tick)
- a consumer regularly serves ≥256² living mazes
- the `Cell` facade itself is removed from the generator SPI

Until then D2 is closed.
