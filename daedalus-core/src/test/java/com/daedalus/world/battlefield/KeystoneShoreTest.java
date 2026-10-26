// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.KeystoneShore.Life;
import com.daedalus.world.battlefield.KeystoneShore.Outcome;
import com.daedalus.world.battlefield.KeystoneShore.Report;
import com.daedalus.world.battlefield.KeystoneShore.Settings;
import com.daedalus.world.battlefield.KeystoneShore.Year;
import org.junit.jupiter.api.Test;

class KeystoneShoreTest {

    private static final Settings D = Settings.DEFAULT;

    private static Report taking(int stars, long seed) {
        KeystoneShore k = KeystoneShore.shore(D, seed);
        if (stars > 0) {
            assertTrue(k.harvest(stars));
        }
        return k.run();
    }

    @Test
    void takeEveryStarAndTheMusselsSmotherTheShore() {
        for (long seed = 1; seed <= 5; seed++) {
            Report r = taking(D.stars(), seed);
            assertEquals(Outcome.MUSSEL_BED, r.outcome());
            assertTrue(r.cover().get(Life.MUSSEL) >= D.bedCover());
            assertTrue(r.species(D.minCover()) < 3);
        }
    }

    @Test
    void leaveEnoughStarsAndTheShoreStaysDiverse() {
        for (long seed = 1; seed <= 5; seed++) {
            Report r = taking(D.baitGoal(), seed);
            assertEquals(Outcome.DIVERSE, r.outcome(), "seed " + seed);
            assertEquals(3, r.species(D.minCover()));
            assertEquals(D.baitGoal(), r.bait());
        }
    }

    @Test
    void noBaitTaken_theShoreIsFineButTheIslandGoesWithout() {
        Report r = taking(0, 1);
        assertEquals(3, r.species(D.minCover()));
        assertEquals(Outcome.THIN, r.outcome());
    }

    @Test
    void moreStarsTakenMeansMoreMussels() {
        double last = -1;
        for (int taken : new int[] {0, 4, 6}) {
            double m = 0;
            for (long seed = 1; seed <= 4; seed++) {
                m += taking(taken, seed).cover().get(Life.MUSSEL);
            }
            assertTrue(m > last, taken + " stars taken");
            last = m;
        }
    }

    @Test
    void eachSpeciesSettlesOnlyInItsZone() {
        KeystoneShore k = KeystoneShore.shore(D, 2);
        Report r = k.run();
        for (int i = 0; i < r.shore().size(); i++) {
            Life l = r.shore().get(i);
            int row = i / D.width();
            if (l == Life.BARNACLE || l == Life.KELP) {
                assertTrue(k.zone(l, row), l + " at row " + row);
            }
        }
        assertTrue(k.zone(Life.BARNACLE, 0));
        assertFalse(k.zone(Life.KELP, 0));
        assertTrue(k.zone(Life.KELP, D.height() - 1));
        assertFalse(k.zone(Life.MUSSEL, 0));
    }

    @Test
    void starsEatNoMoreThanTheirAppetite() {
        Report r = taking(2, 3);
        for (Year y : r.years()) {
            assertTrue(y.eaten() <= y.stars() * D.starAppetite());
            assertEquals(D.stars() - 2, y.stars());
        }
        for (Year y : taking(D.stars(), 3).years()) {
            assertEquals(0, y.eaten());
        }
    }

    @Test
    void coverAddsUpAndBandsReadTheRock() {
        Report r = taking(2, 4);
        double sum = r.cover().values().stream().mapToDouble(Double::doubleValue).sum();
        assertEquals(1.0, sum, 1e-9);
        for (int i = 0; i < r.shore().size(); i++) {
            assertEquals(r.shore().get(i) == Life.KELP ? Vegetation.WETLAND : Vegetation.BARE, r.band(i));
        }
    }

    @Test
    void stormsOpenBareRock() {
        Settings stormy = new Settings(D.width(), D.height(), D.years(), D.stars(), D.starAppetite(), D.starReach(),
                D.settle(), D.overgrow(), 1.0, D.stormPatch(), D.minCover(), D.bedCover(), D.baitGoal());
        Report r = KeystoneShore.shore(stormy, 1).run();
        assertTrue(r.years().stream().allMatch(Year::storm));
        assertTrue(r.cover().get(Life.BARE) >= (double) (D.stormPatch() * D.stormPatch()) / (D.width() * D.height())
                - 1e-9);
    }

    @Test
    void sameShoreSameResult() {
        assertEquals(taking(2, 9), taking(2, 9));
    }

    @Test
    void starsAreBudgeted_andBadInputIsRefused() {
        KeystoneShore k = KeystoneShore.shore(D, 1);
        assertTrue(k.harvest(4));
        assertFalse(k.harvest(3));
        assertTrue(k.harvest(2));
        assertEquals(0, k.starsLeft());
        assertFalse(k.harvest(0));
        assertThrows(IllegalArgumentException.class, () -> KeystoneShore.shore(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(16, 2, 30, 6, 6, 0.7, 0.3, 0.25, 0.3, 3,
                0.06, 0.6, 2));
        assertThrows(IllegalArgumentException.class, () -> new Settings(16, 12, 30, 6, 6, 1.7, 0.3, 0.25, 0.3, 3,
                0.06, 0.6, 2));
    }
}
