// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;
import java.util.OptionalDouble;

/**
 * Cricket Thermometer (contest G159): on warm nights in the regrown woods the crickets tell the temperature.
 *
 * <p>Snowy tree crickets ({@code Oecanthus fultoni}) are ectotherms, so they chirp faster when the air is
 * warmer. Dolbear's law (1897) for this species: degrees F = 40 + chirps counted in 15 seconds, the same as
 * chirps per minute = 7.2 C - 32. Each seeded night has an air temperature; one steady snowy tree cricket and
 * one irregular field cricket call together. The player picks out the steady caller, counts its chirps in the
 * {@link #WINDOW_S} s window and reads the temperature. {@link #solve()} does the same: it keeps the voice whose
 * chirp intervals vary least, counts its onsets and inverts Dolbear's law. The judge scores by error in C.
 * Below {@link #SILENT_BELOW_C} C the snowy tree cricket stays silent and the right answer is "too cold".
 *
 * <p>Ecology caveats: Dolbear's law fits the snowy tree cricket ({@code Oecanthus fultoni}) well over roughly
 * 13-30 C; other species have their own constants, and field crickets chirp at rates far less tied to
 * temperature. The field-cricket rate, the jitter and spread, the silent cut-off and the steady cut-off here are
 * in-game constants and illustrative. Counting one chirp more or less shifts the reading by 1 F (0.56 C), so the
 * judge allows {@link #TOLERANCE_C} C (about 2.7 chirps). Real tree crickets sing near 2-3 kHz and field
 * crickets near 4-5 kHz; the game pitch is compressed below 800 Hz and played soft, and passes
 * {@link EarRule#check}.
 *
 * <p>Sound speed feed: {@link #speedOfSoundMps()} gives c = 331.3 + 0.606 T for tonight. It is one-way and
 * opt-in: {@link OwlFix} and {@link ThunderTowers} keep their own 343 m/s (20 C) defaults and are not changed;
 * a caller may pass this value on if it wants a temperature-aware night.
 */
public final class CricketThermometer {
    /** Counting window, seconds (Dolbear's 15 s count). */
    public static final double WINDOW_S = 15.0;
    /** Coldest seeded night, C. */
    public static final double MIN_C = 10.0;
    /** Warmest seeded night, C. */
    public static final double MAX_C = 30.0;
    /** Below this the snowy tree cricket is silent, C (illustrative). */
    public static final double SILENT_BELOW_C = 13.0;
    /** Full score within this error, C. */
    public static final double TOLERANCE_C = 1.5;
    /** Snowy tree cricket chirp, compressed down (real song near 2-3 kHz), Hz; illustrative. */
    public static final double SNOWY_HZ = 600.0;
    /** Field cricket chirp, compressed down (real song near 4-5 kHz), Hz; illustrative. */
    public static final double FIELD_HZ = 440.0;
    /** Snowy tree cricket timing jitter, fraction of one interval (steady; must stay below 0.5). */
    public static final double SNOWY_JITTER = 0.06;
    /** Field cricket interval spread, fraction of its mean interval (irregular, illustrative). */
    public static final double FIELD_SPREAD = 0.45;
    /** A voice counts as steady (a snowy tree cricket) when its interval CV is at most this (illustrative). */
    public static final double STEADY_CV_MAX = 0.11;
    /** Playback level for every chirp, 0-1 (kept soft). */
    public static final double LEVEL = 0.35;
    private static final long SALT = 0x4352_4B31L; // "CRK1"

    /** One chirp onset. */
    public record Chirp(double t, double hz, double level) { }

    /** One calling insect: a pitch and its onsets inside the window. */
    public record Voice(double hz, List<Double> onsets) {
        /** Copies the onsets. */
        public Voice {
            onsets = List.copyOf(onsets);
        }

        /** Coefficient of variation of the inter-onset intervals; infinite with fewer than three onsets. */
        public double intervalCv() {
            if (onsets.size() < 3) {
                return Double.POSITIVE_INFINITY;
            }
            int n = onsets.size() - 1;
            double mean = 0;
            for (int i = 0; i < n; i++) {
                mean += onsets.get(i + 1) - onsets.get(i);
            }
            mean /= n;
            double var = 0;
            for (int i = 0; i < n; i++) {
                double d = onsets.get(i + 1) - onsets.get(i) - mean;
                var += d * d;
            }
            return Math.sqrt(var / n) / mean;
        }
    }

    /** A reading: the count used and the temperature, or silent ("too cold"). */
    public record Reading(boolean silent, int count, double celsius) { }

    /** A judged guess. */
    public record Verdict(boolean correct, double errorC, int score) { }

    private final long seed;
    private final double tempC;
    private final List<Voice> voices;

    private CricketThermometer(long seed, double tempC, List<Voice> voices) {
        this.seed = seed;
        this.tempC = tempC;
        this.voices = List.copyOf(voices);
    }

