// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Translocation Plan (contest G251): spend an aviary budget of birds over the first years of a release so the
 * marsh flock is least likely to crash.
 *
 * <p>The marsh flock is the G194 {@link CraneCohorts} Leslie matrix. Each year the keeper first adds that year's
 * aviary birds (G163 studbook stock) to one cohort, then the flock grows by the matrix times a log-normal
 * environmental factor {@code exp(sigma Z - sigma^2 / 2)} (mean 1, the G202 {@link DroughtOdds} noise). The flock
 * "crashes" if its total falls below {@code threshold} at any census in the horizon. Risk is the share of seeded runs
 * that crash; every run uses the same hashed shocks for every schedule (common random numbers), so schedules are
 * compared fairly and a seed always replays the same answer.
 *
 * <p>{@link #best()} searches every schedule of {@code budget} birds over {@code releaseYears} years (each year at most
 * {@code perYear}); {@link #greedy()} adds one bird at a time to the year that lowers risk most. Daedalus hook: the
 * plan feeds the census board's release calendar, and its {@link Plan#risk()} uses the same crash threshold as G202.
 */
public final class TranslocationPlan {

    /**
     * Plan tuning.
     *
     * @param start        marsh adults already present
     * @param budget       aviary birds to release in total
     * @param perYear      most birds the aviary can spare in one year
     * @param releaseYears years in which releases may happen (years 0 .. releaseYears - 1)
     * @param horizon      census years checked for a crash
     * @param threshold    crash level (whole flock)
     * @param sigma        environmental sd of log growth
     * @param cohort       cohort the released birds join (G194 index)
     * @param runs         seeded runs per risk estimate
     */
    public record Settings(int start, int budget, int perYear, int releaseYears, int horizon, double threshold,
            double sigma, int cohort, int runs) {

        /** 12 marsh adults, 10 aviary adults over 5 years (at most 6 a year), 30-year horizon, crash at 10, sigma 0.2. */
        public static final Settings DEFAULT = new Settings(12, 10, 6, 5, 30, 10, 0.2, CraneCohorts.ADULT, 400);

        /** Rejects tuning that cannot run, naming the first problem (see {@link #problem}). */
        public Settings {
            String why = problem(start, budget, perYear, releaseYears, horizon, threshold, sigma, cohort, runs);
            if (why != null) {
                throw new IllegalArgumentException("bad translocation settings: " + why);
            }
        }

        /**
         * The first reason this tuning cannot run, or null if it can. Checked in this order so a UI can show one
         * clear message (the C++ core returns the same strings).
         */
        public static String problem(int start, int budget, int perYear, int releaseYears, int horizon,
                double threshold, double sigma, int cohort, int runs) {
            if (start < 0) {
                return "start must be at least 0";
            }
            if (budget < 0) {
                return "budget must be at least 0";
            }
            if (perYear < 0) {
                return "perYear must be at least 0";
            }
            if (releaseYears < 1) {
                return "releaseYears must be at least 1";
            }
            if (horizon < releaseYears) {
                return "horizon must cover the release years";
            }
            if (!(threshold > 0)) {
                return "threshold must be above 0";
            }
            if (!(sigma >= 0) || Double.isInfinite(sigma)) {
                return "sigma must be finite and at least 0";
            }
            if (cohort < 0 || cohort >= CraneCohorts.COHORTS) {
                return "cohort must be a G194 cohort index";
            }
            if (runs < 1) {
                return "runs must be at least 1";
            }
            if ((long) perYear * releaseYears < budget) {
                return "budget does not fit perYear x releaseYears";
            }
            return null;
        }

        /** The same plan with another budget. */
        public Settings withBudget(int b) {
            return new Settings(start, b, Math.max(perYear, 0), releaseYears, horizon, threshold, sigma, cohort, runs);
        }

        /** The same plan releasing into another cohort. */
        public Settings withCohort(int c) {
            return new Settings(start, budget, perYear, releaseYears, horizon, threshold, sigma, c, runs);
        }
    }

    /** A release schedule (birds per release year) and its crash risk. */
    public record Plan(List<Integer> schedule, double risk) {

        /** Copies the schedule. */
        public Plan {
            schedule = List.copyOf(schedule);
        }

        /** Birds released in total. */
        public int total() {
            int s = 0;
            for (int v : schedule) {
                s += v;
            }
            return s;
        }
    }

    private final CraneCohorts flock;
    private final Settings settings;
    private final double[][] shock;
    private final long seed;

    private TranslocationPlan(CraneCohorts flock, Settings settings, long seed) {
        this.flock = flock;
        this.settings = settings;
        this.seed = seed;
        this.shock = new double[settings.runs()][settings.horizon()];
        double s = settings.sigma();
        for (int r = 0; r < settings.runs(); r++) {
            for (int t = 0; t < settings.horizon(); t++) {
                shock[r][t] = Math.exp(s * normal(seed, r, t) - s * s / 2);
            }
        }
    }

    /** A planner for this G194 flock; the seed fixes the shared environmental shocks. */
    public static TranslocationPlan of(CraneCohorts flock, Settings settings, long seed) {
        if (flock == null || settings == null) {
            throw new IllegalArgumentException("flock and settings");
        }
        return new TranslocationPlan(flock, settings, seed);
    }

    /** The tuning. */
    public Settings settings() {
        return settings;
    }

    /** Crash risk of a schedule (one entry per release year). */
    public double risk(int[] schedule) {
        check(schedule);
        int crashes = 0;
        for (int r = 0; r < settings.runs(); r++) {
            if (crashes(schedule, r)) {
                crashes++;
            }
        }
        return (double) crashes / settings.runs();
    }

    /**
     * The lowest-risk schedule over every way to spend the budget (ties go to the earliest-heavy schedule). The search
     * is pruned: it stops counting a schedule's crashes once they reach the best so far, and stops entirely at zero
     * risk; the answer is the same as scoring every schedule.
     */
    public Plan best() {
        int[] cur = new int[settings.releaseYears()];
        Plan[] holder = new Plan[1];
        search(0, settings.budget(), cur, holder);
        return holder[0];
    }

    /** Greedy: add one bird at a time to the year whose extra bird lowers the risk most (earliest on ties). */
    public Plan greedy() {
        int[] cur = new int[settings.releaseYears()];
        for (int b = 0; b < settings.budget(); b++) {
            int bestYear = -1;
            double bestRisk = Double.POSITIVE_INFINITY;
            for (int y = 0; y < cur.length; y++) {
                if (cur[y] >= settings.perYear()) {
                    continue;
                }
                cur[y]++;
                double r = risk(cur);
                cur[y]--;
                if (r < bestRisk) {
                    bestRisk = r;
                    bestYear = y;
                }
            }
            cur[bestYear]++;
        }
        return new Plan(list(cur), risk(cur));
    }

    /**
     * Local search from a schedule: move one bird from year i to year j (first improving move, i then j ascending)
     * while the risk strictly drops. Never worse than the start, and much cheaper than {@link #best()}.
     */
    public Plan polish(int[] schedule) {
        check(schedule);
        int[] cur = schedule.clone();
        double r = risk(cur);
        boolean moved = true;
        while (moved && r > 0) {
            moved = false;
            for (int i = 0; i < cur.length && !moved; i++) {
                for (int j = 0; j < cur.length && !moved; j++) {
                    if (i == j || cur[i] == 0 || cur[j] >= settings.perYear()) {
                        continue;
                    }
                    cur[i]--;
                    cur[j]++;
                    double next = risk(cur);
                    if (next < r) {
                        r = next;
                        moved = true;
                    } else {
                        cur[i]++;
                        cur[j]--;
                    }
                }
            }
        }
        return new Plan(list(cur), r);
    }

    /** Greedy, then polished by single-bird moves. */
    public Plan greedyPolished() {
        return polish(greedy().schedule().stream().mapToInt(Integer::intValue).toArray());
    }

    /**
     * Polished-greedy risk for releasing into each G194 cohort (index = cohort), on the same shocks. The keeper's
     * "which birds?" answer is the lowest entry; it should agree with {@link CraneCohorts#bestRelease()}.
     */
    public double[] cohortRisks() {
        double[] out = new double[CraneCohorts.COHORTS];
        for (int c = 0; c < out.length; c++) {
            out[c] = of(flock, settings.withCohort(c), seed).greedyPolished().risk();
        }
        return out;
    }

    /** Every bird in year 0 (as many as the per-year cap allows, the rest the next years). */
    public int[] frontLoaded() {
        int[] s = new int[settings.releaseYears()];
        int left = settings.budget();
        for (int y = 0; y < s.length && left > 0; y++) {
            s[y] = Math.min(settings.perYear(), left);
            left -= s[y];
        }
        return s;
    }

    /**
     * Survival curve: entry t is the share of seeded runs that have not crashed by the census at the end of year t
     * (t = 0 .. horizon - 1). The last entry is 1 - risk(schedule). The census board can draw this as the release's
     * safety margin over time.
     */
    public double[] survival(int[] schedule) {
        check(schedule);
        int[] crashedBy = new int[settings.horizon()];
        for (int r = 0; r < settings.runs(); r++) {
            int year = firstCrash(schedule, r);
            if (year >= 0) {
                crashedBy[year]++;
            }
        }
        double[] out = new double[settings.horizon()];
        int crashed = 0;
        for (int t = 0; t < out.length; t++) {
            crashed += crashedBy[t];
            out[t] = 1 - (double) crashed / settings.runs();
        }
        return out;
    }

    /** Every bird as late as possible (the last year first, as many as the per-year cap allows). */
    public int[] backLoaded() {
        int[] s = new int[settings.releaseYears()];
        int left = settings.budget();
        for (int y = s.length - 1; y >= 0 && left > 0; y--) {
            s[y] = Math.min(settings.perYear(), left);
            left -= s[y];
        }
        return s;
    }

    /**
     * 95 % Wilson score interval {low, high} for a schedule's crash risk: how far the Monte Carlo estimate can be
     * trusted with this many runs. Two schedules whose intervals overlap are not reliably different.
     */
    public double[] riskInterval(int[] schedule) {
        double p = risk(schedule);
        double n = settings.runs();
        double z = 1.959963984540054;
        double z2 = z * z;
        double centre = (p + z2 / (2 * n)) / (1 + z2 / n);
        double half = z / (1 + z2 / n) * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n));
        // Exact ends when no run (or every run) crashed, so rounding cannot leave the estimate outside its interval.
        return new double[] {p == 0 ? 0 : Math.max(0, centre - half), p == 1 ? 1 : Math.min(1, centre + half)};
    }

    /** The budget spread as evenly as the years allow (extra birds early). */
    public int[] even() {
        int[] s = new int[settings.releaseYears()];
        for (int y = 0; y < s.length; y++) {
            s[y] = settings.budget() / s.length + (y < settings.budget() % s.length ? 1 : 0);
        }
        return s;
    }

    private void search(int year, int left, int[] cur, Plan[] holder) {
        if (holder[0] != null && holder[0].risk() == 0) {
            return; // nothing can beat zero risk, and ties keep the first schedule found
        }
        if (year == cur.length - 1) {
            if (left > settings.perYear()) {
                return;
            }
            cur[year] = left;
            // Only a strictly lower crash count can replace the holder, so stop counting once it is matched.
            int limit = holder[0] == null ? Integer.MAX_VALUE : crashCount(holder[0]);
            int crashes = crashesUpTo(cur, limit);
            if (crashes < limit) {
                holder[0] = new Plan(list(cur), (double) crashes / settings.runs());
            }
            cur[year] = 0;
            return;
        }
        for (int k = Math.min(left, settings.perYear()); k >= 0; k--) {
            cur[year] = k;
            search(year + 1, left - k, cur, holder);
        }
        cur[year] = 0;
    }

    private int crashCount(Plan p) {
        return (int) Math.round(p.risk() * settings.runs());
    }

    /** Crashing runs for a schedule, counting no further than {@code limit}. */
    private int crashesUpTo(int[] schedule, int limit) {
        int crashes = 0;
        for (int r = 0; r < settings.runs() && crashes < limit; r++) {
            if (crashes(schedule, r)) {
                crashes++;
            }
        }
        return crashes;
    }

    private boolean crashes(int[] schedule, int run) {
        return firstCrash(schedule, run) >= 0;
    }

    /** First census year the run falls below the threshold, or -1 if it never does. */
    private int firstCrash(int[] schedule, int run) {
        double[] n = new double[CraneCohorts.COHORTS];
        n[CraneCohorts.ADULT] = settings.start();
        for (int t = 0; t < settings.horizon(); t++) {
            if (t < schedule.length) {
                n[settings.cohort()] += schedule[t];
            }
            n = flock.step(n);
            double f = shock[run][t];
            double total = 0;
            for (int i = 0; i < n.length; i++) {
                n[i] *= f;
                total += n[i];
            }
            if (total < settings.threshold()) {
                return t;
            }
        }
        return -1;
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
        long h = mix(seed ^ 0x6A09E667F3BCC909L);
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
