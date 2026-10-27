// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;

/**
 * Pairing Tongs: two non-negative ingot ids are gripped as one tag by the Cantor (diagonal) and Szudzik (shell)
 * pairing functions, each with an exact inverse. All arithmetic is overflow-checked; inverses use exact integer
 * square roots.
 *
 * <p>Reusable plain long API: {@link #cantor}, {@link #uncantor}, {@link #szudzik}, {@link #unszudzik}.
 */
public final class PairingTongs {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_pairing_tongs";

    /** Grade band. */
    public enum Grade { GRIPPED, DROPPED }

    /** An (x, y) pair of ids. */
    public record Pair(long x, long y) {
    }

    private PairingTongs() {
    }

    /** Cantor pairing (x+y)(x+y+1)/2 + y; throws on negative ids or overflow. */
    public static long cantor(long x, long y) {
        check(x, y);
        try {
            long s = Math.addExact(x, y);
            long t = (s & 1L) == 0L ? Math.multiplyExact(s / 2, s + 1) : Math.multiplyExact(s, (s + 1) / 2);
            return Math.addExact(t, y);
        } catch (ArithmeticException e) {
            throw new IllegalArgumentException("tag overflows a long", e);
        }
    }

    /** Inverse of {@link #cantor}. */
    public static Pair uncantor(long z) {
        if (z < 0) {
            throw new IllegalArgumentException("tag must be non-negative");
        }
        BigInteger bz = BigInteger.valueOf(z);
        BigInteger r = bz.shiftLeft(3).add(BigInteger.ONE).sqrt();
        BigInteger w = r.subtract(BigInteger.ONE).shiftRight(1);
        BigInteger t = w.multiply(w.add(BigInteger.ONE)).shiftRight(1);
        long y = bz.subtract(t).longValueExact();
        long x = w.longValueExact() - y;
        return new Pair(x, y);
    }

    /** Szudzik pairing: y*y + x when x &lt; y, else x*x + x + y; throws on negative ids or overflow. */
    public static long szudzik(long x, long y) {
        check(x, y);
        try {
            return x < y ? Math.addExact(Math.multiplyExact(y, y), x)
                : Math.addExact(Math.addExact(Math.multiplyExact(x, x), x), y);
        } catch (ArithmeticException e) {
            throw new IllegalArgumentException("tag overflows a long", e);
        }
    }

    /** Inverse of {@link #szudzik}. */
    public static Pair unszudzik(long z) {
        if (z < 0) {
            throw new IllegalArgumentException("tag must be non-negative");
        }
        long s = BigInteger.valueOf(z).sqrt().longValueExact();
        long r = z - s * s;
        return r < s ? new Pair(r, s) : new Pair(s, r - s);
    }

    /** GRIPPED when the claimed Cantor tag maps back to (x, y). */
    public static Grade grade(long x, long y, long claimedTag) {
        return claimedTag >= 0 && uncantor(claimedTag).equals(new Pair(x, y)) ? Grade.GRIPPED : Grade.DROPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case GRIPPED -> "Forgemaster: two ingots, one tag, and the tongs give back exactly what they took.";
            case DROPPED -> "Forgemaster: dropped. That tag opens on some other pair of ingots.";
        };
    }

    private static void check(long x, long y) {
        if (x < 0 || y < 0) {
            throw new IllegalArgumentException("ids must be non-negative");
        }
    }
}
