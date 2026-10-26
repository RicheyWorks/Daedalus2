// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import com.daedalus.world.battlefield.BattlefieldEcology.EventKind;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The battlefield ecology against what a fight should feel: fire runs through grass and stops at water, a blast
 * leaves a bare crater that regrows meadow-scrub-pine-oak, forest is better cover than meadow, smoke hides, and the
 * whole thing replays exactly from its seed and events (ADR-061).
 */
class BattlefieldEcologyTest {

    private static BattlefieldEcology field(Vegetation v, int n) {
        BattlefieldEcology e = new BattlefieldEcology(n, n, 100, 0, 0, 42);
        for (int j = 0; j < n; j++) {
            for (int i = 0; i < n; i++) {
                e.set(i, j, v);
            }
        }
        return e;
    }

    @Test
    void fireRunsThroughMeadowAndBurnsOutToBare() {
        BattlefieldEcology e = field(Vegetation.MEADOW, 20);
        e.apply(EventKind.IGNITE, 1000, 1000, 50);
        for (int t = 0; t < 80; t++) {
            e.tick();
        }
        int[] c = e.census();
        assertThat(c[Vegetation.BARE.ordinal()]).isGreaterThan(200);
        assertThat(c[c.length - 1]).isZero();
    }

    @Test
    void wetlandIsAFirebreak() {
        BattlefieldEcology e = field(Vegetation.MEADOW, 21);
        for (int j = 0; j < 21; j++) {
            e.set(10, j, Vegetation.WETLAND);
        }
        e.apply(EventKind.IGNITE, 300, 1000, 150);
        for (int t = 0; t < 120; t++) {
            e.tick();
        }
        for (int j = 0; j < 21; j++) {
            assertThat(e.vegetation(10, j)).isEqualTo(Vegetation.WETLAND);
            for (int i = 11; i < 21; i++) {
                assertThat(e.vegetation(i, j)).as("east of the wetland %d,%d", i, j).isEqualTo(Vegetation.MEADOW);
            }
        }
    }

    @Test
    void oakBurnsFarLessThanMeadow() {
        BattlefieldEcology m = field(Vegetation.MEADOW, 30);
        BattlefieldEcology o = field(Vegetation.OAK, 30);
        for (BattlefieldEcology e : List.of(m, o)) {
            e.apply(EventKind.IGNITE, 1500, 1500, 50);
            for (int t = 0; t < 100; t++) {
                e.tick();
            }
        }
        assertThat(o.census()[Vegetation.BARE.ordinal()]).isLessThan(m.census()[Vegetation.BARE.ordinal()] / 4);
    }

    @Test
    void windCarriesFireDownwind() {
        BattlefieldEcology e = field(Vegetation.SCRUB, 41).wind(1, 0);
        e.apply(EventKind.IGNITE, 2050, 2050, 50);
        for (int t = 0; t < 12; t++) {
            e.tick();
        }
        int east = 0;
        int west = 0;
        for (int j = 0; j < 41; j++) {
            for (int i = 0; i < 41; i++) {
                boolean hit = e.burning(i, j) > 0 || e.vegetation(i, j) == Vegetation.BARE;
                if (hit && i > 20) east++;
                if (hit && i < 20) west++;
            }
        }
        assertThat(east).isGreaterThan(west);
    }

    @Test
    void blastLeavesACraterThatRegrowsUpTheLadder() {
        BattlefieldEcology e = field(Vegetation.OAK, 10);
        e.apply(EventKind.BLAST, 500, 500, 120);
        e.apply(EventKind.DOUSE, 500, 500, 1000);
        assertThat(e.at(500, 500)).isEqualTo(Vegetation.BARE);
        e.grow(3);
        assertThat(e.at(500, 500)).isEqualTo(Vegetation.MEADOW);
        e.grow(10);
        assertThat(e.at(500, 500)).isEqualTo(Vegetation.SCRUB);
        e.grow(50);
        assertThat(e.at(500, 500)).isEqualTo(Vegetation.OAK);
    }

    @Test
    void bestCoverPrefersTheWoodOverOpenGround() {
        BattlefieldEcology e = field(Vegetation.MEADOW, 20);
        for (int j = 0; j < 20; j++) {
            for (int i = 14; i < 17; i++) {
                e.set(i, j, Vegetation.OAK);
            }
        }
        double[] c = e.bestCover(1000, 1000, 0, 1000, 600);
        assertThat(e.at(c[0], c[1])).isEqualTo(Vegetation.OAK);
        e.apply(EventKind.IGNITE, 1550, 1050, 200);
        double[] c2 = e.bestCover(1000, 1000, 0, 1000, 600);
        assertThat(e.burningAt(c2[0], c2[1])).isFalse();
    }

