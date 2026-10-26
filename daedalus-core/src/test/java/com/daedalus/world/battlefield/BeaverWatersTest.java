// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.BeaverWaters.Outcome;
import com.daedalus.world.battlefield.BeaverWaters.Plot;
import com.daedalus.world.battlefield.BeaverWaters.Settings;
import org.junit.jupiter.api.Test;

class BeaverWatersTest {

    private static final int W = 16;
    private static final int H = 20;
    /** The homestead on the east slope above the valley floor. */
    private static final Plot HOME = new Plot(11, 5, 12, 6);
    /** The meadow on the valley floor the colony should flood. */
    private static final Plot TARGET = new Plot(7, 6, 9, 8);
    private static final Settings S = new Settings(40, 60, 1, 4, 0.75);

    /** A V valley running south: the floor at i = 8 falls 40 cm a cell toward the south edge, walls rise 30 cm a cell. */
    private static int[] valley() {
        int[] g = new int[W * H];
        for (int j = 0; j < H; j++) {
            for (int i = 0; i < W; i++) {
                g[j * W + i] = 1000 - 40 * j + 30 * Math.abs(i - 8);
            }
        }
        return g;
    }

    /** Meadow with a pine every third column (the beavers' timber). */
    private static BattlefieldEcology forest() {
        BattlefieldEcology f = new BattlefieldEcology(W, H, 100, 0, 0, 1);
        for (int j = 0; j < H; j++) {
            for (int i = 0; i < W; i++) {
                f.set(i, j, i % 3 == 0 ? Vegetation.PINE : Vegetation.MEADOW);
            }
        }
        return f;
    }

    private static BeaverWaters spring(BattlefieldEcology f, Settings s) {
        return BeaverWaters.spring(f, valley(), 8, 2, HOME, TARGET, s);
    }

    /** One layer on every cell of the dam line across the valley at row 10, from 8 - half to 8 + half. */
    private static void layer(BeaverWaters g, int half) {
        for (int i = 8 - half; i <= 8 + half; i++) {
            g.dam(i, 10);
        }
    }

    @Test
    void withoutADam_theStreamRunsDownTheValleyAndOffTheEdge() {
        BattlefieldEcology f = forest();
        BeaverWaters g = spring(f, S);
        assertEquals(Outcome.DRY, g.outcome());
        assertEquals(0, g.pondCells());
        assertEquals(H - 2, g.wetCells(), "spring at row 2 down to the edge row");
        for (int j = 2; j < H; j++) {
            assertTrue(g.water(8, j));
            assertEquals(Vegetation.WETLAND, f.vegetation(8, j));
        }
        assertFalse(g.water(8, 1), "water does not run uphill");
    }

    @Test
    void aDamBacksUpAPondBehindIt_neverBelowIt() {
        BeaverWaters g = spring(forest(), S);
        layer(g, 4);
        assertEquals(60, g.damCm(8, 10));
        assertTrue(g.pondCells() > 0);
        assertTrue(g.pond(8, 9));
        assertTrue(g.depthCm(8, 9) > 0);
        for (int j = 10; j < H; j++) {
            for (int i = 0; i < W; i++) {
                assertFalse(g.pond(i, j), "no pond at or below the dam: " + i + "," + j);
            }
        }
    }

    @Test
    void aShortDamStopsHelping_theWaterRunsAroundItsEnds() {
        BeaverWaters g = spring(forest(), S);
        layer(g, 3);
        layer(g, 3);
        layer(g, 3);
        int ponded = g.pondCells();
        layer(g, 3);
        assertEquals(ponded, g.pondCells(), "the extra layer is wasted");
        assertTrue(g.water(4, 10) || g.water(12, 10), "the overflow runs past the end of the dam");
        assertEquals(Outcome.DRY, g.outcome());
    }

    @Test
    void aWideEnoughDam_floodsTheTargetMeadow_andTheHomesteadStaysDry() {
        BeaverWaters g = spring(forest(), S);
        layer(g, 4);
        layer(g, 4);
        assertEquals(Outcome.DRY, g.outcome());
        layer(g, 4);
        assertEquals(Outcome.WET, g.outcome());
        assertTrue(g.targetWet() >= 0.75);
        assertFalse(g.homeFlooded());
    }

