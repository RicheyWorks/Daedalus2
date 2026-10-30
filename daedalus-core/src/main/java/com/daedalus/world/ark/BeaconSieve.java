// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G246 The Beacon Sieve: the ark's lighthouse keeper lights beacons only on prime-numbered mooring
 * posts. {@link #primesUpTo} and {@link #count} use the sieve of Eratosthenes, {@link #kth} names
 * the k-th beacon, and {@link #segment} surveys a far stretch {@code [lo, hi]} with a segmented
 * sieve that only needs primes up to {@code sqrt(hi)}.
 */
public final class BeaconSieve {

    public static final String QUEST_ID = "q_beacon_sieve";
    public static final int MAX_N = 100_000_000;
    public static final long MAX_HI = 1_000_000_000_000L;
    public static final int MAX_SPAN = 10_000_000;

    private BeaconSieve() { }

    /** {@code composite[i]} is true for non-primes 0..n. */
    static boolean[] composite(int n) {
        if (n < 0 || n > MAX_N) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        boolean[] c = new boolean[n + 1];
        c[0] = true;
        if (n >= 1) {
            c[1] = true;
        }
        for (long p = 2; p * p <= n; p++) {
            if (!c[(int) p]) {
                for (long m = p * p; m <= n; m += p) {
                    c[(int) m] = true;
                }
            }
        }
        return c;
    }

    public static int[] primesUpTo(int n) {
        boolean[] c = composite(n);
        int[] out = new int[n + 1];
        int k = 0;
        for (int i = 2; i <= n; i++) {
            if (!c[i]) {
                out[k++] = i;
            }
        }
        return Arrays.copyOf(out, k);
    }

    public static int count(int n) {
        return primesUpTo(n).length;
    }

    /** The k-th prime, 1-based (kth(1) = 2). */
    public static int kth(int k) {
        if (k < 1 || k > 5_000_000) {
            throw new IllegalArgumentException("k out of range: " + k);
        }
        double lk = Math.log(k);
        int bound = k < 6 ? 15 : (int) Math.ceil(k * (lk + Math.log(lk))) + 1;
        return primesUpTo(bound)[k - 1];
    }

    /** Primes in {@code [lo, hi]} by segmented sieve. */
    public static long[] segment(long lo, long hi) {
        if (lo < 0 || hi > MAX_HI || hi < lo || hi - lo >= MAX_SPAN) {
            throw new IllegalArgumentException("bad stretch [" + lo + ", " + hi + "]");
        }
        long from = Math.max(lo, 2);
        if (hi < from) {
            return new long[0];
        }
        int root = (int) Math.sqrt((double) hi);
        while ((long) (root + 1) * (root + 1) <= hi) {
            root++;
        }
        boolean[] hit = new boolean[(int) (hi - from + 1)];
        for (int p : primesUpTo(root)) {
            long start = Math.max((long) p * p, (from + p - 1) / p * p);
            for (long m = start; m <= hi; m += p) {
                hit[(int) (m - from)] = true;
            }
        }
        long[] out = new long[hit.length];
        int k = 0;
        for (int i = 0; i < hit.length; i++) {
            if (!hit[i]) {
                out[k++] = from + i;
            }
        }
        return Arrays.copyOf(out, k);
    }

    /** Trial-division check, used to validate a keeper's claim. */
    public static boolean isPrime(long x) {
        if (x < 2) {
            return false;
        }
        for (long d = 2; d * d <= x; d++) {
            if (x % d == 0) {
                return false;
            }
        }
        return true;
    }

    /** Quest q_beacon_sieve: the keeper must name the post of the k-th beacon. */
    public static boolean quest(int k, int post) {
        return kth(k) == post;
    }
}
