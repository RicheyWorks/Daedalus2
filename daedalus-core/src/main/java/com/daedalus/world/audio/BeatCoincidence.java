// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

/**
 * Reusable beat-coincidence solver (Chinese remainder over small periods), first used by
 * {@link DripCaveChorus}. Any realm with repeating timers (drips, bells, tides, patrols) can ask when they
 * all line up.
 *
 * <p>A cycle {@code i} fires on beat {@code t} when {@code t mod periods[i] == offsets[i]}. Works for
 * non-coprime periods (it checks consistency instead of assuming coprimality).
 */
public final class BeatCoincidence {
    private BeatCoincidence() { }

    /** Least common multiple of all periods (the pattern repeats with this length). */
    public static long lcm(int... periods) {
        long l = 1;
        for (int p : periods) {
            if (p < 1) {
                throw new IllegalArgumentException("period must be >= 1: " + p);
            }
            l = l / gcd(l, p) * p;
        }
        return l;
    }

    /**
     * First beat {@code t >= from} on which every cycle fires, or -1 if they never coincide.
     *
     * @param periods beat period of each cycle (>= 1)
     * @param offsets beat offset of each cycle, {@code 0 <= offset < period}
     * @param from first beat to consider (>= 0)
     */
    public static long next(int[] periods, int[] offsets, long from) {
        if (periods.length != offsets.length || periods.length == 0) {
            throw new IllegalArgumentException("need matching, non-empty periods and offsets");
        }
        if (from < 0) {
            throw new IllegalArgumentException("from must be >= 0");
        }
        long r = 0;
        long m = 1;
        for (int i = 0; i < periods.length; i++) {
            int p = periods[i];
            int o = offsets[i];
            if (p < 1 || o < 0 || o >= p) {
                throw new IllegalArgumentException("bad cycle " + p + "/" + o);
            }
            long g = gcd(m, p);
            if (Math.floorMod(o - r, g) != 0) {
                return -1;
            }
            long step = m / g;
            long k = 0;
            while (Math.floorMod(r + k * m - o, p) != 0) {
                k++;
            }
            r += k * m;
            m = step * p;
            r = Math.floorMod(r, m);
        }
        long t = r;
        if (t < from) {
            t += ((from - t + m - 1) / m) * m;
        }
        return t;
    }

    private static long gcd(long a, long b) {
        return b == 0 ? a : gcd(b, a % b);
    }
}