    @Test
    void canopyAndSmokeConceal() {
        BattlefieldEcology open = field(Vegetation.BARE, 20);
        BattlefieldEcology wood = field(Vegetation.PINE, 20);
        assertThat(open.concealmentBetween(50, 50, 1950, 50)).isZero();
        assertThat(wood.concealmentBetween(50, 50, 1950, 50)).isGreaterThan(0.9);
        BattlefieldEcology smoky = field(Vegetation.MEADOW, 20);
        double before = smoky.concealmentBetween(50, 1050, 1950, 1050);
        smoky.apply(EventKind.IGNITE, 1000, 1050, 150);
        assertThat(smoky.concealmentBetween(50, 1050, 1950, 1050)).isGreaterThan(before);
    }

    @Test
    void replaysBitForBitFromSeedAndEvents() {
        String a = run(7);
        String b = run(7);
        assertThat(a).isEqualTo(b);
        assertThat(run(8)).isNotEqualTo(a);
    }

    private static String run(long seed) {
        BattlefieldEcology e = new BattlefieldEcology(30, 30, 100, 0, 0, seed).wind(0.3, -0.2);
        for (int i = 0; i < 30; i++) {
            e.set(i, 15, Vegetation.PINE);
        }
        e.apply(EventKind.BLAST, 1500, 1500, 250);
        for (int t = 0; t < 25; t++) {
            e.tick();
        }
        return Dbe.write(e);
    }

    @Test
    void dbeRoundTripsAndRefusesBadSpecs() {
        BattlefieldEcology e = field(Vegetation.SCRUB, 6);
        e.set(0, 0, Vegetation.WETLAND).set(5, 5, Vegetation.OAK);
        e.apply(EventKind.IGNITE, 250, 250, 60);
        e.tick();
        String s = Dbe.write(e);
        assertThat(Dbe.write(Dbe.read(s))).isEqualTo(s);
        assertThat(s).startsWith("DBE 1\ngrid 6 6 100 0 0 42\ntick 1\nrow 0 w");

        assertThatThrownBy(() -> Dbe.read("DBE 2\n")).hasMessageContaining("line 1");
        assertThatThrownBy(() -> Dbe.read("DBE 1\ngrid 2 2 100 0 0 1\ntick 0\nrow 0 mm\nrow 1 mx\n")).hasMessageContaining("line 5");
        assertThatThrownBy(() -> Dbe.read("DBE 1\ngrid 2 2 100 0 0 1\ntick 0\nrow 0 mm\nrow 1 m\n")).hasMessageContaining("width is 2");
        assertThatThrownBy(() -> Dbe.read("DBE 1\ngrid 2 2 100 0 0 1\ntick 0\nrow 1 mm\nrow 0 mm\n")).hasMessageContaining("in order");
        assertThatThrownBy(() -> Dbe.read("DBE 1\ngrid 2 2 100 0 0 1\ntick 0\nrow 0 ww\nrow 1 mm\nfire 0 0 3\n")).hasMessageContaining("cannot burn");
        assertThatThrownBy(() -> Dbe.read("DBE 1\ngrid 0 2 100 0 0 1\ntick 0\n")).hasMessageContaining("line 2");
    }

    @Test
    void eventsParseApplyAndAreBounded() {
        List<Dbe.Event> ev = Dbe.readEvents("DBE-E 1\nevent BLAST 500 500 0 150\nevent IGNITE 900 900 0 50\n");
        assertThat(ev).hasSize(2);
        BattlefieldEcology e = field(Vegetation.MEADOW, 12);
        assertThat(Dbe.apply(e, ev)).isPositive();
        assertThat(e.at(500, 500)).isEqualTo(Vegetation.BARE);
        assertThatThrownBy(() -> Dbe.readEvents("DBE-E 1\nevent NUKE 0 0 0 1\n")).hasMessageContaining("line 2");
        assertThatThrownBy(() -> Dbe.readEvents("DBE-E 1\nevent BLAST 0 0 0 -1\n")).hasMessageContaining("radius");
        StringBuilder many = new StringBuilder("DBE-E 1\n");
        for (int i = 0; i < 257; i++) {
            many.append("event DOUSE 0 0 0 1\n");
        }
        assertThatThrownBy(() -> Dbe.readEvents(many.toString())).hasMessageContaining("at most 256");
    }

    @Test
    void aBattlefieldTickStaysInsideAFrameBudget() {
        // 256x256 cells (25.6 m at 10 cm... here 100 cm cells = 256 m square) with an active fire front.
        BattlefieldEcology e = new BattlefieldEcology(256, 256, 100, 0, 0, 3);
        e.apply(EventKind.IGNITE, 12800, 12800, 3000);
        for (int t = 0; t < 5; t++) {
            e.tick();   // warm-up
        }
        long t0 = System.nanoTime();
        for (int t = 0; t < 20; t++) {
            e.tick();
        }
        double msPerTick = (System.nanoTime() - t0) / 20.0 / 1e6;
        // Java runs ecology off the frame path (ADR-060 rule); this only bounds it to well under a 1 s director tick.
        assertThat(msPerTick).isLessThan(50.0);
    }
}
