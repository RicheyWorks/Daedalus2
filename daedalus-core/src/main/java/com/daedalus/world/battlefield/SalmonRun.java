// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Salmon Run (contest G71): the river's salmon come home to spawn, and their bodies feed the forest.
 *
 * <p>Each year's run is the recruits from the spawners {@code lag} years before, by the Ricker stock-recruitment curve:
 * R = alpha·S·exp(−S/capacity)·ocean. The seeded ocean survival is lognormal with mean 1 and spread {@code sigma}.
 * Rearing ponds (beaver ponds, BEAVER01) raise juvenile survival by {@code pondBoost} each.
 *
 * <p>Spawning capacity is the lower gravel plus the upper gravel. Without a fish ladder at the old weir, only
 * {@code weirPassage} of the upper gravel counts. The island takes {@code harvest} of each run as catch, and the rest
 * spawn (the escapement). Bears carry {@code bearCarry} of the spawned-out carcasses into the riverside forest. That
 * marine nitrogen is what feeds the forest.
 *
 * <p>Outcomes:
 * <ul>
 *   <li>FISHED_OUT: mean escapement over the last {@code judgeYears} years falls below {@code collapse}.</li>
 *   <li>RESTORED: that mean is at least {@code target} and the total catch reaches {@code catchGoal}.</li>
 *   <li>HOLDING: anything else.</li>
 * </ul>
 * Past a harvest of 1 − 1/alpha, the stock cannot replace itself.
 */
public final class SalmonRun {

    /** What the river became. */
    public enum Outcome { RESTORED, HOLDING, FISHED_OUT }

    /**
     * River tuning.
     *
     * @param years       years to run
     * @param lag         years from spawning to the return
     * @param spawners    spawners in each of the first {@code lag} years
     * @param alpha       Ricker productivity (recruits per spawner at low density)
     * @param lowerGravel spawning capacity below the weir
     * @param upperGravel spawning capacity above the weir
     * @param weirPassage fraction of the upper gravel reachable without a ladder
     * @param pondBoost   extra juvenile survival per rearing pond
     * @param maxPonds    most rearing ponds
     * @param sigma       lognormal spread of ocean survival
     * @param bearCarry   fraction of carcasses bears carry into the forest
     * @param judgeYears  final years averaged for the outcome
     * @param target      mean escapement for a restored run
     * @param collapse    mean escapement below which the run is fished out
     * @param catchGoal   total catch the island needs for a restored run
     */
    public record Settings(int years, int lag, double spawners, double alpha, double lowerGravel, double upperGravel,
            double weirPassage, double pondBoost, int maxPonds, double sigma, double bearCarry, int judgeYears,
            double target, double collapse, double catchGoal) {

        /** The default river. */
        public static final Settings DEFAULT = new Settings(40, 4, 150, 4.0, 400, 800, 0.25, 0.1, 3, 0.4, 0.5, 8,
                1000, 50, 12000);

        /** Rejects a river that cannot run. */
        public Settings {
            if (years < 1 || lag < 1 || !(spawners >= 0) || !(alpha >= 0) || !(lowerGravel >= 0)
                    || !(upperGravel >= 0) || !(lowerGravel + upperGravel > 0)
                    || !(weirPassage >= 0 && weirPassage <= 1) || !(pondBoost >= 0) || maxPonds < 0
                    || !(sigma >= 0) || !(bearCarry >= 0 && bearCarry <= 1) || judgeYears < 1 || judgeYears > years
                    || !(target >= 0) || !(collapse >= 0) || !(catchGoal >= 0)) {
                throw new IllegalArgumentException("bad salmon run settings");
            }
        }
    }

    /** One year's run. */
    public record Year(int index, double spawnersBack, double run, double caught, double escapement,
            double forestNitrogen) {}

