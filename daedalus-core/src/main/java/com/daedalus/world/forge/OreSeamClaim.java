// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Ore Seam Claim (contest gap G214): a grid of the Meteor Scar floor ({@link ScarDig}) shows each cell's ore value less
 * its digging cost, which can be negative. Stake one non-empty rectangular claim for the most net ore.
 *
 * <p>The tool is plain: {@link #bestRun} is 1D Kadane over an {@code int[]} and {@link #bestClaim} is the exact 2D
 * maximum-sum rectangle (Kadane over every strip of rows, O(rows^2 x cols)). Any project can use it for the best
 * stretch of a timeline or the best region of a map.
 */
public final class OreSeamClaim {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_ore_seam_claim";

    /** How a claim compares with the best. */
    public enum Grade { RICH, FAIR, BUST }

    /** A run [from, to] (inclusive) and its sum. */
    public record Run(int from, int to, long sum) {
    }

    /** A rectangle rows [top, bottom] x columns [left, right] (inclusive) and its sum. */
    public record Claim(int top, int left, int bottom, int right, long sum) {
    }

    private OreSeamClaim() {
    }

    /** A seeded rows x cols grid of net ore in [-spread, spread]. Same seed, same scar. */
    public static int[][] scar(long seed, int rows, int cols, int spread) {
        if (rows < 1 || cols < 1 || spread < 0) {
            throw new IllegalArgumentException("need rows, cols >= 1 and spread >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] g = new int[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                g[i][j] = r.nextInt(-spread, spread + 1);
            }
        }
        return g;
    }

    /** The best non-empty contiguous run (earliest, then shortest, on ties). */
    public static Run bestRun(int[] a) {
        if (a.length == 0) {
            throw new IllegalArgumentException("empty run");
        }
        long best = a[0];
        int bf = 0;
        int bt = 0;
        long cur = 0;
        int start = 0;
        for (int i = 0; i < a.length; i++) {
            if (cur <= 0) {
                cur = a[i];
                start = i;
            } else {
                cur += a[i];
            }
            if (cur > best) {
                best = cur;
                bf = start;
                bt = i;
            }
        }
        return new Run(bf, bt, best);
    }

    /** The best non-empty rectangle. */
    public static Claim bestClaim(int[][] g) {
        int rows = check(g);
        int cols = g[0].length;
        Claim best = null;
        int[] col = new int[cols];
        for (int top = 0; top < rows; top++) {
            Arrays.fill(col, 0);
            for (int bottom = top; bottom < rows; bottom++) {
                for (int j = 0; j < cols; j++) {
                    col[j] += g[bottom][j];
                }
                Run r = bestRun(col);
                if (best == null || r.sum() > best.sum()) {
                    best = new Claim(top, r.from(), bottom, r.to(), r.sum());
                }
            }
        }
        return best;
    }

    /** Net ore inside a rectangle. */
    public static long sum(int[][] g, int top, int left, int bottom, int right) {
        int rows = check(g);
        if (top < 0 || left < 0 || bottom >= rows || right >= g[0].length || top > bottom || left > right) {
            throw new IllegalArgumentException("claim outside the scar");
        }
        long s = 0;
        for (int i = top; i <= bottom; i++) {
            for (int j = left; j <= right; j++) {
                s += g[i][j];
            }
        }
        return s;
    }

    /** RICH at the best, FAIR at 75% or more of a positive best, BUST otherwise. */
    public static Grade grade(long sum, long best) {
        if (sum > best) {
            throw new IllegalArgumentException("sum above the best");
        }
        if (sum == best) {
            return Grade.RICH;
        }
        return best > 0 && 4 * sum >= 3 * best ? Grade.FAIR : Grade.BUST;
    }

    /** The Forgemaster's line for a claim. */
    public static String forgemasterLine(long sum, long best) {
        return switch (grade(sum, best)) {
            case RICH -> "Forgemaster: " + sum + " net. You found the heart of the seam.";
            case FAIR -> "Forgemaster: " + sum + " of " + best + ". A fair claim. The heart is close.";
            case BUST -> "Forgemaster: " + sum + " net. You dug more than you found.";
        };
    }

    private static int check(int[][] g) {
        if (g.length == 0 || g[0].length == 0) {
            throw new IllegalArgumentException("empty scar");
        }
        for (int[] row : g) {
            if (row.length != g[0].length) {
                throw new IllegalArgumentException("scar must be rectangular");
            }
        }
        return g.length;
    }
}
