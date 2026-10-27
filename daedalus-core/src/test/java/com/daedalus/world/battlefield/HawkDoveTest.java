// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.HawkDove.Outcome;
import com.daedalus.world.battlefield.HawkDove.Report;
import com.daedalus.world.battlefield.HawkDove.Season;
import com.daedalus.world.battlefield.HawkDove.Settings;
import org.junit.jupiter.api.Test;

class HawkDoveTest {

    private static final Settings D = Settings.DEFAULT;
    private static final int SEEDS = 30;

    private static double lateHawks(Settings s, int start) {
        double sum = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            sum += HawkDove.ridge(s, seed).run(start).lateHawks();
        }
        return sum / SEEDS;
    }

    @Test
    void theStableShareIsValueOverCost() {
        HawkDove h = HawkDove.ridge(D, 1);
        assertEquals(0.4, h.ess(), 1e-12);
        assertEquals(h.expectedPayoff(true, 0.4), h.expectedPayoff(false, 0.4), 1e-12);
        assertTrue(h.expectedPayoff(true, 0.2) > h.expectedPayoff(false, 0.2));
        assertTrue(h.expectedPayoff(true, 0.6) < h.expectedPayoff(false, 0.6));
        assertEquals(1.0, HawkDove.ridge(new Settings(200, 4, 3, 10, 10, 150), 1).ess(), 0.0);
    }

    @Test
    void theHerdSettlesAtTheEssFromAnyStart() {
        for (int start : new int[] {20, 100, 180}) {
            double late = lateHawks(D, start);
            assertEquals(0.4, late, 0.04, "start " + start);
        }
    }

    @Test
    void costlierFightsMeanFewerHawks() {
        Settings c8 = new Settings(200, 4, 8, 10, 10, 150);
        assertEquals(0.5, lateHawks(c8, 100), 0.05);
        assertTrue(lateHawks(c8, 100) > lateHawks(D, 100));
    }

    @Test
    void cheapFightsLetHawksTakeOver() {
        Settings cheap = new Settings(200, 4, 3, 10, 10, 150);
        int allHawk = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            Report r = HawkDove.ridge(cheap, seed).run(20);
            if (r.outcome() == Outcome.ALL_HAWK) {
                allHawk++;
            }
            assertEquals(Vegetation.BARE, r.band());
        }
        assertTrue(allHawk >= 27, "all hawk " + allHawk);
    }

    @Test
    void atTheEssHawksAndDovesEarnAboutTheSame() {
        double hp = 0;
        double dp = 0;
        int n = 0;
        for (long seed = 1; seed <= 10; seed++) {
            for (Season s : HawkDove.ridge(D, seed).run(80).seasons().subList(100, 150)) {
                if (!Double.isNaN(s.hawkPayoff()) && !Double.isNaN(s.dovePayoff())) {
                    hp += s.hawkPayoff();
                    dp += s.dovePayoff();
                    n++;
                }
            }
        }
        assertTrue(n > 0);
        assertEquals(hp / n, dp / n, 0.25, "hawk " + hp / n + " dove " + dp / n);
    }

    @Test
    void pureHerdsStayPure() {
        Report doves = HawkDove.ridge(D, 1).run(0);
        assertEquals(Outcome.ALL_DOVE, doves.outcome());
        assertEquals(Vegetation.MEADOW, doves.band());
        assertEquals(Outcome.ALL_HAWK, HawkDove.ridge(D, 1).run(D.herd()).outcome());
        for (Season s : doves.seasons()) {
            assertTrue(Double.isNaN(s.hawkPayoff()));
        }
    }

    @Test
    void aMixedRidgeKeepsItsGrazing() {
        for (long seed = 1; seed <= 10; seed++) {
            Report r = HawkDove.ridge(D, seed).run(100);
            assertEquals(Outcome.MIXED, r.outcome());
            assertEquals(Vegetation.MEADOW, r.band());
            assertEquals(D.seasons(), r.seasons().size());
        }
    }

    @Test
    void sameSeedSameRut() {
        for (long seed = 1; seed <= 5; seed++) {
            assertEquals(HawkDove.ridge(D, seed).run(60), HawkDove.ridge(D, seed).run(60));
        }
    }

    @Test
    void badInputIsRefused() {
        assertThrows(IllegalArgumentException.class, () -> HawkDove.ridge(null, 1));
        assertThrows(IllegalArgumentException.class, () -> HawkDove.ridge(D, 1).run(-1));
        assertThrows(IllegalArgumentException.class, () -> HawkDove.ridge(D, 1).run(D.herd() + 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1, 4, 10, 10, 10, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(200, 0, 10, 10, 10, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(200, 4, -1, 10, 10, 10));
    }
}
