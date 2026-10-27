// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Hawk-Dove (contest G188, "Rut on the Ridge"): an evolutionary game among Hornback bulls over grazing rights.
 *
 * <p>Each season every bull meets random rivals {@code rounds} times over a resource worth {@code value}. A HAWK
 * fights; a DOVE displays and backs down. Hawk meets hawk: one wins {@code value}, the loser pays {@code cost} (each
 * equally likely); hawk meets dove: the hawk takes it all; dove meets dove: one gets it after a display. Bulls then
 * breed in proportion to {@code base + payoff} (a seeded Wright-Fisher draw), so the herd's hawk share evolves.
 *
 * <p>When {@code cost > value}, the evolutionarily stable hawk share is {@code value / cost} ({@link #ess()}): the
 * herd settles there whatever share it starts at, and at that share hawks and doves earn the same
 * ({@link #expectedPayoff(boolean, double)}). When fights are cheap ({@code cost ≤ value}) hawks take over. Every draw
 * is a splitmix hash of (seed, season, bull, round, salt).
 */
public final class HawkDove {

    /** Where the herd ended. */
    public enum Outcome { MIXED, ALL_HAWK, ALL_DOVE }

    /**
     * Ridge tuning.
     *
     * @param herd    bulls in the herd
     * @param value   worth of the grazing right
     * @param cost    cost of losing a fight
     * @param base    baseline fitness every bull has (keeps fitness positive)
     * @param rounds  contests per bull per season
     * @param seasons seasons to run
     */
    public record Settings(int herd, double value, double cost, double base, int rounds, int seasons) {

        /** The default ridge: 200 bulls, V 4, C 10, base 10, 10 contests, 150 seasons. */
        public static final Settings DEFAULT = new Settings(200, 4, 10, 10, 10, 150);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (herd < 2 || !(value > 0) || !(cost >= 0) || !(base > 0) || Double.isInfinite(value)
                    || Double.isInfinite(cost) || Double.isInfinite(base) || rounds < 1
                    || seasons < 1) {
                throw new IllegalArgumentException("bad hawk-dove settings");
            }
        }
    }

    /** One season: the hawk share after breeding and the mean payoff of each strategy (NaN if absent). */
    public record Season(int index, double hawks, double hawkPayoff, double dovePayoff) {}

    /** The result. */
    public record Report(Outcome outcome, double hawks, double lateHawks, List<Season> seasons) {

        /** Defensive copy. */
        public Report {
            seasons = List.copyOf(seasons);
        }

        /** Ridge cover: endless fighting (over 80% hawks) tramples the grazing to BARE; otherwise MEADOW. */
        public Vegetation band() {
            return lateHawks > 0.8 ? Vegetation.BARE : Vegetation.MEADOW;
        }
    }

    /** Seasons averaged at the end for {@link Report#lateHawks()}. */
    public static final int LATE = 50;

    private final Settings s;
    private final long seed;

    private HawkDove(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
    }

    /** A seeded ridge. */
    public static HawkDove ridge(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new HawkDove(settings, seed);
    }

    /** The evolutionarily stable hawk share: V/C when C &gt; V, otherwise 1. */
    public double ess() {
        return s.cost() > s.value() ? s.value() / s.cost() : 1;
    }

    /** Expected payoff of one contest for a hawk (or dove) in a herd with hawk share {@code h}. */
    public double expectedPayoff(boolean hawk, double h) {
        double v = s.value();
        double c = s.cost();
        return hawk ? h * (v - c) / 2 + (1 - h) * v : (1 - h) * v / 2;
    }

    /** Runs {@code seasons} from a herd with {@code hawks} of {@code herd} bulls hawkish. */
    public Report run(int hawks) {
        if (hawks < 0 || hawks > s.herd()) {
            throw new IllegalArgumentException("hawks");
        }
        int n = s.herd();
        boolean[] hawk = new boolean[n];
        for (int i = 0; i < hawks; i++) {
            hawk[i] = true;
        }
        List<Season> log = new ArrayList<>();
        double late = 0;
        int count = hawks;
        for (int g = 0; g < s.seasons(); g++) {
            double[] pay = new double[n];
            for (int i = 0; i < n; i++) {
                for (int r = 0; r < s.rounds(); r++) {
                    int j = (int) (roll(g, i, r, 1) * (n - 1));
                    if (j >= i) {
                        j++;
                    }
                    boolean win = roll(g, i, r, 2) < 0.5;
                    pay[i] += contest(hawk[i], hawk[j], win);
                }
            }
            double fit = 0;
            double[] cum = new double[n];
            double hp = 0;
            double dp = 0;
            for (int i = 0; i < n; i++) {
                fit += Math.max(0, s.base() + pay[i] / s.rounds());
                cum[i] = fit;
                if (hawk[i]) {
                    hp += pay[i] / s.rounds();
                } else {
                    dp += pay[i] / s.rounds();
                }
            }
            boolean[] next = new boolean[n];
            int nextCount = 0;
            for (int c = 0; c < n; c++) {
                double x = roll(g, c, 0, 3) * fit;
                int lo = 0;
                int hi = n - 1;
                while (lo < hi) {
                    int mid = (lo + hi) >>> 1;
                    if (cum[mid] > x) {
                        hi = mid;
                    } else {
                        lo = mid + 1;
                    }
                }
                next[c] = hawk[lo];
                if (next[c]) {
                    nextCount++;
                }
            }
            double hawkPay = count == 0 ? Double.NaN : hp / count;
            double dovePay = count == n ? Double.NaN : dp / (n - count);
            hawk = next;
            count = nextCount;
            log.add(new Season(g + 1, (double) count / n, hawkPay, dovePay));
            if (g >= s.seasons() - LATE) {
                late += (double) count / n;
            }
        }
        double share = (double) count / n;
        Outcome o = count == n ? Outcome.ALL_HAWK : count == 0 ? Outcome.ALL_DOVE : Outcome.MIXED;
        return new Report(o, share, late / Math.min(LATE, s.seasons()), log);
    }

    /** One contest from the focal bull's side. */
    private double contest(boolean me, boolean them, boolean win) {
        double v = s.value();
        if (me && them) {
            return win ? v : -s.cost();
        }
        if (me) {
            return v;
        }
        if (them) {
            return 0;
        }
        return win ? v : 0;
    }

    private double roll(int season, long bull, int round, int salt) {
        long z = seed + 0x9E3779B97F4A7C15L * (season + 1) + 0xBF58476D1CE4E5B9L * (bull + 1)
                + 0x94D049BB133111EBL * (salt + 4L * (round + 1));
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
