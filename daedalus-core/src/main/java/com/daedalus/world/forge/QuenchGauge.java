// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Quench Gauge (contest gap G234): a row of seeded quench troughs cools over the shift, and apprentices are asked for
 * the coldest and hottest trough in a span of the row, again and again.
 *
 * <p>The tool is plain: a sparse table over an {@code int[]} answers range minimum, range maximum and the index of the
 * minimum in O(1) after an O(n log n) build. Any project can use it for repeated range queries on a fixed array.
 */
public final class QuenchGauge {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_quench_gauge";

    /** How an apprentice's answers went. */
    public enum Grade { SHARP, DULL }

    private final int[] values;
    private final int[][] minIdx;
    private final int[][] maxIdx;

    /** Builds the gauge over a copy of {@code values}. */
    public QuenchGauge(int[] values) {
        this.values = values.clone();
        int n = values.length;
        int levels = n == 0 ? 1 : 32 - Integer.numberOfLeadingZeros(n);
        minIdx = new int[levels][];
        maxIdx = new int[levels][];
        minIdx[0] = new int[n];
        maxIdx[0] = new int[n];
        for (int i = 0; i < n; i++) {
            minIdx[0][i] = i;
            maxIdx[0][i] = i;
        }
        for (int k = 1; k < levels; k++) {
            int len = n - (1 << k) + 1;
            minIdx[k] = new int[len];
            maxIdx[k] = new int[len];
            int half = 1 << (k - 1);
            for (int i = 0; i < len; i++) {
                minIdx[k][i] = pickMin(minIdx[k - 1][i], minIdx[k - 1][i + half]);
                maxIdx[k][i] = pickMax(maxIdx[k - 1][i], maxIdx[k - 1][i + half]);
            }
        }
    }

    /** {@code n} seeded trough temperatures in 0..maxTemp. Same seed, same row. */
    public static int[] troughs(long seed, int n, int maxTemp) {
        if (n < 0 || maxTemp < 0) {
            throw new IllegalArgumentException("need n >= 0 and maxTemp >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] t = new int[n];
        for (int i = 0; i < n; i++) {
            t[i] = r.nextInt(maxTemp + 1);
        }
        return t;
    }

    private int pickMin(int a, int b) {
        return values[b] < values[a] ? b : a;
    }

    private int pickMax(int a, int b) {
        return values[b] > values[a] ? b : a;
    }

    private int level(int from, int to) {
        if (from < 0 || to >= values.length || from > to) {
            throw new IllegalArgumentException("bad span [" + from + ", " + to + "]");
        }
        return 31 - Integer.numberOfLeadingZeros(to - from + 1);
    }

    /** Index of the coldest trough in [from, to] (leftmost on ties). */
    public int argMin(int from, int to) {
        int k = level(from, to);
        return pickMin(minIdx[k][from], minIdx[k][to - (1 << k) + 1]);
    }

    /** Coldest temperature in [from, to]. */
    public int min(int from, int to) {
        return values[argMin(from, to)];
    }

    /** Hottest temperature in [from, to]. */
    public int max(int from, int to) {
        int k = level(from, to);
        return values[pickMax(maxIdx[k][from], maxIdx[k][to - (1 << k) + 1])];
    }

    /** SHARP only if every answered coldest temperature matches its span; spans are {from, to} pairs. */
    public Grade grade(int[][] spans, int[] coldest) {
        if (spans.length != coldest.length) {
            return Grade.DULL;
        }
        for (int i = 0; i < spans.length; i++) {
            if (min(spans[i][0], spans[i][1]) != coldest[i]) {
                return Grade.DULL;
            }
        }
        return Grade.SHARP;
    }

    /** The Forgemaster's line for a round. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case SHARP -> "Forgemaster: you read every trough true. Your blades will never crack in the quench.";
            case DULL -> "Forgemaster: a trough ran colder than you said. Dip your hand again.";
        };
    }
}
