// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.ReedCeiling.Regime;
import com.daedalus.world.battlefield.ReedCeiling.Run;
import com.daedalus.world.battlefield.ReedCeiling.Settings;
import org.junit.jupiter.api.Test;

class ReedCeilingTest {

    private static final Settings D = Settings.DEFAULT;

    @Test
    void equilibriumIsARestPoint() {
        ReedCeiling m = ReedCeiling.of(D);
        double[] f = m.rate(m.cranesStar(), m.hawksStar());
        assertEquals(0, f[0], 1e-9);
        assertEquals(0, f[1], 1e-9);
        assertEquals(0.15 / (0.02 * 0.525), m.cranesStar(), 1e-12);
        assertEquals(2 * m.cranesStar() + 100, m.hopfCapacity(), 1e-12);
    }

    @Test
    void biggerReedFeedsHawksNotCranes() {
        double n = ReedCeiling.of(D).cranesStar();
        double prev = 0;
        for (double ha = 10; ha <= 60; ha += 5) {
            ReedCeiling m = ReedCeiling.of(D.withReed(ha));
            assertEquals(n, m.cranesStar(), 0);
            assertTrue(m.hawksStar() > prev);
            prev = m.hawksStar();
        }
    }

    @Test
    void numericJacobianMatchesAnalyticTrace() {
        for (double ha : new double[] {20, 40, 64, 80, 150}) {
            ReedCeiling m = ReedCeiling.of(D.withReed(ha));
            double n = m.cranesStar();
            double p = m.hawksStar();
            double eps = 1e-6;
            double dfn = (m.rate(n + eps, p)[0] - m.rate(n - eps, p)[0]) / (2 * eps);
            double dgp = (m.rate(n, p + eps)[1] - m.rate(n, p - eps)[1]) / (2 * eps);
            double dfp = (m.rate(n, p + eps)[0] - m.rate(n, p - eps)[0]) / (2 * eps);
            double dgn = (m.rate(n + eps, p)[1] - m.rate(n - eps, p)[1]) / (2 * eps);
            assertEquals(m.trace(), dfn + dgp, 1e-6, "ha " + ha);
            assertTrue(dfn * dgp - dfp * dgn > 0, "determinant must be positive");
        }
    }

    @Test
    void bruteForceRegimesMatchTheHopfThreshold() {
        ReedCeiling base = ReedCeiling.of(D);
        double kh = base.hopfCapacity();
        double ns = base.cranesStar();
        int checked = 0;
        for (double k = 5; k <= 300; k += 7.5) {
            if (Math.abs(k - kh) < 0.12 * kh || Math.abs(k - ns) < 0.12 * ns) {
                continue;
            }
            ReedCeiling m = ReedCeiling.of(D.withReed(k / D.cranesPerHectare()));
            Run run = m.integrate(k * 0.6, 3, 3000, 0.02);
            Regime seen;
            if (run.finalHawks() < 1e-3) {
                seen = Regime.NO_HAWKS;
            } else {
                seen = run.amplitude() > 0.02 * k ? Regime.CYCLES : Regime.STABLE;
            }
            assertEquals(m.regime(), seen, "K " + k + " amp " + run.amplitude());
            if (seen == Regime.STABLE) {
                assertEquals(m.cranesStar(), run.points().get(run.points().size() - 1).cranes(), 0.01 * k);
            }
            checked++;
        }
        assertTrue(checked > 25);
    }

    @Test
    void cyclesGrowWithTheReedbed() {
        double a1 = ReedCeiling.of(D.withReed(80)).integrate(100, 3, 3000, 0.02).amplitude();
        double a2 = ReedCeiling.of(D.withReed(150)).integrate(100, 3, 3000, 0.02).amplitude();
        assertTrue(a2 > a1 && a1 > 1, a1 + " vs " + a2);
        // In deep cycles the cranes dip far below N*: the boom-and-bust the quest warns about.
        assertTrue(ReedCeiling.of(D.withReed(150)).integrate(100, 3, 3000, 0.02).minCranes()
                < 0.5 * ReedCeiling.of(D).cranesStar());
    }

    @Test
    void questAnswersAreInHectares() {
        ReedCeiling m = ReedCeiling.of(D);
        assertEquals(m.hopfCapacity() / 2, m.cycleHectares(), 1e-12);
        assertEquals(Regime.STABLE, ReedCeiling.of(D.withReed(m.cycleHectares() - 1)).regime());
        assertEquals(Regime.CYCLES, ReedCeiling.of(D.withReed(m.cycleHectares() + 1)).regime());
        assertEquals(Regime.NO_HAWKS, ReedCeiling.of(D.withReed(m.hawkHectares() - 0.5)).regime());
    }

    @Test
    void g194FlockSetsTheGrowthRate() {
        CraneCohorts flock = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT, 1);
        ReedCeiling m = ReedCeiling.fromCohorts(flock, D);
        assertEquals(Math.log(flock.lambda()), m.settings().r(), 1e-15);
        // Growth rate does not move N* or K_H, only how hard the marsh pulls back.
        assertEquals(ReedCeiling.of(D).hopfCapacity(), m.hopfCapacity(), 1e-12);
        CraneCohorts drought = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT.withAdultSurvival(0.8), 1);
        assertThrows(IllegalArgumentException.class, () -> ReedCeiling.fromCohorts(drought, D));
    }

    @Test
    void noisyRunsReplay() {
        ReedCeiling m = ReedCeiling.of(D);
        Run a = m.noisy(50, 3, 60, 11);
        assertEquals(a, m.noisy(50, 3, 60, 11));
        assertNotEquals(a.points(), m.noisy(50, 3, 60, 12).points());
        assertTrue(a.finalHawks() > 0);
    }

    @Test
    void badInputIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> new Settings(0, 40, 2, 0.02, 0.5, 0.6, 0.15));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0.4, 40, 2, 0.02, 5, 0.6, 0.15));
        assertThrows(IllegalArgumentException.class, () -> ReedCeiling.of(null));
        ReedCeiling m = ReedCeiling.of(D);
        assertThrows(IllegalArgumentException.class, () -> m.integrate(-1, 1, 10, 0.1));
        assertThrows(IllegalArgumentException.class, () -> m.integrate(1, 1, 10, 2));
        assertThrows(IllegalArgumentException.class, () -> m.noisy(1, 1, 0, 1));
    }
}
