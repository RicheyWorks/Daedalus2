// SPDX-License-Identifier: MIT

package com.daedalus.world.pilot;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * CPython {@code random.Random(str)} (seed version 2) for string-seeded game cores: key = utf-8 bytes followed by
 * their SHA-512, read as one big-endian integer and fed to MT19937 {@code init_by_array} in 32-bit limbs, least
 * significant first. Draws match CPython and the C++ {@code daedalus::pyrandom::PyRandom} in
 * DaedalusPyRandomCore.h, so a seed string gives the same game in Python, Java and Unreal. Not cryptographic.
 */
public final class PyStringRandom {

    private static final int N = 624;
    private final int[] mt = new int[N];
    private int index = N;

    public PyStringRandom(String seed) {
        byte[] text = seed.getBytes(StandardCharsets.UTF_8);
        byte[] digest;
        try {
            digest = MessageDigest.getInstance("SHA-512").digest(text);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-512 is required by every Java runtime", e);
        }
        byte[] bytes = new byte[text.length + digest.length];
        System.arraycopy(text, 0, bytes, 0, text.length);
        System.arraycopy(digest, 0, bytes, text.length, digest.length);
        int words = (bytes.length + 3) / 4;
        int[] key = new int[words];
        int used = 0;
        for (int end = bytes.length; end > 0; end = Math.max(0, end - 4)) {
            int v = 0;
            for (int b = Math.max(0, end - 4); b < end; b++) {
                v = (v << 8) | (bytes[b] & 0xff);
            }
            key[used++] = v;
        }
        while (used > 1 && key[used - 1] == 0) {
            used--;
        }
        initByArray(key, used);
    }

    private void initByArray(int[] key, int len) {
        mt[0] = 19650218;
        for (int k = 1; k < N; k++) {
            mt[k] = 1812433253 * (mt[k - 1] ^ (mt[k - 1] >>> 30)) + k;
        }
        int i = 1;
        int j = 0;
        for (int k = Math.max(N, len); k > 0; k--) {
            mt[i] = (mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >>> 30)) * 1664525)) + key[j] + j;
            i++;
            j++;
            if (i >= N) {
                mt[0] = mt[N - 1];
                i = 1;
            }
            if (j >= len) {
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

    /** {@code getrandbits(32)} as an unsigned value. */
    public long nextU32() {
        if (index >= N) {
            for (int k = 0; k < N; k++) {
                int y = (mt[k] & 0x80000000) | (mt[(k + 1) % N] & 0x7fffffff);
                mt[k] = mt[(k + 397) % N] ^ (y >>> 1) ^ ((y & 1) != 0 ? 0x9908b0df : 0);
            }
            index = 0;
        }
        int z = mt[index++];
        z ^= z >>> 11;
        z ^= (z << 7) & 0x9d2c5680;
        z ^= (z << 15) & 0xefc60000;
        z ^= z >>> 18;
        return z & 0xffffffffL;
    }

    /** {@code randrange(n)} for 0 &lt; n: CPython's getrandbits rejection loop. */
    public int below(int n) {
        if (n <= 0) {
            throw new IllegalArgumentException("empty range");
        }
        int k = 32 - Integer.numberOfLeadingZeros(n);
        long r = nextU32() >>> (32 - k);
        while (r >= n) {
            r = nextU32() >>> (32 - k);
        }
        return (int) r;
    }
}