    @Test
    void overDammingDrownsTheHomestead_andABreachDrainsItBackToWetMeadow() {
        BattlefieldEcology f = forest();
        BeaverWaters g = spring(f, new Settings(400, 60, 0, 4, 0.75));
        int layers = 0;
        while (g.outcome() != Outcome.FLOODED && layers < 12) {
            layer(g, 7);
            layers++;
        }
        assertEquals(Outcome.FLOODED, g.outcome(), "after " + layers + " layers");
        boolean[] wetBefore = new boolean[W * H];
        for (int k = 0; k < W * H; k++) {
            wetBefore[k] = g.water(k % W, k / W);
        }
        for (int i = 1; i <= 15; i++) {
            assertTrue(g.breach(i, 10));
        }
        assertFalse(g.homeFlooded());
        int drained = 0;
        for (int k = 0; k < W * H; k++) {
            if (wetBefore[k] && !g.water(k % W, k / W)) {
                drained++;
                assertEquals(Vegetation.MEADOW, f.vegetation(k % W, k / W));
            }
        }
        assertTrue(drained > 0);
        assertFalse(g.breach(0, 0), "no dam there");
    }

    @Test
    void damsCostTimber_theNearestTreesAreFelledToMeadow() {
        BattlefieldEcology f = forest();
        BeaverWaters g = spring(f, S);
        assertEquals(Vegetation.PINE, f.vegetation(9, 9));
        assertTrue(g.dam(8, 10));
        assertEquals(1, g.felled());
        assertEquals(Vegetation.MEADOW, f.vegetation(9, 9), "nearest pine, lowest index on ties");
        assertEquals(Vegetation.PINE, f.vegetation(9, 10));

        BattlefieldEcology bare = new BattlefieldEcology(W, H, 100, 0, 0, 1);
        BeaverWaters none = spring(bare, S);
        assertFalse(none.dam(8, 10), "no timber within reach");
        assertEquals(0, none.damCm(8, 10));
    }

    @Test
    void theColonyCannotDamTheSpring_aPond_theHomestead_orPastItsBudget() {
        BeaverWaters g = spring(forest(), new Settings(4, 60, 0, 4, 0.75));
        assertFalse(g.dam(8, 2), "the spring");
        assertFalse(g.dam(11, 5), "the homestead");
        assertTrue(g.dam(8, 10), "a stream cell can be dammed");
        assertTrue(g.pond(8, 9));
        assertFalse(g.dam(8, 9), "a pond cell cannot");
        assertTrue(g.dam(7, 10));
        assertTrue(g.dam(9, 10));
        assertTrue(g.dam(6, 10));
        assertEquals(0, g.layersLeft());
        assertFalse(g.dam(10, 10), "four layers only");
    }

    @Test
    void theBeaverPondIsFireproofWetland_aFirebreakForTheFirelineWarden() {
        BattlefieldEcology f = forest();
        BeaverWaters g = spring(f, S);
        layer(g, 4);
        layer(g, 4);
        layer(g, 4);
        assertEquals(Vegetation.WETLAND, f.vegetation(8, 7));
        assertEquals(0.0, f.vegetation(8, 7).flammability());
        assertEquals(0, f.apply(BattlefieldEcology.EventKind.IGNITE, 850, 750, 0));
    }

    @Test
    void sameMovesSameWater() {
        BeaverWaters a = spring(forest(), S);
        BeaverWaters b = spring(forest(), S);
        for (int n = 0; n < 3; n++) {
            layer(a, 5);
            layer(b, 5);
        }
        for (int j = 0; j < H; j++) {
            for (int i = 0; i < W; i++) {
                assertEquals(a.water(i, j), b.water(i, j));
                assertEquals(a.depthCm(i, j), b.depthCm(i, j));
            }
        }
        assertEquals(a.felled(), b.felled());
    }

    @Test
    void refusesBadInput() {
        assertThrows(IllegalArgumentException.class, () -> BeaverWaters.spring(null, valley(), 8, 2, HOME, TARGET, S));
        assertThrows(IllegalArgumentException.class,
                () -> BeaverWaters.spring(forest(), new int[3], 8, 2, HOME, TARGET, S));
        assertThrows(IllegalArgumentException.class,
                () -> BeaverWaters.spring(forest(), valley(), 11, 5, HOME, TARGET, S));
        assertThrows(IllegalArgumentException.class,
                () -> BeaverWaters.spring(forest(), valley(), 8, 2, new Plot(15, 19, 16, 19), TARGET, S));
        assertThrows(IndexOutOfBoundsException.class,
                () -> BeaverWaters.spring(forest(), valley(), 16, 2, HOME, TARGET, S));
        assertThrows(IllegalArgumentException.class, () -> new Plot(2, 2, 1, 2));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1, 0, 1, 1, 0.5));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1, 60, 1, 1, 0));
    }
}
