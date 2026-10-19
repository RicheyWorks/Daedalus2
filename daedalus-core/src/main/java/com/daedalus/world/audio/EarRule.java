// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

/**
 * Richey's ear rule, shared by every audio piece: no bright or piercing tones. Fundamentals stay low-mid,
 * below {@link #MAX_FUNDAMENTAL_HZ}, and passing notes stay light.
 */
public final class EarRule {
    /** Highest fundamental any game sound may emit or any listener may hear, Hz. */
    public static final double MAX_FUNDAMENTAL_HZ = 800.0;

    private EarRule() { }

    /** True when {@code hz} is a positive fundamental under the ceiling. */
    public static boolean ok(double hz) {
        return hz > 0 && hz < MAX_FUNDAMENTAL_HZ;
    }

    /**
     * Returns {@code hz} when it obeys the ear rule, otherwise throws.
     *
     * @param what what is sounding, for the error message
     */
    public static double check(double hz, String what) {
        if (!ok(hz)) {
            throw new IllegalArgumentException(what + " at " + hz + " Hz breaks the ear rule (< " + MAX_FUNDAMENTAL_HZ + " Hz)");
        }
        return hz;
    }
}