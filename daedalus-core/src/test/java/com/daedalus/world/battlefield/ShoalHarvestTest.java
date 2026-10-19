// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.ShoalHarvest.Outcome;
import com.daedalus.world.battlefield.ShoalHarvest.Report;
import com.daedalus.world.battlefield.ShoalHarvest.Rule;
import com.daedalus.world.battlefield.ShoalHarvest.Settings;
import com.daedalus.world.battlefield.ShoalHarvest.Year;
import org.junit.jupiter.api.Test;

class ShoalHarvestTest {

    private static final Settings D = Settings.DEFAULT;
    private static final int SEEDS = 200;
    private static final double E = ShoalHarvest.shoal(D, 1).msyEffort();

    private static int count(Rule rule, double level, Outcome o) {
        int n = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            if (ShoalHarvest.shoal(D, seed).run(rule, level).outcome() == o) {
                n++;
            }
        }
        return n;
    }

    private static double meanCatch(Rule rule, double level) {
        double sum = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            sum += ShoalHarvest.shoal(D, seed).run(rule, level).meanCatch();
        }
        return sum / SEEDS;
    }

    @Test
    void maximumSustainableYieldMatchesTheTextbook() {
        ShoalHarvest h = ShoalHarvest.shoal(D, 1);
        assertEquals(150.0, h.msy(), 1e-12);
        assertEquals(0.3 / 1.3, h.msyEffort(), 1e-12);
    }

    @Test
    void withoutNoiseBothRulesHoldTheShoalAtHalfCapacityForMsy() {
        ShoalHarvest calm = ShoalHarvest.shoal(new Settings(1000, 0.6, 0, 50, 0.05), 1);
        for (Report r : new Report[] {calm.run(Rule.QUOTA, calm.msy()), calm.run(Rule.EFFORT, calm.msyEffort())}) {
            assertEquals(Outcome.THRIVING, r.outcome());
            assertEquals(150.0, r.meanCatch(), 1e-9);
            assertEquals(500.0, r.shoal(), 1e-9);
            for (Year y : r.years()) {
                assertEquals(650.0, y.shoal(), 1e-9);
                assertEquals(150.0, y.catchTonnes(), 1e-9);
            }
        }
    }

    @Test
    void withNoiseTheMsyQuotaIsAKnifeEdge() {
        int collapsed = count(Rule.QUOTA, 150, Outcome.COLLAPSED);
        assertTrue(collapsed >= 100, "MSY quota collapsed " + collapsed);
        assertEquals(0, count(Rule.EFFORT, E, Outcome.COLLAPSED));
        assertEquals(SEEDS, count(Rule.EFFORT, E, Outcome.THRIVING));
    }

    @Test
    void theNoiseModelAndSeedsAreLocked() {
        // seed 1, year 0: 500 + 0.6 * 500 * 0.5 * (1 + 0.5 * (2u - 1)) for the splitmix draw u of (seed 1, year 0)
        Report r = ShoalHarvest.shoal(D, 1).run(Rule.QUOTA, 150);
        assertEquals(659.9842362758421, r.years().get(0).shoal(), 1e-9);
        assertEquals(696.776988431989, r.years().get(1).shoal(), 1e-9);
        assertEquals(138, count(Rule.QUOTA, 150, Outcome.COLLAPSED));
        assertEquals(0, count(Rule.EFFORT, E, Outcome.COLLAPSED));
        assertEquals(0.3 / 1.3, E, 0.0);
    }

    @Test
    void theMsyEffortLandsMoreFishThanTheMsyQuota() {
        double effort = meanCatch(Rule.EFFORT, E);
        double quota = meanCatch(Rule.QUOTA, 150);
        assertTrue(effort > quota + 30, "effort " + effort + " quota " + quota);
        assertTrue(effort > 140, "effort " + effort);
    }

    @Test
    void aPrecautionaryQuotaSurvivesAndOverfishingDoesNot() {
        assertEquals(0, count(Rule.QUOTA, 120, Outcome.COLLAPSED));
        assertEquals(SEEDS, count(Rule.EFFORT, 0.45, Outcome.COLLAPSED));
        assertEquals(SEEDS, count(Rule.EFFORT, 0, Outcome.THRIVING));
    }

    @Test
    void effortTakesLessWhenTheShoalIsSmall() {
        for (long seed = 1; seed <= 10; seed++) {
            for (Year y : ShoalHarvest.shoal(D, seed).run(Rule.EFFORT, E).years()) {
                assertEquals(E * y.shoal(), y.catchTonnes(), 1e-9);
            }
            for (Year y : ShoalHarvest.shoal(D, seed).run(Rule.QUOTA, 150).years()) {
                assertEquals(Math.min(150, y.shoal()), y.catchTonnes(), 1e-9);
            }
        }
    }

    @Test
    void aThrivingShoalKeepsTheKelpBanks() {
        for (long seed = 1; seed <= 20; seed++) {
            Report r = ShoalHarvest.shoal(D, seed).run(Rule.QUOTA, 150);
            assertEquals(r.outcome() == Outcome.THRIVING ? Vegetation.WETLAND : Vegetation.BARE, r.band());
            assertEquals(D.years(), r.years().size());
        }
    }

    @Test
    void sameSeedSameRuleSameSeason() {
        for (long seed = 1; seed <= 10; seed++) {
            assertEquals(ShoalHarvest.shoal(D, seed).run(Rule.QUOTA, 140),
                    ShoalHarvest.shoal(D, seed).run(Rule.QUOTA, 140));
            assertEquals(ShoalHarvest.shoal(D, seed).run(Rule.EFFORT, E),
                    ShoalHarvest.shoal(D, seed).run(Rule.EFFORT, E));
        }
    }

    @Test
    void badRulesAndSettingsAreRefused() {
        ShoalHarvest h = ShoalHarvest.shoal(D, 1);
        assertThrows(IllegalArgumentException.class, () -> h.run(null, 1));
        assertThrows(IllegalArgumentException.class, () -> h.run(Rule.EFFORT, 1.5));
        assertThrows(IllegalArgumentException.class, () -> h.run(Rule.QUOTA, -1));
        assertThrows(IllegalArgumentException.class, () -> ShoalHarvest.shoal(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0, 0.6, 0.5, 50, 0.05));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1000, 1.6, 0.5, 50, 0.05));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1000, 0.6, 1.0, 50, 0.05));
    }
}
