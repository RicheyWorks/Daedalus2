// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Bee Bloom (contest G48): the ark's bees and the regrown wildflowers have to meet.
 *
 * <p>A season is a seeded run of daily mean temperatures: a warm arc from early spring to autumn, day-to-day noise,
 * and maybe one late frost. Warmth adds up as growing degree days (GDD, base {@code baseC}). Each flower blooms
 * while the season's GDD is inside its window. Bees leave the hive once the GDD passes {@code hiveWakeGdd} and fly
 * only on days at or above {@code flightC}. On a flying day each hive makes {@code visitsPerHive} visits, shared
 * evenly by the open beds. A bed's seed set is its visits over the visits it needs, capped at 1. A frost (a day below
 * 0 C) kills every bloom open that day for the rest of the season. A hive that flies with nothing in bloom goes
 * hungry, and after {@code starveDays} hungry days in a row it dies, unless the keeper feeds sugar syrup
 * ({@code syrupDays} days in the season).
 *
 * <p>The player sows beds (a fixed number) and places hives before the season, then runs it. A bloom calendar with
 * no gaps keeps the hives alive; flowers that open before the late frost risk losing their seed.
 */
public final class BeeBloom {

    /** Wildflowers on the regrown fragment: GDD bloom window, visits needed per bed, and the band they belong to. */
    public enum Flora {
        WILLOW_CATKIN(15, 120, 800, Vegetation.WETLAND),
        CROCUS(30, 160, 800, Vegetation.MEADOW),
        CLOVER(140, 600, 2500, Vegetation.MEADOW),
        BRAMBLE(450, 950, 2500, Vegetation.SCRUB),
        HEATHER(900, 1600, 3000, Vegetation.MEADOW);

        private final double fromGdd;
        private final double toGdd;
        private final double visitsNeeded;
        private final Vegetation band;

        Flora(double fromGdd, double toGdd, double visitsNeeded, Vegetation band) {
            this.fromGdd = fromGdd;
            this.toGdd = toGdd;
            this.visitsNeeded = visitsNeeded;
            this.band = band;
        }

        public double fromGdd() { return fromGdd; }
        public double toGdd() { return toGdd; }
        public double visitsNeeded() { return visitsNeeded; }
        public Vegetation band() { return band; }

        public boolean blooming(double gdd) { return gdd >= fromGdd && gdd <= toGdd; }
    }

    public enum Outcome { THRIVING, PATCHY, COLLAPSED }

    /**
     * Tuning.
     *
     * @param days          season length in days
     * @param coldC         temperature at the start and end of the season
     * @param peakC         temperature at midsummer
     * @param noiseC        day-to-day noise, uniform in +/- noiseC
     * @param frostChance   chance of one late frost in the season
     * @param frostFrom     the late frost falls on a day in [frostFrom, frostTo]
     * @param frostTo       last day the late frost can fall on
     * @param baseC         growing-degree-day base temperature
     * @param flightC       bees fly on days at or above this
     * @param hiveWakeGdd   bees leave the hive once the season's GDD passes this
     * @param visitsPerHive visits per hive per flying day
     * @param starveDays    hungry flying days in a row that kill a hive
     * @param syrupDays     days of sugar syrup the keeper has: a fed hive does not go hungry on a day with no bloom
     * @param beds          flower beds the player can sow
     * @param hives         hives the player can place
     * @param thriveSet     THRIVING needs this mean seed set (and every hive alive)
     */
    public record Settings(int days, double coldC, double peakC, double noiseC, double frostChance, int frostFrom,
            int frostTo, double baseC, double flightC, double hiveWakeGdd, double visitsPerHive, int starveDays,
            int syrupDays, int beds, int hives, double thriveSet) {

        public static final Settings DEFAULT =
                new Settings(150, 3, 23, 3, 0.5, 15, 40, 5, 10, 25, 100, 6, 10, 6, 3, 0.7);

        public Settings {
            if (days < 1 || !Double.isFinite(coldC) || !(peakC >= coldC) || !(noiseC >= 0)
                    || !(frostChance >= 0 && frostChance <= 1) || frostFrom < 0 || frostTo < frostFrom
                    || !Double.isFinite(baseC) || !Double.isFinite(flightC) || !(hiveWakeGdd >= 0)
                    || !(visitsPerHive >= 0) || starveDays < 1 || syrupDays < 0 || beds < 0 || hives < 0
                    || !(thriveSet > 0 && thriveSet <= 1)) {
                throw new IllegalArgumentException("bad BeeBloom settings");
            }
        }
    }

    /** One day of the season. */
    public record Day(int index, double tempC, double gdd, boolean frost, boolean flying, int openBeds,
            double visits, int hivesAlive) {}

