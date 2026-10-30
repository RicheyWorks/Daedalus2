// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

/**
 * Lucky Feather (contest G523): a seeded Moran process in the G163 sky-crane aviary.
 *
 * <p>The aviary holds {@code flock} cranes; {@code start} of them carry a new feather-colour allele with relative
 * fitness {@code fitness} (r). Each step one crane is chosen to breed in proportion to fitness and its chick replaces
 * a crane chosen uniformly at random, so the carrier count i moves up with probability
 * {@code P+ = r i / (r i + N - i) * (N - i) / N}, down with {@code P- = (N - i) / (r i + N - i) * i / N}, and
 * otherwise stays put. The allele is lost at 0 and fixed at N.
 *
 * <p>Fixation probability has the closed form {@code (1 - r^-i) / (1 - r^-N)} ({@code i / N} when r = 1),
 * {@link #fixation(int)}. {@link #exact()} solves the absorbing Markov chain directly (tridiagonal, Thomas
 * algorithm) and {@link #meanSteps()} gives the expected steps until the allele is fixed or lost. {@link
 * #simulate(int, long)} replays the process with splitmix-hashed draws, so a seed always gives the same aviary.
 *
 * <p>Daedalus hook: {@link Settings#aviary(double)} uses the G163 studbook aviary cap of 20, and
 * {@link #carriersNeeded(double)} answers the quest: how many carriers must Pip bring in for the colour to take over
 * with a given chance.
 */
public final class LuckyFeather {

    /**
     * Aviary tuning.
     *
     * @param flock    cranes in the aviary (N)
     * @param fitness  relative fitness r of the new allele
     * @param start    carriers at the start (i)
     * @param maxSteps cap on steps per simulated run
     */
    public record Settings(int flock, double fitness, int start, int maxSteps) {

        /** The G163 aviary cap. */
        public static final int AVIARY_CAP = 20;

        /** Rejects tuning that cannot run. */
        public Settings {
            if (flock < 2 || flock > 10_000 || !(fitness > 0) || Double.isInfinite(fitness) || start < 0
                    || start > flock || maxSteps < 1) {
                throw new IllegalArgumentException("bad lucky feather settings");
            }
        }

        /** The G163 aviary (20 cranes) with one carrier of fitness r. */
        public static Settings aviary(double fitness) {
            return new Settings(AVIARY_CAP, fitness, 1, 1_000_000);
        }

        /** The same aviary with another starting carrier count. */
        public Settings withStart(int i) {
            return new Settings(flock, fitness, i, maxSteps);
        }
    }

    /** A simulation summary: share of runs fixed, mean steps to absorption, runs that hit the step cap. */
    public record Result(double fixed, double meanSteps, int capped) {}

    private final Settings s;

    private LuckyFeather(Settings s) {
        this.s = s;
    }

    /** An aviary with this tuning. */
    public static LuckyFeather of(Settings settings) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new LuckyFeather(settings);
    }

    /** The tuning. */
    public Settings settings() {
        return s;
    }

    /** Probability the carrier count rises from i in one step. */
    public double up(int i) {
        int n = s.flock();
        double r = s.fitness();
        return r * i / (r * i + n - i) * (n - i) / n;
    }

    /** Probability the carrier count falls from i in one step. */
    public double down(int i) {
        int n = s.flock();
        double r = s.fitness();
        return (n - i) / (r * i + n - i) * i / n;
    }

    /** Closed-form fixation probability from i carriers. */
    public double fixation(int i) {
        int n = s.flock();
        if (i < 0 || i > n) {
            throw new IllegalArgumentException("carriers");
        }
        double r = s.fitness();
        if (Math.abs(r - 1) < 1e-12) {
            return (double) i / n;
        }
        // (1 - r^-i) / (1 - r^-N), written with expm1 for accuracy near r = 1.
        double lr = Math.log(r);
        return Math.expm1(-i * lr) / Math.expm1(-n * lr);
    }

    /** Fixation probability from the configured start. */
    public double fixation() {
        return fixation(s.start());
    }

    /** Exact fixation probabilities for every i (0..N) by solving the absorbing chain. */
    public double[] exact() {
        int n = s.flock();
        // p_i (P+ + P-) - P+ p_{i+1} - P- p_{i-1} = 0, p_0 = 0, p_N = 1.
        double[] lo = new double[n + 1];
        double[] di = new double[n + 1];
        double[] hi = new double[n + 1];
        double[] rhs = new double[n + 1];
        di[0] = 1;
        di[n] = 1;
        rhs[n] = 1;
        for (int i = 1; i < n; i++) {
            lo[i] = -down(i);
            di[i] = up(i) + down(i);
            hi[i] = -up(i);
        }
        return thomas(lo, di, hi, rhs);
    }

    /** Expected steps from each i until the allele is fixed or lost (0 at the ends). */
    public double[] meanStepsAll() {
        int n = s.flock();
        double[] lo = new double[n + 1];
        double[] di = new double[n + 1];
        double[] hi = new double[n + 1];
        double[] rhs = new double[n + 1];
        di[0] = 1;
        di[n] = 1;
        for (int i = 1; i < n; i++) {
            lo[i] = -down(i);
            di[i] = up(i) + down(i);
            hi[i] = -up(i);
            rhs[i] = 1;
        }
        return thomas(lo, di, hi, rhs);
    }

    /** Expected steps from the configured start. */
    public double meanSteps() {
        return meanStepsAll()[s.start()];
    }

    /** Fewest starting carriers whose fixation chance reaches {@code target}. */
    public int carriersNeeded(double target) {
        if (!(target >= 0) || target > 1) {
            throw new IllegalArgumentException("target");
        }
        for (int i = 0; i <= s.flock(); i++) {
            if (fixation(i) >= target - 1e-12) {
                return i;
            }
        }
        return s.flock();
    }

    /** Seeded Moran runs from the configured start. */
    public Result simulate(int runs, long seed) {
        if (runs < 1) {
            throw new IllegalArgumentException("runs");
        }
        int n = s.flock();
        int fixed = 0;
        int capped = 0;
        double steps = 0;
        for (int r = 0; r < runs; r++) {
            int i = s.start();
            long k = 0;
            while (i > 0 && i < n && k < s.maxSteps()) {
                double u = uniform(seed, r, k);
                double pu = up(i);
                if (u < pu) {
                    i++;
                } else if (u < pu + down(i)) {
                    i--;
                }
                k++;
            }
            if (i == n) {
                fixed++;
            } else if (i > 0) {
                capped++;
            }
            steps += k;
        }
        return new Result((double) fixed / runs, steps / runs, capped);
    }

    private static double[] thomas(double[] a, double[] b, double[] c, double[] d) {
        int n = b.length;
        double[] cp = new double[n];
        double[] dp = new double[n];
        cp[0] = c[0] / b[0];
        dp[0] = d[0] / b[0];
        for (int i = 1; i < n; i++) {
            double m = b[i] - a[i] * cp[i - 1];
            cp[i] = c[i] / m;
            dp[i] = (d[i] - a[i] * dp[i - 1]) / m;
        }
        double[] x = new double[n];
        x[n - 1] = dp[n - 1];
        for (int i = n - 2; i >= 0; i--) {
            x[i] = dp[i] - cp[i] * x[i + 1];
        }
        return x;
    }

    private static double uniform(long seed, int run, long step) {
        long h = mix(seed ^ 0xA54FF53A5F1D36F1L);
        h = mix(h ^ run);
        h = mix(h ^ step);
        return (h >>> 11) * 0x1.0p-53;
    }

    private static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
}
