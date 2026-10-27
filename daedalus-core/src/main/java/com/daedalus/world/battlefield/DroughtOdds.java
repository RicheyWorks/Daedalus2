// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

/**
 * Drought Odds (contest G202): how likely the sky-crane flock is to crash in bad years.
 *
 * <p>Environmental stochasticity: good and bad years multiply the flock by a log-normal factor, so
 * {@code ln N} is a random walk with drift {@code mu} (median log growth per year) and standard deviation
 * {@code sigma} per year. The flock is "quasi-extinct" once it falls to {@code threshold} birds. With
 * {@code d = ln(start / threshold)} the diffusion approximation (Dennis, Munholland and Scott 1991) gives the
 * chance of hitting the threshold within {@code T} years as an inverse-Gaussian distribution:
 *
 * <pre>
 *   G(T) = Phi((-d - mu T) / (sigma sqrt T)) + exp(-2 mu d / sigma^2) Phi((-d + mu T) / (sigma sqrt T))
 * </pre>
 *
 * <p>and the ultimate risk is 1 when {@code mu <= 0}, else {@code exp(-2 mu d / sigma^2)} ({@link #ultimate()}).
 * {@link #simulate(int, int, int, long)} checks it by Monte Carlo: {@code substeps} steps a year, every normal draw a
 * splitmix hash of (seed, run, step), so a seed always replays the same odds. Coarse steps miss crossings between
 * steps, so Monte Carlo with 1 step a year sits a little below G(T).
 *
 * <p>Daedalus hook: {@link #fromCohorts(CraneCohorts, double, int, int)} takes {@code mu = ln lambda} from the G194
 * flock, so a drought (lower adult survival) shows up straight away as worse odds on the census board.
 */
public final class DroughtOdds {

    /**
     * Odds tuning.
     *
     * @param mu        median log growth per year
     * @param sigma     standard deviation of log growth per year
     * @param start     starting flock
     * @param threshold quasi-extinction flock size (below start)
     */
    public record Settings(double mu, double sigma, int start, int threshold) {

        /** A release of 40 birds, threshold 10, mu ln 1.029, sigma 0.15. */
        public static final Settings DEFAULT = new Settings(Math.log(1.029), 0.15, 40, 10);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (Double.isNaN(mu) || Double.isInfinite(mu) || !(sigma > 0) || Double.isInfinite(sigma)
                    || threshold < 1 || start <= threshold) {
                throw new IllegalArgumentException("bad drought odds settings");
            }
        }

        /** Log distance from the start down to the threshold. */
        public double distance() {
            return Math.log((double) start / threshold);
        }
    }

    private final Settings settings;

    private DroughtOdds(Settings settings) {
        this.settings = settings;
    }

    /** Odds for this tuning. */
    public static DroughtOdds of(Settings settings) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new DroughtOdds(settings);
    }

    /** Odds for the G194 flock: mu = ln lambda. */
    public static DroughtOdds fromCohorts(CraneCohorts flock, double sigma, int start, int threshold) {
        if (flock == null) {
            throw new IllegalArgumentException("flock");
        }
        return of(new Settings(Math.log(flock.lambda()), sigma, start, threshold));
    }

    /** The tuning. */
    public Settings settings() {
        return settings;
    }

    /** Chance of reaching the threshold within {@code years} (inverse-Gaussian, diffusion approximation). */
    public double within(double years) {
        if (!(years >= 0)) {
            throw new IllegalArgumentException("years");
        }
        if (years == 0) {
            return 0;
        }
        double d = settings.distance();
        double mu = settings.mu();
        double s = settings.sigma() * Math.sqrt(years);
        double first = phi((-d - mu * years) / s);
        double logW = -2 * mu * d / (settings.sigma() * settings.sigma());
        double second = phi((-d + mu * years) / s);
        double g = first + (second == 0 ? 0 : Math.exp(logW + Math.log(second)));
        return Math.min(1, Math.max(0, g));
    }

    /** Chance of ever reaching the threshold. */
    public double ultimate() {
        if (settings.mu() <= 0) {
            return 1;
        }
        return Math.exp(-2 * settings.mu() * settings.distance() / (settings.sigma() * settings.sigma()));
    }

    /** Median years to reach the threshold among flocks that do (bisection on G), or infinity if under half do. */
    public double medianYears() {
        double target = 0.5 * ultimate();
        if (target <= 0) {
            return Double.POSITIVE_INFINITY;
        }
        double lo = 0;
        double hi = 1;
        while (within(hi) < target) {
            hi *= 2;
            if (hi > 1e7) {
                return Double.POSITIVE_INFINITY;
            }
        }
        for (int it = 0; it < 200; it++) {
            double mid = (lo + hi) / 2;
            if (within(mid) < target) {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        return (lo + hi) / 2;
    }

    /** Monte Carlo share of {@code runs} flocks that hit the threshold within {@code years}. */
    public double simulate(int runs, int years, int substeps, long seed) {
        if (runs < 1 || years < 1 || substeps < 1) {
            throw new IllegalArgumentException("bad simulation size");
        }
        double d = settings.distance();
        double dt = 1.0 / substeps;
        double drift = settings.mu() * dt;
        double sd = settings.sigma() * Math.sqrt(dt);
        int steps = years * substeps;
        int hits = 0;
        for (int r = 0; r < runs; r++) {
            double x = 0;
            for (int k = 0; k < steps; k++) {
                x += drift + sd * normal(seed, r, k);
                if (x <= -d) {
                    hits++;
                    break;
                }
            }
        }
        return (double) hits / runs;
    }

    /** Standard normal CDF (Abramowitz and Stegun 7.1.26 erf, error below 1.5e-7). */
    public static double phi(double z) {
        double x = Math.abs(z) / Math.sqrt(2);
        double t = 1 / (1 + 0.3275911 * x);
        double y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t
                + 0.254829592) * t * Math.exp(-x * x);
        return z >= 0 ? 0.5 * (1 + y) : 0.5 * (1 - y);
    }

    private static double normal(long seed, int run, int step) {
        double u1 = Math.max(uniform(seed, run, step, 0), 1e-300);
        double u2 = uniform(seed, run, step, 1);
        return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    }

    private static double uniform(long seed, int run, int step, int salt) {
        long h = mix(seed ^ 0x2545F4914F6CDD1DL);
        h = mix(h ^ ((long) run << 32 | (step & 0xFFFFFFFFL)));
        h = mix(h ^ salt);
        return (h >>> 11) * 0x1.0p-53;
    }

    private static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
}
