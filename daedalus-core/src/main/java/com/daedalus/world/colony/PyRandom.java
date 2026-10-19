// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Bit-for-bit port of CPython's {@code random.Random} (MT19937) for the calls the Python game cores use:
 * {@code Random(int)}, {@code random()}, {@code getrandbits(k)}, {@code choice}, {@code sample}.
 *
 * <p>The Colony Ledger, island chemistry and other {@code tools/} cores are written in Python first and seeded
 * with {@code random.Random(seed)}. A Java port only agrees with them if it draws the very same numbers, so this
 * class reproduces CPython 3 exactly (seed from |n| split into 32-bit words, init_by_array, 53-bit random(),
 * rejection-sampled randbelow, and both branches of {@code sample}). Reusable by any Java port of a Python core.
 */
public final class PyRandom {
    private static final int N = 624;
    private static final int M = 397;
    private final int[] mt = new int[N];
    private int mti;

    public PyRandom(long seed) {
        long a = Math.abs(seed);
        List<Integer> key = new ArrayList<>();
        do {
            key.add((int) (a & 0xffffffffL));
            a >>>= 32;
        } while (a != 0);
        initByArray(key.stream().mapToInt(Integer::intValue).toArray());
    }

    private void initGenrand(int s) {
        mt[0] = s;
        for (mti = 1; mti < N; mti++) {
            mt[mti] = 1812433253 * (mt[mti - 1] ^ (mt[mti - 1] >>> 30)) + mti;
        }
    }

    private void initByArray(int[] key) {
        initGenrand(19650218);
        int i = 1;
        int j = 0;
        for (int k = Math.max(N, key.length); k > 0; k--) {
            mt[i] = (mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >>> 30)) * 1664525)) + key[j] + j;
            i++;
            j++;
            if (i >= N) {
                mt[0] = mt[N - 1];
                i = 1;
            }
            if (j >= key.length) {
                j = 0;
            }
        }
        for (int k = N - 1; k > 0; k--) {
            mt[i] = (mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >>> 30)) * 1566083941)) - i;
            i++;
            if (i >= N) {
                mt[0] = mt[N - 1];
                i = 1;
            }
        }
        mt[0] = 0x80000000;
    }

    /** One raw 32-bit output, as an unsigned value in a long. */
    long genrand() {
        if (mti >= N) {
            for (int kk = 0; kk < N; kk++) {
                int y = (mt[kk] & 0x80000000) | (mt[(kk + 1) % N] & 0x7fffffff);
                mt[kk] = mt[(kk + M) % N] ^ (y >>> 1) ^ ((y & 1) != 0 ? 0x9908b0df : 0);
            }
            mti = 0;
        }
        int y = mt[mti++];
        y ^= y >>> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >>> 18;
        return y & 0xffffffffL;
    }

    /** {@code random.random()}: a float in [0, 1) with 53 random bits. */
    public double random() {
        long a = genrand() >>> 5;
        long b = genrand() >>> 6;
        return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0);
    }

    /** {@code random.getrandbits(k)} for 0 &lt; k &lt;= 62. */
    public long getrandbits(int k) {
        if (k <= 0 || k > 62) {
            throw new IllegalArgumentException("k must be 1..62");
        }
        if (k <= 32) {
            return genrand() >>> (32 - k);
        }
        long lo = genrand();
        long hi = genrand() >>> (64 - k);
        return (hi << 32) | lo;
    }

    /** CPython {@code _randbelow_with_getrandbits(n)}. */
    public int randbelow(int n) {
        if (n <= 0) {
            throw new IllegalArgumentException("empty range");
        }
        int k = 32 - Integer.numberOfLeadingZeros(n);
        long r = getrandbits(k);
        while (r >= n) {
            r = getrandbits(k);
        }
        return (int) r;
    }

    /** {@code random.choice(seq)}. */
    public <T> T choice(List<T> seq) {
        if (seq.isEmpty()) {
            throw new IllegalArgumentException("Cannot choose from an empty sequence");
        }
        return seq.get(randbelow(seq.size()));
    }

    /** {@code random.sample(population, k)}, both the pool and the set branch, same draws as CPython 3.11+. */
    public <T> List<T> sample(List<T> population, int k) {
        int n = population.size();
        if (k < 0 || k > n) {
            throw new IllegalArgumentException("Sample larger than population or is negative");
        }
        List<T> result = new ArrayList<>(k);
        int setsize = 21;
        if (k > 5) {
            setsize += (int) Math.pow(4, Math.ceil(Math.log(k * 3) / Math.log(4)));
        }
        if (n <= setsize) {
            List<T> pool = new ArrayList<>(population);
            for (int i = 0; i < k; i++) {
                int j = randbelow(n - i);
                result.add(pool.get(j));
                pool.set(j, pool.get(n - i - 1));
            }
        } else {
            Set<Integer> selected = new HashSet<>();
            for (int i = 0; i < k; i++) {
                int j = randbelow(n);
                while (selected.contains(j)) {
                    j = randbelow(n);
                }
                selected.add(j);
                result.add(population.get(j));
            }
        }
        return result;
    }
}
