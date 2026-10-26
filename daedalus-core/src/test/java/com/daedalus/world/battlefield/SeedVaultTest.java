// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.SeedVault.Settings;
import com.daedalus.world.battlefield.SeedVault.Species;
import org.junit.jupiter.api.Test;

class SeedVaultTest {

    private static final Settings D = Settings.DEFAULT;
    private static final Species[] ORTHODOX = {Species.WILLOW, Species.MEADOW_GRASS, Species.BRAMBLE, Species.PINE};

    /** Dry the orthodox lots to 6% as the power allows (keeping 18 for 2 C cooling), store at 2 C. */
    private static SeedVault voyage(boolean regrowOak) {
        SeedVault v = SeedVault.stock(D, 1);
        while (!v.landed()) {
            for (Species sp : ORTHODOX) {
                if (v.moisture(sp) > 6 && v.powerLeft() - 9 >= 18) {
                    assertTrue(v.dry(sp, 6));
                }
            }
            if (regrowOak && v.regrowsLeft() > 0) {
                assertTrue(v.regrow(Species.OAK));
            }
            assertTrue(v.year(2));
        }
        return v;
    }

    @Test
    void ageingFollowsTheEllisRobertsViabilityEquation() {
        double expected = Math.pow(10, 8.6 - 4.9 * Math.log10(8) - 0.0329 * 15 - 0.000478 * 225);
        assertEquals(expected, Species.MEADOW_GRASS.sigmaDays(8, 15), 1e-9 * expected);
        assertEquals(0.5, SeedVault.phi(0), 1e-7);
        assertEquals(0.977250, SeedVault.phi(2), 1e-6);
        assertEquals(0.022750, SeedVault.phi(-2), 1e-6);

        SeedVault v = SeedVault.stock(D, 1);
        assertEquals(SeedVault.phi(2), v.viability(Species.PINE), 1e-12);
        assertTrue(v.year(15));
        double sigma = Species.PINE.sigmaDays(15, 15);
        assertEquals(2 - 365 / sigma, v.probit(Species.PINE), 1e-9);
        assertTrue(Species.PINE.sigmaDays(6, 2) > Species.PINE.sigmaDays(15, 20), "drier and colder keeps longer");
    }

    @Test
    void aNeglectedVaultLandsWithNothing() {
        SeedVault v = SeedVault.stock(D, 1);
        while (!v.landed()) {
            assertTrue(v.year(D.ambientC()));
        }
        assertEquals(12, v.year());
        assertEquals(0, v.caches());
        assertEquals(0, v.survivingSpecies());
        assertFalse(v.year(2), "the voyage is over");
    }

    @Test
    void driedAndCooledOrthodoxSeedSurvivesTheVoyage_butOakDoesNot() {
        SeedVault v = voyage(false);
        for (Species sp : ORTHODOX) {
            assertTrue(v.caches(sp) >= 1, sp + " " + v.liveSeeds(sp));
        }
        assertEquals(0, v.caches(Species.OAK));
        assertEquals(4, v.survivingSpecies());
    }

    @Test
    void regrowingTheOakAtEveryStopover_bringsAllFiveBandsToLandfall() {
        SeedVault v = voyage(true);
        assertEquals(5, v.survivingSpecies());
        assertTrue(v.caches() > voyage(false).caches());
        assertTrue(v.caches(Species.OAK) >= 1);
    }

    @Test
    void oakAcornsAreRecalcitrant_dryingThemKillsThem() {
        SeedVault v = SeedVault.stock(D, 1);
        assertTrue(v.dry(Species.OAK, 35), "still above the critical moisture");
        assertTrue(v.viability(Species.OAK) > 0.9);
        assertTrue(v.dry(Species.OAK, 20));
        assertEquals(0.0, v.viability(Species.OAK));
        assertEquals(SeedVault.DEAD, v.probit(Species.OAK));
    }

    @Test
    void moistSeedFreezesBelowZero() {
        SeedVault v = SeedVault.stock(D, 1);
        assertTrue(v.year(-5));
        assertEquals(0.0, v.viability(Species.OAK), "40% moisture: ice");
        assertTrue(v.viability(Species.MEADOW_GRASS) > 0, "15% is below the ice line");
    }

