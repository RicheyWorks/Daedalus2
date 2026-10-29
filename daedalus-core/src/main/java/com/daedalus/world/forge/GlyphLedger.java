// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Glyph Ledger: the scribe packs forge ledgers into glyph codes with Lempel-Ziv-Welch and unpacks them.
 * The dictionary starts with the 256 single characters and grows by one phrase per emitted code.
 *
 * <p>Reusable plain String/int[] API: {@link #encode}, {@link #decode}.
 */
public final class GlyphLedger {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_glyph_ledger";

    /** Glyphs used for seeded ledgers. */
    public static final String GLYPHS = "forge ";

    /** Largest ledger length. */
    public static final int MAX_LEN = 1 << 20;

    /** Grade band. */
    public enum Grade { INTACT, SMUDGED }

    private GlyphLedger() {
    }

    /** Seeded ledger of n glyphs. */
    public static String ledger(long seed, int n) {
        if (n < 0 || n > MAX_LEN) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            sb.append(GLYPHS.charAt(r.nextInt(GLYPHS.length())));
        }
        return sb.toString();
    }

    /** LZW codes for text (every character below 256). */
    public static int[] encode(String text) {
        if (text.length() > MAX_LEN) {
            throw new IllegalArgumentException("text too long");
        }
        Map<String, Integer> dict = new HashMap<>();
        for (int c = 0; c < 256; c++) {
            dict.put(String.valueOf((char) c), c);
        }
        int[] out = new int[text.length()];
        int k = 0;
        String w = "";
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c >= 256) {
                throw new IllegalArgumentException("glyph out of range at " + i);
            }
            String wc = new StringBuilder(w.length() + 1).append(w).append(c).toString();
            if (dict.containsKey(wc)) {
                w = wc;
            } else {
                out[k++] = dict.get(w);
                dict.put(wc, dict.size());
                w = String.valueOf(c);
            }
        }
        if (!w.isEmpty()) {
            out[k++] = dict.get(w);
        }
        return Arrays.copyOf(out, k);
    }

    /** Text for LZW codes. */
    public static String decode(int[] codes) {
        if (codes.length == 0) {
            return "";
        }
        List<String> dict = new ArrayList<>();
        for (int c = 0; c < 256; c++) {
            dict.add(String.valueOf((char) c));
        }
        if (codes[0] < 0 || codes[0] >= 256) {
            throw new IllegalArgumentException("bad first code");
        }
        String w = dict.get(codes[0]);
        StringBuilder sb = new StringBuilder(w);
        for (int i = 1; i < codes.length; i++) {
            int code = codes[i];
            String entry;
            if (code >= 0 && code < dict.size()) {
                entry = dict.get(code);
            } else if (code == dict.size()) {
                entry = w + w.charAt(0);
            } else {
                throw new IllegalArgumentException("bad code at " + i);
            }
            sb.append(entry);
            dict.add(w + entry.charAt(0));
            w = entry;
        }
        return sb.toString();
    }

    /** INTACT when the codes unpack to exactly the text. */
    public static Grade grade(String text, int[] codes) {
        try {
            return decode(codes).equals(text) ? Grade.INTACT : Grade.SMUDGED;
        } catch (IllegalArgumentException e) {
            return Grade.SMUDGED;
        }
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case INTACT -> "Forgemaster: packed small and opened whole, every glyph in its place. Good scribing.";
            case SMUDGED -> "Forgemaster: smudged. The ledger will not read back true; pack it again.";
        };
    }
}
