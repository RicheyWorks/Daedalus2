// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;

/**
 * G265 The Gear Train: the ark's windlass needs a gear pair {@code p:q}, each gear with at most
 * {@code N} teeth, as close as possible to a target ratio {@code a/b}. {@link #best} walks the
 * Stern-Brocot tree in continued-fraction-sized jumps, so it takes O(log N) steps; when the walk
 * runs out of teeth the answer is the nearer of the two bounding fractions (ties go to the
 * smaller ratio). {@link #path} and {@link #fromPath} spell any ratio as an L/R route from 1:1.
 */
public final class GearTrain {

    public static final String QUEST_ID = "q_gear_train";
    public static final long MAX_TEETH = 1_000_000L;
    public static final long MAX_TARGET = 1_000_000_000L;

    /** A reduced gear ratio p:q (q &gt;= 1). */
    public record Ratio(long p, long q) { }

    private GearTrain() { }

    /** Closest p/q to a/b with 0 &lt;= p &lt;= n and 1 &lt;= q &lt;= n. */
    public static Ratio best(long a, long b, long n) {
        if (a < 0 || b < 1 || a > MAX_TARGET || b > MAX_TARGET || n < 1 || n > MAX_TEETH) {
            throw new IllegalArgumentException("bad target or teeth");
        }
        long lp = 0;
        long lq = 1;
        long hp = 1;
        long hq = 0;
        while (true) {
            long k1 = (a * lq - lp * b) / (hp * b - a * hq);
            long k = Math.min(k1, limit(lp, lq, hp, hq, n));
            lp += k * hp;
            lq += k * hq;
            if (lp * b == a * lq) {
                return new Ratio(lp, lq);
            }
            if (k < k1) {
                break;
            }
            long k2 = (hp * b - a * hq) / (a * lq - lp * b);
            k = Math.min(k2, limit(hp, hq, lp, lq, n));
            hp += k * lp;
            hq += k * lq;
            if (hp * b == a * hq) {
                return new Ratio(hp, hq);
            }
            if (k < k2) {
                break;
            }
        }
        if (hq == 0) {
            return new Ratio(lp, lq);
        }
        BigInteger dl = BigInteger.valueOf(Math.abs(a * lq - lp * b)).multiply(BigInteger.valueOf(hq));
        BigInteger dh = BigInteger.valueOf(Math.abs(hp * b - a * hq)).multiply(BigInteger.valueOf(lq));
        return dh.compareTo(dl) < 0 ? new Ratio(hp, hq) : new Ratio(lp, lq);
    }

    /** Largest k with x + k*y staying within n teeth on both gears. */
    private static long limit(long xp, long xq, long yp, long yq, long n) {
        long k = Long.MAX_VALUE;
        if (yp > 0) {
            k = Math.min(k, (n - xp) / yp);
        }
        if (yq > 0) {
            k = Math.min(k, (n - xq) / yq);
        }
        return Math.max(k, 0);
    }

    /** Stern-Brocot route from 1:1 to p:q (R = larger ratio, L = smaller). */
    public static String path(long p, long q) {
        if (p < 1 || q < 1 || p > MAX_TEETH || q > MAX_TEETH) {
            throw new IllegalArgumentException("bad ratio");
        }
        long g = BigInteger.valueOf(p).gcd(BigInteger.valueOf(q)).longValue();
        long x = p / g;
        long y = q / g;
        StringBuilder sb = new StringBuilder();
        while (x != y) {
            if (x > y) {
                long k = (x - 1) / y;
                sb.append("R".repeat((int) k));
                x -= k * y;
            } else {
                long k = (y - 1) / x;
                sb.append("L".repeat((int) k));
                y -= k * x;
            }
        }
        return sb.toString();
    }

    public static Ratio fromPath(String route) {
        long lp = 0;
        long lq = 1;
        long hp = 1;
        long hq = 0;
        for (int i = 0; i < route.length(); i++) {
            char c = route.charAt(i);
            long mp = lp + hp;
            long mq = lq + hq;
            if (c == 'R') {
                lp = mp;
                lq = mq;
            } else if (c == 'L') {
                hp = mp;
                hq = mq;
            } else {
                throw new IllegalArgumentException("bad step: " + c);
            }
        }
        return new Ratio(lp + hp, lq + hq);
    }

    /** Quest q_gear_train: the engineer's pair must be as close as the best pair within n teeth. */
    public static boolean quest(long a, long b, long n, long p, long q) {
        if (p < 0 || q < 1 || p > n || q > n) {
            return false;
        }
        Ratio r = best(a, b, n);
        BigInteger mine = BigInteger.valueOf(Math.abs(p * b - a * q)).multiply(BigInteger.valueOf(r.q()));
        BigInteger opt = BigInteger.valueOf(Math.abs(r.p() * b - a * r.q())).multiply(BigInteger.valueOf(q));
        return mine.compareTo(opt) <= 0;
    }
}
