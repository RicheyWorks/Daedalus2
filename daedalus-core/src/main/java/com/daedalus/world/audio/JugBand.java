// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Jug Band (contest G114): the kennel crews' evening jug band.
 *
 * <p>Each salvaged water jug is a Helmholtz resonator: blowing across the neck sounds
 * {@code f = (c / 2 pi) sqrt(A / (V L))} ({@link #frequency}), with neck area A, effective neck length L and
 * air volume V. Pouring water in shrinks V and raises the pitch, and water cannot be taken back out, so
 * tuning is fill-only. The band asks for a seeded 4-note melody from a low D minor pentatonic (D3-D4,
 * under 300 Hz); the player chooses the litres to pour into each jug. The judge reports cents per jug
 * (within {@link #TOLERANCE_CENTS} passes) and refuses overfills (a jug must keep {@link #MIN_AIR} of its
 * air). Every pitch passes {@link EarRule#check}.
 */
public final class JugBand {
    /** Speed of sound, m/s. */
    public static final double C = 343.0;
    /** Allowed detuning per jug, cents. */
    public static final double TOLERANCE_CENTS = 10.0;
    /** Least fraction of the jug that must stay air. */
    public static final double MIN_AIR = 0.1;
    /** Jugs in the band. */
    public static final int JUGS = 4;
    private static final double[] SCALE = {146.832, 174.614, 195.998, 220.0, 261.626, 293.665};
    private static final long SALT = 0x4A55_4731L; // "JUG1"

    /** A jug: neck area (m^2), effective neck length (m), empty volume (litres). */
    public record Jug(double neckArea, double neckLength, double litres) { }

    /** Per-jug result. */
    public record Note(double hz, double targetHz, double cents, boolean ok) { }

    /** A judged tuning. */
    public record Verdict(boolean tuned, List<Note> notes, String reason) {
        /** Defensive copy. */
        public Verdict {
            notes = List.copyOf(notes);
        }
    }

    private final long seed;
    private final List<Jug> jugs;
    private final double[] melody;

    private JugBand(long seed, List<Jug> jugs, double[] melody) {
        this.seed = seed;
        this.jugs = List.copyOf(jugs);
        this.melody = melody.clone();
    }

    /** A seeded band: melody first, then jugs that can reach it by filling. */
    public static JugBand seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        double[] melody = new double[JUGS];
        List<Jug> jugs = new ArrayList<>();
        for (int i = 0; i < JUGS; i++) {
            melody[i] = SCALE[(int) Long.remainderUnsigned(rng.nextLong(), SCALE.length)];
            double r = (10 + Long.remainderUnsigned(rng.nextLong(), 11)) / 1000.0; // neck radius 10-20 mm
            double a = Math.PI * r * r;
            double l = (30 + Long.remainderUnsigned(rng.nextLong(), 51)) / 1000.0; // 30-80 mm
            double airAtTarget = airFor(a, l, melody[i]);
            double keep = (30 + Long.remainderUnsigned(rng.nextLong(), 61)) / 100.0; // target air = 30-90% of jug
            jugs.add(new Jug(a, l, Math.round(airAtTarget / keep * 1000 * 1000) / 1000.0));
        }
        return new JugBand(seed, jugs, melody);
    }

    private static double airFor(double area, double length, double hz) {
        double k = 2 * Math.PI * hz / C;
        return area / (length * k * k); // m^3
    }

    /** Pitch of a jug holding {@code waterLitres} (ear-rule checked). */
    public static double frequency(Jug j, double waterLitres) {
        double air = (j.litres() - waterLitres) / 1000.0;
        if (!(air > 0)) {
            throw new IllegalArgumentException("jug has no air left");
        }
        return EarRule.check(C / (2 * Math.PI) * Math.sqrt(j.neckArea() / (air * j.neckLength())), "jug band jug");
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The jugs. */
    public List<Jug> jugs() {
        return jugs;
    }

    /** The requested melody, Hz. */
    public List<Double> melody() {
        List<Double> out = new ArrayList<>();
        for (double m : melody) {
            out.add(m);
        }
        return out;
    }

    /** Exact litres to pour into each jug. */
    public List<Double> solution() {
        List<Double> out = new ArrayList<>();
        for (int i = 0; i < JUGS; i++) {
            Jug j = jugs.get(i);
            out.add(j.litres() - airFor(j.neckArea(), j.neckLength(), melody[i]) * 1000);
        }
        return out;
    }

    /** Judge litres poured per jug. */
    public Verdict judge(List<Double> water) {
        if (water == null || water.size() != JUGS) {
            return new Verdict(false, List.of(), "pour into all " + JUGS + " jugs");
        }
        List<Note> notes = new ArrayList<>();
        boolean all = true;
        String reason = "the band plays the tune";
        for (int i = 0; i < JUGS; i++) {
            Jug j = jugs.get(i);
            double w = water.get(i);
            if (w < 0 || w > j.litres() * (1 - MIN_AIR)) {
                return new Verdict(false, List.of(), "jug " + (i + 1) + " overfilled or emptied below zero");
            }
            double hz = frequency(j, w);
            double cents = 1200 * Math.log(hz / melody[i]) / Math.log(2);
            boolean ok = Math.abs(cents) <= TOLERANCE_CENTS;
            if (!ok && all) {
                reason = "jug " + (i + 1) + " off by " + Math.round(cents) + " cents";
            }
            all &= ok;
            notes.add(new Note(hz, melody[i], cents, ok));
        }
        return new Verdict(all, notes, reason);
    }
}