package com.daedalus.world.battlefield;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Fair Par Calibrator (G600; all six marsh cabinets and the par board in G602, Prismheart balance lane). A seeded
 * "casual" bot plays a marsh cabinet many times; the sorted bot scores set bronze, silver and gold pars so about
 * 60 %, 25 % and 5 % of bot runs reach each tier. The exact optimum of the cabinet is the PERFECT tier and caps gold.
 * Scores are survival chances (1 - crash risk) or guess accuracy, so higher is better. The bot hashes (seed, run,
 * pick, salt) statelessly with the SplitMix64 finalizer, like the other marsh cores, so the C++ port
 * (DaedalusMarshFairParCore.h) replays the same runs.
 */
public final class FairPar {

    /** Percent of bot runs that should reach bronze, silver and gold. */
    private static final int[] TIER_PERCENT = {60, 25, 5};

    /** Tiers from worst to best. */
    public enum Tier { NONE, BRONZE, SILVER, GOLD, PERFECT }

    /**
     * Pars for one cabinet: bot runs, par scores, exact optimum, the share of bot runs reaching each par, and the
     * median bot score.
     */
    public record Pars(int runs, double bronze, double silver, double gold, double perfect, double bronzeHit,
            double silverHit, double goldHit, double median) {

        /**
         * True when every tier needs a strictly better score than the one below it. False flags a flat cabinet:
         * casual bot play already lands near the optimum, so the tiers collapse and the cabinet needs tuning.
         */
        public boolean separated() {
            return bronze < silver && silver < gold && gold < perfect;
        }

        /** The tier a player score earns. */
        public Tier tier(double score) {
            if (score >= perfect) {
                return Tier.PERFECT;
            }
            if (score >= gold) {
                return Tier.GOLD;
            }
            if (score >= silver) {
                return Tier.SILVER;
            }
            return score >= bronze ? Tier.BRONZE : Tier.NONE;
        }
    }

    private FairPar() {
    }

    /** Uniform in [0, 1) from the SplitMix64 finalizer of (seed, run, pick, salt). */
    public static double uniform(long seed, int run, int pick, int salt) {
        long z = seed + 0x9E3779B97F4A7C15L * (run + 1L) + 0xBF58476D1CE4E5B9L * (pick + 1L)
                + 0x94D049BB133111EBL * (salt + 1L);
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z ^= z >>> 31;
        return (z >>> 11) * 0x1.0p-53;
    }

    /** Uniform integer in [0, bound]. */
    public static int pick(long seed, int run, int pick, int salt, int bound) {
        return Math.min(bound, (int) (uniform(seed, run, pick, salt) * (bound + 1)));
    }

    /**
     * The casual bot's release schedule: a random count each year (at most perYear and what is left), then any
     * birds still left go out as early as the yearly cap allows, so every run spends the whole budget.
     */
    public static int[] botSchedule(long seed, int run, int budget, int perYear, int years) {
        if (budget < 0 || perYear < 0 || years < 1 || (long) perYear * years < budget) {
            throw new IllegalArgumentException("bad bot budget");
        }
        int[] out = new int[years];
        int left = budget;
        for (int y = 0; y < years; y++) {
            out[y] = pick(seed, run, y, 0, Math.min(perYear, left));
            left -= out[y];
        }
        for (int y = 0; y < years && left > 0; y++) {
            int add = Math.min(perYear - out[y], left);
            out[y] += add;
            left -= add;
        }
        return out;
    }

    /** Pars from bot scores and the exact optimum. Needs at least one score and no NaN. */
    public static Pars calibrate(double[] scores, double perfect) {
        if (scores == null || scores.length == 0 || Double.isNaN(perfect)) {
            throw new IllegalArgumentException("need bot scores");
        }
        double[] s = scores.clone();
        for (double v : s) {
            if (Double.isNaN(v)) {
                throw new IllegalArgumentException("NaN score");
            }
        }
        Arrays.sort(s);
        int n = s.length;
        double[] par = new double[3];
        double[] hit = new double[3];
        for (int t = 0; t < 3; t++) {
            int reach = (n * TIER_PERCENT[t] + 99) / 100;
            par[t] = Math.min(s[n - Math.max(1, reach)], perfect);
            int count = 0;
            for (double v : s) {
                count += v >= par[t] ? 1 : 0;
            }
            hit[t] = (double) count / n;
        }
        return new Pars(n, par[0], par[1], par[2], perfect, hit[0], hit[1], hit[2], s[(n - 1) / 2]);
    }

    /** Bot survival scores on TRANS01 (G589): one bot schedule per run. */
    public static double[] translocationScores(TranslocationPlan plan, int runs, long seed) {
        TranslocationPlan.Settings st = plan.settings();
        double[] out = new double[runs];
        for (int r = 0; r < runs; r++) {
            out[r] = 1 - plan.risk(botSchedule(seed, r, st.budget(), st.perYear(), st.releaseYears()));
        }
        return out;
    }

    /** TRANS01 pars: bot runs against the exact best schedule. */
    public static Pars translocation(TranslocationPlan plan, int runs, long seed) {
        return calibrate(translocationScores(plan, runs, seed), 1 - plan.best().risk());
    }

    /** Bot survival scores on REEDREL01 (G593): a random reedbed option and a bot schedule per run. */
    public static double[] reedReleaseScores(ReedRelease rr, int runs, long seed) {
        ReedRelease.Settings st = rr.settings();
        double[] out = new double[runs];
        for (int r = 0; r < runs; r++) {
            double ha = st.reedOptions().get(pick(seed, r, 0, 1, st.reedOptions().size() - 1));
            out[r] = 1 - rr.risk(ha, botSchedule(seed, r, st.budget(), st.perYear(), st.releaseYears()));
        }
        return out;
    }

