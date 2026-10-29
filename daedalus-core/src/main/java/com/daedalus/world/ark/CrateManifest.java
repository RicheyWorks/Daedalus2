// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * G274 The Crate Manifest: the quartermaster factors each manifest number into prime crate lots
 * with Pollard's rho (Brent's cycle detection, Miller-Rabin from {@link LanternHandshake}), then
 * counts its divisors and the lock settings coprime to it (Euler's totient). Manifest numbers are
 * below {@link LanternHandshake#MAX_MOD} so every product fits in a long.
 */
public final class CrateManifest {

    public static final String QUEST_ID = "q_crate_manifest";

    private CrateManifest() { }

    /** Prime factors of n with multiplicity, ascending; empty for n = 1. */
    public static List<Long> factor(long n) {
        if (n < 1 || n >= LanternHandshake.MAX_MOD) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        List<Long> out = new ArrayList<>();
        long m = n;
        for (long p : new long[] {2, 3, 5, 7, 11, 13}) {
            while (m % p == 0) {
                out.add(p);
                m /= p;
            }
        }
        split(m, out);
        Collections.sort(out);
        return List.copyOf(out);
    }

    private static void split(long n, List<Long> out) {
        if (n == 1) {
            return;
        }
        if (LanternHandshake.isPrime(n)) {
            out.add(n);
            return;
        }
        long d = rho(n);
        split(d, out);
        split(n / d, out);
    }

    /** A non-trivial factor of odd composite n (Brent's variant of Pollard's rho). */
    static long rho(long n) {
        for (long c = 1; ; c++) {
            long y = 2;
            long x = y;
            long g = 1;
            long q = 1;
            long ys = y;
            int r = 1;
            while (g == 1) {
                x = y;
                for (int i = 0; i < r; i++) {
                    y = (y * y + c) % n;
                }
                for (int k = 0; k < r && g == 1; k += 64) {
                    ys = y;
                    for (int i = 0; i < Math.min(64, r - k); i++) {
                        y = (y * y + c) % n;
                        q = q * Math.abs(x - y) % n;
                    }
                    g = gcd(q, n);
                }
                r <<= 1;
            }
            if (g == n) {
                do {
                    ys = (ys * ys + c) % n;
                    g = gcd(Math.abs(x - ys), n);
                } while (g == 1);
            }
            if (g != n) {
                return g;
            }
        }
    }

    static long gcd(long a, long b) {
        while (b != 0) {
            long t = a % b;
            a = b;
            b = t;
        }
        return a;
    }

    /** Prime to exponent, ascending. */
    public static Map<Long, Integer> lots(long n) {
        Map<Long, Integer> m = new TreeMap<>();
        for (long p : factor(n)) {
            m.merge(p, 1, Integer::sum);
        }
        return m;
    }

    /** Euler's totient: settings in 1..n coprime to n. */
    public static long totient(long n) {
        long t = n;
        for (long p : lots(n).keySet()) {
            t = t / p * (p - 1);
        }
        return t;
    }

    public static long divisorCount(long n) {
        long d = 1;
        for (int e : lots(n).values()) {
            d *= e + 1;
        }
        return d;
    }

    /** Quest q_crate_manifest: the quartermaster's lots must multiply back to n, all prime. */
    public static boolean quest(long n, List<Long> answer) {
        List<Long> sorted = new ArrayList<>(answer);
        Collections.sort(sorted);
        return sorted.equals(factor(n));
    }
}
