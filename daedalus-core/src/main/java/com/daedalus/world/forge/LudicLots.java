// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Ludic Lots: the smith lines lots 2..N, keeps the first lot x and culls it together with every x-th lot after it,
 * then repeats on what is left. The kept lots, plus 1, are the ludic numbers 1, 2, 3, 5, 7, 11, 13, 17, 23, 25, ...
 *
 * <p>Reusable plain int API for N up to {@link #MAX_N}: {@link #ludicUpTo}, {@link #isLudic} and {@link #triplets}
 * (ludic x, x + 2, x + 6). Positions never depend on lots beyond N, so a list up to N is a prefix of any longer one.
 */
public final class LudicLots {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_ludic_lots";
    /** Largest supported line of lots. */
    public static final int MAX_N = 200_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private static boolean[] table;

    private LudicLots() {
    }

    private static void checkLimit(int n) {
        if (n < 0 || n > MAX_N) {
            throw new IllegalArgumentException("line out of range: " + n);
        }
    }

    /** Ludic numbers in 1..n, ascending. */
    public static int[] ludicUpTo(int n) {
        checkLimit(n);
        if (n < 1) {
            return new int[0];
        }
        int[] out = new int[n];
        int k = 0;
        out[k++] = 1;
        int len = n - 1;
        int[] a = new int[Math.max(len, 0)];
        for (int i = 0; i < len; i++) {
            a[i] = i + 2;
        }
        while (len > 0) {
            int x = a[0];
            if (x >= len) {
                for (int i = 0; i < len; i++) {
                    out[k++] = a[i];
                }
                break;
            }
            out[k++] = x;
            int m = 0;
            for (int i = 0; i < len; i++) {
                if (i % x != 0) {
                    a[m++] = a[i];
                }
            }
            len = m;
        }
        return Arrays.copyOf(out, k);
    }

    private static synchronized boolean[] table() {
        if (table == null) {
            boolean[] t = new boolean[MAX_N + 1];
            for (int v : ludicUpTo(MAX_N)) {
                t[v] = true;
            }
            table = t;
        }
        return table;
    }

    /** True when lot v survives the cull. */
    public static boolean isLudic(int v) {
        if (v < 1 || v > MAX_N) {
            throw new IllegalArgumentException("lot out of range: " + v);
        }
        return table()[v];
    }

    /** Ludic triplets (x, x + 2, x + 6) with x + 6 &lt;= n, each as {x, x + 2, x + 6}. */
    public static List<int[]> triplets(int n) {
        checkLimit(n);
        List<int[]> out = new ArrayList<>();
        for (int x = 1; x + 6 <= n; x++) {
            if (isLudic(x) && isLudic(x + 2) && isLudic(x + 6)) {
                out.add(new int[] {x, x + 2, x + 6});
            }
        }
        return out;
    }

    /** Grade a claim that lot v is (or is not) ludic. */
    public static Grade grade(int v, boolean claimedLudic) {
        return isLudic(v) == claimedLudic ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you followed the cull to the end. The lot's fate is read true.";
            case SLIPPED -> "Forgemaster: the cull slipped. Each kept lot culls itself and every x-th one after.";
        };
    }
}
