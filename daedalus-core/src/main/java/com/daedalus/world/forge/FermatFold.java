// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Fermat Fold: an odd ingot of n grains is folded into a rectangle a x b as close to square as possible. The smith
 * walks x up from ceil(sqrt n) until x^2 - n is a perfect square y^2 (Fermat's method), giving n = (x - y)(x + y).
 *
 * <p>Reusable plain long API: {@link #fold} returns {a, b, steps} with a &lt;= b the divisor pair nearest sqrt n, or an
 * empty array when the walk exceeds the step budget. Odd n in 1..{@link #MAX_N}, budgets up to {@link #MAX_STEPS}.
 */
public final class FermatFold {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_fermat_fold";
    /** Largest supported ingot. */
    public static final long MAX_N = 1_000_000_000_000_000_000L;
    /** Largest supported step budget. */
    public static final long MAX_STEPS = 10_000_000L;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private FermatFold() {
    }

    static long isqrt(long n) {
        long r = (long) Math.sqrt((double) n);
        while (r * r > n) {
            r--;
        }
        while ((r + 1) * (r + 1) <= n) {
            r++;
        }
        return r;
    }

    /** {a, b, steps} with a*b = n, a &lt;= b nearest sqrt n; empty when the budget runs out. */
    public static long[] fold(long n, long maxSteps) {
        if (n < 1 || n > MAX_N || (n & 1) == 0) {
            throw new IllegalArgumentException("need odd n in range: " + n);
        }
        if (maxSteps < 0 || maxSteps > MAX_STEPS) {
            throw new IllegalArgumentException("step budget out of range: " + maxSteps);
        }
        long s = isqrt(n);
        long x = s * s == n ? s : s + 1;
        for (long k = 0; k <= maxSteps; k++) {
            long r = x * x - n;
            long y = isqrt(r);
            if (y * y == r) {
                return new long[] {x - y, x + y, k};
            }
            x++;
        }
        return new long[0];
    }

    /** Grade a claimed fold a x b of n: it must multiply to n and be the pair nearest square. */
    public static Grade grade(long n, long a, long b) {
        long lo = Math.min(a, b);
        long[] f = fold(n, MAX_STEPS);
        boolean ok = f.length == 3 && lo == f[0] && Math.max(a, b) == f[1];
        return ok ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: squared off as near as the grains allow. Fermat folds true.";
            case SLIPPED -> "Forgemaster: the fold slipped. Walk x up from the root until x^2 - n is square.";
        };
    }
}
