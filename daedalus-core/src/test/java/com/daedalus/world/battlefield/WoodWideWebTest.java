// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.WoodWideWeb.Outcome;
import com.daedalus.world.battlefield.WoodWideWeb.Report;
import com.daedalus.world.battlefield.WoodWideWeb.Settings;
import com.daedalus.world.battlefield.WoodWideWeb.Tree;
import com.daedalus.world.battlefield.WoodWideWeb.Year;
import org.junit.jupiter.api.Test;

class WoodWideWebTest {

    private static final Settings D = Settings.DEFAULT;

    private static Settings small(int w, int h, double drought, double spread, int timberGoal) {
        return new Settings(w, h, D.years(), D.motherChance(), D.matureChance(), D.seedlingChance(),
                D.motherSurplus(), D.matureSurplus(), D.seedlingNeed(), drought, D.droughtCost(), D.startStore(),
                spread, D.seedlingYears(), D.spores(), D.motherTimber(), timberGoal, D.seedlingGoal());
    }

    @Test
    void aSeedlingAloneInTheShadeStarves() {
        Report r = WoodWideWeb.planted(small(1, 1, 0, 0, 0), 1, "S").run();
        assertEquals(Outcome.COLLAPSED, r.outcome());
        assertEquals(Tree.EMPTY, r.stand().get(0));
        assertEquals(1, r.years().get(2).deaths(), "store 2, need 1 a year: gone in the third year");
    }

    @Test
    void aMotherFeedsTheSeedlingsHerThreadsReach() {
        Settings s = small(3, 1, 0, 0, 0);
        WoodWideWeb linked = WoodWideWeb.planted(s, 1, "SMS");
        assertTrue(linked.inoculate(0, 0));
        assertTrue(linked.inoculate(2, 0));
        Report r = linked.run();
        assertEquals(2, r.seedlingsRaised());
        assertEquals(Tree.MATURE, r.stand().get(0));
        assertEquals(Outcome.OLD_GROWTH, r.outcome());
        Report bare = WoodWideWeb.planted(s, 1, "SMS").run();
        assertEquals(0, bare.seedlingsRaised(), "no threads, no carbon: spread is off here");
    }

    @Test
    void theFungusSpreadsFromTheMotherOnItsOwn() {
        Report r = WoodWideWeb.planted(small(3, 1, 0, 1.0, 0), 1, "SMS").run();
        assertEquals(2, r.seedlingsRaised());
        assertEquals(1, r.years().get(0).networks());
        assertEquals(3, r.years().get(0).linkedTrees());
    }

    @Test
    void inADroughtTheNetworkSavesWhoItCan_neverHalfSavingTwo() {
        Settings s = small(3, 3, 1.0, 0, 0);
        WoodWideWeb w = WoodWideWeb.planted(s, 1, ".S./SMS/.S.");
        assertTrue(w.inoculate(1, 0));
        assertTrue(w.inoculate(0, 1));
        assertTrue(w.inoculate(2, 1));
        assertTrue(w.inoculate(1, 2));
        Report r = w.run();
        for (Year y : r.years()) {
            assertTrue(y.drought());
        }
        assertTrue(r.seedlingsRaised() >= 1, "the mother carries some through");
        assertTrue(r.seedlingsRaised() < 4, "but not all four through a drought every year");
        assertEquals(Tree.MOTHER, r.stand().get(4));
    }

    @Test
    void aSeedlingCutOffWhenItsBridgeDiesStandsAlone() {
        Settings s = small(5, 1, 1.0, 0, 0);
        WoodWideWeb w = WoodWideWeb.planted(s, 1, "SSMSS");
        for (int x : new int[] {0, 1, 3, 4}) {
            assertTrue(w.inoculate(x, 0));
        }
        Report r = w.run();
        assertEquals(2, r.years().get(3).networks(), "the web split when the middle seedlings died");
        assertEquals(0, r.seedlingsRaised());
    }

