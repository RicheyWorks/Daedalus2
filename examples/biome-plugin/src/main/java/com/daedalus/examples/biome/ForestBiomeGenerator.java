// SPDX-License-Identifier: MIT

package com.daedalus.examples.biome;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Random;

/**
 * Forest-biome generator — recursive backtracker with a weighted vertical-first
 * direction bias.
 *
 * <p>This is one of two worked examples that ship with the {@code biome-plugin}
 * reference module. It's intentionally written from scratch against the public
 * SPI ({@link AbstractMazeGenerator}, {@link MazeGrid}, {@link MazeStats}) — no
 * reach-ins to package-private engine internals — so it's a faithful template
 * for what plugin authors actually have to write.
 *
 * <p><b>Texture.</b> With probability {@link #P_VERTICAL_FIRST} the two
 * vertical directions ({@code NORTH}, {@code SOUTH}) take slots 0–1 of the
 * carve-attempt order and the two horizontal directions take slots 2–3 (each
 * pair internally shuffled). With the complementary probability the pairs
 * swap. Because the DFS commits to the first unvisited direction in iteration
 * order, putting both vertical directions ahead of both horizontal directions
 * on most calls produces long vertical "trunks" with shorter horizontal
 * "branches" — visually evocative of a forest. The maze is still a perfect
 * spanning tree (single connected component, no cycles) because the DFS
 * contract is unchanged; only the order we try neighbours is biased.
 *
 * <p><b>Why a weighted first slot rather than a biased shuffle?</b> A
 * naive "start the priority array vertical-first then Fisher–Yates" approach
 * is a no-op: Fisher–Yates produces every permutation with equal probability
 * regardless of starting order. The bias has to live somewhere the shuffle
 * can't wash out — for us, that's the choice of the first slot.
 *
 * <p><b>Seed contract.</b> Given the same {@code (rows, cols, seed)} the output
 * is bit-for-bit deterministic. The biome generators are not seed-compatible
 * with any in-tree generator — they have their own consumption pattern.
 *
 * @since 1.0
 */
public final class ForestBiomeGenerator extends AbstractMazeGenerator {

    /** Probability that the first direction tried is vertical (N or S). */
    static final double P_VERTICAL_FIRST = 0.7;

    /** Vertical directions. Used to pick the first slot when the bias fires. */
    private static final Direction[] VERTICAL = { Direction.NORTH, Direction.SOUTH };

    /** Horizontal directions. Used to pick the first slot when the bias misses. */
    private static final Direction[] HORIZONTAL = { Direction.EAST, Direction.WEST };

    @Override public String id()          { return "forest-biome"; }
    @Override public String displayName() { return "Forest Biome"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Weighted vertical-first DFS — long trunks, short side branches",
                "Recursive backtracker variant that, with probability " +
                Math.round(P_VERTICAL_FIRST * 100) + "%, tries the two vertical " +
                "directions before the two horizontal directions; with the " +
                "complementary probability the pairs swap. Within-pair order is " +
                "uniformly random. Worked example shipped with the biome-plugin " +
                "reference module.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        Point start = new Point(rng.nextInt(rows), rng.nextInt(cols));
        Deque<Point> stack = new ArrayDeque<>();
        stack.push(start);
        grid.cell(start).markVisited();
        stats.incVisited();

        while (!stack.isEmpty()) {
            stats.recordFrontier(stack.size());
            Point cur = stack.peek();

            Direction[] order = orderWithVerticalBias(rng);
            Point chosen = null;
            for (Direction d : order) {
                Point n = cur.step(d);
                if (grid.inBounds(n) && !grid.cell(n).isVisited()) {
                    grid.carve(grid.cell(cur), d);
                    grid.cell(n).markVisited();
                    stats.incVisited();
                    chosen = n;
                    break;
                }
            }

            if (chosen == null) {
                stack.pop();
                stats.incBacktrack();
            } else {
                stack.push(chosen);
            }
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }

    /**
     * Produce a length-4 direction ordering with a real vertical bias.
     *
     * <p>With probability {@link #P_VERTICAL_FIRST} the two vertical directions
     * fill slots 0–1 (in random order) and the two horizontal directions fill
     * slots 2–3 (in random order). With the complementary probability the
     * pairs swap. Because the DFS commits to the first unvisited direction in
     * iteration order, putting both vertical directions ahead of both
     * horizontal directions on 70% of calls strongly biases corridor growth
     * along the row axis — long trunks.
     *
     * <p>Random consumption per call: one {@code nextDouble()} to decide which
     * axis pair wins slots 0–1, then two {@code nextBoolean()} to pick the
     * within-pair order on each side. Deterministic given a fixed seed.
     */
    private static Direction[] orderWithVerticalBias(Random rng) {
        boolean verticalWins = rng.nextDouble() < P_VERTICAL_FIRST;
        Direction[] pref  = verticalWins ? VERTICAL   : HORIZONTAL;
        Direction[] other = verticalWins ? HORIZONTAL : VERTICAL;

        // Randomize the within-pair order so we don't deterministically pick
        // N before S (or E before W) — that would make the bias asymmetric
        // along the row index and visibly skew the maze.
        boolean prefSwap  = rng.nextBoolean();
        boolean otherSwap = rng.nextBoolean();

        return new Direction[] {
                pref[prefSwap   ? 1 : 0],
                pref[prefSwap   ? 0 : 1],
                other[otherSwap ? 1 : 0],
                other[otherSwap ? 0 : 1],
        };
    }
}