    /** The season's result. */
    public record Report(Outcome outcome, double meanSeedSet, Map<Flora, Double> seedSet, int hivesAlive,
            int frostDay, double unusedVisits, List<Day> days) {
        public Report {
            seedSet = Map.copyOf(seedSet);
            days = List.copyOf(days);
        }
    }

    private final Settings s;
    private final long seed;
    private final Map<Flora, Integer> sown = new EnumMap<>(Flora.class);
    private int beds;
    private int hives;

    private BeeBloom(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
    }

    /** A season on the fragment, fixed by its seed. */
    public static BeeBloom season(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings are required");
        }
        return new BeeBloom(settings, seed);
    }

    /** Sows n beds of a flower. False when the beds would run past the budget. */
    public boolean sow(Flora flora, int n) {
        if (flora == null || n < 1 || beds + n > s.beds()) {
            return false;
        }
        beds += n;
        sown.merge(flora, n, Integer::sum);
        return true;
    }

    /** Places n hives. False past the budget. */
    public boolean hive(int n) {
        if (n < 1 || hives + n > s.hives()) {
            return false;
        }
        hives += n;
        return true;
    }

    public int bedsLeft() { return s.beds() - beds; }
    public int hivesLeft() { return s.hives() - hives; }

    /** The season's daily temperatures (seeded, independent of what is sown). */
    public double[] temperatures() {
        SplittableRandom rng = new SplittableRandom(seed);
        double[] t = new double[s.days()];
        for (int d = 0; d < t.length; d++) {
            double arc = Math.sin(Math.PI * (d + 0.5) / s.days());
            t[d] = s.coldC() + (s.peakC() - s.coldC()) * arc + (rng.nextDouble() * 2 - 1) * s.noiseC();
        }
        if (rng.nextDouble() < s.frostChance()) {
            int day = Math.min(s.days() - 1, s.frostFrom() + rng.nextInt(s.frostTo() - s.frostFrom() + 1));
            t[day] = Math.min(t[day], -2.0);
        }
        return t;
    }

    /** Runs the season with what is sown and placed. */
    public Report run() {
        double[] temp = temperatures();
        Flora[] kinds = Flora.values();
        double[] visits = new double[kinds.length];
        boolean[] killed = new boolean[kinds.length];
        int alive = hives;
        int hungry = 0;
        int syrup = s.syrupDays();
        double gdd = 0;
        double unused = 0;
        int frostDay = -1;
        List<Day> log = new ArrayList<>(temp.length);
        for (int d = 0; d < temp.length; d++) {
            gdd += Math.max(0, temp[d] - s.baseC());
            boolean frost = temp[d] < 0;
            int open = 0;
            for (Flora f : kinds) {
                int n = sown.getOrDefault(f, 0);
                if (n > 0 && !killed[f.ordinal()] && f.blooming(gdd)) {
                    if (frost) {
                        killed[f.ordinal()] = true;
                    } else {
                        open += n;
                    }
                }
            }
            if (frost && frostDay < 0) {
                frostDay = d;
            }
            boolean flying = alive > 0 && gdd >= s.hiveWakeGdd() && temp[d] >= s.flightC();
            double made = 0;
            if (flying) {
                made = alive * s.visitsPerHive();
                if (open == 0 && syrup > 0) {
                    syrup--;
                    unused += made;
                } else if (open == 0) {
                    hungry++;
                    unused += made;
                    if (hungry >= s.starveDays()) {
                        alive--;
                        hungry = 0;
                    }
                } else {
                    hungry = 0;
                    double perBed = made / open;
                    for (Flora f : kinds) {
                        int n = sown.getOrDefault(f, 0);
                        if (n > 0 && !killed[f.ordinal()] && f.blooming(gdd)) {
                            double want = f.visitsNeeded() * n - visits[f.ordinal()];
                            double got = Math.min(want, perBed * n);
                            visits[f.ordinal()] += Math.max(0, got);
                            unused += perBed * n - Math.max(0, got);
                        }
                    }
                }
            }
            log.add(new Day(d, temp[d], gdd, frost, flying, open, made, alive));
        }
        Map<Flora, Double> set = new EnumMap<>(Flora.class);
        double sum = 0;
        int count = 0;
        for (Map.Entry<Flora, Integer> e : sown.entrySet()) {
            double v = Math.min(1, visits[e.getKey().ordinal()] / (e.getKey().visitsNeeded() * e.getValue()));
            set.put(e.getKey(), v);
            sum += v * e.getValue();
            count += e.getValue();
        }
        double mean = count == 0 ? 0 : sum / count;
        Outcome outcome = hives > 0 && alive == 0 ? Outcome.COLLAPSED
                : alive == hives && hives > 0 && mean >= s.thriveSet() ? Outcome.THRIVING : Outcome.PATCHY;
        return new Report(outcome, mean, set, alive, frostDay, unused, log);
    }
}
