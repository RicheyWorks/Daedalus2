// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Temper Trials (contest gap G261): the smith has {@code k} test bars and {@code n} heat levels. A bar heated above
 * the hidden crack point shatters; one heated at or below it survives and can be reused. Find the fewest heatings that
 * always pin the crack point, and the next level to try.
 *
 * <p>The tool is plain: {@link #cover} is the egg-drop coverage f(t, k) = f(t-1, k-1) + f(t-1, k) + 1,
 * {@link #minTrials} the smallest t with f(t, k) &gt;= n, and {@link #nextProbe} the optimal level to test inside an
 * open range. Any project can use it for worst-case search with a limited number of failures.
 */
public final class TemperTrials {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_temper_trials";

    /** How a trial run went. */
    public enum Grade { MASTERFUL, WASTEFUL }

    private TemperTrials() {
    }

    /** A seeded hidden crack point in 0..n (0 = even the lowest level cracks the bar). */
    public static int crackPoint(long seed, int n) {
        if (n < 0) {
            throw new IllegalArgumentException("need n >= 0");
        }
        return new SplittableRandom(seed).nextInt(n + 1);
    }

    /** Most heat levels that t heatings with k bars can always resolve (saturates at Long.MAX_VALUE). */
    public static long cover(int t, int k) {
        if (t < 0 || k < 0) {
            throw new IllegalArgumentException("need t >= 0 and k >= 0");
        }
        long[] f = new long[k + 1];
        for (int step = 1; step <= t; step++) {
            for (int j = k; j >= 1; j--) {
                long s = f[j - 1] + f[j] + 1;
                f[j] = s < 0 || f[j - 1] == Long.MAX_VALUE || f[j] == Long.MAX_VALUE ? Long.MAX_VALUE : s;
            }
        }
        return f[k];
    }

    /** Fewest heatings that always pin the crack point among n levels with k bars. */
    public static int minTrials(int k, int n) {
        if (n < 0 || k < 0 || (k == 0 && n > 0)) {
            throw new IllegalArgumentException("need n >= 0 and k >= 1 when n > 0");
        }
        int t = 0;
        while (cover(t, k) < n) {
            t++;
        }
        return t;
    }

    /** Best level to heat next when levels up to {@code safe} survive and {@code cracks} is known to crack. */
    public static int nextProbe(int k, int safe, int cracks) {
        int open = cracks - safe - 1;
        if (open < 1) {
            throw new IllegalArgumentException("nothing left to test");
        }
        int t = minTrials(k, open);
        long step = cover(t - 1, k - 1) + 1;
        return (int) Math.min(cracks - 1L, safe + step);
    }

    /** Plays the optimal strategy against a hidden crack point; returns the heatings used. */
    public static int play(int k, int n, int crack) {
        if (crack < 0 || crack > n) {
            throw new IllegalArgumentException("crack point out of range");
        }
        int safe = 0;
        int cracks = n + 1;
        int bars = k;
        int used = 0;
        while (cracks - safe > 1) {
            int probe = nextProbe(bars, safe, cracks);
            used++;
            if (probe <= crack) {
                safe = probe;
            } else {
                cracks = probe;
                bars--;
            }
        }
        if (safe != crack) {
            throw new IllegalStateException("strategy failed");
        }
        return used;
    }

    /** MASTERFUL only if the claimed worst case is the true minimum. */
    public static Grade grade(int k, int n, int claimedTrials) {
        return claimedTrials == minTrials(k, n) ? Grade.MASTERFUL : Grade.WASTEFUL;
    }

    /** The Forgemaster's line for a trial run. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case MASTERFUL -> "Forgemaster: not one heating wasted, and the crack point is ours. Spoken like a master.";
            case WASTEFUL -> "Forgemaster: you burned more bars and coal than the job needed. Plan the heats again.";
        };
    }
}
