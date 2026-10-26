// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Drip Cave Chorus (contest G64): the island's caves keep time for the arks' bell crews.
 *
 * <p>A seeded cave has 3-5 drips. Drip {@code i} falls on every beat {@code t} with
 * {@code t mod period == offset}, and each sounds its own pentatonic pitch. The player taps the first beat
 * (beat 1 onwards) on which every drip lands together, a Chinese-remainder timing puzzle solved by the
 * reusable {@link BeatCoincidence}. Caves are built
 * solvable (offsets come from a hidden common beat), and the judge accepts only the earliest common beat,
 * tapped within {@link #WINDOW_MS} of it.
 *
 * <p>Ear rules: beat {@link #BEAT_MS} ms; drip pitches are A3 major pentatonic ({@link #hz(int)}), gain
 * {@link #GAIN} each.
 */
public final class DripCaveChorus {
    /** Beat length, ms. */
    public static final int BEAT_MS = 250;
    /** Tap window either side of the beat, ms. */
    public static final int WINDOW_MS = 80;
    /** Drip gain. */
    public static final double GAIN = 0.35;
    private static final int[] PENTA = {0, 2, 4, 7, 9};
    private static final long SALT = 0x4443_4331L; // "DCC1"

    /** One drip. */
    public record Drip(int period, int offset, double hz) { }

    /** A judged tap. */
    public record Verdict(boolean correct, int beat, int answer, int offMs, String reason) { }

    private final long seed;
    private final List<Drip> drips;
    private final int answer;

    private DripCaveChorus(long seed, List<Drip> drips) {
        this.seed = seed;
        this.drips = List.copyOf(drips);
        this.answer = earliest(this.drips);
    }

    /** A seeded cave. */
    public static DripCaveChorus seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int n = 3 + (int) Long.remainderUnsigned(rng.nextLong(), 3);
        List<Integer> pool = new ArrayList<>(List.of(2, 3, 4, 5, 6, 7, 8, 9));
        int hidden = 1 + (int) Long.remainderUnsigned(rng.nextLong(), 240);
        List<Drip> drips = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            int p = pool.remove((int) Long.remainderUnsigned(rng.nextLong(), pool.size()));
            drips.add(new Drip(p, hidden % p, hz(i)));
        }
        return new DripCaveChorus(seed, drips);
    }

    /** A cave from explicit drips (for tests and authored caves); must have a common beat. */
    public static DripCaveChorus of(List<Drip> drips) {
        if (drips == null || drips.isEmpty()) {
            throw new IllegalArgumentException("cave needs drips");
        }
        for (Drip d : drips) {
            if (d.period() < 1 || d.offset() < 0 || d.offset() >= d.period()) {
                throw new IllegalArgumentException("bad drip " + d);
            }
        }
        return new DripCaveChorus(0, drips);
    }

    /** Pitch of drip {@code i}: A3 major pentatonic, climbing an octave every five drips. */
    public static double hz(int i) {
        int semis = PENTA[i % PENTA.length] + 12 * (i / PENTA.length);
        return Math.round(220.0 * Math.pow(2, semis / 12.0) * 1000) / 1000.0;
    }

    private static int earliest(List<Drip> drips) {
        int[] p = new int[drips.size()];
        int[] o = new int[drips.size()];
        for (int i = 0; i < p.length; i++) {
            p[i] = drips.get(i).period();
            o[i] = drips.get(i).offset();
        }
        long t = BeatCoincidence.next(p, o, 1);
        if (t < 0) {
            throw new IllegalArgumentException("drips never land together");
        }
        return (int) t;
    }
    /** The seed (0 for authored caves). */
    public long seed() {
        return seed;
    }

    /** The drips. */
    public List<Drip> drips() {
        return drips;
    }

    /** Earliest beat on which every drip lands. */
    public int answer() {
        return answer;
    }

    /** Pitches sounding on {@code beat}. */
    public List<Double> sounding(int beat) {
        List<Double> out = new ArrayList<>();
        for (Drip d : drips) {
            if (beat >= 0 && beat % d.period() == d.offset()) {
                out.add(d.hz());
            }
        }
        return out;
    }

    /** Judge a tap at {@code ms} from the start of beat 0. */
    public Verdict judge(int ms) {
        int beat = Math.floorDiv(ms + BEAT_MS / 2, BEAT_MS);
        int off = ms - beat * BEAT_MS;
        if (Math.abs(off) > WINDOW_MS) {
            return new Verdict(false, beat, answer, off, "off the beat by " + off + " ms");
        }
        if (beat != answer) {
            return new Verdict(false, beat, answer, off, beat < answer ? "too early" : "a later chorus; listen for the first");
        }
        return new Verdict(true, beat, answer, off, "chorus");
    }
}