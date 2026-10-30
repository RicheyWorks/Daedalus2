// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Reed Ceiling (contest G504): marsh hawks and sky-cranes as a Rosenzweig-MacArthur predator-prey model, with the
 * cranes' carrying capacity set by the reedbed.
 *
 * <pre>
 *   dN/dt = r N (1 - N / K) - a N P / (1 + a h N)        cranes, K = reedHectares * cranesPerHectare
 *   dP/dt = e a N P / (1 + a h N) - m P                  hawks (Holling type II)
 * </pre>
 *
 * <p>Equilibrium: {@code N* = m / (a (e - m h))} (independent of the reedbed) and
 * {@code P* = (r / a)(1 - N* / K)(1 + a h N*)}. Hawks can live on the marsh only when {@code K > N*}. The coexistence
 * point is stable while {@code K < K_H = 2 N* + 1 / (a h)}; above that a Hopf bifurcation turns it into boom-and-bust
 * cycles (the paradox of enrichment): a bigger reedbed feeds more hawks and swings, not more cranes.
 * {@link #integrate(double, double, double, double)} is a plain RK4 run used as the brute-force check, and
 * {@link #noisy(double, double, int, long)} adds seeded log-normal year shocks to the cranes.
 *
 * <p>Daedalus hook: {@link #fromCohorts(CraneCohorts, Settings)} sets {@code r = ln lambda} from G194, and
 * {@link #cycleHectares()} is the quest answer, the reedbed size where the marsh starts to swing.
 */
public final class ReedCeiling {

    /** Long-run behaviour. */
    public enum Regime { NO_HAWKS, STABLE, CYCLES }

    /**
     * Marsh tuning.
     *
     * @param r                crane growth rate per year at low density
     * @param reedHectares     reedbed size
     * @param cranesPerHectare cranes a hectare of reed can hold
     * @param attack           hawk attack rate (per crane per hawk per year)
     * @param handling         handling time per crane, years
     * @param conversion       hawks gained per crane eaten
     * @param mortality        hawk death rate per year
     */
    public record Settings(double r, double reedHectares, double cranesPerHectare, double attack, double handling,
            double conversion, double mortality) {

        /** 40 ha of reed at 2 cranes/ha (K 80), r 0.4, a 0.02, h 0.5, e 0.6, m 0.15: stable (K_H about 128.6). */
        public static final Settings DEFAULT = new Settings(0.4, 40, 2, 0.02, 0.5, 0.6, 0.15);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (!pos(r) || !pos(reedHectares) || !pos(cranesPerHectare) || !pos(attack) || !pos(handling)
                    || !pos(conversion) || !pos(mortality) || !(conversion > mortality * handling)) {
                throw new IllegalArgumentException("bad reed ceiling settings");
            }
        }

        private static boolean pos(double x) {
            return x > 0 && !Double.isInfinite(x);
        }

        /** Carrying capacity of the reedbed. */
        public double capacity() {
            return reedHectares * cranesPerHectare;
        }

        /** The same marsh with another reedbed. */
        public Settings withReed(double hectares) {
            return new Settings(r, hectares, cranesPerHectare, attack, handling, conversion, mortality);
        }

        /** The same marsh with another crane growth rate. */
        public Settings withGrowth(double growth) {
            return new Settings(growth, reedHectares, cranesPerHectare, attack, handling, conversion, mortality);
        }
    }

    /** One sampled year. */
    public record Point(double year, double cranes, double hawks) {}

    /** A run: samples plus long-run crane min/max over the final quarter. */
    public record Run(List<Point> points, double minCranes, double maxCranes, double finalHawks) {

        /** Copies the samples. */
        public Run {
            points = List.copyOf(points);
        }

        /** Long-run crane swing. */
        public double amplitude() {
            return maxCranes - minCranes;
        }
    }

    private final Settings s;

    private ReedCeiling(Settings s) {
        this.s = s;
    }

    /** A marsh with this tuning. */
    public static ReedCeiling of(Settings settings) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new ReedCeiling(settings);
    }

    /** A marsh whose crane growth is ln lambda of the G194 flock (must be growing). */
    public static ReedCeiling fromCohorts(CraneCohorts flock, Settings settings) {
        if (flock == null || settings == null || !(flock.lambda() > 1)) {
            throw new IllegalArgumentException("need a growing G194 flock");
        }
        return of(settings.withGrowth(Math.log(flock.lambda())));
    }

    /** The tuning. */
    public Settings settings() {
        return s;
    }

    /** Crane equilibrium with hawks present. */
    public double cranesStar() {
        return s.mortality() / (s.attack() * (s.conversion() - s.mortality() * s.handling()));
    }

    /** Hawk equilibrium (0 when the reedbed cannot feed hawks). */
    public double hawksStar() {
        double n = cranesStar();
        double k = s.capacity();
        if (k <= n) {
            return 0;
        }
        return (s.r() / s.attack()) * (1 - n / k) * (1 + s.attack() * s.handling() * n);
    }

    /** Hopf capacity K_H = 2 N* + 1 / (a h). */
    public double hopfCapacity() {
        return 2 * cranesStar() + 1 / (s.attack() * s.handling());
    }

    /** Reedbed hectares where the marsh starts to cycle (the quest answer). */
    public double cycleHectares() {
        return hopfCapacity() / s.cranesPerHectare();
    }

    /** Reedbed hectares hawks need to persist. */
    public double hawkHectares() {
        return cranesStar() / s.cranesPerHectare();
    }

    /** Analytic regime. */
    public Regime regime() {
        double k = s.capacity();
        if (k <= cranesStar()) {
            return Regime.NO_HAWKS;
        }
        return k < hopfCapacity() ? Regime.STABLE : Regime.CYCLES;
    }

    /** Right-hand side (dN/dt, dP/dt). */
    public double[] rate(double n, double p) {
        double eat = s.attack() * n * p / (1 + s.attack() * s.handling() * n);
        return new double[] {s.r() * n * (1 - n / s.capacity()) - eat, s.conversion() * eat - s.mortality() * p};
    }

    /** Trace of the Jacobian at the coexistence point (negative means stable), analytic. */
    public double trace() {
        double n = cranesStar();
        double k = s.capacity();
        double ah = s.attack() * s.handling();
        // Only the crane self-term survives on the diagonal: N* times the slope of the prey isocline.
        return s.r() * n * ah * (k - 1 / ah - 2 * n) / (k * (1 + ah * n));
    }

    /** RK4 run from (n0, p0) for {@code years} with step {@code dt}; one sample a year. */
    public Run integrate(double n0, double p0, double years, double dt) {
        if (!(n0 >= 0) || !(p0 >= 0) || !(years > 0) || !(dt > 0) || dt > 1) {
            throw new IllegalArgumentException("bad run");
        }
        double n = n0;
        double p = p0;
        int steps = (int) Math.round(years / dt);
        int perYear = Math.max(1, (int) Math.round(1 / dt));
        int tail = steps - steps / 4;
        double lo = Double.POSITIVE_INFINITY;
        double hi = 0;
        List<Point> pts = new ArrayList<>();
        pts.add(new Point(0, n, p));
        for (int i = 1; i <= steps; i++) {
            double[] k1 = rate(n, p);
            double[] k2 = rate(n + dt / 2 * k1[0], p + dt / 2 * k1[1]);
            double[] k3 = rate(n + dt / 2 * k2[0], p + dt / 2 * k2[1]);
            double[] k4 = rate(n + dt * k3[0], p + dt * k3[1]);
            n = Math.max(0, n + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]));
            p = Math.max(0, p + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]));
            if (i >= tail) {
                lo = Math.min(lo, n);
                hi = Math.max(hi, n);
            }
            if (i % perYear == 0) {
                pts.add(new Point(i * dt, n, p));
            }
        }
        return new Run(pts, lo, hi, p);
    }

    /** Yearly RK4 seasons with a seeded log-normal shock on the cranes each year; same seed, same run. */
    public Run noisy(double n0, double p0, int years, long seed) {
        if (years < 1) {
            throw new IllegalArgumentException("years");
        }
        double n = n0;
        double p = p0;
        double sigma = 0.1;
        double lo = Double.POSITIVE_INFINITY;
        double hi = 0;
        List<Point> pts = new ArrayList<>();
        pts.add(new Point(0, n, p));
        for (int y = 1; y <= years; y++) {
            Run season = of(s).integrate(n, p, 1, 0.05);
            Point last = season.points().get(season.points().size() - 1);
            n = last.cranes() * Math.exp(sigma * normal(seed, y) - sigma * sigma / 2);
            p = last.hawks();
            if (y > years - years / 4) {
                lo = Math.min(lo, n);
                hi = Math.max(hi, n);
            }
            pts.add(new Point(y, n, p));
        }
        return new Run(pts, lo, hi, p);
    }

    private static double normal(long seed, int y) {
        double u1 = Math.max(uniform(seed, y, 0), 1e-300);
        double u2 = uniform(seed, y, 1);
        return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    }

    private static double uniform(long seed, int y, int salt) {
        long h = mix(seed ^ 0xBB67AE8584CAA73BL);
        h = mix(h ^ y);
        h = mix(h ^ salt);
        return (h >>> 11) * 0x1.0p-53;
    }

    private static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
}
