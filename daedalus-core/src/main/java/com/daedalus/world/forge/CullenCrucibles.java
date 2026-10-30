// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;

/**
 * Cullen Crucibles: crucible n holds n x 2^n grains. Its Cullen pour n x 2^n + 1 and Woodall pour n x 2^n - 1 may be
 * prime (Cullen 1 x 2 + 1 = 3; Woodall 2 x 4 - 1 = 7, 23, 383, ...).
 *
 * <p>Reusable plain long API for 1 &lt;= n &lt;= {@link #MAX_N} (pours stay below 2^63): {@link #cullen},
 * {@link #woodall}, {@link #isPrimePour} (deterministic Miller-Rabin from {@link PrimorialPyres#isPrime}),
 * {@link #smallestFactor} by trial division up to {@link #TRIAL_LIMIT}, and {@link #primePours}.
 */
public final class CullenCrucibles {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_cullen_crucibles";
    /** Largest supported crucible. */
    public static final int MAX_N = 57;
    /** Trial-division bound for {@link #smallestFactor}. */
    public static final long TRIAL_LIMIT = 2_000_000L;

    /** Which pour. */
    public enum Kind { CULLEN, WOODALL }

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private CullenCrucibles() {
    }

    private static void check(int n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("crucible out of range: " + n);
        }
    }

    /** n x 2^n + 1. */
    public static long cullen(int n) {
        check(n);
        return ((long) n << n) + 1;
    }

    /** n x 2^n - 1. */
    public static long woodall(int n) {
        check(n);
        return ((long) n << n) - 1;
    }

    /** The pour of the given kind. */
    public static long pour(Kind k, int n) {
        return k == Kind.CULLEN ? cullen(n) : woodall(n);
    }

    /** True when the pour is prime. */
    public static boolean isPrimePour(Kind k, int n) {
        return PrimorialPyres.isPrime(pour(k, n));
    }

    /**
     * Smallest prime factor of the pour: the pour itself when prime, a factor up to {@link #TRIAL_LIMIT}, or -1 when
     * the pour is composite with no factor that small (and 1 for the unit pour 1).
     */
    public static long smallestFactor(Kind k, int n) {
        long v = pour(k, n);
        if (v == 1) {
            return 1;
        }
        if (PrimorialPyres.isPrime(v)) {
            return v;
        }
        for (long d = 2; d <= TRIAL_LIMIT && d * d <= v; d++) {
            if (v % d == 0) {
                return d;
            }
        }
        return -1;
    }

    /** The n in 1..limit whose pour of the given kind is prime. */
    public static List<Integer> primePours(Kind k, int limit) {
        if (limit < 0 || limit > MAX_N) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        List<Integer> out = new ArrayList<>();
        for (int n = 1; n <= limit; n++) {
            if (isPrimePour(k, n)) {
                out.add(n);
            }
        }
        return out;
    }

    /** Grade a claim that a pour is (or is not) prime. */
    public static Grade grade(Kind k, int n, boolean claimedPrime) {
        return isPrimePour(k, n) == claimedPrime ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you weighed the pour true. Prime pours are rare as river gold.";
            case SLIPPED -> "Forgemaster: the pour slipped. One grain more or less changes everything.";
        };
    }
}
