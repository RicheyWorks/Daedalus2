// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G237 The Strongroom Lock: the ark strongroom's dial has {@code k} digits and opens as soon as
 * the last {@code n} digits entered match the code. The shortest key sequence that tries every
 * code is a de Bruijn sequence {@code B(k, n)} (built here from Lyndon words, the
 * Fredricksen-Kessler-Maiorana algorithm) plus its first {@code n - 1} digits again: length
 * {@code k^n + n - 1}, against {@code n * k^n} for trying codes one by one.
 */
public final class StrongroomLock {

    public static final String QUEST_ID = "q_strongroom_lock";
    public static final int MAX_CODES = 1 << 22;

    private StrongroomLock() { }

    /** Number of codes, {@code k^n}. */
    public static int codes(int k, int n) {
        if (k < 1 || n < 1) {
            throw new IllegalArgumentException("need k >= 1 and n >= 1");
        }
        long c = 1;
        for (int i = 0; i < n; i++) {
            c *= k;
            if (c > MAX_CODES) {
                throw new IllegalArgumentException("too many codes");
            }
        }
        return (int) c;
    }

    /** Cyclic de Bruijn sequence of length {@code k^n}. */
    public static int[] cyclic(int k, int n) {
        int[] out = new int[codes(k, n)];
        int[] a = new int[n + 1];
        int len = 0;
        // iterative FKM: generate Lyndon words in lexicographic order, emit those whose length divides n
        a[1] = 0;
        int i = 1;
        if (k == 1) {
            Arrays.fill(out, 0);
            return out;
        }
        while (true) {
            if (n % i == 0) {
                for (int j = 1; j <= i; j++) {
                    out[len++] = a[j];
                }
            }
            // next Lyndon word (Duval's successor)
            for (int j = i + 1; j <= n; j++) {
                a[j] = a[j - i];
            }
            i = n;
            while (i > 0 && a[i] == k - 1) {
                i--;
            }
            if (i == 0) {
                break;
            }
            a[i]++;
        }
        return out;
    }

    /** Linear key sequence that tries every code: cyclic sequence plus its first n-1 digits. */
    public static int[] keySequence(int k, int n) {
        int[] c = cyclic(k, n);
        int[] out = Arrays.copyOf(c, c.length + n - 1);
        for (int j = 0; j < n - 1; j++) {
            out[c.length + j] = c[j % c.length];
        }
        return out;
    }

    /** True when every one of the k^n codes appears as an n-digit window of {@code keyed}. */
    public static boolean triesEveryCode(int k, int n, int[] keyed) {
        int total = codes(k, n);
        boolean[] seen = new boolean[total];
        int found = 0;
        for (int s = 0; s + n <= keyed.length; s++) {
            int code = 0;
            for (int j = 0; j < n; j++) {
                int d = keyed[s + j];
                if (d < 0 || d >= k) {
                    return false;
                }
                code = code * k + d;
            }
            if (!seen[code]) {
                seen[code] = true;
                found++;
            }
        }
        return found == total;
    }

    /** Quest q_strongroom_lock: open the lock in the fewest possible key presses. */
    public static boolean quest(int k, int n, int[] keyed) {
        return keyed.length == codes(k, n) + n - 1 && triesEveryCode(k, n, keyed);
    }
}
