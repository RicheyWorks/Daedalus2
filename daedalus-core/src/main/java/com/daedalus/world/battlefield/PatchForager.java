// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Patch Forager (contest G129): Charnov's marginal value theorem for a squirrel stocking its winter hoard.
 *
 * <p>The autumn meadow has bramble patches visited in a seeded order. Patch i holds {@code A_i} berries; the seeded
 * amounts are uniform in {@code amount · (1 ± spread)}. The longer the squirrel stays, the slower it picks:
 * {@code G_i(t) = A_i (1 − e^{−t/τ})}, so the instant rate is {@code (A_i/τ) e^{−t/τ}}. Every move to the next patch
 * costs a seeded travel time, uniform in {@code travel · (1 ± travelSpread)} minutes. The day lasts {@code day} minutes,
 * and a patch or a trip cut off by dusk counts what was picked so far.
 *
 * <p>Two leaving rules:
 * <ul>
 *   <li><b>rate rule</b> {@code rate(θ)}: leave when the instant rate drops to θ berries/min. Patches that never reach
 *       θ are passed by. Charnov: the best θ equals the long-run rate of the whole day,
 *       {@code θ* = E[G] / (E[t] + E[T])}, found by {@link #optimalRate()}.</li>
 *   <li><b>fixed rule</b> {@code fixed(minutes)}: stay the same time at every patch. On uneven patches this always
 *       does worse than the rate rule at its own best.</li>
 * </ul>
 * Quest outcomes, compared with the θ* day: HOARDED at {@code goalShare} or more, SHORT at 70% or more, otherwise
 * STARVED.
 */
public final class PatchForager {

    /** How the hoard went. */
    public enum Outcome { HOARDED, SHORT, STARVED }

    /**
     * Meadow tuning.
     *
     * @param patches      patches in the visiting order (the order wraps around)
     * @param day          minutes of daylight
     * @param amount       mean berries per patch
     * @param spread       half-width of the patch amounts as a share of the mean, in [0, 1)
     * @param tau          minutes for a patch's picking rate to fall by a factor of e
     * @param travel       mean minutes between patches
     * @param travelSpread half-width of the travel times as a share of the mean, in [0, 1)
     * @param goalShare    share of the θ* day needed to hoard
     */
    public record Settings(int patches, double day, double amount, double spread, double tau, double travel,
            double travelSpread, double goalShare) {

        /** The default autumn meadow. */
        public static final Settings DEFAULT = new Settings(120, 1200, 120, 0.9, 12, 8, 0.5, 0.97);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (patches < 1 || !(day > 0) || !(amount > 0) || !(spread >= 0 && spread < 1) || !(tau > 0)
                    || !(travel > 0) || !(travelSpread >= 0 && travelSpread < 1) || !(goalShare > 0 && goalShare <= 1)
                    || Double.isInfinite(day) || Double.isInfinite(amount) || Double.isInfinite(tau)
                    || Double.isInfinite(travel)) {
                throw new IllegalArgumentException("bad forager settings");
            }
        }
    }

    /** One visit: the patch, minutes spent there, berries picked. */
    public record Visit(int patch, double minutes, double berries) {}

    /** A day's result. */
    public record Report(Outcome outcome, double berries, double best, List<Visit> visits) {

        /** Defensive copy. */
        public Report {
            visits = List.copyOf(visits);
        }

        /** Share of the θ* day. */
        public double share() {
            return best <= 0 ? 0 : berries / best;
        }

        /** Patch cover after the day: a patch picked to under half of what it held reads SCRUB, otherwise MEADOW. */
        public Vegetation band(int patch, double held) {
            double picked = 0;
            for (Visit v : visits) {
                if (v.patch() == patch) {
                    picked += v.berries();
                }
            }
            return held - picked < held / 2 ? Vegetation.SCRUB : Vegetation.MEADOW;
        }
    }

    private final Settings s;
    private final double[] held;
    private final double[] trips;

    private PatchForager(Settings s, long seed) {
        this.s = s;
        this.held = new double[s.patches()];
        this.trips = new double[s.patches()];
        for (int i = 0; i < s.patches(); i++) {
            held[i] = s.amount() * (1 + s.spread() * (2 * roll(seed, i, 1) - 1));
            trips[i] = s.travel() * (1 + s.travelSpread() * (2 * roll(seed, i, 2) - 1));
        }
    }

    /** A seeded meadow. */
    public static PatchForager meadow(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new PatchForager(settings, seed);
    }

    /** Berries patch {@code i} holds before the squirrel arrives. */
    public double held(int i) {
        return held[i];
    }

    /** Minutes the rate rule stays at a patch holding {@code a}: τ ln(a / (τ θ)), or 0 if it never reaches θ. */
    public double stay(double a, double theta) {
        double start = a / s.tau();
        return start <= theta ? 0 : s.tau() * Math.log(start / theta);
    }

    /**
     * Charnov's θ*: the fixed point of θ = E[G] / (E[t] + E[T]) over the meadow's amount distribution (midpoint rule,
     * 200 bins), where the expectations use the rate rule at θ.
     */
    public double optimalRate() {
        int bins = 200;
        double theta = s.amount() / (s.tau() + s.travel()) / 4;
        for (int it = 0; it < 200; it++) {
            double gain = 0;
            double time = 0;
            for (int b = 0; b < bins; b++) {
                double a = s.amount() * (1 + s.spread() * (2 * (b + 0.5) / bins - 1));
                double t = stay(a, theta);
                gain += a * (1 - Math.exp(-t / s.tau()));
                time += t;
            }
            double next = (gain / bins) / (time / bins + s.travel());
            if (Math.abs(next - theta) < 1e-12) {
                return next;
            }
            theta = next;
        }
        return theta;
    }

    /** One day with the rate rule at θ. */
    public Report rate(double theta) {
        if (!(theta > 0) || Double.isInfinite(theta)) {
            throw new IllegalArgumentException("theta");
        }
        return judge(day(theta, -1));
    }

    /** One day staying {@code minutes} at every patch. */
    public Report fixed(double minutes) {
        if (!(minutes >= 0) || Double.isInfinite(minutes)) {
            throw new IllegalArgumentException("minutes");
        }
        return judge(day(-1, minutes));
    }

    private Report judge(List<Visit> visits) {
        double got = 0;
        for (Visit v : visits) {
            got += v.berries();
        }
        double best = 0;
        for (Visit v : day(optimalRate(), -1)) {
            best += v.berries();
        }
        double share = best <= 0 ? 0 : got / best;
        Outcome o = share >= s.goalShare() ? Outcome.HOARDED : share >= 0.7 ? Outcome.SHORT : Outcome.STARVED;
        return new Report(o, got, best, visits);
    }

    private List<Visit> day(double theta, double fixedStay) {
        List<Visit> visits = new ArrayList<>();
        double clock = 0;
        double[] left = held.clone();
        for (int k = 0; clock < s.day(); k++) {
            int i = k % s.patches();
            double a = left[i];
            double want = theta > 0 ? stay(a, theta) : fixedStay;
            double t = Math.min(want, s.day() - clock);
            double got = a * (1 - Math.exp(-t / s.tau()));
            left[i] -= got;
            visits.add(new Visit(i, t, got));
            clock += t + trips[i];
            if (k > 100_000) {
                break;
            }
        }
        return visits;
    }

    private static double roll(long seed, long key, int salt) {
        long z = seed + 0x9E3779B97F4A7C15L * (key + 1) + 0x94D049BB133111EBL * salt;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
