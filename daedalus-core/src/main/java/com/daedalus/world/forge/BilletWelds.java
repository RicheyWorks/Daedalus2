// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Billet Welds (contest gap G216): a row of billets must be forge-welded into one bar for {@link IngotCuts}, always
 * joining two neighbours. Each weld costs heat equal to the combined weight of the two pieces. Find the weld order with
 * the least total heat.
 *
 * <p>The engine is plain interval DP over an {@code int[]}: {@link #leastHeat} for adjacent merging (with
 * {@link #order}, the welds as left-piece indices) and {@link #matrixChain} for the classic matrix-chain cost on the
 * same idea. {@link #greedy} welds the lightest neighbouring pair first and can lose. Any project can use it for
 * merge order, expression order or batching.
 */
public final class BilletWelds {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_billet_welds";

    /** How a weld order compares with the least heat. */
    public enum Grade { SEAMLESS, WARM, SCORCHED }

    private BilletWelds() {
    }

    /** {@code n} seeded billets weighing 1..maxWeight. Same seed, same row. */
    public static int[] billets(long seed, int n, int maxWeight) {
        if (n < 0 || maxWeight < 1) {
            throw new IllegalArgumentException("need n >= 0 and maxWeight >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] w = new int[n];
        for (int i = 0; i < n; i++) {
            w[i] = 1 + r.nextInt(maxWeight);
        }
        return w;
    }

    /** Least total heat to weld the whole row (0 for zero or one billet). */
    public static long leastHeat(int[] w) {
        return solve(w)[0][0];
    }

    /** Returns {{answer}}. */
    private static long[][] solve(int[] w) {
        check(w);
        int n = w.length;
        if (n <= 1) {
            return new long[][] {{0}};
        }
        long[] pre = new long[n + 1];
        for (int i = 0; i < n; i++) {
            pre[i + 1] = pre[i] + w[i];
        }
        long[][] f = new long[n][n];
        for (int len = 2; len <= n; len++) {
            for (int i = 0; i + len - 1 < n; i++) {
                int j = i + len - 1;
                long best = Long.MAX_VALUE;
                for (int k = i; k < j; k++) {
                    best = Math.min(best, f[i][k] + f[k + 1][j]);
                }
                f[i][j] = best + pre[j + 1] - pre[i];
            }
        }
        return new long[][] {{f[0][n - 1]}};
    }

    /**
     * One least-heat weld order: each entry is the index (in the current row) of the left piece of the next weld.
     * Replaying it with {@link #heat} gives {@link #leastHeat}.
     */
    public static List<Integer> order(int[] w) {
        check(w);
        int n = w.length;
        List<Integer> out = new ArrayList<>();
        if (n <= 1) {
            return out;
        }
        long[] pre = new long[n + 1];
        for (int i = 0; i < n; i++) {
            pre[i + 1] = pre[i] + w[i];
        }
        long[][] f = new long[n][n];
        int[][] cut = new int[n][n];
        for (int len = 2; len <= n; len++) {
            for (int i = 0; i + len - 1 < n; i++) {
                int j = i + len - 1;
                long best = Long.MAX_VALUE;
                for (int k = i; k < j; k++) {
                    long c = f[i][k] + f[k + 1][j];
                    if (c < best) {
                        best = c;
                        cut[i][j] = k;
                    }
                }
                f[i][j] = best + pre[j + 1] - pre[i];
            }
        }
        emit(cut, 0, n - 1, 0, out);
        return out;
    }

    /** Emits welds for [i, j] assuming pieces left of i have already collapsed into {@code offset} pieces. */
    private static void emit(int[][] cut, int i, int j, int offset, List<Integer> out) {
        if (i == j) {
            return;
        }
        int k = cut[i][j];
        emit(cut, i, k, offset, out);
        emit(cut, k + 1, j, offset + 1, out);
        out.add(offset);
    }

    /** Total heat of a weld order (left-piece indices in the current row). */
    public static long heat(int[] w, List<Integer> welds) {
        check(w);
        if (welds.size() != Math.max(0, w.length - 1)) {
            throw new IllegalArgumentException("a row of n billets takes n - 1 welds");
        }
        List<Long> row = new ArrayList<>();
        for (int x : w) {
            row.add((long) x);
        }
        long total = 0;
        for (int at : welds) {
            if (at < 0 || at + 1 >= row.size()) {
                throw new IllegalArgumentException("no neighbour to weld at " + at);
            }
            long joined = row.get(at) + row.get(at + 1);
            total += joined;
            row.set(at, joined);
            row.remove(at + 1);
        }
        return total;
    }

    /** Greedy: weld the lightest neighbouring pair first (leftmost on ties). */
    public static List<Integer> greedy(int[] w) {
        check(w);
        List<Long> row = new ArrayList<>();
        for (int x : w) {
            row.add((long) x);
        }
        List<Integer> out = new ArrayList<>();
        while (row.size() > 1) {
            int at = 0;
            for (int i = 1; i + 1 < row.size(); i++) {
                if (row.get(i) + row.get(i + 1) < row.get(at) + row.get(at + 1)) {
                    at = i;
                }
            }
            out.add(at);
            row.set(at, row.get(at) + row.get(at + 1));
            row.remove(at + 1);
        }
        return out;
    }

    /** Classic matrix-chain cost: matrices dims[i] x dims[i+1]; fewest scalar multiplications. */
    public static long matrixChain(int[] dims) {
        check(dims);
        int n = dims.length - 1;
        if (n <= 1) {
            return 0;
        }
        long[][] f = new long[n][n];
        for (int len = 2; len <= n; len++) {
            for (int i = 0; i + len - 1 < n; i++) {
                int j = i + len - 1;
                long best = Long.MAX_VALUE;
                for (int k = i; k < j; k++) {
                    best = Math.min(best, f[i][k] + f[k + 1][j] + (long) dims[i] * dims[k + 1] * dims[j + 1]);
                }
                f[i][j] = best;
            }
        }
        return f[0][n - 1];
    }

    /** SEAMLESS at the least heat, WARM within 10% over, SCORCHED beyond. */
    public static Grade grade(long heat, long least) {
        if (heat < least) {
            throw new IllegalArgumentException("heat below the least");
        }
        if (heat == least) {
            return Grade.SEAMLESS;
        }
        return 10L * heat <= 11L * least ? Grade.WARM : Grade.SCORCHED;
    }

    /** The Forgemaster's line for a weld order. */
    public static String forgemasterLine(long heat, long least) {
        return switch (grade(heat, least)) {
            case SEAMLESS -> "Forgemaster: " + heat + " heat. The bar sings when you tap it.";
            case WARM -> "Forgemaster: " + heat + " of " + least + " heat. Close. Weld the heavy ones last.";
            case SCORCHED -> "Forgemaster: " + heat + " heat for a " + least + "-heat bar. The coal bin is empty.";
        };
    }

    private static void check(int[] w) {
        for (int x : w) {
            if (x <= 0) {
                throw new IllegalArgumentException("weights must be positive: " + x);
            }
        }
    }
}
