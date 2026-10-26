// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Brook Babble (contest G173): the regrown brook babbles because air bubbles trapped by its riffles ring as they
 * form.
 *
 * <p>A newly formed bubble rings at its Minnaert resonance, f = (1 / 2 pi R) sqrt(3 gamma P / rho), where R is the
 * RADIUS (not the diameter: f R is about 3.28 m Hz at 1 atm, so a 6 mm radius rings near 550 Hz while a 6 mm
 * diameter bubble rings near 1.1 kHz), gamma the ratio of specific heats of air, rho the water density and P the water pressure at the bubble,
 * P = surface pressure + rho g depth. Bigger bubbles ring lower; deeper bubbles ring a little higher. A hydrophone
 * hears each riffle's bubbles together with their depths. The player sizes every bubble by its pitch, totals the
 * trapped air in each riffle and picks the best-aerated riffle for the trout and mayfly nymphs.
 * {@link #solve()} inverts Minnaert with the depth correction; the judge scores sizes (within
 * {@link #SIZE_TOL} of the radius) and the riffle pick.
 *
 * <p>Caveats: only bubbles of {@link #MIN_R_M} m and larger are voiced so every ring stays below 800 Hz and passes
 * {@link EarRule#check}; real brooks also make many smaller, higher bubbles, which are left out here. The adiabatic
 * Minnaert form ignores surface tension and damping (fine at these millimetre sizes). Trapped air as an aeration
 * score is an illustrative index: real dissolved oxygen in a brook also depends on temperature, flow, plants and
 * respiration. Counts, sizes and depths are illustrative.
 */
public final class BrookBabble {
    /** Surface (atmospheric) pressure, Pa. */
    public static final double P0_PA = 101_325.0;
    /** Water density, kg/m^3. */
    public static final double RHO = 1000.0;
    /** Gravity, m/s^2. */
    public static final double G = 9.81;
    /** Ratio of specific heats for air (adiabatic). */
    public static final double GAMMA = 1.4;
    /** Smallest voiced bubble radius, m (keeps rings below 800 Hz). */
    public static final double MIN_R_M = 0.0045;
    /** Largest bubble radius, m (illustrative). */
    public static final double MAX_R_M = 0.010;
    /** Deepest bubble, m (illustrative riffle depth). */
    public static final double MAX_DEPTH_M = 0.40;
    /** Riffles per round. */
    public static final int RIFFLES = 3;
    /** Listening window, s. */
    public static final double WINDOW_S = 10.0;
    /** A size guess counts when within this fraction of the true radius. */
    public static final double SIZE_TOL = 0.01;
    /** The best riffle holds at least this much more air than the next, as a fraction. */
    public static final double PICK_MARGIN = 0.15;
    /** UI label for the riffle air totals; the index is illustrative, not a dissolved-oxygen reading. */
    public static final String AERATION_LABEL = "Trapped air (illustrative aeration index, not dissolved oxygen)";
    /** Radius draw step, m (0.01 mm). */
    public static final double R_STEP_M = 1e-5;
    /** Playback level, 0-1 (soft). */
    public static final double LEVEL = 0.3;
    private static final int MAX_TRIES = 1000;
    private static final long SALT = 0x4252_4B31L; // "BRK1"

    /** One bubble: when it rang, its depth, the heard pitch (rounded to 0.1 Hz) and its true RADIUS in metres. */
    public record Bubble(double t, double depthM, double heardHz, double radiusM) {
        /** True radius in millimetres (radius, not diameter). */
        public double radiusMm() {
            return radiusM * 1000.0;
        }
    }

    /** One ring for playback. */
    public record Ring(double t, double hz, double level) { }

    /** The solver's reading: radii per riffle (m), trapped air per riffle (mL), best riffle index. */
    public record Reading(List<List<Double>> radiiM, List<Double> airMl, int best) {
        /** Copies the lists. */
        public Reading {
            List<List<Double>> r = new ArrayList<>();
            radiiM.forEach(x -> r.add(List.copyOf(x)));
            radiiM = List.copyOf(r);
            airMl = List.copyOf(airMl);
        }
    }

    /** A judged answer. */
    public record Verdict(int sizesRight, int sizes, boolean pickRight, int score) { }

    private final long seed;
    private final List<List<Bubble>> riffles;

    private BrookBabble(long seed, List<List<Bubble>> riffles) {
        this.seed = seed;
        List<List<Bubble>> r = new ArrayList<>();
        riffles.forEach(x -> r.add(List.copyOf(x)));
        this.riffles = List.copyOf(r);
    }

    /** A seeded round; draws are repeated (deterministically) until the best riffle clears {@link #PICK_MARGIN}. */
    public static BrookBabble seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        List<List<Bubble>> rs = draw(rng);
        for (int k = 1; k < MAX_TRIES && margin(trueAir(rs)) < PICK_MARGIN; k++) {
            rs = draw(rng);
        }
        return new BrookBabble(seed, rs);
    }

    private static List<List<Bubble>> draw(Rng rng) {
        List<List<Bubble>> rs = new ArrayList<>();
        for (int i = 0; i < RIFFLES; i++) {
            int n = 6 + roll(rng, 13); // 6-18 bubbles
            List<Bubble> b = new ArrayList<>();
            for (int j = 0; j < n; j++) {
                double r = (450 + roll(rng, 551)) / 1e5; // radius 4.50-10.00 mm on the 0.01 mm grid
                double h = roll(rng, (int) Math.round(MAX_DEPTH_M * 1000) + 1) / 1000.0;
                double t = roll(rng, (int) Math.round(WINDOW_S * 1000)) / 1000.0;
                double hz = Math.round(frequency(r, h) * 10) / 10.0;
                b.add(new Bubble(t, h, hz, r));
            }
            b.sort((x, y) -> Double.compare(x.t(), y.t()));
            rs.add(b);
        }
        return rs;
    }

    private static int roll(Rng rng, int n) {
        return (int) Long.remainderUnsigned(rng.nextLong(), n);
    }

    /**
     * Deepest point at which the smallest voiced bubble still rings below 800 Hz, m (about 2.1 m); riffle depth
     * ({@link #MAX_DEPTH_M}) stays well under it.
     */
    public static double maxVoicedDepthM() {
        double w = EarRule.MAX_FUNDAMENTAL_HZ * 2 * Math.PI * MIN_R_M;
        return (w * w * RHO / (3 * GAMMA) - P0_PA) / (RHO * G);
    }

    /** Whether a bubble of radius {@code r} (m) is voiced: {@link #MIN_R_M} and up; smaller ones stay silent. */
    public static boolean voiced(double r) {
        return r >= MIN_R_M;
    }

    /** Water pressure at depth {@code h}, Pa. */
    public static double pressure(double h) {
        return P0_PA + RHO * G * h;
    }

    /** Minnaert resonance of a bubble of radius {@code r} (m) at depth {@code h} (m), Hz. */
    public static double frequency(double r, double h) {
        return Math.sqrt(3 * GAMMA * pressure(h) / RHO) / (2 * Math.PI * r);
    }

    /** Minnaert inverted: radius (m) from pitch {@code hz} at depth {@code h}. */
    public static double radius(double hz, double h) {
        return Math.sqrt(3 * GAMMA * pressure(h) / RHO) / (2 * Math.PI * hz);
    }

    /** Sphere volume in mL for radius {@code r} in m. */
    public static double volumeMl(double r) {
        return 4.0 / 3.0 * Math.PI * r * r * r * 1e6;
    }

    /** Relative lead of the largest value over the second largest. */
    static double margin(List<Double> air) {
        double a = Double.NEGATIVE_INFINITY;
        double b = Double.NEGATIVE_INFINITY;
        for (double x : air) {
            if (x > a) {
                b = a;
                a = x;
            } else if (x > b) {
                b = x;
            }
        }
        return (a - b) / b;
    }

    private static List<Double> trueAir(List<List<Bubble>> rs) {
        List<Double> out = new ArrayList<>();
        for (List<Bubble> r : rs) {
            double s = 0;
            for (Bubble b : r) {
                s += volumeMl(b.radiusM());
            }
            out.add(s);
        }
        return out;
    }

    /** Index of the largest value; ties keep the lowest riffle index (deterministic). */
    static int argmax(List<Double> xs) {
        int best = 0;
        for (int i = 1; i < xs.size(); i++) {
            if (xs.get(i) > xs.get(best)) {
                best = i;
            }
        }
        return best;
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** All riffles' bubbles (true radii are for the judge and tests). */
    public List<List<Bubble>> riffles() {
        return riffles;
    }

    /** True trapped air per riffle, mL. */
    public List<Double> airMl() {
        return trueAir(riffles);
    }

    /** True best riffle. */
    public int bestRiffle() {
        return argmax(airMl());
    }

    /** One riffle's rings for playback (ear-rule checked). */
    public List<Ring> soundscape(int riffle) {
        List<Ring> out = new ArrayList<>();
        for (Bubble b : riffles.get(riffle)) {
            if (!voiced(b.radiusM())) {
                continue;
            }
            out.add(new Ring(b.t(), EarRule.check(b.heardHz(), "brook bubble"), LEVEL));
        }
        return out;
    }

    /** Invert every heard pitch with its depth, total the air, pick the riffle with the most (ties: lowest index). */
    public Reading solve() {
        return read(true);
    }

    /** Same as {@link #solve()} but ignoring depth (all at surface pressure); for tests and hints. */
    public Reading solveIgnoringDepth() {
        return read(false);
    }

    private Reading read(boolean useDepth) {
        List<List<Double>> radii = new ArrayList<>();
        List<Double> air = new ArrayList<>();
        for (List<Bubble> r : riffles) {
            List<Double> rr = new ArrayList<>();
            double s = 0;
            for (Bubble b : r) {
                double x = radius(b.heardHz(), useDepth ? b.depthM() : 0.0);
                rr.add(x);
                s += volumeMl(x);
            }
            radii.add(rr);
            air.add(s);
        }
        return new Reading(radii, air, argmax(air));
    }

    /** Judge: 60 x (sizes within tolerance / all bubbles) + 40 for the right riffle, rounded. */
    public Verdict judge(List<List<Double>> radiiM, int pick) {
        int right = 0;
        int total = 0;
        for (int i = 0; i < riffles.size(); i++) {
            List<Bubble> r = riffles.get(i);
            List<Double> g = i < radiiM.size() ? radiiM.get(i) : List.of();
            for (int j = 0; j < r.size(); j++) {
                total++;
                double tr = r.get(j).radiusM();
                if (j < g.size() && g.get(j) != null && Math.abs(g.get(j) - tr) <= SIZE_TOL * tr) {
                    right++;
                }
            }
        }
        boolean ok = pick == bestRiffle();
        int score = (int) Math.round(60.0 * right / total + (ok ? 40 : 0));
        return new Verdict(right, total, ok, score);
    }
}