    /** REEDREL01 pars: bot runs against the exact best reedbed and schedule. */
    public static Pars reedRelease(ReedRelease rr, int runs, long seed) {
        return calibrate(reedReleaseScores(rr, runs, seed), 1 - rr.best().risk());
    }
    /**
     * COHORTS (G585 cabinet on the G194 flock): the player splits a release of birds over the four cohorts and
     * scores its value in adults ({@link CraneCohorts#adultEquivalents}). The bot splits at random; the optimum is
     * found by trying every split.
     */
    public static Pars cohorts(CraneCohorts flock, int birds, int runs, long seed) {
        double[] out = new double[runs];
        for (int r = 0; r < runs; r++) {
            out[r] = flock.adultEquivalents(botSchedule(seed, r, birds, birds, CraneCohorts.COHORTS));
        }
        int best = 0;
        for (int a = 0; a <= birds; a++) {
            for (int b = 0; a + b <= birds; b++) {
                for (int c = 0; a + b + c <= birds; c++) {
                    best = Math.max(best, flock.adultEquivalents(new int[] {a, b, c, birds - a - b - c}));
                }
            }
        }
        return calibrate(out, best);
    }

    /**
     * REEDCEIL01 (G591 cabinet on G504): the player picks a reedbed for a seeded noisy crane-and-hawk run and scores
     * the lowest crane count of the run. Every pick shares the run seed; the optimum is the best reedbed.
     */
    public static Pars reedCeiling(ReedCeiling.Settings marsh, double[] reedOptions, double hawks, int years,
            long runSeed, int runs, long seed) {
        if (reedOptions == null || reedOptions.length == 0) {
            throw new IllegalArgumentException("need reedbed options");
        }
        double[] value = new double[reedOptions.length];
        double best = Double.NEGATIVE_INFINITY;
        for (int i = 0; i < reedOptions.length; i++) {
            ReedCeiling rc = ReedCeiling.of(marsh.withReed(reedOptions[i]));
            value[i] = rc.noisy(rc.settings().capacity() * 0.6, hawks, years, runSeed).minCranes();
            best = Math.max(best, value[i]);
        }
        double[] out = new double[runs];
        for (int r = 0; r < runs; r++) {
            out[r] = value[pick(seed, r, 0, 2, reedOptions.length - 1)];
        }
        return calibrate(out, best);
    }

    /**
     * DROUGHT01 (G570 cabinet on G202): the player guesses the chance the flock hits the threshold within some years;
     * score = 1 - |guess - exact chance|. The bot guesses uniformly; a perfect guess scores 1.
     */
    public static Pars droughtOdds(DroughtOdds odds, double years, int runs, long seed) {
        double truth = odds.within(years);
        double[] out = new double[runs];
        for (int r = 0; r < runs; r++) {
            out[r] = 1 - Math.abs(uniform(seed, r, 0, 3) - truth);
        }
        return calibrate(out, 1);
    }

    /**
     * SPREAD01 (G583 cabinet on G200): the player guesses the year the seeded crane front first reaches some
     * distance; score = 1 - |guess - year| / years (a front that never arrives counts as the last year). The bot
     * guesses a uniform year; a perfect guess scores 1.
     */
    public static Pars craneSpread(CraneSpread marsh, double km, long runSeed, int runs, long seed) {
        int years = marsh.settings().years();
        int reached = marsh.run(runSeed).yearReached(km);
        int truth = reached < 0 ? years : reached;
        double[] out = new double[runs];
        for (int r = 0; r < runs; r++) {
            out[r] = 1 - (double) Math.abs(pick(seed, r, 0, 4, years) - truth) / years;
        }
        return calibrate(out, 1);
    }
    /** Cabinet ids in par-board order. */
    public static final List<String> MARSH_CABINETS = List.of("DROUGHT01", "SPREAD01", "COHORTS01", "TRANS01",
            "REEDCEIL01", "REEDREL01");

    /**
     * Daedalus hook: the Prismheart par board for the six marsh cabinets on their default tuning, in
     * {@link #MARSH_CABINETS} order. Fixed seeds, so every build shows the same pars.
     */
    public static Map<String, Pars> marshTable() {
        Map<String, Pars> out = new LinkedHashMap<>();
        out.put("DROUGHT01", droughtOdds(DroughtOdds.of(DroughtOdds.Settings.DEFAULT), 20, 200, 800));
        out.put("SPREAD01", craneSpread(CraneSpread.marsh(new CraneSpread.Settings(1.5, 1.0, 0.25, 100, 40), 1), 5,
                11, 200, 801));
        CraneCohorts flock = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT, 1);
        out.put("COHORTS01", cohorts(flock, 12, 200, 802));
        out.put("TRANS01", translocation(TranslocationPlan.of(flock, TranslocationPlan.Settings.DEFAULT, 7), 200,
                600));
        out.put("REEDCEIL01", reedCeiling(ReedCeiling.Settings.DEFAULT, new double[] {10, 25, 40, 55, 80, 110, 150},
                5, 40, 17, 200, 804));
        out.put("REEDREL01", reedRelease(ReedRelease.of(ReedRelease.Settings.DEFAULT, 23), 120, 700));
        return out;
    }
}
