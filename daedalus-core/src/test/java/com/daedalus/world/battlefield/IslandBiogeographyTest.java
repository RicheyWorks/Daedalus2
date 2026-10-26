// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.IslandBiogeography.Isle;
import com.daedalus.world.battlefield.IslandBiogeography.Outcome;
import com.daedalus.world.battlefield.IslandBiogeography.Report;
import com.daedalus.world.battlefield.IslandBiogeography.Settings;
import java.util.List;
import org.junit.jupiter.api.Test;

class IslandBiogeographyTest {

    private static final Settings D = Settings.DEFAULT;
    private static final List<Isle> SKY = IslandBiogeography.SKY;

    private static IslandBiogeography arch(long seed, int... rafts) {
        IslandBiogeography b = IslandBiogeography.archipelago(D, SKY, seed);
        for (int r : rafts) {
            assertTrue(b.raft(r));
        }
        return b;
    }

    @Test
    void everyRaftToTheRefugeUsuallyThrives_andEachRaftHelps() {
        int last = -1;
        for (int k = 0; k <= D.stones(); k++) {
            int thriving = 0;
            for (long seed = 1; seed <= 50; seed++) {
                IslandBiogeography b = arch(seed);
                for (int j = 0; j < k; j++) {
                    assertTrue(b.raft(3));
                }
                Report r = b.run();
                if (r.outcome() == Outcome.THRIVING) {
                    thriving++;
                    assertTrue(r.census() >= D.goal());
                }
            }
            assertTrue(thriving > last || thriving == 50, k + " rafts: " + thriving);
            last = thriving;
        }
        assertTrue(last >= 43, "three rafts thrive in " + last + " of 50");
    }

    @Test
    void noRaftsAndTheFarRefugeStaysBarren() {
        for (long seed = 1; seed <= 20; seed++) {
            assertEquals(Outcome.BARREN, arch(seed).run().outcome());
        }
    }

    @Test
    void raftsSpentElsewhereDoNotHelpTheRefuge() {
        assertEquals(Outcome.BARREN, arch(1, 4, 4, 4).run().outcome());
    }

    @Test
    void largerAndNearerIslandsHoldMoreSpecies() {
        List<Isle> pair = List.of(new Isle("Small", 2, 4), new Isle("Large", 50, 4), new Isle("Far", 50, 12));
        Settings s = new Settings(D.pool(), D.years(), D.colonize(), D.reach(), D.extinct(), D.z(), 0, 0, 0);
        IslandBiogeography b = IslandBiogeography.archipelago(s, pair, 1);
        assertTrue(b.equilibrium(1) > b.equilibrium(0));
        assertTrue(b.equilibrium(1) > b.equilibrium(2));
        assertTrue(b.immigration(1) > b.immigration(2));
        assertTrue(b.extinction(0) > b.extinction(1));
    }

    @Test
    void longRunRichnessSettlesOnTheEquilibrium() {
        double sum = 0;
        int n = 0;
        double eq = 0;
        for (long seed = 1; seed <= 5; seed++) {
            Report r = arch(seed, 3, 3, 3).run();
            eq = r.equilibrium().get(3);
            for (int y = 40; y < D.years(); y++) {
                sum += r.years().get(y).richness().get(3);
                n++;
            }
        }
        assertEquals(eq, sum / n, 1.5);
    }

    @Test
    void raftsDivideTheDistance() {
        IslandBiogeography b = arch(1);
        assertEquals(9.0, b.distance(3), 1e-12);
        assertTrue(b.raft(3));
        assertTrue(b.raft(3));
        assertEquals(3.0, b.distance(3), 1e-12);
    }

    @Test
    void movingARaftNeverShiftsAnotherIslandsDice() {
        Report none = arch(7).run();
        Report refuge = arch(7, 3, 3, 3).run();
        for (int i = 0; i < SKY.size(); i++) {
            if (i != 3) {
                assertEquals(none.richness().get(i), refuge.richness().get(i), "isle " + i);
            }
        }
        assertEquals(arch(7, 3).run(), arch(7, 3).run());
    }

    @Test
    void bandsFollowTheShareOfThePool() {
        Report r = arch(2, 3, 3, 3).run();
        for (int i = 0; i < SKY.size(); i++) {
            double share = (double) r.richness().get(i) / D.pool();
            Vegetation v = r.band(i, D.pool());
            assertEquals(share < 0.15 ? Vegetation.BARE : share < 0.35 ? Vegetation.SCRUB
                    : share < 0.6 ? Vegetation.MEADOW : Vegetation.OAK, v);
        }
    }

    @Test
    void aTinyIslandLosesEverySpeciesEachYear() {
        List<Isle> tiny = List.of(new Isle("Pebble", 0.01, 0));
        Settings s = new Settings(D.pool(), D.years(), D.colonize(), D.reach(), D.extinct(), D.z(), 0, 0, 0);
        IslandBiogeography b = IslandBiogeography.archipelago(s, tiny, 1);
        assertEquals(1.0, b.extinction(0), 1e-12);
        Report r = b.run();
        for (int y = 0; y < D.years(); y++) {
            assertTrue(r.years().get(y).richness().get(0) <= D.pool());
        }
        assertTrue(r.equilibrium().get(0) < D.pool() * D.colonize());
    }

    @Test
    void raftBudgetAndBadInputAreRefused() {
        IslandBiogeography b = arch(1, 0, 1);
        assertEquals(1, b.raftsLeft());
        assertFalse(b.raft(9));
        assertTrue(b.raft(2));
        assertFalse(b.raft(2));
        assertEquals(0, b.raftsLeft());
        assertThrows(IllegalArgumentException.class, () -> new Isle("x", 0, 1));
        assertThrows(IllegalArgumentException.class, () -> new Isle(" ", 1, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(40, 80, 1.2, 3, 0.6, 0.5, 3, 3, 18));
        assertThrows(IllegalArgumentException.class, () -> new Settings(40, 80, 0.2, 3, 0.6, 0.5, 3, 3, 41));
        assertThrows(IllegalArgumentException.class, () -> IslandBiogeography.archipelago(
                new Settings(40, 80, 0.2, 3, 0.6, 0.5, 3, 9, 18), SKY, 1));
        assertThrows(IllegalArgumentException.class, () -> IslandBiogeography.archipelago(D, List.of(), 1));
    }
}
