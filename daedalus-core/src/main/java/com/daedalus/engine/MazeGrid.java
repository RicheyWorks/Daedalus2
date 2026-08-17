// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.Cell;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import java.util.ArrayList;
import java.util.List;

/**
 * The maze: a grid of {@link Cell}s, each holding its four walls, plus the start and goal the
 * whole stack routes between.
 *
 * <h3>There used to be a second copy of "visited", and it was not faster</h3>
 *
 * <p>This class carried a {@code boolean[][] visited} layer beside the cells, introduced with a
 * header promising "dramatically faster generation", a comment reading {@code ← THIS IS THE BIG
 * SPEED WIN}, and an {@code Arrays.fill} annotated "blazing fast primitive blast". Two things
 * were wrong with it. Nothing in production ever read it: every generator uses
 * {@code grid.cell(p).isVisited()}, and {@code grid.isVisited(Point)} — the fast path the array
 * existed for — had no caller anywhere in the repository (found by {@code mutants/gridteeth.py},
 * where removing the array's synchronisation was inert for exactly that reason). And the array
 * cost more than it saved: {@code markVisited(Point)} wrote both copies to keep them in step, and
 * {@code clearVisited()} did the primitive fill <em>and then</em> the full Cell loop anyway.
 *
 * <p>Measured before removing it, interleaved A/B at 300×300, best of five runs each:
 *
 * <pre>
 *                            with array   without
 *   recursive-backtracker      71.2 ms     57.5 ms
 *   prims                     115.8 ms     98.8 ms
 *   aldous-broder             859.8 ms    864.4 ms
 *   copy()                     51.5 ms     49.1 ms
 * </pre>
 *
 * <p>Removing it was never slower across eight paired runs, and it saves {@code rows × cols}
 * bytes per grid and per {@link #copy()} — which the living-maze tick performs every two seconds
 * per animated maze. Aldous-Broder is the honest control: dominated by its random walk, it does
 * not care either way.
 *
 * <p>What the removal actually buys is not the milliseconds. Two mutable copies of the same fact,
 * kept in step by one line in one method, is a correctness hazard whose failure mode is a caller
 * reading whichever copy happens to be wrong. There is now one visited flag, on the Cell, and the
 * grid-level accessors delegate to it — the public API is unchanged and the two views can no
 * longer disagree, which {@code MazeGridContractTest} pins.
 */
public class MazeGrid {
    private final int rows;
    private final int cols;
    private final Cell[][] cells;
    private Point start;
    private Point goal;

