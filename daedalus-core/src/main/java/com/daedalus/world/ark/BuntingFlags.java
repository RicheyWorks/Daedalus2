// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.Arrays;

/**
 * G284 The Bunting Flags: the signal mate strings n flags in k colours around the mast ring.
 * Rings that differ only by turning the mast are the same bunting (necklaces); seen from both
 * sides of the sail, a flipped ring is also the same (bracelets). Counts both with Burnside's
 * lemma over the cyclic and dihedral groups, and gives each ring's canonical form.
 */
public final class BuntingFlags {

    public static final String QUEST_ID = "q_bunting_flags";
    public static final int MAX_FLAGS = 5000;

    private BuntingFlags() { }

    private static void check(int n, int k) {
        if (n < 1 || n > MAX_FLAGS || k < 1) {
            throw new IllegalArgumentException("need 1 <= n <= " + MAX_FLAGS + " and k >= 1");
        }
    }

    static int phi(int n) {
        int r = n;
        int m = n;
        for (int p = 2; (long) p * p <= m; p++) {
            if (m % p == 0) {
                while (m % p == 0) {
                    m /= p;
                }
                r -= r / p;
            }
        }
        if (m > 1) {
            r -= r / m;
        }
        return r;
    }

    /** Rings up to rotation: (1/n) sum over d | n of phi(d) k^(n/d). */
    public static BigInteger necklaces(int n, int k) {
        check(n, k);
        BigInteger bk = BigInteger.valueOf(k);
        BigInteger sum = BigInteger.ZERO;
        for (int d = 1; d <= n; d++) {
            if (n % d == 0) {
                sum = sum.add(BigInteger.valueOf(phi(d)).multiply(bk.pow(n / d)));
            }
        }
        return sum.divide(BigInteger.valueOf(n));
    }

    /** Rings up to rotation or flip: Burnside over the dihedral group of order 2n. */
    public static BigInteger bracelets(int n, int k) {
        check(n, k);
        BigInteger bk = BigInteger.valueOf(k);
        BigInteger rot = necklaces(n, k).multiply(BigInteger.valueOf(n));
        BigInteger flips;
        if (n % 2 == 1) {
            flips = BigInteger.valueOf(n).multiply(bk.pow((n + 1) / 2));
        } else {
            BigInteger half = BigInteger.valueOf(n / 2);
            flips = half.multiply(bk.pow(n / 2 + 1)).add(half.multiply(bk.pow(n / 2)));
        }
        return rot.add(flips).divide(BigInteger.valueOf(2L * n));
    }

    private static int[] rotate(int[] a, int s) {
        int[] r = new int[a.length];
        for (int i = 0; i < a.length; i++) {
            r[i] = a[(i + s) % a.length];
        }
        return r;
    }

    /** Lexicographically least rotation (and, when flips count, least of the ring and its mirror). */
    public static int[] canonical(int[] ring, boolean flips) {
        if (ring.length == 0) {
            throw new IllegalArgumentException("empty ring");
        }
        int[] best = null;
        int[] mirror = new int[ring.length];
        for (int i = 0; i < ring.length; i++) {
            mirror[i] = ring[ring.length - 1 - i];
        }
        int[][] sides = flips ? new int[][] {ring, mirror} : new int[][] {ring};
        for (int[] side : sides) {
            for (int s = 0; s < side.length; s++) {
                int[] r = rotate(side, s);
                if (best == null || Arrays.compare(r, best) < 0) {
                    best = r;
                }
            }
        }
        return best;
    }

    /** Quest q_bunting_flags: are the two rings the same bunting when seen from either side? */
    public static boolean quest(int[] a, int[] b, boolean claimSame) {
        boolean same = a.length == b.length && Arrays.equals(canonical(a, true), canonical(b, true));
        return same == claimSame;
    }
}