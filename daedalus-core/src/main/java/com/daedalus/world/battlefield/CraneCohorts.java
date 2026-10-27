// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Crane Cohorts (contest G194): the sky-crane flock as an age-structured Leslie matrix.
 *
 * <p>Four cohorts: CHICK (age 0), JUVENILE (1), SUBADULT (2) and ADULT (3+). Each year chicks survive to juveniles
 * with {@code chickSurvival}, juveniles to subadults with {@code juvenileSurvival}, subadults to adults with
 * {@code subadultSurvival}, and adults stay adults with {@code adultSurvival}. Subadults and adults raise
 * {@code subadultFecundity} and {@code adultFecundity} chicks per bird. That gives the Leslie matrix
 *
 * <pre>
 *   [ 0   0   Fs  Fa ]
 *   [ s0  0   0   0  ]
 *   [ 0   s1  0   0  ]
 *   [ 0   0   s2  p  ]
 * </pre>
 *
 * <p>Its dominant eigenvalue {@link #lambda()} is the long-run yearly growth factor (found by power iteration and
 * satisfying the Euler-Lotka equation), the right eigenvector is the stable age distribution
 * {@link #stableAges()}, the left eigenvector is the reproductive value {@link #reproductiveValue()} (chick = 1),
 * and {@link #elasticity(int, int)} is the share of lambda owed to each matrix entry (all shares sum to 1).
 * {@link #project(int[], long)} runs the same flock with demographic noise: binomial survival and Poisson chicks,
 * every draw a splitmix hash of (seed, year, cohort, bird, salt), so a seed always replays the same flock.
 *
 * <p>Daedalus hook: {@link #adultEquivalents(int[])} turns a mixed release into the adult count that G142
 * {@link AlleeRelease#release(int, int)} expects, and {@link #bestRelease()} names the cohort worth most per bird.
 */
public final class CraneCohorts {

    /** Number of cohorts. */
    public static final int COHORTS = 4;
    /** Cohort index of chicks. */
    public static final int CHICK = 0;
    /** Cohort index of juveniles. */
    public static final int JUVENILE = 1;
    /** Cohort index of subadults. */
    public static final int SUBADULT = 2;
    /** Cohort index of adults. */
    public static final int ADULT = 3;

    /** Where a flock is heading or ended. */
    public enum Outcome { GROWING, STEADY, DECLINING, EXTINCT }

    /**
     * Flock vital rates.
     *
     * @param chickSurvival     chick to juvenile survival
     * @param juvenileSurvival  juvenile to subadult survival
     * @param subadultSurvival  subadult to adult survival
     * @param adultSurvival     adult yearly survival
     * @param subadultFecundity chicks per subadult per year
     * @param adultFecundity    chicks per adult per year
     * @param years             years a projection runs
     */
    public record Settings(double chickSurvival, double juvenileSurvival, double subadultSurvival,
            double adultSurvival, double subadultFecundity, double adultFecundity, int years) {

        /** The marsh flock: s 0.5 / 0.7 / 0.85, adults 0.9, chicks 0.15 and 0.45, 30 years (lambda about 1.029). */
        public static final Settings DEFAULT = new Settings(0.5, 0.7, 0.85, 0.9, 0.15, 0.45, 30);

        /** Rejects rates that cannot run. */
        public Settings {
            if (!prob(chickSurvival) || !prob(juvenileSurvival) || !prob(subadultSurvival) || !prob(adultSurvival)
                    || !(subadultFecundity >= 0) || !(adultFecundity >= 0) || Double.isInfinite(subadultFecundity)
                    || Double.isInfinite(adultFecundity) || years < 1) {
                throw new IllegalArgumentException("bad crane cohort settings");
            }
            if (adultSurvival == 0 && subadultFecundity == 0 && adultFecundity == 0) {
                throw new IllegalArgumentException("flock has no dominant eigenvalue");
            }
        }

        private static boolean prob(double p) {
            return p >= 0 && p <= 1;
        }

        /** The same flock with another adult survival (a drought or poaching year). */
        public Settings withAdultSurvival(double p) {
            return new Settings(chickSurvival, juvenileSurvival, subadultSurvival, p, subadultFecundity,
                    adultFecundity, years);
        }
    }

    /** One projected year: birds per cohort. */
    public record Year(int index, int chicks, int juveniles, int subadults, int adults) {

        /** Whole flock. */
        public int total() {
            return chicks + juveniles + subadults + adults;
        }
    }

    /** A projection: outcome, final flock and every year (year 0 is the start). */
    public record Report(Outcome outcome, int flock, List<Year> years) {

        /** Copies the year list. */
        public Report {
            years = List.copyOf(years);
        }
    }

    private static final double TOL = 1e-14;
    private static final int MAX_ITER = 200_000;
    private static final int SALT_SURVIVE = 1;
    private static final int SALT_BIRTH = 2;
    private static final int POISSON_DIRECT = 40;

    private final Settings settings;
    private final long seed;
    private final double[][] matrix;
    private final double lambda;
    private final double[] right;
    private final double[] left;

    private CraneCohorts(Settings settings, long seed) {
        this.settings = settings;
        this.seed = seed;
        this.matrix = new double[][] {
            {0, 0, settings.subadultFecundity(), settings.adultFecundity()},
            {settings.chickSurvival(), 0, 0, 0},
            {0, settings.juvenileSurvival(), 0, 0},
            {0, 0, settings.subadultSurvival(), settings.adultSurvival()},
        };
        double[] w = power(false);
        this.lambda = rayleigh(w);
        this.right = normalise(w);
        double[] v = power(true);
        double scale = v[CHICK] > 0 ? v[CHICK] : v[ADULT];
        for (int i = 0; i < COHORTS; i++) {
            v[i] /= scale;
        }
        this.left = v;
    }

    /** A flock with these rates; the seed drives {@link #project(int[])} draws. */
    public static CraneCohorts marsh(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new CraneCohorts(settings, seed);
    }

    /** The rates. */
    public Settings settings() {
        return settings;
    }

    /** Leslie matrix entry (row, column). */
    public double entry(int row, int column) {
        return matrix[row][column];
    }

    /** Long-run yearly growth factor (dominant eigenvalue). */
    public double lambda() {
        return lambda;
    }

    /** Whether the flock grows, holds or shrinks in the long run (1e-9 band around lambda 1). */
    public Outcome trend() {
        if (lambda > 1 + 1e-9) {
            return Outcome.GROWING;
        }
        return lambda < 1 - 1e-9 ? Outcome.DECLINING : Outcome.STEADY;
    }

    /** Stable age distribution, shares summing to 1. */
    public List<Double> stableAges() {
        return list(right);
    }

    /** Reproductive value per cohort, chick = 1 (adult = 1 if chicks are worth nothing). */
    public List<Double> reproductiveValue() {
        return list(left);
    }

    /** Elasticity of lambda to entry (row, column): a v_row w_col / (lambda v.w). Sums to 1 over all entries. */
    public double elasticity(int row, int column) {
        double dot = 0;
        for (int i = 0; i < COHORTS; i++) {
            dot += left[i] * right[i];
        }
        return matrix[row][column] * left[row] * right[column] / (lambda * dot);
    }

    /** The cohort with the highest reproductive value: the best bird to release. */
    public int bestRelease() {
        int best = 0;
        for (int i = 1; i < COHORTS; i++) {
            if (left[i] > left[best]) {
                best = i;
            }
        }
        return best;
    }

    /** A mixed release valued in adults: sum of birds times reproductive value over the adult value, rounded. */
    public int adultEquivalents(int[] birds) {
        check(birds);
        double sum = 0;
        for (int i = 0; i < COHORTS; i++) {
            sum += birds[i] * left[i];
        }
        return (int) Math.round(sum / left[ADULT]);
    }

    /** One deterministic year: the Leslie matrix times the cohort vector. */
    public double[] step(double[] n) {
        if (n == null || n.length != COHORTS) {
            throw new IllegalArgumentException("need " + COHORTS + " cohorts");
        }
        double[] out = new double[COHORTS];
        for (int i = 0; i < COHORTS; i++) {
            for (int j = 0; j < COHORTS; j++) {
                out[i] += matrix[i][j] * n[j];
            }
        }
        return out;
    }

    /** Projects a starting flock for {@code settings.years()} years with demographic noise; same seed, same run. */
    public Report project(int[] start, long runSeed) {
        check(start);
        int[] n = start.clone();
        List<Year> years = new ArrayList<>();
        years.add(year(0, n));
        for (int t = 1; t <= settings.years(); t++) {
            int[] next = new int[COHORTS];
            next[CHICK] = poisson(settings.subadultFecundity() * n[SUBADULT] + settings.adultFecundity() * n[ADULT],
                    runSeed, t);
            next[JUVENILE] = binomial(n[CHICK], settings.chickSurvival(), runSeed, t, CHICK);
            next[SUBADULT] = binomial(n[JUVENILE], settings.juvenileSurvival(), runSeed, t, JUVENILE);
            next[ADULT] = binomial(n[SUBADULT], settings.subadultSurvival(), runSeed, t, SUBADULT)
                    + binomial(n[ADULT], settings.adultSurvival(), runSeed, t, ADULT);
            n = next;
            years.add(year(t, n));
            if (total(n) == 0) {
                break;
            }
        }
        int flock = total(n);
        Outcome out;
        if (flock == 0) {
            out = Outcome.EXTINCT;
        } else if (flock > total(start)) {
            out = Outcome.GROWING;
        } else if (flock < total(start)) {
            out = Outcome.DECLINING;
        } else {
            out = Outcome.STEADY;
        }
        return new Report(out, flock, years);
    }

    /** Projects with this flock's own seed. */
    public Report project(int[] start) {
        return project(start, seed);
    }

    private double[] power(boolean transpose) {
        double[] x = {0.25, 0.25, 0.25, 0.25};
        for (int it = 0; it < MAX_ITER; it++) {
            double[] y = new double[COHORTS];
            for (int i = 0; i < COHORTS; i++) {
                for (int j = 0; j < COHORTS; j++) {
                    y[i] += (transpose ? matrix[j][i] : matrix[i][j]) * x[j];
                }
            }
            // Average with x (a shifted power step) so a periodic matrix still converges to the same vector.
            for (int i = 0; i < COHORTS; i++) {
                y[i] = 0.5 * (y[i] + x[i]);
            }
            y = normalise(y);
            double diff = 0;
            for (int i = 0; i < COHORTS; i++) {
                diff = Math.max(diff, Math.abs(y[i] - x[i]));
            }
            x = y;
            if (diff < TOL) {
                break;
            }
        }
        return x;
    }

    private double rayleigh(double[] w) {
        double[] aw = step(w);
        double num = 0;
        double den = 0;
        for (int i = 0; i < COHORTS; i++) {
            num += aw[i] * w[i];
            den += w[i] * w[i];
        }
        return num / den;
    }

    private static double[] normalise(double[] x) {
        double s = 0;
        for (double v : x) {
            s += v;
        }
        double[] out = new double[x.length];
        for (int i = 0; i < x.length; i++) {
            out[i] = x[i] / s;
        }
        return out;
    }

    private static List<Double> list(double[] x) {
        List<Double> out = new ArrayList<>(x.length);
        for (double v : x) {
            out.add(v);
        }
        return List.copyOf(out);
    }

    private static void check(int[] birds) {
        if (birds == null || birds.length != COHORTS) {
            throw new IllegalArgumentException("need " + COHORTS + " cohorts");
        }
        for (int b : birds) {
            if (b < 0) {
                throw new IllegalArgumentException("negative cohort");
            }
        }
    }

    private static int total(int[] n) {
        int s = 0;
        for (int v : n) {
            s += v;
        }
        return s;
    }

    private static Year year(int t, int[] n) {
        return new Year(t, n[CHICK], n[JUVENILE], n[SUBADULT], n[ADULT]);
    }

    private static int binomial(int n, double p, long runSeed, int t, int cohort) {
        int k = 0;
        for (int b = 0; b < n; b++) {
            if (uniform(runSeed, t, cohort, b, SALT_SURVIVE) < p) {
                k++;
            }
        }
        return k;
    }

    private static int poisson(double mean, long runSeed, int t) {
        if (mean <= 0) {
            return 0;
        }
        if (mean > POISSON_DIRECT) {
            // Normal approximation for big clutches: Box-Muller from two hashed uniforms.
            double u1 = Math.max(uniform(runSeed, t, COHORTS, 0, SALT_BIRTH), 1e-300);
            double u2 = uniform(runSeed, t, COHORTS, 1, SALT_BIRTH);
            double z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
            return (int) Math.max(0, Math.round(mean + Math.sqrt(mean) * z));
        }
        double limit = Math.exp(-mean);
        double prod = 1;
        int k = -1;
        int draw = 0;
        do {
            k++;
            prod *= uniform(runSeed, t, COHORTS, draw++, SALT_BIRTH);
        } while (prod > limit);
        return k;
    }

    private static double uniform(long runSeed, int t, int cohort, int bird, int salt) {
        long h = mix(runSeed ^ 0x9E3779B97F4A7C15L);
        h = mix(h ^ t);
        h = mix(h ^ ((long) cohort << 32 | (bird & 0xFFFFFFFFL)));
        h = mix(h ^ salt);
        return (h >>> 11) * 0x1.0p-53;
    }

    private static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
}
