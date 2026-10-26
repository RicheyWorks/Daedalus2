// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Wind Chime Tuning (contest G60): salvaged ark pipes become the island's wind chimes.
 *
 * <p>A seeded set of {@link #TUBES} tubes (300-600 mm) hangs longest first. A free-free tube rings at a
 * frequency proportional to 1/L^2 ({@link #frequency(double)}); a tube can only be trimmed shorter, so its
 * pitch can only rise. The player tunes the set to a major pentatonic (0, 2, 4, 7, 9 semitones, longest tube
 * lowest) on the lowest equal-tempered root every tube can still reach. {@link #solution()} is the
 * minimal-trim answer; {@link #judge(List)} reports cents error per tube and passes within
 * {@link #TOLERANCE_CENTS}.
 *
 * <p>Ear rules: each strike at gain {@link #GAIN}, ringing {@link #DECAY_MS} ms.
 */
public final class WindChimeTuning {
    /** Tubes per set. */
    public static final int TUBES = 5;
    /** Major pentatonic steps, longest tube first. */
    public static final List<Integer> PENTATONIC = List.of(0, 2, 4, 7, 9);
    /** Allowed error per tube, cents. */
    public static final double TOLERANCE_CENTS = 5.0;
    /** Strike gain. */
    public static final double GAIN = 0.4;
    /** Ring time, ms. */
    public static final int DECAY_MS = 2500;
    /** Tube constant: a 450 mm tube rings at G3 (196 Hz). */
    public static final double K = 196.0 * 450.0 * 450.0;
    private static final long SALT = 0x5743_4831L; // "WCH1"

    /** Per-tube judgement. */
    public record Tube(double lengthMm, double hz, double targetHz, double cents, boolean ok) { }

    /** A judged set. */
    public record Verdict(boolean tuned, double trimMm, List<Tube> tubes, String reason) {
        /** Defensive copy. */
        public Verdict {
            tubes = List.copyOf(tubes);
        }
    }

    private final long seed;
    private final double[] lengths;
    private final int root;

    private WindChimeTuning(long seed, double[] lengths) {
        this.seed = seed;
        this.lengths = lengths.clone();
        double need = Double.NEGATIVE_INFINITY;
        for (int i = 0; i < TUBES; i++) {
            need = Math.max(need, midi(frequency(lengths[i])) - PENTATONIC.get(i));
        }
        this.root = (int) Math.ceil(need - 1e-9);
    }

    /** A seeded set of salvaged tubes, sorted longest first (lengths to 0.1 mm). */
    public static WindChimeTuning seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        double[] l = new double[TUBES];
        for (int i = 0; i < TUBES; i++) {
            l[i] = 300 + Long.remainderUnsigned(rng.nextLong(), 3001) / 10.0;
        }
        Arrays.sort(l);
        for (int i = 0; i < TUBES / 2; i++) {
            double t = l[i];
            l[i] = l[TUBES - 1 - i];
            l[TUBES - 1 - i] = t;
        }
        return new WindChimeTuning(seed, l);
    }

    /** Ring frequency of a tube of {@code lengthMm}. */
    public static double frequency(double lengthMm) {
        if (!(lengthMm > 0)) {
            throw new IllegalArgumentException("tube length must be positive");
        }
        return K / (lengthMm * lengthMm);
    }

    /** Tube length that rings at {@code hz}. */
    public static double lengthFor(double hz) {
        return Math.sqrt(K / hz);
    }

    /** Equal-tempered frequency of a MIDI note (A4 = 69 = 440 Hz). */
    public static double hzOf(int midiNote) {
        return 440.0 * Math.pow(2, (midiNote - 69) / 12.0);
    }

    private static double midi(double hz) {
        return 69 + 12 * Math.log(hz / 440.0) / Math.log(2);
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** Salvaged lengths, longest first. */
    public List<Double> lengths() {
        List<Double> out = new ArrayList<>();
        for (double l : lengths) {
            out.add(l);
        }
        return out;
    }

    /** Lowest reachable root (MIDI note). */
    public int root() {
        return root;
    }

    /** Target frequency of tube {@code i}. */
    public double targetHz(int i) {
        return hzOf(root + PENTATONIC.get(i));
    }

    /** Minimal-trim tuned lengths, longest first. */
    public List<Double> solution() {
        List<Double> out = new ArrayList<>();
        for (int i = 0; i < TUBES; i++) {
            out.add(lengthFor(targetHz(i)));
        }
        return out;
    }

    /** Judge trimmed lengths (longest first). */
    public Verdict judge(List<Double> trimmed) {
        if (trimmed == null || trimmed.size() != TUBES) {
            return new Verdict(false, 0, List.of(), "need " + TUBES + " tubes");
        }
        List<Tube> out = new ArrayList<>();
        double trim = 0;
        boolean all = true;
        String reason = "tuned";
        for (int i = 0; i < TUBES; i++) {
            double l = trimmed.get(i);
            if (!(l > 0) || l > lengths[i] + 1e-9) {
                return new Verdict(false, 0, List.of(), "tube " + i + " cannot grow (salvaged " + lengths[i] + " mm)");
            }
            double hz = frequency(l);
            double target = targetHz(i);
            double cents = 1200 * Math.log(hz / target) / Math.log(2);
            boolean ok = Math.abs(cents) <= TOLERANCE_CENTS;
            if (!ok && all) {
                reason = "tube " + i + " off by " + Math.round(cents) + " cents";
            }
            all &= ok;
            trim += lengths[i] - l;
            out.add(new Tube(l, hz, target, cents, ok));
        }
        return new Verdict(all, trim, out, reason);
    }
}