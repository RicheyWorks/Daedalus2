// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.SalmonRun.Outcome;
import com.daedalus.world.battlefield.SalmonRun.Report;
import com.daedalus.world.battlefield.SalmonRun.Settings;
import com.daedalus.world.battlefield.SalmonRun.Year;
import org.junit.jupiter.api.Test;

class SalmonRunTest {

    private static final Settings D = Settings.DEFAULT;

    private static Settings calm() {
        return new Settings(D.years(), D.lag(), D.spawners(), D.alpha(), D.lowerGravel(), D.upperGravel(),
                D.weirPassage(), D.pondBoost(), D.maxPonds(), 0.0, D.bearCarry(), D.judgeYears(), D.target(),
                D.collapse(), D.catchGoal());
    }

    private static SalmonRun works(Settings s, long seed, double harvest) {
        SalmonRun r = SalmonRun.river(s, seed);
        assertTrue(r.buildLadder());
        for (int i = 0; i < s.maxPonds(); i++) {
            assertTrue(r.pond());
        }
        assertTrue(r.harvest(harvest));
        return r;
    }

    @Test
    void aCalmOceanFollowsTheRickerCurveToItsEquilibrium() {
        Report r = SalmonRun.river(calm(), 1).run();
        double cap = D.lowerGravel() + D.upperGravel() * D.weirPassage();
        double equilibrium = cap * Math.log(D.alpha());
        assertEquals(equilibrium, r.years().get(D.years() - 1).escapement(), equilibrium * 0.02);
        Year first = r.years().get(0);
        assertEquals(D.alpha() * D.spawners() * Math.exp(-D.spawners() / cap), first.run(), 1e-9);
    }

    @Test
    void theLadderOpensTheUpperGravel() {
        SalmonRun plain = SalmonRun.river(D, 1);
        SalmonRun ladder = SalmonRun.river(D, 1);
        assertTrue(ladder.buildLadder());
        assertFalse(ladder.buildLadder());
        assertEquals(D.lowerGravel() + D.upperGravel(), ladder.capacity());
        assertTrue(ladder.run().meanEscapement() > 1.5 * plain.run().meanEscapement());
    }

    @Test
    void ladderPondsAndAFairCatchRestoreTheRun() {
        for (long seed = 1; seed <= 5; seed++) {
            Report r = works(D, seed, 0.4).run();
            assertEquals(Outcome.RESTORED, r.outcome(), "seed " + seed);
            assertTrue(r.totalCatch() >= D.catchGoal());
            assertTrue(r.meanEscapement() >= D.target());
        }
    }

    @Test
    void theSameCatchWithoutTheWorksOnlyHolds() {
        SalmonRun r = SalmonRun.river(D, 1);
        assertTrue(r.harvest(0.4));
        assertEquals(Outcome.HOLDING, r.run().outcome());
        assertEquals(Outcome.HOLDING, SalmonRun.river(D, 1).run().outcome(), "no catch misses the island's goal");
    }

    @Test
    void harvestPastTheReplacementLimitFishesItOut() {
        SalmonRun r = SalmonRun.river(D, 1);
        assertEquals(0.75, r.replacementLimit(), 1e-12);
        assertTrue(r.harvest(0.85));
        Report x = r.run();
        assertEquals(Outcome.FISHED_OUT, x.outcome());
        assertEquals(Vegetation.MEADOW, x.forest(D), "no salmon, no marine nitrogen");
        SalmonRun ponds = works(D, 1, 0.0);
        assertTrue(ponds.replacementLimit() > r.replacementLimit());
    }

    @Test
    void bearsCarryTheSpawnedOutIntoTheForest() {
        Report r = works(D, 2, 0.4).run();
        double carried = 0;
        for (Year y : r.years()) {
            assertEquals(D.bearCarry() * y.escapement(), y.forestNitrogen(), 1e-9);
            assertEquals(y.run(), y.caught() + y.escapement(), 1e-9);
            carried += y.forestNitrogen();
        }
        assertEquals(carried, r.forestNitrogen(), 1e-6);
        assertNotEquals(Vegetation.MEADOW, r.forest(D));
        Report rich = works(calm(), 2, 0.0).run();
        assertEquals(Vegetation.OAK, rich.forest(calm()));
    }

    @Test
    void eachReturnIsTheChildOfTheRunLagYearsBefore() {
        Report r = works(D, 3, 0.4).run();
        for (int y = D.lag(); y < D.years(); y++) {
            assertEquals(r.years().get(y - D.lag()).escapement(), r.years().get(y).spawnersBack(), 1e-9);
        }
        assertEquals(D.spawners(), r.years().get(0).spawnersBack());
    }

    @Test
    void sameRiverSameResult_andOceansDifferBySeed() {
        assertEquals(works(D, 4, 0.4).run(), works(D, 4, 0.4).run());
        assertNotEquals(works(D, 4, 0.4).run().totalCatch(), works(D, 5, 0.4).run().totalCatch());
    }

    @Test
    void pondsAreBudgeted_andBadInputIsRefused() {
        SalmonRun r = SalmonRun.river(D, 1);
        for (int i = 0; i < D.maxPonds(); i++) {
            assertTrue(r.pond());
        }
        assertFalse(r.pond());
        assertFalse(r.harvest(-0.1));
        assertFalse(r.harvest(1.1));
        assertFalse(r.harvest(Double.NaN));
        assertThrows(IllegalArgumentException.class, () -> SalmonRun.river(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(40, 4, 150, 4, 0, 0, 0.25, 0.1, 3, 0.4,
                0.5, 8, 1000, 50, 12000));
        assertThrows(IllegalArgumentException.class, () -> new Settings(40, 4, 150, 4, 400, 800, 0.25, 0.1, 3,
                0.4, 0.5, 41, 1000, 50, 12000));
        Settings barren = new Settings(10, 2, 100, 0.5, 400, 800, 0.25, 0.0, 3, 0.0, 0.5, 2, 1000, 50, 0);
        assertEquals(0.0, SalmonRun.river(barren, 1).replacementLimit());
    }
}
