// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Allee Release (contest G142): bringing the sky-cranes back, where too few birds cannot find mates.
 *
 * <p>The ark aviary has bred {@code budget} cranes. The player schedules releases ({@code release(year, birds)}) onto
 * the marsh. Each year, in this order:
 * <ul>
 *   <li>the year's released birds join the flock;</li>
 *   <li>each crane survives with chance {@code survival};</li>
 *   <li>the survivors form ⌊N/2⌋ possible pairs. A pair finds a mate and nests with chance {@code N / (N + mateHalf)};
 *       this is the mate-finding <b>Allee effect</b>;</li>
 *   <li>each nest raises two eggs, and each fledges with chance {@code fledge · max(0, 1 − N/capacity)}.</li>
 * </ul>
 * The expected growth {@link #growth(double)} is below 1 under the Allee threshold ({@link #threshold()}), so small
 * flocks dwindle even with room to spare. Every draw is a splitmix hash of (seed, year, bird, salt).
 *
 * <p>After {@code years}: ESTABLISHED if the flock is at least {@code goal}, LINGERING if any birds are left,
 * otherwise EXTINCT.
 */
public final class AlleeRelease {

    /** How the reintroduction went. */
    public enum Outcome { ESTABLISHED, LINGERING, EXTINCT }

    /**
     * Marsh tuning.
     *
     * @param budget   cranes the aviary has bred
     * @param years    years to run
     * @param survival yearly adult survival
     * @param mateHalf flock size at which half the pairs find a mate
     * @param fledge   chance each egg fledges on an empty marsh
     * @param capacity flock size at which no egg fledges
     * @param goal     flock that counts as established
     */
    public record Settings(int budget, int years, double survival, double mateHalf, double fledge, double capacity,
            int goal) {

        /** The default marsh. */
        public static final Settings DEFAULT = new Settings(40, 40, 0.75, 30, 1.0, 150, 50);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (budget < 0 || years < 1 || !(survival >= 0 && survival <= 1) || !(mateHalf >= 0)
                    || !(fledge >= 0 && fledge <= 1) || !(capacity > 0) || goal < 1 || Double.isInfinite(mateHalf)
                    || Double.isInfinite(capacity)) {
                throw new IllegalArgumentException("bad allee settings");
            }
        }
    }

    /** One year: birds released, flock after the year, nests and fledglings. */
    public record Year(int index, int released, int flock, int nests, int fledged) {}

    /** The result. */
    public record Report(Outcome outcome, int flock, int peak, List<Year> years) {

        /** Defensive copy. */
        public Report {
            years = List.copyOf(years);
        }

        /** Marsh cover for the crane grounds: an established flock keeps the marsh WETLAND, otherwise it scrubs over. */
        public Vegetation band() {
            return outcome == Outcome.ESTABLISHED ? Vegetation.WETLAND : Vegetation.SCRUB;
        }
    }

    private final Settings s;
    private final long seed;
    private final Map<Integer, Integer> plan = new TreeMap<>();

    private AlleeRelease(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
    }

    /** A seeded marsh. */
    public static AlleeRelease marsh(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new AlleeRelease(settings, seed);
    }

    /** Schedules {@code birds} for release in {@code year}. False if the year is out of range or the aviary is short. */
    public boolean release(int year, int birds) {
        if (year < 0 || year >= s.years() || birds < 1 || birds > left()) {
            return false;
        }
        plan.merge(year, birds, Integer::sum);
        return true;
    }

    /** Cranes still in the aviary. */
    public int left() {
        int used = 0;
        for (int b : plan.values()) {
            used += b;
        }
        return s.budget() - used;
    }

    /** Expected flock next year over this year, from a flock of n (continuous pairs; 0 for n ≤ 0). */
    public double growth(double n) {
        if (!(n > 0)) {
            return 0;
        }
        double after = s.survival() * n;
        double mate = after + s.mateHalf() <= 0 ? 0 : after / (after + s.mateHalf());
        double chick = s.fledge() * Math.max(0, 1 - after / s.capacity());
        return (after + after / 2 * mate * 2 * chick) / n;
    }

    /** The Allee threshold: the smallest whole flock whose expected growth is at least 1, or −1 if none. */
    public int threshold() {
        for (int n = 1; n <= (int) Math.ceil(s.capacity()); n++) {
            if (growth(n) >= 1) {
                return n;
            }
        }
        return -1;
    }

    /** Runs the schedule. Deterministic in the settings, the seed and the plan. */
    public Report run() {
        int flock = 0;
        int peak = 0;
        List<Year> log = new ArrayList<>();
        for (int y = 0; y < s.years(); y++) {
            int released = plan.getOrDefault(y, 0);
            flock += released;
            int alive = 0;
            for (int b = 0; b < flock; b++) {
                if (roll(y, b, 1) < s.survival()) {
                    alive++;
                }
            }
            double mate = alive + s.mateHalf() <= 0 ? 0 : alive / (alive + s.mateHalf());
            double chick = s.fledge() * Math.max(0, 1 - alive / s.capacity());
            int nests = 0;
            int fledged = 0;
            for (int p = 0; p < alive / 2; p++) {
                if (roll(y, p, 2) < mate) {
                    nests++;
                    for (int e = 0; e < 2; e++) {
                        if (roll(y, 2L * p + e, 3) < chick) {
                            fledged++;
                        }
                    }
                }
            }
            flock = alive + fledged;
            peak = Math.max(peak, flock);
            log.add(new Year(y, released, flock, nests, fledged));
        }
        Outcome o = flock >= s.goal() ? Outcome.ESTABLISHED : flock > 0 ? Outcome.LINGERING : Outcome.EXTINCT;
        return new Report(o, flock, peak, log);
    }

    private double roll(int year, long key, int salt) {
        long z = seed + 0x9E3779B97F4A7C15L * (year + 1) + 0xBF58476D1CE4E5B9L * (key + 1) + 0x94D049BB133111EBL * salt;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
