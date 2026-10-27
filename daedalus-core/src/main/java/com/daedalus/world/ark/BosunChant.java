// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Optional;

/**
 * G332 The Bosun's Chant: each verse of the chant reads the previous verse's digit runs aloud
 * ("1211" is "one 1, one 2, two 1s", so the next verse is "111221"). The bosun can sing forward,
 * count verse lengths, and un-sing a verse back to the one that produced it when that is possible.
 */
public final class BosunChant {

    public static final String QUEST_ID = "q_bosun_chant";

    private static final int MAX_LENGTH = 1_000_000;

    private BosunChant() { }

    private static void digits(String s) {
        if (s.isEmpty()) {
            throw new IllegalArgumentException("empty verse");
        }
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c < '1' || c > '9') {
                throw new IllegalArgumentException("verse digits are 1..9");
            }
        }
    }

    /** The next verse. Run lengths above 9 are spoken as their decimal digits. */
    public static String next(String verse) {
        digits(verse);
        StringBuilder sb = new StringBuilder();
        int i = 0;
        while (i < verse.length()) {
            char c = verse.charAt(i);
            int j = i;
            while (j < verse.length() && verse.charAt(j) == c) {
                j++;
            }
            sb.append(j - i).append(c);
            i = j;
            if (sb.length() > MAX_LENGTH) {
                throw new IllegalArgumentException("verse grew too long");
            }
        }
        return sb.toString();
    }

    /** Verse number k (0 = the seed). */
    public static String verse(String seed, int k) {
        if (k < 0) {
            throw new IllegalArgumentException("k " + k);
        }
        String v = seed;
        digits(v);
        for (int i = 0; i < k; i++) {
            v = next(v);
        }
        return v;
    }

    /** The verse that sings into this one, if any (pairs of count and digit, runs merged). */
    public static Optional<String> previous(String verse) {
        digits(verse);
        if (verse.length() % 2 != 0) {
            return Optional.empty();
        }
        StringBuilder sb = new StringBuilder();
        char last = 0;
        for (int i = 0; i < verse.length(); i += 2) {
            int count = verse.charAt(i) - '0';
            char d = verse.charAt(i + 1);
            if (d == last) {
                return Optional.empty();
            }
            for (int k = 0; k < count; k++) {
                sb.append(d);
            }
            last = d;
        }
        return Optional.of(sb.toString());
    }

    /** Quest q_bosun_chant: sing the next verse. */
    public static boolean quest(String verse, String answer) {
        return next(verse).equals(answer);
    }
}