    @Test
    void loggingTheMothersBreaksTheWeb() {
        int kept = 0;
        int felled = 0;
        for (long seed = 1; seed <= 6; seed++) {
            kept += WoodWideWeb.stand(D, seed).run().seedlingsRaised();
            WoodWideWeb w = WoodWideWeb.stand(D, seed);
            for (int y = 0; y < D.height(); y++) {
                for (int x = 0; x < D.width(); x++) {
                    if (w.at(x, y) == Tree.MOTHER) {
                        assertTrue(w.log(x, y));
                    }
                }
            }
            Report r = w.run();
            felled += r.seedlingsRaised();
            assertTrue(r.timber() > 0);
            assertFalse(r.outcome() == Outcome.OLD_GROWTH, "no mothers left: not old growth");
        }
        assertTrue(felled < kept / 2, "felled " + felled + " vs kept " + kept);
    }

    @Test
    void timberCountsMothersHeavier() {
        Settings s = small(3, 1, 0, 0, 4);
        WoodWideWeb w = WoodWideWeb.planted(s, 1, "MTt");
        assertTrue(w.log(0, 0));
        assertTrue(w.log(2, 0));
        assertFalse(w.log(2, 0));
        assertEquals(D.motherTimber() + 1, w.run().timber());
        assertFalse(WoodWideWeb.planted(s, 1, "S.M").log(0, 0), "seedlings are not timber");
    }

    @Test
    void thePlanNeverShiftsTheWeather() {
        WoodWideWeb a = WoodWideWeb.stand(D, 3);
        WoodWideWeb b = WoodWideWeb.stand(D, 3);
        for (int y = 0; y < D.height(); y++) {
            for (int x = 0; x < D.width(); x++) {
                if (b.at(x, y) == Tree.MATURE && !b.colonized(x, y)) {
                    b.log(x, y);
                }
            }
        }
        Report ra = a.run();
        Report rb = b.run();
        for (int y = 0; y < D.years(); y++) {
            assertEquals(ra.years().get(y).drought(), rb.years().get(y).drought());
        }
    }

    @Test
    void bandsReadTheStand() {
        Report r = WoodWideWeb.planted(small(4, 1, 0, 0, 0), 1, "MT.S").run();
        assertEquals(Vegetation.OAK, r.band(0));
        assertEquals(Vegetation.PINE, r.band(1));
        assertEquals(Vegetation.MEADOW, r.band(2));
        assertEquals(Vegetation.MEADOW, r.band(3), "the lone seedling starved");
        Report young = WoodWideWeb.planted(new Settings(1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 5, 0, 3, 0, 0), 1,
                "S").run();
        assertEquals(Vegetation.SCRUB, young.band(0));
    }

    @Test
    void sameStandSameResult() {
        assertEquals(WoodWideWeb.stand(D, 9).run(), WoodWideWeb.stand(D, 9).run());
    }

    @Test
    void sporesAreBudgeted_andBadInputIsRefused() {
        WoodWideWeb w = WoodWideWeb.planted(small(8, 1, 0, 0, 0), 1, "SSSSSSSS");
        for (int x = 0; x < D.spores(); x++) {
            assertTrue(w.inoculate(x, 0));
        }
        assertEquals(0, w.sporesLeft());
        assertFalse(w.inoculate(7, 0));
        WoodWideWeb m = WoodWideWeb.planted(small(2, 1, 0, 0, 0), 1, "M.");
        assertFalse(m.inoculate(0, 0), "already colonized");
        assertFalse(m.inoculate(1, 0), "empty");
        assertThrows(IllegalArgumentException.class, () -> m.at(2, 0));
        assertThrows(IllegalArgumentException.class, () -> WoodWideWeb.stand(null, 1));
        assertThrows(IllegalArgumentException.class, () -> WoodWideWeb.planted(D, 1, "M"));
        assertThrows(IllegalArgumentException.class, () -> WoodWideWeb.planted(small(1, 1, 0, 0, 0), 1, "X"));
        assertThrows(IllegalArgumentException.class, () -> WoodWideWeb.planted(small(2, 1, 0, 0, 0), 1, "M"));
        assertThrows(IllegalArgumentException.class, () -> small(1, 1, 1.5, 0, 0));
    }
}
