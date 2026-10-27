// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Reed Hum (G178, claimed in the 19 Oct contest, landed after it): wind across the regrown marsh makes the reed stems hum, and the hum tells the wind.
 *
 * <p>Air flowing past a cylinder sheds vortices from alternate sides once the Reynolds number Re = U D / nu passes
 * about {@link #RE_MIN} (47), and the stem sounds an aeolian tone at f = St U / D, where U is the wind speed, D the
 * stem diameter and St the Strouhal number. In the laminar band (Re about 47 to 190) shedding is most regular and the
 * tone purest; there Roshko's fit St = 0.212 (1 - 21.2 / Re) holds, used here below Re {@link #RE_LAMINAR_MAX}.
 * Above it St is taken as about {@link #STROUHAL} (subcritical range). Below Re 47 there is no shedding and the stem
 * is silent, and hums under {@link #MIN_AUDIBLE_HZ} (thick stems in light air) are infrasound and go unheard.
 * Each stem also feels its own gust, within {@link #GUST} of the mean wind. The player hears the voiced
 * stems with their diameters, estimates the wind and calls whether the bumblebees will forage today (wind under
 * {@link #FORAGE_MAX_MPS}, an illustrative line). {@link #solve()} inverts f = St(Re) U / D with the same
 * {@link #strouhal(double)} the generator used, for every voiced stem, and takes the median.
 *
 * <p>Caveats: reeds are treated as rigid smooth cylinders; real stems flex, carry leaves and sit in turbulent,
 * sheared wind, so real hums are less pure. The Roshko fit and St 0.2 are textbook values (the step between them at
 * Re 150 stands in for the irregular transition range). The bumblebee forage threshold is illustrative: bumblebees
 * fly in stronger wind than many bees, and it varies by species, temperature and load. Air viscosity is taken at
 * about 20 C. Stem diameters ({@link #MIN_D_M} and up) and winds (up to {@link #MAX_WIND_MPS}) are clamped so every
 * hum stays below 800 Hz and passes {@link EarRule#check}; it plays soft.
 */
public final class ReedHum {
    /** Strouhal number for a cylinder, subcritical range (above {@link #RE_LAMINAR_MAX}). */
    public static final double STROUHAL = 0.2;
    /** Below this Reynolds number Roshko's laminar fit is used. */
    public static final double RE_LAMINAR_MAX = 150.0;
    /** Kinematic viscosity of air near 20 C, m^2/s. */
    public static final double NU = 1.5e-5;
    /** Vortex shedding (and the hum) starts near this Reynolds number; below it the stem is silent. */
    public static final double RE_MIN = 47.0;
    /** Hums below this are infrasound and go unheard, Hz (lower edge of human hearing). */
    public static final double MIN_AUDIBLE_HZ = 20.0;
    /** Lightest seeded mean wind, m/s. */
    public static final double MIN_WIND_MPS = 0.6;
    /** Thinnest stem, m (ear clamp). */
    public static final double MIN_D_M = 0.003;
    /** Thickest stem, m. */
    public static final double MAX_D_M = 0.012;
    /** Strongest seeded mean wind, m/s (ear clamp). */
    public static final double MAX_WIND_MPS = 8.0;
    /** Stems per round. */
    public static final int STEMS = 9;
    /** Fewest voiced stems in a round. */
    public static final int MIN_VOICED = 3;
    /** Per-stem gust spread, fraction of the mean wind. */
    public static final double GUST = 0.06;
    /** Bumblebees forage below this wind, m/s (illustrative line, not a measured species limit). */
    public static final double FORAGE_MAX_MPS = 5.0;
    /** Seeded winds keep at least this distance from the forage threshold, m/s. */
    public static final double CALL_MARGIN_MPS = 0.6;
    /** Wind guess counts within this many m/s of the true wind. */
    public static final double WIND_TOL_MPS = 0.5;
    /** UI label for the forage call. */
    public static final String FORAGE_LABEL = "Bumblebees forage below 5 m/s (illustrative line)";
    /** Playback level, 0-1 (soft). */
    public static final double LEVEL = 0.3;
    private static final int MAX_TRIES = 1000;
    private static final long SALT = 0x5245_4431L; // "RED1"

    /**
     * One stem: diameter (m), the wind it feels (m/s), its Reynolds number and its heard hum (Hz; NaN when it sheds no
     * vortices or its hum is below {@link #MIN_AUDIBLE_HZ}).
     */
    public record Stem(double diameterM, double localMps, double re, double heardHz) {
        /** Whether this stem sheds vortices at all (Re above {@link #RE_MIN}). */
        public boolean shedding() {
            return re > RE_MIN;
        }

        /** Whether the player hears this stem. */
        public boolean voiced() {
            return !Double.isNaN(heardHz);
        }
    }

    /** One hum for playback. */
    public record Hum(double hz, double level) { }

    /** The solver's reading: per-stem wind estimates (voiced only), median wind, forage call, ambiguity flag. */
    public record Reading(List<Double> perStemMps, double windMps, boolean forage, boolean ambiguous) {
        /** Copies the list. */
        public Reading {
            perStemMps = List.copyOf(perStemMps);
        }
    }

    /** A judged answer. */
    public record Verdict(boolean windRight, boolean callRight, int score) { }

    private final long seed;
    private final double wind;
    private final List<Stem> stems;

    private ReedHum(long seed, double wind, List<Stem> stems) {
        this.seed = seed;
        this.wind = wind;
        this.stems = List.copyOf(stems);
    }

    /** A seeded day; draws repeat (deterministically) until the wind is clear of the threshold and enough stems hum. */
    public static ReedHum seeded(long seed) {
        return build(seed, GUST);
    }

    /** A seeded day with a chosen gust spread, for tests. */
    static ReedHum of(long seed, double gust) {
        return build(seed, gust);
    }

    private static ReedHum build(long seed, double gust) {
        Rng rng = new Rng(seed ^ SALT);
        double u = drawWind(rng);
        List<Stem> s = drawStems(rng, u, gust);
        for (int k = 1; k < MAX_TRIES && !ok(u, s); k++) {
            u = drawWind(rng);
            s = drawStems(rng, u, gust);
        }
        return new ReedHum(seed, u, s);
    }

    private static boolean ok(double u, List<Stem> s) {
        return Math.abs(u - FORAGE_MAX_MPS) >= CALL_MARGIN_MPS && s.stream().filter(Stem::voiced).count() >= MIN_VOICED;
    }

    private static double drawWind(Rng rng) {
        return (60 + roll(rng, 741)) / 100.0; // MIN_WIND_MPS 0.60 up to MAX_WIND_MPS 8.00
    }

    private static List<Stem> drawStems(Rng rng, double u, double gust) {
        List<Stem> out = new ArrayList<>();
        for (int i = 0; i < STEMS; i++) {
            double d = (30 + roll(rng, 91)) / 10000.0; // MIN_D_M..MAX_D_M, 3.0-12.0 mm
            double local = u * (1 + gust * (roll(rng, 2001) / 1000.0 - 1.0));
            out.add(stem(d, local));
        }
        return out;
    }

    /** A stem of diameter {@code d} (m) in local wind {@code u} (m/s); silent at or below {@link #RE_MIN}. */
    public static Stem stem(double d, double u) {
        double re = reynolds(u, d);
        double hz = Double.NaN;
        if (re > RE_MIN) {
            double f = Math.round(frequency(u, d) * 10) / 10.0;
            hz = f >= MIN_AUDIBLE_HZ ? f : Double.NaN;
        }
        return new Stem(d, u, re, hz);
    }

    private static int roll(Rng rng, int n) {
        return (int) Long.remainderUnsigned(rng.nextLong(), n);
    }

    /** Reynolds number U D / nu. */
    public static double reynolds(double u, double d) {
        return u * d / NU;
    }

    /** Strouhal number at Reynolds number {@code re}: Roshko's laminar fit below {@link #RE_LAMINAR_MAX}, else 0.2. */
    public static double strouhal(double re) {
        return re < RE_LAMINAR_MAX ? 0.212 * (1 - 21.2 / re) : STROUHAL;
    }

    /** Aeolian tone, Hz: St(Re) U / D. */
    public static double frequency(double u, double d) {
        return strouhal(reynolds(u, d)) * u / d;
    }

    /**
     * Wind from a hum, inverting {@link #frequency} with the same {@link #strouhal}: in the laminar band
     * f = 0.212 (U / D - 21.2 nu / D^2), so U = f D / 0.212 + 21.2 nu / D; above it U = f D / 0.2. The branch whose
     * U lands in its own Re range is used; if rounding puts both or neither there, the one whose predicted pitch is
     * nearer wins (laminar first on ties).
     */
    public static double windFrom(double hz, double d) {
        double lam = hz * d / 0.212 + 21.2 * NU / d;
        double sub = hz * d / STROUHAL;
        boolean lamOk = reynolds(lam, d) < RE_LAMINAR_MAX;
        boolean subOk = reynolds(sub, d) >= RE_LAMINAR_MAX;
        if (lamOk && !subOk) {
            return lam;
        }
        if (subOk && !lamOk) {
            return sub;
        }
        return Math.abs(frequency(lam, d) - hz) <= Math.abs(frequency(sub, d) - hz) ? lam : sub;
    }

    /** Whether a wind estimate is too close to the forage line to call: within the gust spread at the line. */
    public static boolean ambiguous(double windEstimate) {
        return Math.abs(windEstimate - FORAGE_MAX_MPS) <= GUST * FORAGE_MAX_MPS;
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** True mean wind, m/s (for the judge and tests). */
    public double windMps() {
        return wind;
    }

    /** True forage call. */
    public boolean forage() {
        return wind < FORAGE_MAX_MPS;
    }

    /** All stems, voiced and silent. */
    public List<Stem> stems() {
        return stems;
    }

    /** Voiced stems' hums for playback (ear-rule checked). */
    public List<Hum> hums() {
        List<Hum> out = new ArrayList<>();
        for (Stem s : stems) {
            if (s.voiced()) {
                out.add(new Hum(EarRule.check(s.heardHz(), "reed hum"), LEVEL));
            }
        }
        return out;
    }

    /** Invert each voiced hum and take the median wind. */
    public Reading solve() {
        List<Double> us = new ArrayList<>();
        for (Stem s : stems) {
            if (s.voiced()) {
                us.add(windFrom(s.heardHz(), s.diameterM()));
            }
        }
        double m = median(us);
        return new Reading(us, m, m < FORAGE_MAX_MPS, ambiguous(m));
    }

    static double median(List<Double> xs) {
        List<Double> s = new ArrayList<>(xs);
        s.sort(Double::compare);
        int n = s.size();
        return n % 2 == 1 ? s.get(n / 2) : (s.get(n / 2 - 1) + s.get(n / 2)) / 2;
    }

    /**
     * Judge: 60 for a wind within {@link #WIND_TOL_MPS} of the truth, 40 for the right forage call; on an ambiguous
     * day (true wind within the gust spread of the line) either call is accepted.
     */
    public Verdict judge(double windGuess, boolean forageCall) {
        boolean w = Math.abs(windGuess - wind) <= WIND_TOL_MPS;
        boolean c = ambiguous(wind) || forageCall == forage();
        return new Verdict(w, c, (w ? 60 : 0) + (c ? 40 : 0));
    }
}