    /**
     * The result.
     *
     * @param outcome        what the river became
     * @param meanEscapement mean escapement over the judged years
     * @param totalCatch     catch over the whole run
     * @param forestNitrogen carcasses carried into the forest over the whole run
     * @param years          one row per year
     */
    public record Report(Outcome outcome, double meanEscapement, double totalCatch, double forestNitrogen,
            List<Year> years) {

        /** Defensive copy. */
        public Report {
            years = List.copyOf(years);
        }

        /**
         * What the riverside forest grows into, fed on salmon. OAK for at least 1.5× the target in carcasses a year
         * on average, PINE for at least half the target, SCRUB for any steady supply, MEADOW otherwise.
         */
        public Vegetation forest(Settings s) {
            double perYear = forestNitrogen / years.size() / Math.max(s.bearCarry(), 1e-9);
            if (perYear >= 1.5 * s.target()) {
                return Vegetation.OAK;
            }
            if (perYear >= 0.5 * s.target()) {
                return Vegetation.PINE;
            }
            return perYear >= s.collapse() ? Vegetation.SCRUB : Vegetation.MEADOW;
        }
    }

    private final Settings s;
    private final long seed;
    private boolean ladder;
    private int ponds;
    private double harvest;

    private SalmonRun(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
    }

    /** A river with these settings and this seed for the ocean years. */
    public static SalmonRun river(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new SalmonRun(settings, seed);
    }

    /** Build the fish ladder at the old weir. Returns false if it is already built. */
    public boolean buildLadder() {
        if (ladder) {
            return false;
        }
        ladder = true;
        return true;
    }

    /** Let beavers keep one more rearing pond. Returns false over the pond budget. */
    public boolean pond() {
        if (ponds >= s.maxPonds()) {
            return false;
        }
        ponds++;
        return true;
    }

    /** The island's catch as a fraction of each run, 0..1. Returns false out of range. */
    public boolean harvest(double fraction) {
        if (!(fraction >= 0 && fraction <= 1)) {
            return false;
        }
        harvest = fraction;
        return true;
    }

    /** Spawning capacity with the current works. */
    public double capacity() {
        return s.lowerGravel() + s.upperGravel() * (ladder ? 1 : s.weirPassage());
    }

    /** Harvest fraction above which the stock cannot replace itself (1 − 1/alpha, ponds included). */
    public double replacementLimit() {
        double a = s.alpha() * (1 + s.pondBoost() * ponds);
        return a <= 1 ? 0 : 1 - 1 / a;
    }

    /** Runs the river. Deterministic in the settings, the seed and the plan. */
    public Report run() {
        SplittableRandom rng = new SplittableRandom(seed);
        double cap = capacity();
        double rear = 1 + s.pondBoost() * ponds;
        double[] esc = new double[s.years() + s.lag()];
        for (int i = 0; i < s.lag(); i++) {
            esc[i] = s.spawners();
        }
        List<Year> log = new ArrayList<>();
        double catchTotal = 0;
        double nitrogen = 0;
        for (int y = 0; y < s.years(); y++) {
            double parents = esc[y];
            double ocean = Math.exp(s.sigma() * gaussian(rng) - s.sigma() * s.sigma() / 2);
            double run = s.alpha() * parents * Math.exp(-parents / cap) * ocean * rear;
            double caught = harvest * run;
            double escapement = run - caught;
            esc[y + s.lag()] = escapement;
            double carried = s.bearCarry() * escapement;
            catchTotal += caught;
            nitrogen += carried;
            log.add(new Year(y, parents, run, caught, escapement, carried));
        }
        double judged = 0;
        for (int y = s.years() - s.judgeYears(); y < s.years(); y++) {
            judged += log.get(y).escapement();
        }
        judged /= s.judgeYears();
        Outcome outcome = judged < s.collapse() ? Outcome.FISHED_OUT
                : judged >= s.target() && catchTotal >= s.catchGoal() ? Outcome.RESTORED : Outcome.HOLDING;
        return new Report(outcome, judged, catchTotal, nitrogen, log);
    }

    private static double gaussian(SplittableRandom rng) {
        double u = 1 - rng.nextDouble();
        double v = rng.nextDouble();
        return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    }
}
