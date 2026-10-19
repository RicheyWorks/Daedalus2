// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Shoal Harvest (contest G176, "Net Quota"): fixed-catch versus fixed-effort fishing on a noisy logistic shoal.
 *
 * <p>The silverfin shoal grows logistically, {@code B' = B + r·B·(1 − B/K)·ε}, where ε is seeded year-to-year noise
 * (uniform in {@code 1 ± noise}). Each year the harbour master sets one rule for the fleet:
 * <ul>
 *   <li>{@link Rule#QUOTA}: land a fixed tonnage {@code q} (or everything left, if less);</li>
 *   <li>{@link Rule#EFFORT}: land a fixed share {@code e} of the shoal.</li>
 * </ul>
 * Maximum sustainable yield is {@code rK/4} at {@code B = K/2} ({@link #msy()}), reached by quota {@code rK/4} or by
 * the share {@link #msyEffort()} on the deterministic model. With noise, the MSY quota is a knife-edge (one bad year below K/2 and
 * the fixed catch drives the shoal down), while the MSY effort takes less when the shoal is small and recovers. Every
 * draw is a splitmix hash of (seed, year).
 */
public final class ShoalHarvest {

    /** The fleet's rule. */
    public enum Rule { QUOTA, EFFORT }

    /** How the fishery ended. */
    public enum Outcome { THRIVING, DEPLETED, COLLAPSED }

    /**
     * Shoal tuning.
     *
     * @param capacity carrying capacity K (tonnes)
     * @param growth   intrinsic growth r
     * @param noise    half-width of the yearly growth noise
     * @param years    years to fish
     * @param collapse shoal below this share of K counts as collapsed
     */
    public record Settings(double capacity, double growth, double noise, int years, double collapse) {

        /** The default shoal: K 1000 t, r 0.6, noise ±0.5, 50 years, collapse under 5% of K. */
        public static final Settings DEFAULT = new Settings(1000, 0.6, 0.5, 50, 0.05);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (!(capacity > 0) || Double.isInfinite(capacity) || !(growth > 0 && growth <= 1)
                    || !(noise >= 0 && noise < 1) || years < 1 || !(collapse >= 0 && collapse < 1)) {
                throw new IllegalArgumentException("bad shoal settings");
            }
        }
    }

    /** One year: shoal before fishing, catch landed. */
    public record Year(int index, double shoal, double catchTonnes) {}

    /** The result. */
    public record Report(Outcome outcome, double shoal, double total, List<Year> years) {

        /** Defensive copy. */
        public Report {
            years = List.copyOf(years);
        }

        /** Mean catch per year. */
        public double meanCatch() {
            return years.isEmpty() ? 0 : total / years.size();
        }

        /** Kelp cover on the fishing banks: a thriving shoal keeps them WETLAND (kelp), otherwise BARE. */
        public Vegetation band() {
            return outcome == Outcome.THRIVING ? Vegetation.WETLAND : Vegetation.BARE;
        }
    }

    private final Settings s;
    private final long seed;

    private ShoalHarvest(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
    }

    /** A seeded shoal. */
    public static ShoalHarvest shoal(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new ShoalHarvest(settings, seed);
    }

    /** Maximum sustainable yield rK/4. */
    public double msy() {
        return s.growth() * s.capacity() / 4;
    }

    /**
     * Share that gives MSY on the deterministic model. The shoal grows before the fleet fishes, so the equilibrium under
     * share e satisfies (1 − e)·G(B) = B; the catch e·G(B) peaks at rK/4 when e/(1 − e) = r/2, that is e = (r/2)/(1 + r/2).
     */
    public double msyEffort() {
        double u = s.growth() / 2;
        return u / (1 + u);
    }

    /**
     * Fishes {@code years} from a shoal at half capacity under one rule. {@code level} is tonnes for QUOTA and a share
     * (0..1) for EFFORT. Deterministic in the settings, the seed, the rule and the level.
     */
    public Report run(Rule rule, double level) {
        if (rule == null || !(level >= 0) || Double.isInfinite(level) || (rule == Rule.EFFORT && level > 1)) {
            throw new IllegalArgumentException("bad rule");
        }
        double b = s.capacity() / 2;
        double total = 0;
        boolean collapsed = false;
        List<Year> log = new ArrayList<>();
        for (int y = 0; y < s.years(); y++) {
            double eps = 1 + s.noise() * (2 * roll(y) - 1);
            b = Math.max(0, b + s.growth() * b * (1 - b / s.capacity()) * eps);
            double take = rule == Rule.QUOTA ? Math.min(level, b) : level * b;
            log.add(new Year(y, b, take));
            b -= take;
            total += take;
            if (b < s.collapse() * s.capacity()) {
                collapsed = true;
                b = Math.max(b, 0);
            }
        }
        Outcome o = collapsed ? Outcome.COLLAPSED : b >= s.capacity() / 4 ? Outcome.THRIVING : Outcome.DEPLETED;
        return new Report(o, b, total, log);
    }

    private double roll(int year) {
        long z = seed + 0x9E3779B97F4A7C15L * (year + 1);
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
