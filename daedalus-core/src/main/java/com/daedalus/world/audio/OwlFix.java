// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Owl Fix (contest G150): the owl is back, so the regrown woods have prey again.
 *
 * <p>A great horned owl hoots from one cell of a {@link #GRID} x {@link #GRID} patch of woods
 * ({@link #CELL_M} m cells). Four listening posts (four, not three: three posts give only two time differences\n * for (x, y) and the hyperbolas can cross twice, a mirror solution) at the corners hear the hoot at slightly different times.
 * The player is given the arrival-time differences relative to post 0 and picks the owl's cell.
 * {@link #solve()} checks every cell and keeps the one whose predicted time differences best fit the heard
 * ones (least squares; ties keep the first cell in row-major order, so it is deterministic). The judge
 * scores by distance from the true cell.
 *
 * <p>Ecology caveats: values are illustrative. Speed of sound is taken as {@link #SOUND_MPS} m/s (about
 * 20 C air); real arrivals also shift with wind, temperature and echoes off trunks. Field owl surveys usually
 * locate birds by compass bearings from several observers; time-difference arrays of recorders are a
 * research method, used here as the puzzle. The hoot sits around 250-350 Hz (great horned owl hoots are low)
 * and passes {@link EarRule#check}.
 */
public final class OwlFix {
    /** Cells per side. */
    public static final int GRID = 10;
    /** Cell size, metres (illustrative). */
    public static final double CELL_M = 50.0;
    /** Speed of sound used, m/s: 343 = dry air at about 20 C (c = 331.3 + 0.606 T); the woods have no temperature model. */
    public static final double SOUND_MPS = 343.0;
    /** Timing jitter amplitude per post, seconds (illustrative recorder clock error). */
    public static final double JITTER_S = 0.001;
    private static final double SIDE = GRID * CELL_M;
    /** Listening posts (x, y) in metres: the four corners. */
    private static final List<double[]> POSTS = List.of(new double[] {0, 0}, new double[] {SIDE, 0},
        new double[] {0, SIDE}, new double[] {SIDE, SIDE});
    private static final long SALT = 0x4F57_4C31L; // "OWL1"

    /** A cell (column x, row y). */
    public record Cell(int x, int y) {
        /** Whether the cell is inside the woods. */
        public boolean inside() {
            return x >= 0 && x < GRID && y >= 0 && y < GRID;
        }

        double cx() {
            return (x + 0.5) * CELL_M;
        }

        double cy() {
            return (y + 0.5) * CELL_M;
        }
    }

    /** A judged guess. */
    public record Verdict(boolean exact, double distanceM, int score) { }

    private final long seed;
    private final Cell owl;
    private final double hootHz;
    private final double[] delays;

    private OwlFix(long seed, Cell owl, double hootHz, double[] delays) {
        this.seed = seed;
        this.owl = owl;
        this.hootHz = hootHz;
        this.delays = delays.clone();
    }

    /** A seeded night. */
    public static OwlFix seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        Cell owl = new Cell(roll(rng, GRID), roll(rng, GRID));
        double hz = 250 + roll(rng, 1001) / 10.0;
        double[] t = new double[POSTS.size()];
        for (int i = 0; i < t.length; i++) {
            t[i] = travel(owl, i) + JITTER_S * (roll(rng, 2001) / 1000.0 - 1.0);
        }
        double[] d = new double[t.length];
        for (int i = 0; i < t.length; i++) {
            d[i] = Math.round((t[i] - t[0]) * 1e4) / 1e4;
        }
        return new OwlFix(seed, owl, hz, d);
    }

    private static int roll(Rng rng, int n) {
        return (int) Long.remainderUnsigned(rng.nextLong(), n);
    }

    /** Travel time, seconds, from a cell centre to post {@code i}. */
    public static double travel(Cell c, int i) {
        double[] p = POSTS.get(i);
        return Math.hypot(c.cx() - p[0], c.cy() - p[1]) / SOUND_MPS;
    }

    /** Noise-free time differences, seconds, relative to post 0, for an owl in cell {@code c}. */
    public static double[] exactDelays(Cell c) {
        double[] d = new double[POSTS.size()];
        for (int i = 0; i < d.length; i++) {
            d[i] = travel(c, i) - travel(c, 0);
        }
        return d;
    }

    /** Sum of squared misfits (s^2) between a cell's predicted time differences and heard ones. */
    public static double misfit(Cell c, double[] heard) {
        double s = 0;
        for (int i = 1; i < heard.length; i++) {
            double r = (travel(c, i) - travel(c, 0)) - heard[i];
            s += r * r;
        }
        return s;
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The true cell (for the judge and tests). */
    public Cell owl() {
        return owl;
    }

    /** Heard arrival-time differences, seconds, relative to post 0 (rounded to 0.1 ms). */
    public double[] delays() {
        return delays.clone();
    }

    /** Hoot pitch (ear-rule checked). */
    public double hootHz() {
        return EarRule.check(hootHz, "great horned owl hoot");
    }

    /** All cells in row-major order. */
    public static List<Cell> cells() {
        List<Cell> out = new ArrayList<>();
        for (int y = 0; y < GRID; y++) {
            for (int x = 0; x < GRID; x++) {
                out.add(new Cell(x, y));
            }
        }
        return out;
    }

    /** Best-fitting cell; ties keep the first in row-major order. */
    public Cell solve() {
        Cell best = null;
        double bestS = Double.POSITIVE_INFINITY;
        for (Cell c : cells()) {
            double s = misfit(c, delays);
            if (s < bestS) {
                bestS = s;
                best = c;
            }
        }
        return best;
    }

    /** Judge a guess: 100 for the right cell, minus 20 per cell-width of distance; outside the woods scores 0. */
    public Verdict judge(Cell guess) {
        if (guess == null || !guess.inside()) {
            return new Verdict(false, Double.NaN, 0);
        }
        double d = Math.hypot(guess.cx() - owl.cx(), guess.cy() - owl.cy());
        int score = (int) Math.max(0, Math.round(100 - 20 * d / CELL_M));
        return new Verdict(guess.equals(owl), d, score);
    }
}