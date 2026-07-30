// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;

/**
 * A scale-invariant structural signature of a maze (ADR-007 idea 4).
 *
 * <p>Generators leave fingerprints. A binary tree carves north-or-east and nothing else, so its
 * corridors run in two directions and its top row is one long hall. A recursive backtracker
 * follows a single winding "river", so it is mostly degree-2 cells strung into long runs.
 * Kruskal's fuses random edges and comes out bushy and short-branched. Those differences are
 * visible to the eye, which means they are measurable — and if they are measurable, an
 * unlabelled maze can be traced back to the algorithm that produced it.
 *
 * <p><b>Every feature is a ratio, never a count.</b> That is what makes a 15×15 and a 61×61 from
 * the same generator land in the same place: the signature describes texture, not size. A raw
 * dead-end <em>count</em> would classify by dimensions and look impressive doing it.
 *
 * <p>Deterministic and O(cells) — a single sweep over the grid.
 */
public final class MazeFingerprint {

    private MazeFingerprint() {
    }

    /**
     * The signature. All components are in {@code [0, 1]} except {@link #meanStraightRun()},
     * which is normalised against the grid's own edge length so it stays scale-free.
     *
     * @param deadEndRatio      cells with exactly one opening — corridors that end
     * @param corridorRatio     cells with exactly two openings — pass-throughs
     * @param junctionRatio     cells with three openings — T-junctions
     * @param crossroadRatio    cells with four openings — full crossings
     * @param horizontalBias    share of passages running east–west; 0.5 is unbiased, and a
     *                          strong departure is the signature of a directional generator
     * @param straightRatio     of the two-opening cells, the share that pass straight through
     *                          rather than turning — high means long halls, low means switchbacks
     * @param meanStraightRun   average uninterrupted straight run, divided by the edge length
     * @param edgeDensity       carved passages as a share of all possible passages; below 1 for
     *                          a spanning tree, above it once braided, near 0 for sparse rock
     */
    public record Signature(double deadEndRatio, double corridorRatio, double junctionRatio,
                            double crossroadRatio, double horizontalBias, double straightRatio,
                            double meanStraightRun, double edgeDensity) {

        /** The signature as a vector, in a fixed order, for distance computations. */
        public double[] vector() {
            return new double[] {deadEndRatio, corridorRatio, junctionRatio, crossroadRatio,
                    horizontalBias, straightRatio, meanStraightRun, edgeDensity};
        }

        /** Component names matching {@link #vector()}'s order. */
        public static String[] names() {
            return new String[] {"deadEndRatio", "corridorRatio", "junctionRatio",
                    "crossroadRatio", "horizontalBias", "straightRatio", "meanStraightRun",
                    "edgeDensity"};
        }
    }

    /** Compute a maze's signature in one sweep. */
    public static Signature of(MazeGrid grid) {
        int rows = grid.rows();
        int cols = grid.cols();
        int habitable = 0;
        int[] degrees = new int[5];
        int straightThrough = 0;
        int horizontal = 0;
        int passages = 0;

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                var open = grid.openNeighbors(p);
                int degree = open.size();
                if (degree == 0) {
                    continue; // uncarved rock is not part of the texture being measured
                }
                habitable++;
                degrees[Math.min(4, degree)]++;
                if (degree == 2) {
                    boolean ns = grid.cell(r, c).isOpen(Direction.NORTH)
                            && grid.cell(r, c).isOpen(Direction.SOUTH);
                    boolean ew = grid.cell(r, c).isOpen(Direction.EAST)
                            && grid.cell(r, c).isOpen(Direction.WEST);
                    if (ns || ew) {
                        straightThrough++;
                    }
                }
                // Count each undirected passage once, from its west/north side.
                if (grid.cell(r, c).isOpen(Direction.EAST) && c + 1 < cols) {
                    passages++;
                    horizontal++;
                }
                if (grid.cell(r, c).isOpen(Direction.SOUTH) && r + 1 < rows) {
                    passages++;
                }
            }
        }

        if (habitable == 0 || passages == 0) {
            return new Signature(0, 0, 0, 0, 0.5, 0, 0, 0);
        }

        int twos = degrees[2];
        double possiblePassages = (double) rows * (cols - 1) + (double) cols * (rows - 1);
        return new Signature(
                degrees[1] / (double) habitable,
                twos / (double) habitable,
                degrees[3] / (double) habitable,
                degrees[4] / (double) habitable,
                horizontal / (double) passages,
                twos == 0 ? 0 : straightThrough / (double) twos,
                meanStraightRun(grid) / Math.max(1.0, (rows + cols) / 2.0),
                passages / possiblePassages);
    }

    /**
     * Average length of a maximal straight corridor, counting horizontal and vertical runs.
     * Long runs are the "river" signature of depth-first carving; short ones mean the generator
     * turned constantly.
     */
    private static double meanStraightRun(MazeGrid grid) {
        long totalLength = 0;
        long runs = 0;

        for (int r = 0; r < grid.rows(); r++) {
            int run = 0;
            for (int c = 0; c < grid.cols(); c++) {
                boolean linked = c + 1 < grid.cols() && grid.cell(r, c).isOpen(Direction.EAST);
                if (linked) {
                    run++;
                } else if (run > 0) {
                    totalLength += run;
                    runs++;
                    run = 0;
                }
            }
            if (run > 0) {
                totalLength += run;
                runs++;
            }
        }
        for (int c = 0; c < grid.cols(); c++) {
            int run = 0;
            for (int r = 0; r < grid.rows(); r++) {
                boolean linked = r + 1 < grid.rows() && grid.cell(r, c).isOpen(Direction.SOUTH);
                if (linked) {
                    run++;
                } else if (run > 0) {
                    totalLength += run;
                    runs++;
                    run = 0;
                }
            }
            if (run > 0) {
                totalLength += run;
                runs++;
            }
        }
        return runs == 0 ? 0 : totalLength / (double) runs;
    }
}