    public MazeGrid(int rows, int cols) {
        if (rows < 1 || cols < 1) {
            throw new IllegalArgumentException("Maze dimensions must be positive");
        }
        this.rows = rows;
        this.cols = cols;
        this.cells = new Cell[rows][cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                cells[r][c] = new Cell(r, c);
            }
        }
        this.start = new Point(0, 0);
        this.goal = new Point(rows - 1, cols - 1);
    }

    /* --------- Visited state: one copy, on the Cell. See the class javadoc. --------- */

    /** Marks a cell visited; equivalent to {@code cell(p).markVisited()}. */
    public void markVisited(Point p) {
        cells[p.row()][p.col()].markVisited();
    }

    /** Whether a cell is marked; equivalent to {@code cell(p).isVisited()}. */
    public boolean isVisited(Point p) {
        return cells[p.row()][p.col()].isVisited();
    }

    /** Clears every cell's mark — generators call this when they finish carving. */
    public void clearVisited() {
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                cells[r][c].clearVisited();
            }
        }
    }

    public int rows() { return rows; }
    public int cols() { return cols; }
    public Point start() { return start; }
    public Point goal() { return goal; }
    public void setStart(Point p) { this.start = p; }
    public void setGoal(Point p) { this.goal = p; }

    public Cell cell(int row, int col) {
        if (!inBounds(row, col)) {
            throw new IndexOutOfBoundsException("(" + row + "," + col + ") out of bounds");
        }
        return cells[row][col];
    }
    public Cell cell(Point p) {
        return cell(p.row(), p.col());
    }

    public boolean inBounds(int row, int col) {
        return row >= 0 && row < rows && col >= 0 && col < cols;
    }
    public boolean inBounds(Point p) {
        return inBounds(p.row(), p.col());
    }

    public void carve(Cell from, Direction d) {
        Point np = from.position().step(d);
        if (!inBounds(np)) return;
        Cell to = cell(np);
        from.open(d);
        to.open(d.opposite());
    }

    public void carve(Point a, Point b) {
        Direction d = directionBetween(a, b);
        if (d == null) {
            throw new IllegalArgumentException("Points " + a + " and " + b + " are not adjacent");
        }
        carve(cell(a), d);
    }

    /**
     * Close the passage between two adjacent cells on both sides. The inverse of
     * {@link #carve(Point, Point)} — living-mazes v2 ({@code Sealer}) uses this to harden a
     * maze. Callers that must stay connected have to pick a non-bridge; this method itself
     * only toggles walls.
     */
    public void seal(Point a, Point b) {
        Direction d = directionBetween(a, b);
        if (d == null) {
            throw new IllegalArgumentException("Points " + a + " and " + b + " are not adjacent");
        }
        cell(a).close(d);
        cell(b).close(d.opposite());
    }

    /**
     * ASCII art of the maze (audit recommendation §2.3) — same glyphs the REST surface ships,
     * rendered via {@code AsciiMazeVisualizer}. Debugger- and log-friendly; a 20×20 grid is
     * ~1.7 KB, so this stays cheap at the sizes logs actually see.
     */
    @Override
    public String toString() {
        return com.daedalus.visualize.AsciiMazeVisualizer.renderToString(this, java.util.List.of());
    }

    public static Direction directionBetween(Point a, Point b) {
        int dr = b.row() - a.row();
        int dc = b.col() - a.col();
        if (dr == -1 && dc == 0) return Direction.NORTH;
        if (dr == 1 && dc == 0) return Direction.SOUTH;
        if (dr == 0 && dc == 1) return Direction.EAST;
        if (dr == 0 && dc == -1) return Direction.WEST;
        return null;
    }

    public List<Point> neighbors(Point p) {
        List<Point> out = new ArrayList<>(4);
        for (Direction d : Direction.values()) {
            Point n = p.step(d);
            if (inBounds(n)) out.add(n);
        }
        return out;
    }

    public List<Point> openNeighbors(Point p) {
        List<Point> out = new ArrayList<>(4);
        for (Direction d : Direction.values()) {
            if (isOpen(p.row(), p.col(), d)) {
                Point n = p.step(d);
                if (inBounds(n)) out.add(n);
            }
        }
        return out;
    }

    /**
     * Whether the passage from {@code (row, col)} toward {@code d} is open. Coordinate form
     * so the graph seam can walk walls without allocating a {@link Point} per hop.
     */
    public boolean isOpen(int row, int col, Direction d) {
        return cell(row, col).isOpen(d);
    }

    /**
     * Cost of entering cell {@code p}. The default {@code MazeGrid} is uniform-cost and
     * always returns {@code 1.0}; cost-aware solvers (Dijkstra, A*) read this hook so a
     * subclass like {@link WeightedMazeGrid} can supply per-cell weights without the
     * solvers having to know about the subclass.
     *
     * <p>Returned values must be non-negative (Dijkstra and A* require this) and the
     * starting cell's weight is never charged because we begin there rather than entering
     * it. To preserve A*'s optimality guarantees with a Manhattan heuristic, weights
     * should be {@code >= 1.0}; if the smallest weight in the grid is some {@code wMin < 1},
     * scale the heuristic by {@code wMin} (or pass a custom heuristic to the solver) to
     * keep it admissible.
     *
     * <p><b>{@code final} on purpose.</b> This used to be the extension point, and it is now a
     * thin delegate to {@link #weightOf(int, int)}. A subclass that overrode <em>this</em>
     * method would still compile but would be bypassed entirely by the graph seam, which asks
     * for weights by coordinate — the subclass's costs would vanish silently and A* would
     * quietly optimise the wrong thing. Sealing it turns that into a compile error naming the
     * method to override instead. This matters beyond the repo: {@code daedalus-plugin-runtime}
     * loads third-party jars that may subclass {@code MazeGrid}.
     *
     * @param p cell whose entry-cost is requested; must be {@link #inBounds(Point)}
     * @return the cost of entering {@code p}; always {@code 1.0} for plain {@code MazeGrid}
     * @since 1.0
     */
    public final double weightOf(Point p) {
        return weightOf(p.row(), p.col());
    }

    /**
     * Coordinate-indexed form of {@link #weightOf(Point)} — the one subclasses should override.
     *
     * <p>This exists because the graph seam addresses nodes by dense integer id, so
     * {@link com.daedalus.graph.MazeGraph#edgeWeight(int, int)} previously had to materialise a
     * {@link Point} on every edge relaxation just to ask for its cost. On a weighted Dijkstra
     * sweep that is one allocation per relaxation, in the hottest loop the engine has. Taking
     * {@code (row, col)} directly removes it.
     *
     * <p>{@link #weightOf(Point)} delegates here, so there is a single implementation point:
     * override this, and both forms stay consistent.
     *
     * @param row cell row
     * @param col cell column
     * @return the cost of entering {@code (row, col)}; always {@code 1.0} for plain
     *         {@code MazeGrid}
     */
    public double weightOf(int row, int col) {
        return 1.0;
    }

    /**
     * An independent structural copy: same dimensions, same open walls, same start/goal,
     * fresh (cleared) visited layer. Carving on the copy never touches the original and
     * vice versa — this is the copy-on-write primitive the living-maze feature (ADR-006)
     * mutates so readers holding the previous snapshot stay consistent without locking.
     *
     * <p>Subclasses carrying extra state should override to preserve it and to keep the
     * runtime type — {@link WeightedMazeGrid#copy()} returns a weighted copy with weights
     * intact. (Contrast with {@code new WeightedMazeGrid(source)}, which deliberately
     * resets weights to {@code 1.0}: that constructor is "wrap this topology", this method
     * is "duplicate this maze".)
     *
     * @return a new grid equal in structure to this one and sharing no mutable state
     * @since 1.2
     */
    public MazeGrid copy() {
        MazeGrid out = new MazeGrid(rows, cols);
        copyStructureInto(out);
        return out;
    }

    /** Copy topology + start/goal into {@code target} (same dimensions assumed). */
    protected final void copyStructureInto(MazeGrid target) {
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Cell source = cells[r][c];
                Cell dest = target.cell(r, c);
                for (Direction d : Direction.values()) {
                    if (source.isOpen(d)) {
                        dest.open(d);
                    }
                }
            }
        }
        target.setStart(start);
        target.setGoal(goal);
    }

    /**
     * Project the maze into the {@code (2r+1) x (2c+1)} glyph grid every renderer consumes.
     *
     * <p>Two honesty rules, both added 2026-07-29 after the same misrendering surfaced in
     * three consumers (web canvas, JavaFX desktop, ASCII art):
     * <ul>
     *   <li><b>Uncarved cells are rock, and rock renders as WALL.</b> The old projection
     *       marked every cell PASSAGE unconditionally, so a BSP dungeon's solid rock came
     *       out as a polka-dot field of isolated floor specks. A cell with no open side is
     *       not floor; only 1x1 grids (a single cell that IS the maze) keep the cell open.</li>
     *   <li><b>A wall post surrounded by four open segments is room interior.</b> Corner
     *       tiles (even, even) stay WALL in every spanning tree — a 2x2 of mutually open
     *       cells is a cycle — but inside a dungeon room they are open floor, not a grid of
     *       specks.</li>
     * </ul>
     * For every perfect maze the output is byte-identical to the old projection (each cell
     * has an open side; no post ever has four open neighbours), so spanning-tree consumers
     * see no change — pinned by {@code TileGridProjectionTest}.
     */
    public TileType[][] toTileGrid() {
        int tr = 2 * rows + 1;
        int tc = 2 * cols + 1;
        TileType[][] tiles = new TileType[tr][tc];
        for (int r = 0; r < tr; r++) {
            for (int c = 0; c < tc; c++) {
                tiles[r][c] = TileType.WALL;
            }
        }
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Cell cell = cells[r][c];
                boolean carved = cell.isOpen(Direction.NORTH) || cell.isOpen(Direction.SOUTH)
                        || cell.isOpen(Direction.EAST) || cell.isOpen(Direction.WEST)
                        || (rows == 1 && cols == 1);
                if (carved) {
                    tiles[2 * r + 1][2 * c + 1] = TileType.PASSAGE;
                }
                if (cell.isOpen(Direction.NORTH)) tiles[2 * r][2 * c + 1] = TileType.PASSAGE;
                if (cell.isOpen(Direction.SOUTH)) tiles[2 * r + 2][2 * c + 1] = TileType.PASSAGE;
                if (cell.isOpen(Direction.EAST)) tiles[2 * r + 1][2 * c + 2] = TileType.PASSAGE;
                if (cell.isOpen(Direction.WEST)) tiles[2 * r + 1][2 * c] = TileType.PASSAGE;
            }
        }
        // Interior posts: a corner tile whose four orthogonal wall segments are all open sits
        // inside an open area (a room) and is floor.
        for (int r = 2; r < tr - 1; r += 2) {
            for (int c = 2; c < tc - 1; c += 2) {
                if (tiles[r - 1][c] == TileType.PASSAGE && tiles[r + 1][c] == TileType.PASSAGE
                        && tiles[r][c - 1] == TileType.PASSAGE && tiles[r][c + 1] == TileType.PASSAGE) {
                    tiles[r][c] = TileType.PASSAGE;
                }
            }
        }
        if (start != null) tiles[2 * start.row() + 1][2 * start.col() + 1] = TileType.START;
        if (goal != null) tiles[2 * goal.row() + 1][2 * goal.col() + 1] = TileType.GOAL;
        return tiles;
    }
}
