// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Crane Spread (contest G200): the sky-crane flock spreading along the marsh as an integrodifference model.
 *
 * <p>The marsh is a line of cells {@code cell} km wide. Each year every cell grows by Beverton-Holt,
 * {@code G(n) = lambda n / (1 + (lambda - 1) n / capacity)}, then the birds disperse with a Laplace kernel of mean
 * distance {@code dispersal} km ({@code k(x) = exp(-|x| / b) / 2b}, discretised on the cells and cut at 30 b). The
 * first {@link #SOURCE} cells are the release reedbed and stay full.
 *
 * <p>With no Allee effect the front is linearly determined: it travels at the spreading speed
 * {@code c* = min over 0 < s < 1/b of ln(lambda M(s)) / s}, where {@code M(s)} is the kernel's moment generating
 * function ({@link #spreadingSpeed()}); the simulated front approaches c* from below. A flock with lambda below 1
 * does not spread. {@link #run(long)} adds demographic noise: each cell's count is a Poisson draw (normal above
 * mean 40) around the deterministic value, every draw a splitmix hash of (seed, year, cell, salt).
 *
 * <p>Daedalus hook: {@link #fromCohorts(CraneCohorts, double, double, double, int)} takes lambda from the G194
 * flock, and {@link Report#yearReached(double)} tells the quest when the cranes reach the far reedbed.
 */
public final class CraneSpread {

    /** Release cells held at capacity. */
    public static final int SOURCE = 4;

    /**
     * Spread tuning.
     *
     * @param lambda    yearly growth factor of a sparse flock
     * @param dispersal mean dispersal distance b, km
     * @param cell      cell width, km
     * @param capacity  birds a cell can hold
     * @param years     years to run
     */
    public record Settings(double lambda, double dispersal, double cell, double capacity, int years) {

        /** The marsh: lambda 1.5, b 1 km, 0.25 km cells, 100 birds a cell, 200 years. */
        public static final Settings DEFAULT = new Settings(1.5, 1.0, 0.25, 100, 200);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (!(lambda > 0) || !(dispersal > 0) || !(cell > 0) || !(capacity > 0) || Double.isInfinite(lambda)
                    || Double.isInfinite(dispersal) || Double.isInfinite(capacity) || years < 1
                    || dispersal / cell > 400 || cell > dispersal * 4) {
                throw new IllegalArgumentException("bad crane spread settings");
            }
        }
    }

    /** One year: front position (furthest cell at half capacity, km) and birds on the marsh. */
    public record Year(int index, double front, double birds) {}

    /** A run: every year plus its measured late front speed (km/yr over the second half). */
    public record Report(List<Year> years, double speed) {

        /** Copies the year list. */
        public Report {
            years = List.copyOf(years);
        }

        /** First year the front reaches {@code km}, or -1 if it never does. */
        public int yearReached(double km) {
            for (Year y : years) {
                if (y.front() >= km) {
                    return y.index();
                }
            }
            return -1;
        }
    }

    private static final int SALT = 3;
    private static final int POISSON_DIRECT = 40;

    private final Settings settings;
    private final long seed;
    private final double[] kernel;
    private final int reach;

    private CraneSpread(Settings settings, long seed) {
        this.settings = settings;
        this.seed = seed;
        this.reach = (int) Math.ceil(30 * settings.dispersal() / settings.cell());
        this.kernel = new double[2 * reach + 1];
        double sum = 0;
        for (int j = -reach; j <= reach; j++) {
            kernel[j + reach] = Math.exp(-Math.abs(j) * settings.cell() / settings.dispersal());
            sum += kernel[j + reach];
        }
        for (int j = 0; j < kernel.length; j++) {
            kernel[j] /= sum;
        }
    }

    /** A marsh with this tuning; the seed drives {@link #run(long)}. */
    public static CraneSpread marsh(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new CraneSpread(settings, seed);
    }

    /** A marsh whose sparse growth is the G194 flock's lambda. */
    public static CraneSpread fromCohorts(CraneCohorts flock, double dispersal, double cell, double capacity,
            int years) {
        if (flock == null) {
            throw new IllegalArgumentException("flock");
        }
        return marsh(new Settings(flock.lambda(), dispersal, cell, capacity, years), 1);
    }

    /** The tuning. */
    public Settings settings() {
        return settings;
    }

    /** Moment generating function of the discretised kernel at {@code s} (per km). */
    public double mgf(double s) {
        double m = 0;
        for (int j = -reach; j <= reach; j++) {
            m += kernel[j + reach] * Math.exp(s * j * settings.cell());
        }
        return m;
    }

    /** Spreading speed c* in km/yr (0 when lambda is at most 1): golden-section minimum of ln(lambda M(s)) / s. */
    public double spreadingSpeed() {
        if (settings.lambda() <= 1) {
            return 0;
        }
        double lo = 1e-6;
        double hi = 0.999 / settings.dispersal();
        double g = (Math.sqrt(5) - 1) / 2;
        for (int it = 0; it < 200; it++) {
            double a = hi - g * (hi - lo);
            double b = lo + g * (hi - lo);
            if (speedAt(a) < speedAt(b)) {
                hi = b;
            } else {
                lo = a;
            }
        }
        return speedAt((lo + hi) / 2);
    }

    private double speedAt(double s) {
        return Math.log(settings.lambda() * mgf(s)) / s;
    }

    /** The deterministic spread. */
    public Report run() {
        return simulate(false, 0);
    }

    /** The spread with demographic noise; same seed, same run. */
    public Report run(long runSeed) {
        return simulate(true, runSeed);
    }

    /** Noisy run with this marsh's own seed. */
    public Report runNoisy() {
        return run(seed);
    }

    private Report simulate(boolean noisy, long runSeed) {
        double speedGuess = Math.max(spreadingSpeed(), 0) * 1.2 + settings.dispersal();
        int cells = (int) Math.ceil(speedGuess * settings.years() / settings.cell()) + 2 * reach + SOURCE + 8;
        double cap = settings.capacity();
        double lam = settings.lambda();
        double[] n = new double[cells];
        for (int i = 0; i < SOURCE; i++) {
            n[i] = cap;
        }
        List<Year> years = new ArrayList<>();
        years.add(new Year(0, front(n), sum(n)));
        for (int t = 1; t <= settings.years(); t++) {
            double[] grown = new double[cells];
            for (int i = 0; i < cells; i++) {
                grown[i] = lam * n[i] / (1 + (lam - 1) * n[i] / cap);
            }
            double[] next = new double[cells];
            for (int i = 0; i < cells; i++) {
                if (grown[i] == 0) {
                    continue;
                }
                int from = Math.max(0, i - reach);
                int to = Math.min(cells - 1, i + reach);
                for (int k = from; k <= to; k++) {
                    next[k] += grown[i] * kernel[k - i + reach];
                }
            }
            if (noisy) {
                for (int i = 0; i < cells; i++) {
                    next[i] = poisson(next[i], runSeed, t, i);
                }
            }
            for (int i = 0; i < SOURCE; i++) {
                next[i] = cap;
            }
            n = next;
            years.add(new Year(t, front(n), sum(n)));
        }
        int half = settings.years() / 2;
        double speed = (years.get(settings.years()).front() - years.get(half).front()) / (settings.years() - half);
        return new Report(years, speed);
    }

    private double front(double[] n) {
        int last = 0;
        for (int i = 0; i < n.length; i++) {
            if (n[i] >= settings.capacity() / 2) {
                last = i;
            }
        }
        return last * settings.cell();
    }

    private static double sum(double[] n) {
        double s = 0;
        for (double v : n) {
            s += v;
        }
        return s;
    }

    private static double poisson(double mean, long runSeed, int t, int cell) {
        if (mean <= 0) {
            return 0;
        }
        if (mean > POISSON_DIRECT) {
            double u1 = Math.max(uniform(runSeed, t, cell, 0), 1e-300);
            double u2 = uniform(runSeed, t, cell, 1);
            double z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
            return Math.max(0, Math.round(mean + Math.sqrt(mean) * z));
        }
        double limit = Math.exp(-mean);
        double prod = 1;
        int k = -1;
        int draw = 2;
        do {
            k++;
            prod *= uniform(runSeed, t, cell, draw++);
        } while (prod > limit);
        return k;
    }

    private static double uniform(long runSeed, int t, int cell, int draw) {
        long h = mix(runSeed ^ 0xD1B54A32D192ED03L);
        h = mix(h ^ t);
        h = mix(h ^ ((long) cell << 32 | (draw & 0xFFFFFFFFL)));
        h = mix(h ^ SALT);
        return (h >>> 11) * 0x1.0p-53;
    }

    private static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
}
