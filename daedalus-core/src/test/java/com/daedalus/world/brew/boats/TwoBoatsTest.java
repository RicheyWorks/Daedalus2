// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.boats;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.boats.TwoBoats.Boat;
import com.daedalus.world.brew.boats.TwoBoats.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class TwoBoatsTest {
    static int brute(List<Crate> crates) {
        int total = crates.stream().mapToInt(Crate::weight).sum();
        int best = Integer.MAX_VALUE;
        for (int mask = 0; mask < (1 << crates.size()); mask++) {
            int a = 0;
            for (int i = 0; i < crates.size(); i++) {
                if ((mask >> i & 1) == 1) {
                    a += crates.get(i).weight();
                }
            }
            best = Math.min(best, Math.abs(total - 2 * a));
        }
        return best;
    }

    static TwoBoats small() {
        return new TwoBoats(List.of(new Crate("flour", 8), new Crate("rope", 7), new Crate("salt", 6),
                new Crate("tar", 5), new Crate("nails", 4)));
    }

    @Test
    void seededLandfallIsDeterministic() {
        TwoBoats b = TwoBoats.seeded(7);
        assertTrue(b.cargo().size() >= 6 && b.cargo().size() <= 10);
        assertTrue(b.cargo().stream().allMatch(c -> c.weight() >= 1 && c.weight() <= 20));
        assertEquals(b.cargo(), TwoBoats.seeded(7).cargo());
        assertThrows(IllegalArgumentException.class, () -> new Crate("x", 0));
    }

    @Test
    void bestDifferenceMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TwoBoats b = TwoBoats.seeded(seed);
            assertTrue(b.cargo().size() <= 10, "brute force stays small");
            assertEquals(brute(b.cargo()), b.bestDifference(), "DP == true minimum, seed " + seed);
            int a = b.bestSplit().stream().mapToInt(Crate::weight).sum();
            assertEquals(b.bestDifference(), b.total() - 2 * a, "walk-back split achieves it, seed " + seed);
        }
    }

    @Test
    void greedyHeaviestFirstIsNotAlwaysBest() {
        // heaviest crate onto the lighter boat: 8|7, 8|13, 13|13, 17|13 -> 4 apart; the true best splits 30 as 15|15.
        TwoBoats b = small();
        assertEquals(0, b.bestDifference());
        assertEquals(15, b.bestSplit().stream().mapToInt(Crate::weight).sum());
    }

    @Test
    void anOddTotalCanNeverBeExactlyLevel() {
        TwoBoats b = new TwoBoats(List.of(new Crate("anvil", 9), new Crate("lamp", 2)));
        assertEquals(7, b.bestDifference(), "the anvil can't be cut in half");
        b.load("l1", "anvil", Boat.A);
        b.load("l2", "lamp", Boat.B);
        assertEquals(Outcome.LEVEL, b.cross("c1"), "best possible counts as level");
    }

    @Test
    void guards() {
        TwoBoats b = small();
        assertEquals(Outcome.IGNORED, b.load(" ", "rope", Boat.A));
        assertEquals(Outcome.UNKNOWN, b.load("e0", "gold", Boat.A));
        assertEquals(Outcome.ASHORE, b.cross("c0"));
        assertEquals(Outcome.LOADED, b.load("e1", "rope", Boat.A));
        assertEquals(Outcome.DUPLICATE, b.load("e1", "tar", Boat.A));
        assertEquals(Outcome.MOVED, b.load("e2", "rope", Boat.B));
        assertEquals(Outcome.NOT_LOADED, b.unload("e3", "tar"));
        assertEquals(Outcome.UNLOADED, b.unload("e4", "rope"));
        assertThrows(IllegalArgumentException.class,
                () -> new TwoBoats(List.of(new Crate("a", 1), new Crate("a", 2))));
        assertThrows(IllegalArgumentException.class, () -> new TwoBoats(List.of()));
    }

    @Test
    void questListingThenLevelThenKeeper() {
        TwoBoats b = small();
        assertEquals(KeeperBoatLines.GREETING, b.talk("t0"));
        b.load("l1", "flour", Boat.A);
        assertEquals("4 crates still on the sand. A carries 8, B carries 0.", KeeperBoatLines.line(b));
        b.load("l2", "salt", Boat.A);
        b.load("l3", "nails", Boat.A);
        b.load("l4", "rope", Boat.B);
        b.load("l5", "tar", Boat.B);
        assertEquals(KeeperBoatLines.READY, b.talk("t1"));
        assertEquals(Outcome.LISTING, b.cross("c1"));
        assertEquals(String.format(KeeperBoatLines.LISTING, 6, 0), b.talk("t2"));
        assertEquals("cross", b.quest().currentStep().type(), "no credit for a listing crossing");
        b.load("m1", "nails", Boat.B);
        b.load("m2", "salt", Boat.B);
        b.load("m3", "rope", Boat.A);
        assertEquals(15, b.weight(Boat.A));
        assertEquals(Outcome.LEVEL, b.cross("c2"));
        assertEquals(KeeperBoatLines.THANKS, b.talk("t3"));
        assertNull(b.quest().currentStep());
        assertEquals(KeeperBoatLines.DONE, b.talk("t4"));
    }
}