    @Test
    void dryingAndCoolingSpendTheArksPower() {
        SeedVault v = SeedVault.stock(D, 1);
        assertFalse(v.year(-25), "45 power of cooling, 40 in the budget");
        assertEquals(0, v.year());
        for (Species sp : ORTHODOX) {
            assertTrue(v.dry(sp, 6));
        }
        assertEquals(4, v.powerLeft(), 1e-9);
        assertFalse(v.dry(Species.OAK, 35), "5 points, 4 power left");
        assertFalse(v.year(2), "18 power of cooling");
        assertTrue(v.year(16));
        assertEquals(D.powerPerYear(), v.powerLeft(), 1e-9, "the budget comes back each year");
        assertFalse(v.dry(Species.PINE, 8), "drying cannot add moisture");
    }

    @Test
    void regrowingNeedsAStopover_twoLotsAStop_andHarvestsFreshSeed() {
        SeedVault v = SeedVault.stock(D, 1);
        assertFalse(v.regrow(Species.OAK), "no stopover at the start");
        assertTrue(v.year(10));
        assertTrue(v.year(10));
        assertFalse(v.regrow(Species.OAK));
        assertTrue(v.year(10));
        assertEquals(2, v.regrowsLeft());
        double live = v.liveSeeds(Species.OAK);
        assertTrue(v.regrow(Species.OAK));
        assertEquals(Math.min(D.seedsPerLot(), Math.floor(live * D.harvestPerSeed())), v.seeds(Species.OAK), 1e-9);
        assertEquals(D.startProbit(), v.probit(Species.OAK));
        assertTrue(v.regrow(Species.PINE));
        assertFalse(v.regrow(Species.BRAMBLE), "two lots a stopover");
        assertEquals(Species.PINE.freshMoisture(), v.moisture(Species.PINE), "fresh seed must be dried again");
        assertTrue(v.year(10));
        assertFalse(v.regrow(Species.BRAMBLE), "year 4 is no stopover");
    }

    @Test
    void aGerminationTestSpendsSeedsAndMeasuresTheLot() {
        SeedVault a = SeedVault.stock(D, 7);
        int up = a.germinationTest(Species.BRAMBLE, 1000);
        assertTrue(up >= 945 && up <= 1000, "97.7% expected, got " + up);
        assertEquals(D.seedsPerLot() - 1000, a.seeds(Species.BRAMBLE));
        assertEquals(up, SeedVault.stock(D, 7).germinationTest(Species.BRAMBLE, 1000), "seeded");
        assertThrows(IllegalArgumentException.class, () -> a.germinationTest(Species.BRAMBLE, 0));
        assertThrows(IllegalArgumentException.class, () -> a.germinationTest(Species.BRAMBLE, 999_999));

        SeedVault dead = SeedVault.stock(D, 7);
        dead.year(D.ambientC());
        assertEquals(0, dead.germinationTest(Species.WILLOW, 200));
    }

    @Test
    void landfallFillsTheAshfallRegrowthSeedCaches() {
        SeedVault v = voyage(true);
        AshfallRegrowth.Settings base = AshfallRegrowth.Settings.DEFAULT;
        AshfallRegrowth.Settings landed = v.forRegrowth(base);
        assertEquals(v.caches(), landed.caches());
        assertEquals(base.seedReach(), landed.seedReach());
        BattlefieldEcology f = new BattlefieldEcology(8, 8, 100, 0, 0, 1);
        assertEquals(v.caches(), AshfallRegrowth.scorch(f, landed, 1).cachesLeft());
    }

    @Test
    void refusesBadInput() {
        assertThrows(IllegalArgumentException.class, () -> SeedVault.stock(null, 1));
        assertThrows(IllegalArgumentException.class, () -> SeedVault.stock(D, 1).viability(null));
        assertThrows(IllegalArgumentException.class,
                () -> new Settings(0, 6000, 2.0, 20, 40, 1, 1, 3, 2, 5, 1000));
        assertThrows(IllegalArgumentException.class,
                () -> new Settings(12, 6000, 2.0, 20, -1, 1, 1, 3, 2, 5, 1000));
        assertFalse(SeedVault.stock(D, 1).dry(Species.PINE, 0));
        assertFalse(SeedVault.stock(D, 1).year(Double.NaN));
    }
}
