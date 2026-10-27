// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

/**
 * G283 The Square Deck: the shipwright wants a square deck of x by x planks that, less one plank,
 * splits exactly into D equal square hatches of y by y, so x^2 - D y^2 = 1 (Pell's equation).
 * Expands sqrt(D) as a periodic continued fraction with the exact integer recurrence, reads the
 * least solution from its convergents, and steps to larger solutions. D is a non-square in
 * 2..MAX_D.
 */
public final class SquareDeck {

    public static final String QUEST_ID = "q_square_deck";
    public static final long MAX_D = Integer.MAX_VALUE;

    /** A deck solution: x^2 - D y^2 = 1. */
    public record Deck(BigInteger x, BigInteger y) { }

    private SquareDeck() { }

    private static long check(long d) {
        if (d < 2 || d > MAX_D) {
            throw new IllegalArgumentException("D out of range: " + d);
        }
        long a0 = isqrt(d);
        if (a0 * a0 == d) {
            throw new IllegalArgumentException("D is a perfect square: " + d);
        }
        return a0;
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

    /** [a0, a1, ..., ar] where a1..ar is one full period of sqrt(D) (ar = 2 a0). */
    public static List<Long> expansion(long d) {
        long a0 = check(d);
        List<Long> out = new ArrayList<>();
        out.add(a0);
        long m = 0;
        long den = 1;
        long a = a0;
        do {
            m = den * a - m;
            den = (d - m * m) / den;
            a = (a0 + m) / den;
            out.add(a);
        } while (a != 2 * a0);
        return List.copyOf(out);
    }

    public static int period(long d) {
        return expansion(d).size() - 1;
    }

    /** Least solution with x > 1, from convergent r - 1 (r even) or 2r - 1 (r odd). */
    public static Deck least(long d) {
        List<Long> e = expansion(d);
        int r = e.size() - 1;
        int last = r % 2 == 0 ? r - 1 : 2 * r - 1;
        BigInteger pPrev = BigInteger.ONE;
        BigInteger qPrev = BigInteger.ZERO;
        BigInteger p = BigInteger.valueOf(e.get(0));
        BigInteger q = BigInteger.ONE;
        for (int k = 1; k <= last; k++) {
            BigInteger a = BigInteger.valueOf(e.get((k - 1) % r + 1));
            BigInteger np = a.multiply(p).add(pPrev);
            BigInteger nq = a.multiply(q).add(qPrev);
            pPrev = p;
            qPrev = q;
            p = np;
            q = nq;
        }
        return new Deck(p, q);
    }

    /** The k-th solution (k >= 1), by composing the least one with itself. */
    public static Deck nth(long d, int k) {
        if (k < 1 || k > 10_000) {
            throw new IllegalArgumentException("k out of range: " + k);
        }
        Deck first = least(d);
        BigInteger bd = BigInteger.valueOf(d);
        Deck cur = first;
        for (int i = 1; i < k; i++) {
            cur = new Deck(
                    cur.x().multiply(first.x()).add(bd.multiply(cur.y()).multiply(first.y())),
                    cur.x().multiply(first.y()).add(cur.y().multiply(first.x())));
        }
        return cur;
    }

    public static boolean solves(long d, BigInteger x, BigInteger y) {
        return x.multiply(x).subtract(BigInteger.valueOf(d).multiply(y).multiply(y)).equals(BigInteger.ONE);
    }

    /** Quest q_square_deck: any deck with y >= 1 that solves x^2 - D y^2 = 1. */
    public static boolean quest(long d, BigInteger x, BigInteger y) {
        check(d);
        return y.signum() > 0 && x.signum() > 0 && solves(d, x, y);
    }
}