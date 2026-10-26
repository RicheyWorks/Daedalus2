// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Herd Outbreak (contest G172, "Hoof Blight"): a seeded Reed-Frost epidemic in the Hornback herd, with vaccination and
 * a quarantine fence.
 *
 * <p>The herd has {@code herd} Hornbacks. Before the blight arrives, the herder vaccinates {@code vaccinate(n)} of them
 * (doses are limited); vaccinated animals are immune. One animal brings the blight in. Each generation (about a week),
 * every susceptible animal escapes each infectious one independently with chance {@code 1 − p}, where
 * {@code p = r0 / herd}, so it falls sick with chance {@code 1 − (1 − p)^I}; the sick recover (immune) a generation
 * later. From generation {@code fenceAt} on, the quarantine fence multiplies p by {@code fenceFactor}.
 *
 * <p>The herd-immunity threshold is {@code 1 − 1/r0}: vaccinate more than that share and the blight cannot spread.
 * Without vaccination, a major outbreak infects about the share z solving {@code z = 1 − exp(−r0·z)}
 * ({@link #finalSize(double)}). Every draw is a splitmix hash of (seed, generation, animal).
 */
public final class HerdOutbreak {

    /** How the herd came through. */
    public enum Outcome { CONTAINED, OUTBREAK, EPIDEMIC }

    /** Share of the herd sick at most for CONTAINED. */
    public static final double CONTAINED = 0.1;

    /** Share of the herd sick above which it is an EPIDEMIC. */
    public static final double EPIDEMIC = 0.5;

    /**
     * Herd tuning.
     *
     * @param herd        Hornbacks in the herd
     * @param r0          basic reproduction number of the blight
     * @param doses       vaccine doses available
     * @param generations generations to run at most
     */
    public record Settings(int herd, double r0, int doses, int generations) {

        /** The default herd: 200 Hornbacks, r0 2.5, 150 doses, 60 generations. */
        public static final Settings DEFAULT = new Settings(200, 2.5, 150, 60);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (herd < 2 || !(r0 >= 0) || r0 > herd || doses < 0 || generations < 1) {
                throw new IllegalArgumentException("bad herd-outbreak settings");
            }
        }
    }

    /** One generation: newly sick, still susceptible. */
    public record Generation(int index, int sick, int susceptible) {}

    /** The result: total sick (including the index case), the share of the herd, the outcome. */
    public record Report(Outcome outcome, int sick, double share, int vaccinated, List<Generation> generations) {

        /** Defensive copy. */
        public Report {
            generations = List.copyOf(generations);
        }

        /** Pasture cover after the blight: a contained herd keeps grazing the MEADOW; otherwise it scrubs over. */
        public Vegetation band() {
            return outcome == Outcome.CONTAINED ? Vegetation.MEADOW : Vegetation.SCRUB;
        }
    }

    private final Settings s;
    private final long seed;
    private int vaccinated;
    private int fenceAt = Integer.MAX_VALUE;
    private double fenceFactor = 1;

    private HerdOutbreak(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
    }

    /** A seeded herd. */
    public static HerdOutbreak herd(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new HerdOutbreak(settings, seed);
    }

    /** Vaccinates {@code n} animals before the blight. False if over the doses or leaving no one to catch it. */
    public boolean vaccinate(int n) {
        if (n < 0 || n > s.doses() || n > s.herd() - 1) {
            return false;
        }
        vaccinated = n;
        return true;
    }

    /** Puts up the quarantine fence from generation {@code gen}, scaling contact by {@code factor} (0..1). */
    public boolean fence(int gen, double factor) {
        if (gen < 0 || !(factor >= 0 && factor <= 1)) {
            return false;
        }
        fenceAt = gen;
        fenceFactor = factor;
        return true;
    }

    /** The herd-immunity threshold 1 − 1/r0 (0 when r0 ≤ 1). */
    public double threshold() {
        return s.r0() <= 1 ? 0 : 1 - 1 / s.r0();
    }

    /** Final-size share z solving z = 1 − exp(−r·z) for the major outbreak (0 when r ≤ 1). */
    public static double finalSize(double r) {
        if (!(r > 1)) {
            return 0;
        }
        // bisection on f(z) = z - 1 + exp(-r z): f < 0 just above 0 and f(1) > 0, so it converges even for r near 1
        double lo = 1e-12;
        double hi = 1;
        for (int i = 0; i < 200; i++) {
            double mid = (lo + hi) / 2;
            if (mid - 1 + Math.exp(-r * mid) < 0) {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        return (lo + hi) / 2;
    }

    /** Runs the blight. Deterministic in the settings, the seed and the plan. */
    public Report run() {
        int n = s.herd();
        // 0 susceptible, 1 infectious, 2 removed (vaccinated or recovered)
        byte[] state = new byte[n];
        for (int i = 0; i < vaccinated; i++) {
            state[1 + i] = 2;
        }
        state[0] = 1;
        int infectious = 1;
        int sick = 1;
        List<Generation> log = new ArrayList<>();
        for (int g = 0; g < s.generations() && infectious > 0; g++) {
            double p = s.r0() / n * (g >= fenceAt ? fenceFactor : 1);
            double hit = 1 - Math.pow(1 - p, infectious);
            int fresh = 0;
            int left = 0;
            for (int i = 0; i < n; i++) {
                if (state[i] == 1) {
                    state[i] = 2;
                } else if (state[i] == 0) {
                    if (roll(g, i) < hit) {
                        state[i] = 3;
                        fresh++;
                    } else {
                        left++;
                    }
                }
            }
            for (int i = 0; i < n; i++) {
                if (state[i] == 3) {
                    state[i] = 1;
                }
            }
            infectious = fresh;
            sick += fresh;
            log.add(new Generation(g + 1, fresh, left));
        }
        double share = (double) sick / n;
        Outcome o = share <= CONTAINED ? Outcome.CONTAINED : share > EPIDEMIC ? Outcome.EPIDEMIC : Outcome.OUTBREAK;
        return new Report(o, sick, share, vaccinated, log);
    }

    private double roll(int gen, long animal) {
        long z = seed + 0x9E3779B97F4A7C15L * (gen + 1) + 0xBF58476D1CE4E5B9L * (animal + 1);
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
