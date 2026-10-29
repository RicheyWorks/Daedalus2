// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

/**
 * G263 The Rope Coils: the ark's rope locker stocks coils in Fibonacci lengths 1, 2, 3, 5, 8, ...
 * {@link #cut} makes any length from coils of which no two are adjacent Fibonacci numbers
 * (Zeckendorf's theorem: that choice is unique, and greedy finds it). {@link #fib} sizes the
 * n-th coil exactly by fast doubling, {@link #fibMod} modulo m by 2x2 matrix power.
 */
public final class RopeCoils {

    public static final String QUEST_ID = "q_rope_coils";
    /** F(2..92): every Fibonacci number from 1 that fits in a long, ascending. */
    private static final long[] COILS = new long[91];

    static {
        COILS[0] = 1;
        COILS[1] = 2;
        for (int i = 2; i < COILS.length; i++) {
            COILS[i] = COILS[i - 1] + COILS[i - 2];
        }
    }

    private RopeCoils() { }

    /** F(n) exactly, F(0) = 0, F(1) = 1, by fast doubling. */
    public static BigInteger fib(int n) {
        if (n < 0 || n > 1_000_000) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        return doubling(n)[0];
    }

    private static BigInteger[] doubling(int n) {
        if (n == 0) {
            return new BigInteger[] {BigInteger.ZERO, BigInteger.ONE};
        }
        BigInteger[] h = doubling(n >>> 1);
        BigInteger a = h[0];
        BigInteger b = h[1];
        BigInteger c = a.multiply(b.shiftLeft(1).subtract(a));
        BigInteger d = a.multiply(a).add(b.multiply(b));
        return (n & 1) == 0 ? new BigInteger[] {c, d} : new BigInteger[] {d, c.add(d)};
    }

    /** F(n) mod m via [[1,1],[1,0]]^n; m in 1..2^31. */
    public static long fibMod(long n, long m) {
        if (n < 0 || m < 1 || m > (1L << 31)) {
            throw new IllegalArgumentException("bad n or m");
        }
        long[] r = {1 % m, 0, 0, 1 % m};
        long[] base = {1 % m, 1 % m, 1 % m, 0};
        for (long e = n; e > 0; e >>>= 1) {
            if ((e & 1) != 0) {
                r = mul(r, base, m);
            }
            base = mul(base, base, m);
        }
        return r[1];
    }

    private static long[] mul(long[] x, long[] y, long m) {
        return new long[] {
            (x[0] * y[0] % m + x[1] * y[2] % m) % m,
            (x[0] * y[1] % m + x[1] * y[3] % m) % m,
            (x[2] * y[0] % m + x[3] * y[2] % m) % m,
            (x[2] * y[1] % m + x[3] * y[3] % m) % m,
        };
    }

    /** The unique Zeckendorf cut of {@code length}: coil lengths, largest first. */
    public static List<Long> cut(long length) {
        if (length < 0) {
            throw new IllegalArgumentException("length < 0");
        }
        List<Long> out = new ArrayList<>();
        long left = length;
        for (int i = COILS.length - 1; i >= 0 && left > 0; i--) {
            if (COILS[i] <= left) {
                out.add(COILS[i]);
                left -= COILS[i];
                i--;
            }
        }
        return List.copyOf(out);
    }

    /** True when {@code coils} are Fibonacci coils, none adjacent or repeated, summing to length. */
    public static boolean valid(long length, List<Long> coils) {
        long sum = 0;
        int prev = Integer.MAX_VALUE;
        for (Long c : coils) {
            int idx = c == null ? -1 : java.util.Arrays.binarySearch(COILS, c);
            if (idx < 0 || idx >= prev - 1) {
                return false;
            }
            prev = idx;
            sum += c;
            if (sum < 0) {
                return false;
            }
        }
        return sum == length;
    }

    /** Quest q_rope_coils: the bosun's coils must be the non-adjacent cut of the length. */
    public static boolean quest(long length, List<Long> coils) {
        return valid(length, coils);
    }
}
