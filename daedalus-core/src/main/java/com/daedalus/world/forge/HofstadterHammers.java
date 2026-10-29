// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Hofstadter Hammers: two self-referential hammers ring meta-Fibonacci rhythms. The Q hammer strikes
 * Q(n) = Q(n - Q(n-1)) + Q(n - Q(n-2)) (1, 1, 2, 3, 3, 4, 5, 5, 6, 6, ...); the Conway hammer strikes
 * a(n) = a(a(n-1)) + a(n - a(n-1)) (1, 1, 2, 2, 3, 4, 4, 4, 5, ...), with Q(1) = Q(2) = a(1) = a(2) = 1.
 *
 * <p>Reusable plain int API, linear time, 1-indexed (index 0 unused) for n up to {@link #MAX_N}:
 * {@link #qSequence}, {@link #conwaySequence}, {@link #q}, {@link #conway}.
 */
public final class HofstadterHammers {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_hofstadter_hammers";
    /** Largest supported index. */
    public static final int MAX_N = 10_000_000;

    /** Which hammer. */
    public enum Hammer { Q, CONWAY }

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private HofstadterHammers() {
    }

    private static void check(int n) {
        if (n < 0 || n > MAX_N) {
            throw new IllegalArgumentException("index out of range: " + n);
        }
    }

    /** Q(0..n) with Q(0) = 0 unused. */
    public static int[] qSequence(int n) {
        check(n);
        int[] s = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            if (i <= 2) {
                s[i] = 1;
            } else {
                int x = i - s[i - 1];
                int y = i - s[i - 2];
                if (x < 1 || y < 1) {
                    throw new IllegalStateException("Q index fell below 1 at n=" + i);
                }
                s[i] = s[x] + s[y];
            }
        }
        return s;
    }

    /** a(0..n) with a(0) = 0 unused. */
    public static int[] conwaySequence(int n) {
        check(n);
        int[] s = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            s[i] = i <= 2 ? 1 : s[s[i - 1]] + s[i - s[i - 1]];
        }
        return s;
    }

    /** Q(n), n &gt;= 1. */
    public static int q(int n) {
        if (n < 1) {
            throw new IllegalArgumentException("index must be at least 1: " + n);
        }
        return qSequence(n)[n];
    }

    /** a(n), n &gt;= 1. */
    public static int conway(int n) {
        if (n < 1) {
            throw new IllegalArgumentException("index must be at least 1: " + n);
        }
        return conwaySequence(n)[n];
    }

    /** The strike of a hammer at n. */
    public static int strike(Hammer h, int n) {
        return h == Hammer.Q ? q(n) : conway(n);
    }

    /** Grade a claimed strike. */
    public static Grade grade(Hammer h, int n, int claimed) {
        return strike(h, n) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the hammer rang true. It only ever listens to its own echoes.";
            case SLIPPED -> "Forgemaster: the hammer slipped. Look back by the last strikes and add.";
        };
    }
}
