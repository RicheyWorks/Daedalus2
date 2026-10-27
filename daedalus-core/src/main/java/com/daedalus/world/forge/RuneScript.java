// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;

/**
 * Rune Script: binary blueprints are carved into 64-rune script (Base64, RFC 4648), in the standard or URL-safe
 * alphabet, with or without '=' padding. Decoding is strict: unknown runes, misplaced padding, impossible lengths
 * and non-zero trailing bits are rejected.
 *
 * <p>Reusable plain byte[]/String API: {@link #encode}, {@link #decode}.
 */
public final class RuneScript {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_rune_script";

    private static final String STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    private static final String URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

    /** Grade band. */
    public enum Grade { LEGIBLE, MISCARVED }

    private RuneScript() {
    }

    /** Base64 text for data. */
    public static String encode(byte[] data, boolean urlSafe, boolean pad) {
        String abc = urlSafe ? URL : STD;
        StringBuilder sb = new StringBuilder((data.length + 2) / 3 * 4);
        int i = 0;
        for (; i + 2 < data.length; i += 3) {
            int v = (data[i] & 0xFF) << 16 | (data[i + 1] & 0xFF) << 8 | (data[i + 2] & 0xFF);
            sb.append(abc.charAt(v >>> 18)).append(abc.charAt((v >>> 12) & 63))
                .append(abc.charAt((v >>> 6) & 63)).append(abc.charAt(v & 63));
        }
        int rest = data.length - i;
        if (rest == 1) {
            int v = (data[i] & 0xFF) << 16;
            sb.append(abc.charAt(v >>> 18)).append(abc.charAt((v >>> 12) & 63));
            if (pad) {
                sb.append("==");
            }
        } else if (rest == 2) {
            int v = (data[i] & 0xFF) << 16 | (data[i + 1] & 0xFF) << 8;
            sb.append(abc.charAt(v >>> 18)).append(abc.charAt((v >>> 12) & 63)).append(abc.charAt((v >>> 6) & 63));
            if (pad) {
                sb.append('=');
            }
        }
        return sb.toString();
    }

    /** Bytes for Base64 text (padded or unpadded); throws on any miscarving. */
    public static byte[] decode(String text, boolean urlSafe) {
        String abc = urlSafe ? URL : STD;
        String s = text;
        if (!s.isEmpty() && s.length() % 4 == 0 && s.endsWith("==")) {
            s = s.substring(0, s.length() - 2);
            if (s.length() % 4 != 2) {
                throw new IllegalArgumentException("bad padding");
            }
        } else if (!s.isEmpty() && s.length() % 4 == 0 && s.endsWith("=")) {
            s = s.substring(0, s.length() - 1);
        }
        if (s.length() % 4 == 1) {
            throw new IllegalArgumentException("impossible length");
        }
        int[] v = new int[s.length()];
        for (int i = 0; i < s.length(); i++) {
            int x = abc.indexOf(s.charAt(i));
            if (x < 0) {
                throw new IllegalArgumentException("bad rune at " + i);
            }
            v[i] = x;
        }
        byte[] out = new byte[s.length() * 3 / 4];
        int k = 0;
        int i = 0;
        for (; i + 3 < v.length; i += 4) {
            int w = v[i] << 18 | v[i + 1] << 12 | v[i + 2] << 6 | v[i + 3];
            out[k++] = (byte) (w >>> 16);
            out[k++] = (byte) (w >>> 8);
            out[k++] = (byte) w;
        }
        int rest = v.length - i;
        if (rest == 2) {
            if ((v[i + 1] & 15) != 0) {
                throw new IllegalArgumentException("non-zero trailing bits");
            }
            out[k++] = (byte) (v[i] << 2 | v[i + 1] >>> 4);
        } else if (rest == 3) {
            if ((v[i + 2] & 3) != 0) {
                throw new IllegalArgumentException("non-zero trailing bits");
            }
            int w = v[i] << 12 | v[i + 1] << 6 | v[i + 2];
            out[k++] = (byte) (w >>> 10);
            out[k++] = (byte) (w >>> 2);
        }
        return Arrays.copyOf(out, k);
    }

    /** LEGIBLE when text decodes strictly to data. */
    public static Grade grade(String text, byte[] data, boolean urlSafe) {
        try {
            return Arrays.equals(decode(text, urlSafe), data) ? Grade.LEGIBLE : Grade.MISCARVED;
        } catch (IllegalArgumentException e) {
            return Grade.MISCARVED;
        }
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case LEGIBLE -> "Forgemaster: every rune cut clean; the blueprint reads back to the last byte.";
            case MISCARVED -> "Forgemaster: miscarved. A rune or a pad mark is wrong; the smiths cannot read it.";
        };
    }
}
