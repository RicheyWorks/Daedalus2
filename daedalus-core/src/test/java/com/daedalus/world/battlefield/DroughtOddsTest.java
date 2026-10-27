// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.DroughtOdds.Settings;
import org.junit.jupiter.api.Test;

class DroughtOddsTest {

    @Test
    void normalCdfMatchesTables() {
        assertEquals(0.5, DroughtOdds.phi(0), 1e-7);
        assertEquals(0.8413447, DroughtOdds.phi(1), 2e-7);
        assertEquals(0.9750021, DroughtOdds.phi(1.96), 2e-7);
        assertEquals(0.0227501, DroughtOdds.phi(-2), 2e-7);
    }

    @Test
    void ultimateRiskIsOneWithoutGrowthAndExponentialWithIt() {
        assertEquals(1, DroughtOdds.of(new Settings(0, 0.2, 40, 10)).ultimate(), 0);
        assertEquals(1, DroughtOdds.of(new Settings(-0.01, 0.2, 40, 10)).ultimate(), 0);
        Settings s = new Settings(0.03, 0.2, 40, 10);
        assertEquals(Math.exp(-2 * 0.03 * Math.log(4) / 0.04), DroughtOdds.of(s).ultimate(), 1e-12);
    }

    @Test
    void riskWithinTGrowsToTheUltimateRisk() {
        DroughtOdds o = DroughtOdds.of(new Settings(0.03, 0.2, 40, 10));
        double prev = 0;
        for (int t = 1; t <= 400; t += 7) {
            double g = o.within(t);
            assertTrue(g >= prev - 1e-12);
            prev = g;
        }
        assertEquals(o.ultimate(), o.within(1e6), 1e-6);
        assertEquals(0, o.within(0), 0);
        DroughtOdds flat = DroughtOdds.of(new Settings(0, 0.2, 40, 10));
        // Driftless walk: reflection principle, G(T) = 2 Phi(-d / sigma sqrt T).
        assertEquals(2 * DroughtOdds.phi(-Math.log(4) / (0.2 * Math.sqrt(50))), flat.within(50), 1e-9);
    }

    @Test
    void monteCarloMatchesTheInverseGaussian() {
        Settings[] all = {new Settings(0.03, 0.2, 40, 10), new Settings(-0.02, 0.15, 30, 10),
            new Settings(Math.log(1.029), 0.25, 40, 10)};
        for (Settings s : all) {
            DroughtOdds o = DroughtOdds.of(s);
            double mc = o.simulate(3000, 50, 40, 11);
            assertEquals(o.within(50), mc, 0.035, s.toString());
            // One step a year misses crossings between census days: never more risk than the fine run.
            assertTrue(o.simulate(3000, 50, 1, 11) <= mc + 0.02);
        }
    }

    @Test
    void wilderYearsRaiseTheRiskEvenForAGrowingFlock() {
        double calm = DroughtOdds.of(new Settings(0.03, 0.1, 40, 10)).within(50);
        double wild = DroughtOdds.of(new Settings(0.03, 0.3, 40, 10)).within(50);
        assertTrue(wild > calm + 0.2, calm + " vs " + wild);
        assertTrue(DroughtOdds.of(new Settings(0.03, 0.2, 80, 10)).within(50)
                < DroughtOdds.of(new Settings(0.03, 0.2, 20, 10)).within(50));
    }

    @Test
    void medianYearsSplitsTheHittersInHalf() {
        DroughtOdds o = DroughtOdds.of(new Settings(-0.02, 0.15, 30, 10));
        double m = o.medianYears();
        assertEquals(0.5, o.within(m), 1e-9);
        assertEquals(Double.POSITIVE_INFINITY,
                DroughtOdds.of(new Settings(1.0, 0.01, 40, 10)).medianYears());
    }

    @Test
    void seededOddsReplay() {
        DroughtOdds o = DroughtOdds.of(Settings.DEFAULT);
        assertEquals(o.simulate(500, 30, 4, 5), DroughtOdds.of(Settings.DEFAULT).simulate(500, 30, 4, 5), 0);
        assertNotEquals(o.simulate(500, 30, 4, 5), o.simulate(500, 30, 4, 6));
    }

    @Test
    void droughtFlockFromG194HasWorseOdds() {
        CraneCohorts flock = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT, 1);
        CraneCohorts drought = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT.withAdultSurvival(0.8), 1);
        DroughtOdds good = DroughtOdds.fromCohorts(flock, 0.15, 40, 10);
        DroughtOdds bad = DroughtOdds.fromCohorts(drought, 0.15, 40, 10);
        assertEquals(Math.log(flock.lambda()), good.settings().mu(), 1e-15);
        assertTrue(good.ultimate() < 0.2);
        assertEquals(1, bad.ultimate(), 0);
        assertTrue(bad.within(50) > good.within(50) + 0.5);
    }

    @Test
    void badInputIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> new Settings(0.01, 0, 40, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(Double.NaN, 0.1, 40, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0.01, 0.1, 10, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0.01, 0.1, 40, 0));
        assertThrows(IllegalArgumentException.class, () -> DroughtOdds.of(null));
        assertThrows(IllegalArgumentException.class, () -> DroughtOdds.fromCohorts(null, 0.1, 40, 10));
        DroughtOdds o = DroughtOdds.of(Settings.DEFAULT);
        assertThrows(IllegalArgumentException.class, () -> o.within(-1));
        assertThrows(IllegalArgumentException.class, () -> o.simulate(0, 10, 1, 1));
    }
}
