// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G303 The Log Decimals: the navigator logs a fraction a/b of a league in a given base as its
 * whole part, a pre-period and a repeating block, e.g. 1/12 = 0.08(3) in base ten. Lengths come
 * from number theory (strip the base's primes from the reduced denominator for the pre-period,
 * then the multiplicative order of the base for the period); digits come from long division.
 */
public final class LogDecimals {

    public static final String QUEST_ID = "q_log_decimals";
    public static final long MAX_DEN = 10_000_000L;
    private static final String DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz";

    private LogDecimals() { }

    private static void check(long a, long b, int base) {
        if (a < 0 || b < 1 || b > MAX_DEN || base < 2 || base > DIGITS.length()) {
            throw new IllegalArgumentException("need a >= 0, 1 <= b <= " + MAX_DEN + ", 2 <= base <= 36");
        }
    }

    static long gcd(long x, long y) {
        long p = x;
        long q = y;
        while (q != 0) {
            long t = p % q;
            p = q;
            q = t;
        }
        return p;
    }

    private static long reducedDen(long a, long b) {
        return a == 0 ? 1 : b / gcd(a, b);
    }

    /** Digits after the point before the repeat starts. */
    public static int prePeriod(long a, long b, int base) {
        check(a, b, base);
        long q = reducedDen(a, b);
        int k = 0;
        for (long g = gcd(q, base); g > 1; g = gcd(q, base)) {
            q /= g;
            k++;
        }
        return k;
    }

    /** Length of the repeating block, 0 when the expansion ends. */
    public static int period(long a, long b, int base) {
        check(a, b, base);
        long q = reducedDen(a, b);
        for (long g = gcd(q, base); g > 1; g = gcd(q, base)) {
            q /= g;
        }
        if (q == 1) {
            return 0;
        }
        long r = base % q;
        int k = 1;
        while (r != 1) {
            r = r * base % q;
            k++;
        }
        return k;
    }

    /** The expansion as text: whole part in the base, then ".pre(rep)" (or ".pre", or nothing). */
    public static String expand(long a, long b, int base) {
        int pre = prePeriod(a, b, base);
        int per = period(a, b, base);
        StringBuilder sb = new StringBuilder(Long.toString(a / b, base));
        if (pre + per == 0) {
            return sb.toString();
        }
        sb.append('.');
        long r = a % b;
        for (int i = 0; i < pre + per; i++) {
            if (i == pre) {
                sb.append('(');
            }
            r *= base;
            sb.append(DIGITS.charAt((int) (r / b)));
            r %= b;
        }
        if (per > 0) {
            sb.append(')');
        }
        return sb.toString();
    }

    /** Quest q_log_decimals: the navigator names how many digits repeat. */
    public static boolean quest(long a, long b, int base, int answer) {
        return period(a, b, base) == answer;
    }
}