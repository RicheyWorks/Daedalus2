// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Echo Anvil: strike patterns are packed with LZ77 as flat (offset, length, next) triples. A match must be at
 * least {@link #MIN_MATCH} long (otherwise a literal (0, 0, c) is emitted), lies within the window, may overlap
 * the cursor, and always leaves a next character. Among longest matches the nearest is chosen.
 *
 * <p>Reusable plain String/int[] API: {@link #encode}, {@link #decode}.
 */
public final class EchoAnvil {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_echo_anvil";

    /** Shortest back-reference. */
    public static final int MIN_MATCH = 3;

    /** Largest input length. */
    public static final int MAX_LEN = 1 << 20;

    /** Strikes used for seeded patterns. */
    public static final String STRIKES = "tink";

    /** Grade band. */
    public enum Grade { ECHOED, DULL }

    private EchoAnvil() {
    }

    /** Seeded strike pattern of n strikes. */
    public static String pattern(long seed, int n) {
        if (n < 0 || n > MAX_LEN) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            sb.append(STRIKES.charAt(r.nextInt(STRIKES.length())));
        }
        return sb.toString();
    }

    /** Flat triples (offset, length, next char) for s with the given window and longest match. */
    public static int[] encode(String s, int window, int maxLen) {
        int n = s.length();
        if (n > MAX_LEN || window < 1 || maxLen < MIN_MATCH) {
            throw new IllegalArgumentException("bad arguments");
        }
        int bits = 16;
        int[] head = new int[1 << bits];
        Arrays.fill(head, -1);
        int[] prev = new int[Math.max(1, n)];
        int[] out = new int[3 * Math.max(1, n)];
        int k = 0;
        int inserted = 0;
        int i = 0;
        while (i < n) {
            for (; inserted < i; inserted++) {
                if (inserted + 2 < n) {
                    int h = hash(s, inserted, bits);
                    prev[inserted] = head[h];
                    head[h] = inserted;
                }
            }
            int bestLen = 0;
            int bestOff = 0;
            int cap = Math.min(maxLen, n - 1 - i);
            if (cap >= MIN_MATCH) {
                for (int j = head[hash(s, i, bits)]; j >= 0 && i - j <= window; j = prev[j]) {
                    int len = 0;
                    while (len < cap && s.charAt(j + len) == s.charAt(i + len)) {
                        len++;
                    }
                    if (len > bestLen) {
                        bestLen = len;
                        bestOff = i - j;
                        if (len == cap) {
                            break;
                        }
                    }
                }
            }
            if (bestLen < MIN_MATCH) {
                bestLen = 0;
                bestOff = 0;
            }
            out[k++] = bestOff;
            out[k++] = bestLen;
            out[k++] = s.charAt(i + bestLen);
            i += bestLen + 1;
        }
        return Arrays.copyOf(out, k);
    }

    /** Replays flat triples. */
    public static String decode(int[] triples) {
        if (triples.length % 3 != 0) {
            throw new IllegalArgumentException("triples length must be a multiple of 3");
        }
        StringBuilder sb = new StringBuilder();
        for (int t = 0; t < triples.length; t += 3) {
            int off = triples[t];
            int len = triples[t + 1];
            if (len < 0 || off < 0 || (len > 0 && (off < 1 || off > sb.length())) || sb.length() + len > MAX_LEN) {
                throw new IllegalArgumentException("bad triple at " + t / 3);
            }
            int from = sb.length() - off;
            for (int c = 0; c < len; c++) {
                sb.append(sb.charAt(from + c));
            }
            sb.append((char) triples[t + 2]);
        }
        return sb.toString();
    }

    /** ECHOED when the triples replay to exactly the text. */
    public static Grade grade(String text, int[] triples) {
        try {
            return decode(triples).equals(text) ? Grade.ECHOED : Grade.DULL;
        } catch (IllegalArgumentException e) {
            return Grade.DULL;
        }
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case ECHOED -> "Forgemaster: every strike echoed back in order. The anvil remembers well.";
            case DULL -> "Forgemaster: a dull echo. The replay drifts from the strikes; pack it again.";
        };
    }

    private static int hash(String s, int i, int bits) {
        int h = s.charAt(i) * 0x9E3779B1 ^ s.charAt(i + 1) * 0x85EBCA6B ^ s.charAt(i + 2) * 0xC2B2AE35;
        return (h ^ (h >>> 15)) & ((1 << bits) - 1);
    }
}
