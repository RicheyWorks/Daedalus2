// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.FirelineWarden.Outcome;
import com.daedalus.world.battlefield.FirelineWarden.Plan;
import com.daedalus.world.battlefield.FirelineWarden.Plot;
import com.daedalus.world.battlefield.FirelineWarden.Report;
import com.daedalus.world.battlefield.FirelineWarden.Settings;
import org.junit.jupiter.api.Test;

class FirelineWardenTest {

    private static final Settings D = Settings.DEFAULT;
    /** The homestead yard: 4 x 3 cells near the south edge. */
    private static final Plot HOME = new Plot(8, 16, 11, 18);

    private static double c(int cell) { return cell * 100 + 50; }

    /** 20 x 20 dry scrub with pine stripes, the homestead yard in meadow, 1 m cells. */
    private static BattlefieldEcology forest(long seed) {
        BattlefieldEcology f = new BattlefieldEcology(20, 20, 100, 0, 0, seed);
        for (int j = 0; j < 20; j++) {
            for (int i = 0; i < 20; i++) {
                f.set(i, j, (i + j) % 5 == 0 ? Vegetation.PINE : Vegetation.SCRUB);
            }
        }
        for (int j = HOME.j0(); j <= HOME.j1(); j++) {
            for (int i = HOME.i0(); i <= HOME.i1(); i++) {
                f.set(i, j, Vegetation.MEADOW);
            }
        }
        return f;
    }

    /** Lightning to the north with the wind blowing south, straight at the homestead. */
    private static FirelineWarden storm(long seed) {
        FirelineWarden g = FirelineWarden.command(forest(seed), HOME, D).wind(0, 1);
        assertTrue(g.ignite(c(10), c(3), 300) > 0);
        return g;
    }

    private static int ring(int i, int j) {
        int di = i < HOME.i0() ? HOME.i0() - i : Math.max(0, i - HOME.i1());
        int dj = j < HOME.j0() ? HOME.j0() - j : Math.max(0, j - HOME.j1());
        return Math.max(di, dj);
    }

    private static final Plan CUT_RING = (g, t) -> {
        for (int j = 0; j < 20; j++) {
            for (int i = 0; i < 20; i++) {
                if (ring(i, j) == 3 && !g.cutAt(i, j)) {
                    g.cut(c(i), c(j));
                }
            }
        }
    };

    private static final Plan WET_RING = (g, t) -> {
        int d = g.frontDistance();
        if (d >= 0 && d <= 4) {
            for (int j = 0; j < 20; j++) {
                for (int i = 0; i < 20; i++) {
                    if (ring(i, j) == 1 && !g.wet(i, j)) {
                        g.wet(c(i), c(j));
                    }
                }
            }
        }
    };

    private static final Plan DOUSE_IN_REACH = (g, t) -> {
        for (int j = 0; j < 20; j++) {
            for (int i = 0; i < 20; i++) {
                g.douse(c(i), c(j));
            }
        }
    };

    @Test
    void anUnfoughtWildfireDownwindTakesTheHomestead() {
        int lost = 0;
        for (long seed = 1; seed <= 8; seed++) {
            Report r = storm(seed).play(null);
            assertNotEquals(Outcome.BURNING, r.outcome());
            lost += r.outcome() == Outcome.LOST ? 1 : 0;
        }
        assertTrue(lost >= 6, "lost " + lost + "/8");
    }

    @Test
    void aCutBreakRingAlwaysSavesTheHomestead_butTheCutGrowthIsGone() {
        for (long seed = 1; seed <= 8; seed++) {
            Report r = storm(seed).play(CUT_RING);
            assertNotEquals(Outcome.LOST, r.outcome(), "seed " + seed);
            assertEquals(22, r.cut());
            assertEquals(0, r.wetted());
        }
    }

    @Test
    void aWetLineAlsoSavesTheHomestead_andSpendsWater() {
        for (long seed = 1; seed <= 8; seed++) {
            Report r = storm(seed).play(WET_RING);
            assertNotEquals(Outcome.LOST, r.outcome(), "seed " + seed);
            assertEquals(0, r.cut());
            assertTrue(r.wetted() > 0);
        }
    }

    @Test
    void fightingTheFlamesInReachHoldsTheFire_andSavesTheMostGrowth() {
        double savedDouse = 0;
        double savedNone = 0;
        for (long seed = 1; seed <= 8; seed++) {
            Report r = storm(seed).play(DOUSE_IN_REACH);
            assertEquals(Outcome.HELD, r.outcome(), "seed " + seed);
            assertTrue(r.doused() > 0);
            savedDouse += r.saved();
            savedNone += storm(seed).play(null).saved();
        }
        assertTrue(savedDouse > savedNone);
    }

