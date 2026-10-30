// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Reed Release (contest G507): G251 Translocation Plan meets G504 Reed Ceiling.
 *
 * <p>The keeper chooses how much reed to plant (one of {@code reedOptions} hectares) and how to spend a budget of
 * aviary cranes over the first {@code releaseYears} years (at most {@code perYear} a year). The marsh then runs the
 * G504 hawk/crane Rosenzweig-MacArthur dynamics one season at a time (RK4), with released birds added at the start
 * of each season and a seeded log-normal shock on the cranes at its end. A run "crashes" if cranes fall below
 * {@code threshold} at any census after the last release. Every plan sees the same shocks (common random numbers).
 *
 * <p>{@link #best()} is the brute force: every reed option times every schedule. {@link #fast()} does a greedy
 * schedule per reed option and keeps the best. More reed raises the crane ceiling, but past the Hopf point
 * ({@link ReedCeiling#cycleHectares()}, 64.3 ha by default) the marsh swings into boom and bust and crashes return.
 *
 * <p>Daedalus hook: the census board shows the plan as a planting order for the G183 meadow crew plus a release
 * calendar for the G163 aviary.
 */
public final class ReedRelease {

    /**
     * Plan tuning.
     *
     * @param marsh        G504 marsh (its reed size is replaced by each option)
     * @param reedOptions  reedbed sizes the keeper may choose, hectares
     * @param startCranes  cranes on the marsh at year 0
     * @param startHawks   hawks on the marsh at year 0
     * @param budget       aviary cranes to release in total
     * @param perYear      most cranes released in one year
     * @param releaseYears years releases may happen in
     * @param horizon      seasons simulated
     * @param threshold    crash level for cranes
     * @param sigma        sd of the yearly log shock on cranes
     * @param runs         seeded runs per risk estimate
     */
    public record Settings(ReedCeiling.Settings marsh, List<Double> reedOptions, double startCranes,
            double startHawks, int budget, int perYear, int releaseYears, int horizon, double threshold,
            double sigma, int runs) {

        /** G504 marsh; reed 10..150 ha; 6 cranes, 3 hawks; 8 birds over 4 years (at most 4); 40 seasons. */
        public static final Settings DEFAULT = new Settings(ReedCeiling.Settings.DEFAULT,
                List.of(10.0, 25.0, 40.0, 55.0, 80.0, 110.0, 150.0), 6, 3, 8, 4, 4, 40, 4, 0.15, 150);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (marsh == null || reedOptions == null || reedOptions.isEmpty() || !(startCranes >= 0)
                    || !(startHawks >= 0) || budget < 0 || perYear < 0 || releaseYears < 1
                    || horizon <= releaseYears || !(threshold > 0) || !(sigma >= 0) || Double.isInfinite(sigma)
                    || runs < 1 || (long) perYear * releaseYears < budget) {
                throw new IllegalArgumentException("bad reed release settings");
            }
            reedOptions = List.copyOf(reedOptions);
            for (double h : reedOptions) {
                if (!(h > 0) || Double.isInfinite(h)) {
                    throw new IllegalArgumentException("bad reed option");
                }
            }
        }

        /** The same plan with another budget. */
        public Settings withBudget(int b) {
            return new Settings(marsh, reedOptions, startCranes, startHawks, b, perYear, releaseYears, horizon,
                    threshold, sigma, runs);
        }

        /** The same plan with other reed options. */
        public Settings withReed(List<Double> options) {
            return new Settings(marsh, options, startCranes, startHawks, budget, perYear, releaseYears, horizon,
                    threshold, sigma, runs);
        }
    }

    /** A chosen reedbed and schedule with its crash risk. */
    public record Plan(double hectares, List<Integer> schedule, double risk) {

        /** Copies the schedule. */
        public Plan {
            schedule = List.copyOf(schedule);
        }
    }

    private static final double DT = 0.05;
    private static final int STEPS = 20;

    private final Settings settings;
    private final double[][] shock;

    private ReedRelease(Settings settings, long seed) {
        this.settings = settings;
        this.shock = new double[settings.runs()][settings.horizon()];
        double s = settings.sigma();
        for (int r = 0; r < settings.runs(); r++) {
            for (int t = 0; t < settings.horizon(); t++) {
                shock[r][t] = Math.exp(s * normal(seed, r, t) - s * s / 2);
            }
        }
    }

    /** A planner; the seed fixes the shared year shocks. */
    public static ReedRelease of(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new ReedRelease(settings, seed);
    }

    /** The tuning. */
    public Settings settings() {
        return settings;
    }

    /** Crash risk for a reedbed and schedule. */
    public double risk(double hectares, int[] schedule) {
        check(schedule);
        ReedCeiling m = ReedCeiling.of(settings.marsh().withReed(hectares));
        int crashes = 0;
        for (int r = 0; r < settings.runs(); r++) {
            if (crashes(m, schedule, r)) {
                crashes++;
            }
        }
        return (double) crashes / settings.runs();
    }

    /** Brute force: every reed option and every schedule (ties keep the smaller reedbed, then the earlier-heavy). */
    public Plan best() {
        Plan best = null;
        for (double h : settings.reedOptions()) {
            Plan p = bestSchedule(h);
            if (best == null || p.risk() < best.risk()) {
                best = p;
            }
        }
        return best;
    }

    /** Exhaustive best schedule for one reedbed. */
    public Plan bestSchedule(double hectares) {
        int[] cur = new int[settings.releaseYears()];
        Plan[] holder = new Plan[1];
        search(hectares, 0, settings.budget(), cur, holder);
        return holder[0];
    }

    /** Greedy schedule per reed option, keeping the best. */
    public Plan fast() {
        Plan best = null;
        for (double h : settings.reedOptions()) {
            int[] cur = new int[settings.releaseYears()];
            for (int b = 0; b < settings.budget(); b++) {
                int bestYear = -1;
                double bestRisk = Double.POSITIVE_INFINITY;
                for (int y = 0; y < cur.length; y++) {
                    if (cur[y] >= settings.perYear()) {
                        continue;
                    }
                    cur[y]++;
                    double r = risk(h, cur);
                    cur[y]--;
                    if (r < bestRisk) {
                        bestRisk = r;
                        bestYear = y;
                    }
                }
                cur[bestYear]++;
            }
            Plan p = new Plan(h, list(cur), risk(h, cur));
            if (best == null || p.risk() < best.risk()) {
                best = p;
            }
        }
        return best;
    }

    private void search(double h, int year, int left, int[] cur, Plan[] holder) {
        if (year == cur.length - 1) {
            if (left > settings.perYear()) {
                return;
            }
            cur[year] = left;
            double r = risk(h, cur);
            if (holder[0] == null || r < holder[0].risk()) {
                holder[0] = new Plan(h, list(cur), r);
            }
            cur[year] = 0;
            return;
        }
        for (int k = Math.min(left, settings.perYear()); k >= 0; k--) {
            cur[year] = k;
            search(h, year + 1, left - k, cur, holder);
        }
        cur[year] = 0;
    }

    private boolean crashes(ReedCeiling m, int[] schedule, int run) {
        double n = settings.startCranes();
        double p = settings.startHawks();
        for (int t = 0; t < settings.horizon(); t++) {
            if (t < schedule.length) {
                n += schedule[t];
            }
            for (int i = 0; i < STEPS; i++) {
                double[] k1 = m.rate(n, p);
                double[] k2 = m.rate(n + DT / 2 * k1[0], p + DT / 2 * k1[1]);
                double[] k3 = m.rate(n + DT / 2 * k2[0], p + DT / 2 * k2[1]);
                double[] k4 = m.rate(n + DT * k3[0], p + DT * k3[1]);
                n = Math.max(0, n + DT / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]));
                p = Math.max(0, p + DT / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]));
            }
            n *= shock[run][t];
            if (t >= schedule.length && n < settings.threshold()) {
                return true;
            }
        }
        return false;
    }

    private void check(int[] schedule) {
        if (schedule == null || schedule.length != settings.releaseYears()) {
            throw new IllegalArgumentException("need one entry per release year");
        }
        for (int v : schedule) {
            if (v < 0 || v > settings.perYear()) {
                throw new IllegalArgumentException("bad yearly release");
            }
        }
    }

    private static List<Integer> list(int[] a) {
        List<Integer> out = new ArrayList<>(a.length);
        for (int v : a) {
            out.add(v);
        }
        return out;
    }

    private static double normal(long seed, int run, int t) {
        double u1 = Math.max(uniform(seed, run, t, 0), 1e-300);
        double u2 = uniform(seed, run, t, 1);
        return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    }

    private static double uniform(long seed, int run, int t, int salt) {
        long h = mix(seed ^ 0x3C6EF372FE94F82BL);
        h = mix(h ^ ((long) run << 32 | (t & 0xFFFFFFFFL)));
        h = mix(h ^ salt);
        return (h >>> 11) * 0x1.0p-53;
    }

    private static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
}
