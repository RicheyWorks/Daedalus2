// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.dice;

/**
 * Exact odds for two six-sided storm dice and the Keeper's pass-line game: win on a come-out 7 or 11, lose on 2, 3 or
 * 12, otherwise the total becomes the point and you win if it repeats before a 7. Everything is exact rational
 * arithmetic over 36ths (pass-line win = 244/495).
 */
public final class DiceMath {

    private DiceMath() {
    }

    /** Ways (out of 36) to roll {@code total} with two dice. */
    public static int ways(int total) {
        if (total < 2 || total > 12) {
            return 0;
        }
        return 6 - Math.abs(total - 7);
    }

    public static double chance(int total) {
        return ways(total) / 36.0;
    }

    /** Whether {@code total} becomes a point on the come-out roll. */
    public static boolean isPoint(int total) {
        return total == 4 || total == 5 || total == 6 || total == 8 || total == 9 || total == 10;
    }

    /** Chance the point {@code p} repeats before a 7: ways(p) / (ways(p) + 6). */
    public static double pointMade(int point) {
        if (!isPoint(point)) {
            throw new IllegalArgumentException("not a point: " + point);
        }
        return ways(point) / (double) (ways(point) + 6);
    }

    /** Exact pass-line win chance as {numerator, denominator} in lowest terms (244 / 495). */
    public static long[] passWinFraction() {
        // Over a common denominator 36 x LCM of (ways + 6) for points = 36 x 990.
        long den = 36L * 990;
        long num = (ways(7) + ways(11)) * 990L;
        for (int p = 4; p <= 10; p++) {
            if (isPoint(p)) {
                long w = ways(p);
                num += w * w * (990 / (w + 6));
            }
        }
        long g = gcd(num, den);
        return new long[] {num / g, den / g};
    }

    public static double passWin() {
        long[] f = passWinFraction();
        return f[0] / (double) f[1];
    }

    /** True-odds payout ratio (profit per herb) of an odds bet on point {@code p}: 6 / ways(p) (2:1, 3:2, 6:5). */
    public static double trueOdds(int point) {
        if (!isPoint(point)) {
            throw new IllegalArgumentException("not a point: " + point);
        }
        return 6.0 / ways(point);
    }

    /**
     * House edge per herb wagered on pass plus {@code multiple} x odds behind every point: the odds bet is fair, so the
     * pass-line loss is spread over more herbs.
     */
    public static double edgePerHerbWagered(int multiple) {
        if (multiple < 0) {
            throw new IllegalArgumentException("multiple must be >= 0: " + multiple);
        }
        double passEv = 2 * passWin() - 1;
        double pPoint = 0;
        for (int p = 4; p <= 10; p++) {
            if (isPoint(p)) {
                pPoint += chance(p);
            }
        }
        double wagered = 1 + multiple * pPoint;
        return -passEv / wagered;
    }

    private static long gcd(long a, long b) {
        return b == 0 ? a : gcd(b, a % b);
    }
}
