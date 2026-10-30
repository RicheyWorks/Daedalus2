// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

/**
 * A tiny seeded random source for the Combat Odds Engine (SplitMix64). It is deliberately not {@code java.util.Random}:
 * the sequence is fixed by this file alone, so a seed gives the same odds on every JVM and could be ported to C++ line
 * for line. {@link #forTrial(long, long)} derives an independent stream per trial, so a report does not depend on the
 * order trials run in.
 */
public final class OddsRng {

    private static final long GAMMA = 0x9E3779B97F4A7C15L;

    private long state;

    public OddsRng(long seed) {
        this.state = seed;
    }

    /** The stream for one trial of a run: a pure function of (seed, trial). */
    public static OddsRng forTrial(long seed, long trial) {
        return new OddsRng(mix(seed + GAMMA * (trial + 1)));
    }

    static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }

    public long nextLong() {
        state += GAMMA;
        return mix(state);
    }

    /** Uniform in [0, 1) with 53 bits of precision. */
    public double nextDouble() {
        return (nextLong() >>> 11) * 0x1.0p-53;
    }

    /** True with probability {@code p} (clamped to [0, 1]). */
    public boolean chance(double p) {
        if (p <= 0) {
            return false;
        }
        if (p >= 1) {
            return true;
        }
        return nextDouble() < p;
    }
}