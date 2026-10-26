// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Meadow Metapopulation (contest G183, "Fritillary Meadows"): a seeded Levins metapopulation of meadow butterflies,
 * with ploughing and extinction debt.
 *
 * <p>The regrown valley has {@code patches} meadow patches. Each year, every occupied patch loses its butterflies with
 * chance {@code extinction}, and every empty, unploughed patch is colonised with chance
 * {@code 1 − (1 − colonize/patches)^occupied}. Ploughed patches ({@link #plough(int, int)}) become fields: they lose
 * their butterflies in the year they are ploughed and can never be colonised again.
 *
 * <p>Levins' equilibrium occupancy is {@code p* = 1 − D − e/c} for a ploughed share D ({@link #equilibrium(double)}),
 * so the butterflies vanish once {@code D ≥ 1 − e/c} ({@link #ploughThreshold()}), long before the last meadow goes.
 * Occupancy drifts down to the new p* over years, not at once: the <b>extinction debt</b>. Every draw is a splitmix hash
 * of (seed, year, patch).
 */
public final class Metapopulation {

    /** How the meadows ended. */
    public enum Outcome { FLOURISHING, DWINDLING, LOST }

    /**
     * Valley tuning.
     *
     * @param patches    meadow patches
     * @param colonize   colonisation rate c
     * @param extinction yearly local extinction chance e
     * @param years      years to run
     * @param start      patches occupied at the start (the first ones)
     */
    public record Settings(int patches, double colonize, double extinction, int years, int start) {

        /** The default valley: 100 patches, c 0.5, e 0.1, 200 years, 80 occupied. */
        public static final Settings DEFAULT = new Settings(100, 0.5, 0.1, 200, 80);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (patches < 2 || !(colonize >= 0) || Double.isInfinite(colonize) || !(extinction > 0 && extinction <= 1)
                    || years < 1 || start < 0 || start > patches) {
                throw new IllegalArgumentException("bad metapopulation settings");
            }
        }
    }

    /** One year: occupied patches after it, ploughed patches so far. */
    public record Year(int index, int occupied, int ploughed) {}

    /** The result: final occupancy share of all patches, mean over the last 50 years, outcome. */
    public record Report(Outcome outcome, double occupancy, double lateMean, List<Year> years) {

        /** Defensive copy. */
        public Report {
            years = List.copyOf(years);
        }

        /** The valley's meadow cover: flourishing butterflies keep it MEADOW, otherwise SCRUB. */
        public Vegetation band() {
            return outcome == Outcome.FLOURISHING ? Vegetation.MEADOW : Vegetation.SCRUB;
        }
    }

    /** Years averaged at the end for {@link Report#lateMean()}. */
    public static final int LATE = 50;

    private final Settings s;
    private final long seed;
    private final int[] ploughYear;

    private Metapopulation(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
        this.ploughYear = new int[s.patches()];
        java.util.Arrays.fill(ploughYear, Integer.MAX_VALUE);
    }

    /** A seeded valley. */
    public static Metapopulation valley(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new Metapopulation(settings, seed);
    }

    /**
     * Ploughs {@code count} more patches in {@code year} (the highest-numbered unploughed ones first). False if the year is
     * out of range or there are not that many left.
     */
    public boolean plough(int year, int count) {
        if (year < 0 || year >= s.years() || count < 0) {
            return false;
        }
        int left = 0;
        for (int y : ploughYear) {
            if (y == Integer.MAX_VALUE) {
                left++;
            }
        }
        if (count > left) {
            return false;
        }
        for (int i = s.patches() - 1; i >= 0 && count > 0; i--) {
            if (ploughYear[i] == Integer.MAX_VALUE) {
                ploughYear[i] = year;
                count--;
            }
        }
        return true;
    }

    /** Levins equilibrium occupancy 1 − D − e/c for ploughed share D (0 if negative; 0 when c is 0). */
    public double equilibrium(double ploughed) {
        if (!(s.colonize() > 0)) {
            return 0;
        }
        return Math.max(0, 1 - ploughed - s.extinction() / s.colonize());
    }

    /** The ploughed share at which the butterflies cannot persist: 1 − e/c (0 if they never can). */
    public double ploughThreshold() {
        return equilibrium(0);
    }

    /** Runs the valley. Deterministic in the settings, the seed and the plough plan. */
    public Report run() {
        int n = s.patches();
        boolean[] occ = new boolean[n];
        int occupied = 0;
        for (int i = 0; i < s.start(); i++) {
            occ[i] = true;
            occupied++;
        }
        List<Year> log = new ArrayList<>();
        double late = 0;
        for (int y = 0; y < s.years(); y++) {
            double col = 1 - Math.pow(Math.max(0, 1 - s.colonize() / n), occupied);
            boolean[] next = new boolean[n];
            int now = 0;
            int ploughed = 0;
            for (int i = 0; i < n; i++) {
                if (ploughYear[i] <= y) {
                    ploughed++;
                    continue;
                }
                double r = roll(y, i);
                next[i] = occ[i] ? r >= s.extinction() : r < col;
                if (next[i]) {
                    now++;
                }
            }
            occ = next;
            occupied = now;
            log.add(new Year(y, now, ploughed));
            if (y >= s.years() - LATE) {
                late += now;
            }
        }
        int span = Math.min(LATE, s.years());
        double lateMean = late / span / n;
        double finalShare = (double) occupied / n;
        Outcome o = occupied == 0 ? Outcome.LOST : lateMean >= 0.5 * equilibrium(0) ? Outcome.FLOURISHING
                : Outcome.DWINDLING;
        return new Report(o, finalShare, lateMean, log);
    }

    private double roll(int year, long patch) {
        long z = seed + 0x9E3779B97F4A7C15L * (year + 1) + 0xBF58476D1CE4E5B9L * (patch + 1);
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