    /** A seeded night. */
    public static CricketThermometer seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        double t = MIN_C + roll(rng, (int) Math.round((MAX_C - MIN_C) * 10) + 1) / 10.0;
        double phase = roll(rng, 1000) / 1000.0;
        return build(seed, t, phase, SNOWY_JITTER, rng);
    }

    /** A night with a chosen temperature, phase (0-1 of an interval) and jitter, for tests. */
    static CricketThermometer of(double tempC, double phase, double jitter, long seed) {
        return build(seed, tempC, phase, jitter, new Rng(seed ^ SALT));
    }

    private static CricketThermometer build(long seed, double t, double phase, double jitter, Rng rng) {
        if (jitter < 0 || jitter >= 0.5) {
            throw new IllegalArgumentException("jitter must be in [0, 0.5): " + jitter);
        }
        List<Voice> v = new ArrayList<>();
        List<Double> snowy = new ArrayList<>();
        if (t >= SILENT_BELOW_C) {
            double interval = 60.0 / chirpsPerMinute(t);
            for (int k = 0; ; k++) {
                double base = (phase + k) * interval;
                if (base >= WINDOW_S + interval) {
                    break;
                }
                double on = base + jitter * interval * (roll(rng, 2001) / 1000.0 - 1.0);
                if (on >= 0 && on < WINDOW_S) {
                    snowy.add(on);
                }
            }
        }
        List<Double> field = new ArrayList<>();
        double mean = 60.0 / fieldChirpsPerMinute(t);
        double on = mean * roll(rng, 1000) / 1000.0;
        while (on < WINDOW_S) {
            field.add(on);
            on += mean * (1 + FIELD_SPREAD * (roll(rng, 2001) / 1000.0 - 1.0));
        }
        // Order of voices is seeded so the steady caller is not always first.
        Voice s = new Voice(SNOWY_HZ, snowy);
        Voice f = new Voice(FIELD_HZ, field);
        if (roll(rng, 2) == 0) {
            v.add(s);
            v.add(f);
        } else {
            v.add(f);
            v.add(s);
        }
        return new CricketThermometer(seed, t, v);
    }

    private static int roll(Rng rng, int n) {
        return (int) Long.remainderUnsigned(rng.nextLong(), n);
    }

    /** Dolbear's law for the snowy tree cricket: chirps per minute at {@code c} degrees C. */
    public static double chirpsPerMinute(double c) {
        return 7.2 * c - 32.0;
    }

    /** Dolbear's law inverted: degrees C from chirps counted in 15 s (F = 40 + n). */
    public static double celsiusFromCount(int countIn15s) {
        return (40.0 + countIn15s - 32.0) / 1.8;
    }

    /** Field cricket mean rate, chirps per minute (illustrative, weakly tied to temperature). */
    static double fieldChirpsPerMinute(double c) {
        return 90.0 + 1.5 * c;
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** True air temperature, C (for the judge and tests). */
    public double tempC() {
        return tempC;
    }

    /** Both callers, in seeded order. */
    public List<Voice> voices() {
        return voices;
    }

    /** Everything heard in the window, by onset time (ear-rule checked). */
    public List<Chirp> soundscape() {
        List<Chirp> out = new ArrayList<>();
        for (Voice v : voices) {
            double hz = EarRule.check(v.hz(), "cricket chirp");
            v.onsets().forEach(t -> out.add(new Chirp(t, hz, LEVEL)));
        }
        out.sort((a, b) -> Double.compare(a.t(), b.t()));
        return out;
    }

    /** The steadiest voice (lowest interval CV; ties keep the first), or null if none has three onsets. */
    public Voice steadiest() {
        Voice best = null;
        double bestCv = Double.POSITIVE_INFINITY;
        for (Voice v : voices) {
            double cv = v.intervalCv();
            if (cv < bestCv) {
                bestCv = cv;
                best = v;
            }
        }
        return best;
    }

    /** The reading a careful listener makes. Silent when no voice is steady enough to count. */
    public Reading solve() {
        Voice v = steadiest();
        if (v == null || v.intervalCv() > STEADY_CV_MAX) {
            return new Reading(true, 0, Double.NaN);
        }
        int n = v.onsets().size();
        return new Reading(false, n, celsiusFromCount(n));
    }

    /** Speed of sound for tonight, m/s (dry air, c = 331.3 + 0.606 T); uses the true temperature. */
    public double speedOfSoundMps() {
        return 331.3 + 0.606 * tempC;
    }

    /**
     * Judge a guess. Empty = "too cold, no snowy tree cricket". 100 within {@link #TOLERANCE_C}, then minus 20
     * per further degree; a wrong silent/not-silent call scores 0.
     */
    public Verdict judge(OptionalDouble guessC) {
        boolean silentNight = tempC < SILENT_BELOW_C;
        if (guessC.isEmpty()) {
            return new Verdict(silentNight, Double.NaN, silentNight ? 100 : 0);
        }
        if (silentNight) {
            return new Verdict(false, Double.NaN, 0);
        }
        double err = Math.abs(guessC.getAsDouble() - tempC);
        int score = (int) Math.max(0, Math.round(100 - 20 * Math.max(0, err - TOLERANCE_C)));
        return new Verdict(err <= TOLERANCE_C, err, score);
    }
}
