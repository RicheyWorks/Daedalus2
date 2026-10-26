// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Fog Bell Call Signs (contest G52): the harbour bell tells the island which ark is coming home.
 *
 * <p>Each ark in a seeded roster gets a call sign of {@link #STROKES} bell strokes, each short (0) or
 * long (1). Call signs are drawn so every pair differs in at least {@link #MIN_DISTANCE} strokes, so when
 * the fog blurs one stroke (a short heard as long or the reverse) the nearest call sign is still the
 * right ark. The player hears the (possibly blurred) sign and names the ark; the harbour judges.
 *
 * <p>Ear rules: bell at {@link #BELL_HZ} Hz, gain {@link #GAIN}; short stroke {@link #SHORT_MS} ms, long
 * stroke {@link #LONG_MS} ms, {@link #GAP_MS} ms of silence between strokes.
 */
public final class FogBellCallSigns {
    /** Ark names a roster is drawn from. */
    public static final List<String> ARKS = List.of("Kestrel", "Heron", "Albatross", "Petrel", "Osprey", "Tern",
            "Gannet", "Curlew", "Plover", "Skua");
    /** Strokes per call sign. */
    public static final int STROKES = 7;
    /** Minimum Hamming distance between any two call signs (corrects one blurred stroke). */
    public static final int MIN_DISTANCE = 3;
    /** Bell pitch (G3). */
    public static final double BELL_HZ = 195.997;
    /** Bell gain. */
    public static final double GAIN = 0.5;
    /** Short stroke length, ms. */
    public static final int SHORT_MS = 180;
    /** Long stroke length, ms. */
    public static final int LONG_MS = 540;
    /** Silence between strokes, ms. */
    public static final int GAP_MS = 240;
    private static final long SALT = 0x4642_4331L; // "FBC1"

    /** One stroke of playback. */
    public record Stroke(int onsetMs, int lengthMs, boolean isLong) { }

    /** A judged guess. */
    public record Verdict(boolean correct, String ark, String heard, int blurred) { }

    private final long seed;
    private final List<String> roster;
    private final int[] signs;
    private final int arriving;
    private final int blurred;

    private FogBellCallSigns(long seed, List<String> roster, int[] signs, int arriving, int blurred) {
        this.seed = seed;
        this.roster = List.copyOf(roster);
        this.signs = signs.clone();
        this.arriving = arriving;
        this.blurred = blurred;
    }

    /** A seeded harbour night: 4-6 arks, one arriving, the fog blurs at most one stroke. */
    public static FogBellCallSigns seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int n = 4 + (int) Long.remainderUnsigned(rng.nextLong(), 3);
        List<String> pool = new ArrayList<>(ARKS);
        List<String> roster = new ArrayList<>();
        int[] signs = new int[n];
        int made = 0;
        while (made < n) {
            int code = (int) Long.remainderUnsigned(rng.nextLong(), 1 << STROKES);
            boolean ok = true;
            for (int i = 0; i < made; i++) {
                if (distance(code, signs[i]) < MIN_DISTANCE) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                signs[made++] = code;
                roster.add(pool.remove((int) Long.remainderUnsigned(rng.nextLong(), pool.size())));
            }
        }
        int arriving = (int) Long.remainderUnsigned(rng.nextLong(), n);
        int blurred = (int) Long.remainderUnsigned(rng.nextLong(), STROKES + 1) - 1; // -1 = clear night
        return new FogBellCallSigns(seed, roster, signs, arriving, blurred);
    }

    /** Number of strokes in which two signs differ. */
    public static int distance(int a, int b) {
        return Integer.bitCount(a ^ b);
    }

    /** Sign as text, first stroke first: '.' short, '-' long. */
    public static String text(int sign) {
        StringBuilder sb = new StringBuilder(STROKES);
        for (int i = 0; i < STROKES; i++) {
            sb.append((sign >> (STROKES - 1 - i) & 1) == 1 ? '-' : '.');
        }
        return sb.toString();
    }

    /** Parse '.'/'-' text back to a sign. */
    public static int parse(String text) {
        if (text == null || text.length() != STROKES) {
            throw new IllegalArgumentException("call sign must be " + STROKES + " strokes");
        }
        int sign = 0;
        for (int i = 0; i < STROKES; i++) {
            char c = text.charAt(i);
            if (c != '.' && c != '-') {
                throw new IllegalArgumentException("stroke must be '.' or '-': " + c);
            }
            sign = sign << 1 | (c == '-' ? 1 : 0);
        }
        return sign;
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** Ark names in roster order. */
    public List<String> roster() {
        return roster;
    }

    /** Call sign of roster ark {@code i}. */
    public int sign(int i) {
        return signs[i];
    }

    /** Stroke index the fog blurred, or -1 on a clear night. */
    public int blurred() {
        return blurred;
    }

    /** What the bell sounds through the fog. */
    public int heard() {
        int s = signs[arriving];
        return blurred < 0 ? s : s ^ 1 << (STROKES - 1 - blurred);
    }

    /** Nearest roster ark to a heard sign (unique within one blurred stroke). */
    public String decode(int heard) {
        int best = 0;
        for (int i = 1; i < signs.length; i++) {
            if (distance(heard, signs[i]) < distance(heard, signs[best])) {
                best = i;
            }
        }
        return roster.get(best);
    }

    /** Playback schedule of the heard sign. */
    public List<Stroke> playback() {
        List<Stroke> out = new ArrayList<>();
        int t = 0;
        String h = text(heard());
        for (int i = 0; i < STROKES; i++) {
            boolean lng = h.charAt(i) == '-';
            int len = lng ? LONG_MS : SHORT_MS;
            out.add(new Stroke(t, len, lng));
            t += len + GAP_MS;
        }
        return out;
    }

    /** Judge the player's named ark. */
    public Verdict judge(String guess) {
        String ark = roster.get(arriving);
        return new Verdict(ark.equals(guess), ark, text(heard()), blurred);
    }
}