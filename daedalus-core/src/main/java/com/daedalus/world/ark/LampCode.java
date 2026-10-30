// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.OptionalInt;

/**
 * G353 The Lamp Code: the signal lamps flash a 4-bit order as 8 lamps, an extended Hamming(8,4)
 * word. Lamps 1, 2 and 4 are parity over the lamps whose position has that bit set, and lamp 0 is
 * parity over all. The syndrome names a single flipped lamp, which is corrected; two flips are
 * detected and refused.
 */
public final class LampCode {

    public static final String QUEST_ID = "q_lamp_code";

    private static final int[] DATA_POS = {3, 5, 6, 7};

    private LampCode() { }

    private static int bit(int word, int pos) {
        return word >> pos & 1;
    }

    /** Encode a 4-bit order (0..15) as an 8-lamp word (bit i is lamp i). */
    public static int encode(int order) {
        if (order < 0 || order > 15) {
            throw new IllegalArgumentException("order 0..15: " + order);
        }
        int w = 0;
        for (int i = 0; i < 4; i++) {
            w |= (order >> i & 1) << DATA_POS[i];
        }
        for (int p = 1; p <= 4; p <<= 1) {
            int parity = 0;
            for (int pos = 1; pos <= 7; pos++) {
                if ((pos & p) != 0 && pos != p) {
                    parity ^= bit(w, pos);
                }
            }
            w |= parity << p;
        }
        w |= Integer.bitCount(w) & 1;
        return w;
    }

    private static void checkWord(int word) {
        if (word < 0 || word > 255) {
            throw new IllegalArgumentException("word 0..255: " + word);
        }
    }

    /** Position (1..7) named by the Hamming syndrome, 0 when it is clean. */
    public static int syndrome(int word) {
        checkWord(word);
        int s = 0;
        for (int pos = 1; pos <= 7; pos++) {
            if (bit(word, pos) == 1) {
                s ^= pos;
            }
        }
        return s;
    }

    /** Flips seen: 0 clean, 1 correctable, 2 detected but not correctable. */
    public static int flipsSeen(int word) {
        int s = syndrome(word);
        boolean oddParity = (Integer.bitCount(word) & 1) != 0;
        if (s == 0 && !oddParity) {
            return 0;
        }
        return oddParity ? 1 : 2;
    }

    /** The order, after correcting one flipped lamp; empty when two flips are seen. */
    public static OptionalInt decode(int word) {
        int seen = flipsSeen(word);
        if (seen == 2) {
            return OptionalInt.empty();
        }
        int w = word;
        if (seen == 1) {
            w ^= 1 << syndrome(word);
        }
        int order = 0;
        for (int i = 0; i < 4; i++) {
            order |= bit(w, DATA_POS[i]) << i;
        }
        return OptionalInt.of(order);
    }

    /** Quest q_lamp_code: read the order from a word with at most one flipped lamp. */
    public static boolean quest(int word, int answer) {
        OptionalInt got = decode(word);
        return got.isPresent() && got.getAsInt() == answer;
    }
}