    @Test
    void theCrewHasAFewActionsATick_onlyNearTheHomestead() {
        BattlefieldEcology f = forest(1);
        FirelineWarden g = FirelineWarden.command(f, HOME, D);
        assertFalse(g.cut(c(0), c(0)), "out of reach");
        assertTrue(g.inReach(2, 12));
        assertFalse(g.inReach(1, 12));
        assertTrue(g.cut(c(9), c(14)));
        assertTrue(g.wet(c(10), c(14)));
        assertTrue(g.cut(c(11), c(14)));
        assertEquals(0, g.actionsLeft());
        assertFalse(g.cut(c(12), c(14)), "three actions a tick");
        g.tick();
        assertEquals(D.crew(), g.actionsLeft());
        assertTrue(g.cut(c(12), c(14)));
        assertTrue(g.cutAt(9, 14));
        assertEquals(Vegetation.BARE, f.vegetation(9, 14));
        assertTrue(g.wet(10, 14));
    }

    @Test
    void waterRunsOut_andTheCartRefillsItSlowly() {
        Settings small = new Settings(5, 6, 2, 1, 8, 0.6, 400);
        FirelineWarden g = FirelineWarden.command(forest(1), HOME, small);
        assertTrue(g.wet(c(8), c(13)));
        assertTrue(g.wet(c(9), c(13)));
        assertEquals(0, g.water());
        assertFalse(g.wet(c(10), c(13)), "tank empty");
        g.tick();
        assertEquals(1, g.water());
        g.tick();
        g.tick();
        g.tick();
        assertEquals(2, g.water(), "never above the tank");
    }

    @Test
    void aWetCellWillNotBurnWhileWet_thenDriesOut() {
        BattlefieldEcology f = new BattlefieldEcology(12, 12, 100, 0, 0, 9);
        for (int j = 0; j < 12; j++) {
            for (int i = 0; i < 12; i++) {
                f.set(i, j, Vegetation.SCRUB);
            }
        }
        Settings s = new Settings(3, 12, 24, 1, 3, 0.6, 400);
        FirelineWarden g = FirelineWarden.command(f, new Plot(10, 10, 11, 11), s).wind(1, 0);
        assertTrue(g.wet(c(6), c(6)));
        g.ignite(c(5), c(6), 0);
        assertFalse(g.cut(c(5), c(6)), "a burning cell cannot be cut");
        assertFalse(g.wet(c(5), c(6)), "or wetted");
        for (int t = 0; t < 3; t++) {
            g.tick();
            assertEquals(0, f.burning(6, 6), "wet, so it does not catch");
        }
        assertFalse(g.wet(6, 6), "dried out after wetTicks");
        assertEquals(Vegetation.SCRUB, f.vegetation(6, 6));
    }

    @Test
    void dousingNeedsFlames() {
        FirelineWarden g = FirelineWarden.command(forest(1), HOME, D);
        assertFalse(g.douse(c(9), c(14)), "nothing burning there");
        g.ignite(c(9), c(14), 0);
        assertTrue(g.douse(c(9), c(14)));
        assertEquals(0, g.burning());
        assertEquals(D.tank() - 1, g.water());
    }

    @Test
    void theFrontDistanceClosesAsTheFireComesDownwind() {
        FirelineWarden g = storm(2);
        int first = g.frontDistance();
        assertTrue(first > 0);
        int min = first;
        while (g.outcome() == Outcome.BURNING) {
            g.tick();
            if (g.frontDistance() >= 0) {
                min = Math.min(min, g.frontDistance());
            }
        }
        assertTrue(min < first);
        assertEquals(-1, FirelineWarden.command(forest(1), HOME, D).frontDistance());
    }

    @Test
    void sameSeedSameFire_andTheLostFireCannotTickOn() {
        assertEquals(storm(3).play(WET_RING), storm(3).play(WET_RING));
        FirelineWarden g = storm(1);
        Report r = g.play(null);
        assertEquals(Outcome.LOST, r.outcome());
        assertThrows(IllegalStateException.class, g::tick);
    }

    @Test
    void refusesBadInput() {
        assertThrows(IllegalArgumentException.class, () -> FirelineWarden.command(null, HOME, D));
        assertThrows(IllegalArgumentException.class, () -> FirelineWarden.command(forest(1), null, D));
        assertThrows(IllegalArgumentException.class, () -> FirelineWarden.command(forest(1), HOME, null));
        assertThrows(IllegalArgumentException.class,
                () -> FirelineWarden.command(forest(1), new Plot(18, 18, 20, 19), D));
        assertThrows(IllegalArgumentException.class, () -> new Plot(3, 3, 2, 3));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0, 6, 24, 1, 8, 0.6, 400));
        assertThrows(IllegalArgumentException.class, () -> new Settings(3, 6, 24, 1, 8, 1.5, 400));
        assertThrows(IndexOutOfBoundsException.class, () -> FirelineWarden.command(forest(1), HOME, D).wet(20, 0));
    }
}
