// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Rooms-and-corridors dungeon via binary space partitioning — divide and conquer (CLRS Ch. 4's
 * flavour) applied to level layout rather than to a sort.
 *
 * <p>Recursively split the grid until each region is small, carve a room inside every leaf, then
 * on the way back up connect each pair of sibling regions with an L-shaped corridor. The recursion
 * order guarantees connectivity: every subtree is joined to its sibling exactly once, so all rooms
 * end up in one component.
 *
 * <h3>This is deliberately not a perfect maze</h3>
 *
 * <p>Every other generator here produces a spanning tree: full coverage, no loops, exactly one
 * route anywhere. A dungeon is the opposite on all three counts, and that's the point.
 * <ul>
 *   <li><b>Open rooms</b> — interior room cells have all four sides open, where a maze corridor
 *       has one or two.</li>
 *   <li><b>Loops</b> — a room is a dense block of cycles, so route choice is built in. The
 *       structural metrics that need braiding elsewhere ({@code MazeFlow}, {@code LongestPath})
 *       are interesting here for free.</li>
 *   <li><b>Solid rock</b> — cells between rooms are never carved and stay unreachable. Callers
 *       that assume every cell is reachable must not use this generator.</li>
 * </ul>
 *
 * <p>The {@link com.daedalus.engine.MazeGenerator} contract allows this explicitly: implementations
 * produce a perfect maze "unless their theoretical contract says otherwise".
 *
 * <p>Deterministic for a given seed.
 */
public class DungeonGenerator extends AbstractMazeGenerator {

    /** Regions below twice this size stop splitting and become a room. */
    private static final int DEFAULT_MIN_LEAF = 7;

    private final int minLeaf;

    public DungeonGenerator() {
        this(DEFAULT_MIN_LEAF);
    }

    /**
     * @param minLeaf smallest region half-size; larger values mean fewer, bigger rooms
     */
    public DungeonGenerator(int minLeaf) {
        this.minLeaf = Math.max(2, minLeaf);
    }

    @Override public String id() { return "dungeon"; }

    @Override public String displayName() { return "Procedural Dungeon (BSP)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(log n) recursion depth",
                "Rooms and corridors — open areas, loops, and unreachable rock; not a perfect maze",
                "Binary space partitioning: split recursively, carve a room per leaf, then join "
                        + "sibling regions with L-shaped corridors.");
    }

    /** Inclusive rectangle of cells. */
    private record Rect(int top, int left, int bottom, int right) {
        int height() {
            return bottom - top + 1;
        }

        int width() {
            return right - left + 1;
        }

        Point center() {
            return new Point((top + bottom) / 2, (left + right) / 2);
        }
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        // Room centres are collected through the recursion rather than held on the instance —
        // generators are registered as shared singletons, so they must stay stateless.
        List<Point> roomCenters = new ArrayList<>();
        partition(grid, new Rect(0, 0, rows - 1, cols - 1), rng, stats, roomCenters);

        // Anchor start/goal on carved ground; the corners are usually solid rock here.
        grid.setStart(roomCenters.get(0));
        grid.setGoal(roomCenters.get(roomCenters.size() - 1));

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }

    /** Split, recurse, carve rooms at the leaves, and join siblings on the way back up. */
    private Rect partition(MazeGrid grid, Rect region, Random rng, MazeStats stats,
                           List<Point> roomCenters) {
        boolean canSplitRows = region.height() >= 2 * minLeaf;
        boolean canSplitCols = region.width() >= 2 * minLeaf;
        if (!canSplitRows && !canSplitCols) {
            Rect room = carveRoom(grid, region, rng, stats);
            roomCenters.add(room.center());
            return room;
        }

        boolean splitRows = canSplitRows && (!canSplitCols || region.height() >= region.width());
        Rect a;
        Rect b;
        if (splitRows) {
            int at = region.top() + minLeaf + rng.nextInt(region.height() - 2 * minLeaf + 1);
            a = new Rect(region.top(), region.left(), at, region.right());
            b = new Rect(at + 1, region.left(), region.bottom(), region.right());
        } else {
            int at = region.left() + minLeaf + rng.nextInt(region.width() - 2 * minLeaf + 1);
            a = new Rect(region.top(), region.left(), region.bottom(), at);
            b = new Rect(region.top(), at + 1, region.bottom(), region.right());
        }

        Rect roomA = partition(grid, a, rng, stats, roomCenters);
        Rect roomB = partition(grid, b, rng, stats, roomCenters);
        corridor(grid, roomA.center(), roomB.center(), rng, stats);
        return roomA;
    }

    /** Carve an open room inside {@code region}, inset by a random margin. */
    private Rect carveRoom(MazeGrid grid, Rect region, Random rng, MazeStats stats) {
        int topInset = region.height() > 3 ? rng.nextInt(2) + 1 : 0;
        int leftInset = region.width() > 3 ? rng.nextInt(2) + 1 : 0;
        int bottomInset = region.height() > 3 ? rng.nextInt(2) + 1 : 0;
        int rightInset = region.width() > 3 ? rng.nextInt(2) + 1 : 0;

        Rect room = new Rect(
                region.top() + topInset,
                region.left() + leftInset,
                region.bottom() - bottomInset,
                region.right() - rightInset);

        for (int r = room.top(); r <= room.bottom(); r++) {
            for (int c = room.left(); c <= room.right(); c++) {
                Point here = new Point(r, c);
                touch(grid, here, stats);
                if (c < room.right()) {
                    grid.carve(here, new Point(r, c + 1));
                }
                if (r < room.bottom()) {
                    grid.carve(here, new Point(r + 1, c));
                }
            }
        }
        return room;
    }

    /** L-shaped corridor between two cells, carving through whatever lies between. */
    private void corridor(MazeGrid grid, Point from, Point to, Random rng, MazeStats stats) {
        Point cursor = from;
        if (rng.nextBoolean()) {
            cursor = walkRows(grid, cursor, to.row(), stats);
            walkCols(grid, cursor, to.col(), stats);
        } else {
            cursor = walkCols(grid, cursor, to.col(), stats);
            walkRows(grid, cursor, to.row(), stats);
        }
    }

    private Point walkRows(MazeGrid grid, Point from, int targetRow, MazeStats stats) {
        Point cursor = from;
        while (cursor.row() != targetRow) {
            Point next = new Point(cursor.row() + (targetRow > cursor.row() ? 1 : -1), cursor.col());
            grid.carve(cursor, next);
            touch(grid, next, stats);
            cursor = next;
        }
        return cursor;
    }

    private Point walkCols(MazeGrid grid, Point from, int targetCol, MazeStats stats) {
        Point cursor = from;
        while (cursor.col() != targetCol) {
            Point next = new Point(cursor.row(), cursor.col() + (targetCol > cursor.col() ? 1 : -1));
            grid.carve(cursor, next);
            touch(grid, next, stats);
            cursor = next;
        }
        return cursor;
    }

    /** Count a cell the first time the dungeon claims it. */
    private void touch(MazeGrid grid, Point p, MazeStats stats) {
        if (!grid.cell(p).isVisited()) {
            grid.cell(p).markVisited();
            stats.incVisited();
        }
    }
}
