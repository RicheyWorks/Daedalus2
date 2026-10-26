// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.SootMoths.Outcome;
import com.daedalus.world.battlefield.SootMoths.Report;
import com.daedalus.world.battlefield.SootMoths.Settings;
import org.junit.jupiter.api.Test;

class SootMothsTest {

    private static final Settings D = Settings.DEFAULT;

    private static Settings with(int population, double predation, double startSoot) {
        return new Settings(D.years(), population, D.startDark(), startSoot, D.sootPerLevel(), D.washOff(),
                predation, D.filterShare(), D.maxFilters(), D.forgeGoal(), D.paleGoal());
    }

    private static SootMoths managed(Settings s, long seed) {
        SootMoths m = SootMoths.population(s, seed);
        for (int i = 0; i < s.maxFilters(); i++) {
            assertTrue(m.filter());
        }
        for (int d = 0; d < 4; d++) {
            assertTrue(m.forge(d, 0.6));
        }
        return m;
    }

    @Test
    void aFullForgeBlackensTheBarkAndTheMoths() {
        for (long seed = 1; seed <= 4; seed++) {
            Report r = SootMoths.population(D, seed).run();
            assertEquals(Outcome.DARKENED, r.outcome());
            assertTrue(r.darkAllele() > D.startDark());
            assertEquals(1.0, r.years().get(D.years() - 1).bark(), 1e-3);
            assertEquals(Vegetation.BARE, r.bark());
        }
    }

    @Test
    void filtersAndAGentlerForgeBringThePaleMothsBack() {
        for (long seed = 1; seed <= 6; seed++) {
            Report r = managed(D, seed).run();
            assertEquals(Outcome.RESTORED, r.outcome(), "seed " + seed);
            assertTrue(r.forgeMade() >= D.forgeGoal());
            assertEquals(Vegetation.OAK, r.bark());
        }
    }

    @Test
    void aColdForgeMissesTheIronEvenIfTheMothsRecover() {
        SootMoths m = SootMoths.population(D, 1);
        for (int d = 0; d < 4; d++) {
            m.forge(d, 0);
        }
        Report r = m.run();
        assertEquals(0.0, r.forgeMade());
        assertNotEquals(Outcome.RESTORED, r.outcome());
        assertTrue(r.paleShare() > 0.9);
    }

    @Test
    void barkSettlesWhereSootMeetsRain() {
        Report r = managed(D, 1).run();
        double clean = Math.min(1, D.maxFilters() * D.filterShare());
        double settle = D.sootPerLevel() * 0.6 * (1 - clean) / D.washOff();
        assertEquals(settle, r.years().get(D.years() - 1).bark(), 1e-3);
    }

    @Test
    void theBirdsFavourTheMothThatMatchesTheBark() {
        Settings big = with(200_000, D.predation(), 1.0);
        Report sooty = SootMoths.population(big, 1).run();
        assertTrue(sooty.years().get(0).darkAllele() > D.startDark());
        SootMoths clean = SootMoths.population(with(200_000, D.predation(), 0.0), 1);
        for (int d = 0; d < 4; d++) {
            clean.forge(d, 0);
        }
        assertTrue(clean.run().years().get(0).darkAllele() < D.startDark());
    }

    @Test
    void withoutBirdsOnlyDriftMovesTheGenes() {
        double sum = 0;
        for (long seed = 1; seed <= 20; seed++) {
            Report r = SootMoths.population(with(D.population(), 0.0, D.startSoot()), seed).run();
            sum += r.darkAllele();
            assertEquals(0.0, r.years().get(0).eaten(), 1e-12);
        }
        assertEquals(D.startDark(), sum / 20, 0.06);
    }

    @Test
    void aTinyPopulationLosesAMorphToDrift() {
        int tiny = 0;
        int large = 0;
        for (long seed = 1; seed <= 20; seed++) {
            tiny += SootMoths.population(with(10, 0.0, D.startSoot()), seed).run().outcome() == Outcome.MORPH_LOST ? 1
                    : 0;
            large += SootMoths.population(with(D.population(), 0.0, D.startSoot()), seed).run().outcome()
                    == Outcome.MORPH_LOST ? 1 : 0;
        }
        assertTrue(tiny > large, "tiny " + tiny + " large " + large);
    }

    @Test
    void theDarkShareFollowsHardyWeinberg() {
        Report r = managed(D, 2).run();
        r.years().forEach(y -> assertEquals(1 - (1 - y.darkAllele()) * (1 - y.darkAllele()), y.darkShare(), 1e-12));
        assertEquals((1 - r.darkAllele()) * (1 - r.darkAllele()), r.paleShare(), 1e-12);
    }

    @Test
    void sameSeedSameMoths() {
        assertEquals(managed(D, 5).run(), managed(D, 5).run());
    }

    @Test
    void filtersAndDecadesAreBounded_andBadInputIsRefused() {
        SootMoths m = SootMoths.population(D, 1);
        for (int i = 0; i < D.maxFilters(); i++) {
            assertTrue(m.filter());
        }
        assertFalse(m.filter());
        assertFalse(m.forge(4, 0.5));
        assertFalse(m.forge(-1, 0.5));
        assertFalse(m.forge(0, 1.5));
        assertFalse(m.forge(0, Double.NaN));
        assertThrows(IllegalArgumentException.class, () -> SootMoths.population(null, 1));
        assertThrows(IllegalArgumentException.class, () -> with(0, 0.2, 0.5));
        assertThrows(IllegalArgumentException.class, () -> with(10, 1.2, 0.5));
    }
}
